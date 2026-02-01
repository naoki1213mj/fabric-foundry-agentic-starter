"""
Chat API module for handling chat interactions and responses.

Supports two modes:
- Single Agent Mode (default): Uses a single ChatAgent for all queries
- Multi Agent Mode (MULTI_AGENT_MODE=true): Uses MagenticBuilder for multi-agent orchestration
  - Manager Agent decomposes complex queries into subtasks
  - Specialist Agents execute subtasks in parallel when possible
  - Manager synthesizes final answer from all specialist responses

Architecture (MagenticBuilder - Magentic One Pattern):
1. Manager Agent: タスク分解、進捗管理、最終回答合成
2. SQL Specialist: Fabric SQLデータベースクエリ（売上、注文、顧客、製品分析）
3. Web Specialist: ウェブ検索（最新情報、市場トレンド）
4. Doc Specialist: 製品仕様書PDF検索（Azure AI Search）

Complex Query Flow:
User: "売上データを分析して、最新の市場トレンドと比較して"
→ Manager: Plan = [1. sql_agent: 売上分析, 2. web_agent: 市場トレンド取得]
→ Specialists: 並列実行
→ Manager: 結果を統合して最終回答生成
"""

import json
import logging
import os
import re
from typing import Annotated

from agent_framework import (
    AgentRunUpdateEvent,
    ChatAgent,
    GroupChatRequestSentEvent,
    MagenticBuilder,
    MagenticOrchestratorEvent,
    RequestInfoEvent,
    WorkflowOutputEvent,
    WorkflowStatusEvent,
    tool,
)
from agent_framework.azure import AzureOpenAIChatClient

# Local imports - tool handlers
from agents.web_agent import WebAgentHandler
from azure.identity import DefaultAzureCredential
from azure.monitor.events.extension import track_event
from azure.monitor.opentelemetry import configure_azure_monitor
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from knowledge_base_tool import KnowledgeBaseTool
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

load_dotenv()

# Multi-Agent Configuration
MULTI_AGENT_MODE = os.getenv("MULTI_AGENT_MODE", "false").lower() == "true"

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize tool handlers (singletons)
_web_agent_handler: WebAgentHandler | None = None
_knowledge_base_tool: KnowledgeBaseTool | None = None


def get_web_agent_handler() -> WebAgentHandler:
    """Get or create WebAgentHandler singleton."""
    global _web_agent_handler
    if _web_agent_handler is None:
        _web_agent_handler = WebAgentHandler()
    return _web_agent_handler


def get_knowledge_base_tool() -> KnowledgeBaseTool | None:
    """Get or create KnowledgeBaseTool singleton."""
    global _knowledge_base_tool
    if _knowledge_base_tool is None:
        _knowledge_base_tool = KnowledgeBaseTool.create_from_env()
    return _knowledge_base_tool


# Check if the Application Insights Instrumentation Key is set in the environment variables
instrumentation_key = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if instrumentation_key:
    configure_azure_monitor(connection_string=instrumentation_key)
    logging.info(
        "Application Insights configured with the provided Instrumentation Key"
    )
else:
    logging.warning(
        "No Application Insights Instrumentation Key found. Skipping configuration"
    )

# Suppress noisy loggers
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.WARNING
)
logging.getLogger("azure.identity.aio._internal").setLevel(logging.WARNING)
logging.getLogger("azure.monitor.opentelemetry.exporter.export._base").setLevel(
    logging.WARNING
)


def track_event_if_configured(event_name: str, event_data: dict):
    """Track event to Application Insights if configured."""
    instrumentation_key = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if instrumentation_key:
        track_event(event_name, event_data)


# ============================================================================
# Tool Functions with @tool decorator
# These tools are used by agents in the HandoffBuilder workflow
# ============================================================================

# Global database connection for tools
_db_connection = None


async def get_db_connection():
    """Get or create database connection for tools."""
    global _db_connection
    if _db_connection is None:
        from history_sql import get_fabric_db_connection

        _db_connection = await get_fabric_db_connection()
    return _db_connection


@tool(approval_mode="never_require")
async def run_sql_query(
    sql_query: Annotated[str, "The SQL query to execute against the Fabric database"],
) -> str:
    """Execute a SQL query against the Fabric SQL database and return results as JSON.

    Use this tool to query sales, orders, products, customers, and business data.

    Available tables:
    - orders: Order headers (OrderId, CustomerId, OrderDate, OrderStatus, OrderTotal, PaymentMethod)
    - orderline: Order details (OrderId, ProductId, Quantity, UnitPrice, LineTotal)
    - product: Products (ProductID, ProductName, CategoryName, ListPrice, BrandName)
    - customer: Customers (CustomerId, FirstName, LastName, CustomerTypeId)
    - location: Customer locations (LocationId, CustomerId, Region, City)
    - productcategory: Product categories (CategoryID, CategoryName)
    - customerrelationshiptype: Customer segments (CustomerRelationshipTypeId, CustomerRelationshipTypeName)
    - invoice: Invoices (InvoiceId, CustomerId, OrderId, TotalAmount)
    - payment: Payments (PaymentId, InvoiceId, PaymentAmount, PaymentStatus)

    Args:
        sql_query: The SQL query to execute. Use T-SQL syntax.

    Returns:
        JSON string with query results or error message.
    """
    from datetime import date, datetime
    from decimal import Decimal

    try:
        conn = await get_db_connection()
        if not conn:
            return json.dumps(
                {"error": "Database connection not available"}, ensure_ascii=False
            )

        cursor = conn.cursor()
        cursor.execute(sql_query)
        columns = [desc[0] for desc in cursor.description]
        result = []

        for row in cursor.fetchall():
            row_dict = {}
            for col_name, value in zip(columns, row):
                if isinstance(value, (datetime, date)):
                    row_dict[col_name] = value.isoformat()
                elif isinstance(value, Decimal):
                    row_dict[col_name] = float(value)
                else:
                    row_dict[col_name] = value
            result.append(row_dict)

        cursor.close()
        logger.info(f"SQL query executed successfully, returned {len(result)} rows")
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error executing SQL query: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool(approval_mode="never_require")
async def search_web(
    query: Annotated[str, "The search query for web information"],
) -> str:
    """Search the web for real-time information, news, and current events.

    Use this tool for:
    - Latest news and trends
    - Current market information
    - Weather updates
    - External data not in the database

    Args:
        query: The search query string.

    Returns:
        JSON string with search results or error message.
    """
    try:
        logger.info(f"Web search requested: {query}")
        web_agent = get_web_agent_handler()
        result = await web_agent.bing_grounding(query)
        logger.info(f"Web search completed for query: {query}")
        return result  # Already JSON string
    except Exception as e:
        logger.error(f"Error in web search: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool(approval_mode="never_require")
async def search_documents(
    query: Annotated[str, "The search query for enterprise documents"],
) -> str:
    """Search enterprise documents, product specifications, and knowledge base.

    IMPORTANT: For data analysis questions (sales, orders, customers, products),
    use run_sql_query instead. This tool is for documentation lookup only.

    Use this tool for:
    - Product specifications and manuals
    - Technical documentation
    - Internal knowledge base articles
    - Company policies and procedures

    Args:
        query: The search query string.

    Returns:
        JSON string with document search results (max 3 results, truncated).
    """
    try:
        logger.info(f"Document search requested: {query}")
        kb_tool = get_knowledge_base_tool()
        if kb_tool is None:
            return json.dumps(
                {
                    "message": "Document search is not configured. AI_SEARCH_* environment variables are missing.",
                    "query": query,
                    "results": [],
                },
                ensure_ascii=False,
            )
        result = await kb_tool.search(query)

        # Limit results to prevent token overflow
        if isinstance(result, dict) and "results" in result:
            result["results"] = result["results"][:3]  # Max 3 documents
            # Truncate long content
            for doc in result["results"]:
                if "content" in doc and len(doc["content"]) > 1000:
                    doc["content"] = doc["content"][:1000] + "...(truncated)"

        logger.info(f"Document search completed for query: {query}")
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in document search: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================================
# Multi-Agent Workflow using MagenticBuilder (Magentic One Pattern)
# ============================================================================


def create_specialist_agents(
    chat_client: AzureOpenAIChatClient,
) -> tuple[ChatAgent, ChatAgent, ChatAgent]:
    """Create specialist agents for MagenticBuilder workflow.

    MagenticBuilder の Manager が各スペシャリストを動的に選択・調整するため、
    トリアージエージェントは不要。Manager がその役割を担う。

    Args:
        chat_client: The AzureOpenAIChatClient to use for creating agents.

    Returns:
        Tuple of (sql_agent, web_agent, doc_agent)
    """
    # SQL specialist: Handles database queries
    sql_agent = ChatAgent(
        name="sql_agent",
        description="【優先】Fabric SQLデータベースでビジネスデータ（売上、注文、顧客、製品）を直接分析・集計する専門家。数値データの質問にはこのエージェントを最優先で使用",
        instructions="""あなたはFabric SQLデータベースを使ってビジネスデータを分析する専門家です。

## 重要：あなたは数値データ分析の最優先エージェントです
売上、注文、顧客、製品に関する質問は、まずあなたがSQLクエリで回答してください。

## 利用可能なテーブル（実際のスキーマ）

### 主要テーブル
- **orders**: 注文ヘッダー
  - OrderId, SalesChannelId, OrderNumber, CustomerId, CustomerAccountId
  - OrderDate, OrderStatus (Completed/Pending/Cancelled), SubTotal, TaxAmount, OrderTotal
  - PaymentMethod (MC/VISA/PayPal/Discover), IsoCurrencyCode, CreatedBy

- **orderline**: 注文明細（売上詳細）
  - OrderId, OrderLineNumber, ProductId, Quantity, UnitPrice, LineTotal, DiscountAmount, TaxAmount

- **product**: 製品マスタ
  - ProductID, ProductName, ProductDescription, BrandName, Color, ProductModel
  - ProductCategoryID, CategoryName, ListPrice, StandardCost, Weight, ProductStatus

- **productcategory**: 製品カテゴリ
  - CategoryID, ParentCategoryId, CategoryName, CategoryDescription, BrandName

- **customer**: 顧客マスタ
  - CustomerId, CustomerTypeId (Individual/Business/Government)
  - CustomerRelationshipTypeId, FirstName, LastName, Gender, PrimaryEmail, IsActive

- **customerrelationshiptype**: 顧客セグメント
  - CustomerRelationshipTypeId, CustomerRelationshipTypeName (VIP/Premium/Standard/SMB/Partner等)

- **location**: 顧客所在地
  - LocationId, CustomerId, AddressLine1, City, StateId, ZipCode, CountryId, Region, Latitude, Longitude

- **invoice**: 請求書
  - InvoiceId, InvoiceNumber, CustomerId, OrderId, InvoiceDate, DueDate, TotalAmount, InvoiceStatus

- **payment**: 支払い
  - PaymentId, PaymentNumber, InvoiceId, OrderId, PaymentDate, PaymentAmount, PaymentStatus, PaymentMethod

## タスク
1. ユーザーの質問を分析し、適切なSQLクエリを作成
2. run_sql_query ツールを使ってクエリを実行
3. 結果を分かりやすく整形して報告
4. グラフ表示が要求された場合は、Chart.js JSON形式で出力

## 重要なJOINパターン

### 売上分析（orders + orderline + product）
```sql
SELECT p.ProductName, SUM(ol.LineTotal) as TotalSales
FROM orders o
JOIN orderline ol ON o.OrderId = ol.OrderId
JOIN product p ON ol.ProductId = p.ProductID
WHERE o.OrderStatus = 'Completed'
GROUP BY p.ProductName
```

### 顧客別売上（orders + customer）
```sql
SELECT c.FirstName + ' ' + c.LastName as CustomerName, SUM(o.OrderTotal) as TotalSpent
FROM orders o
JOIN customer c ON o.CustomerId = c.CustomerId
GROUP BY c.CustomerId, c.FirstName, c.LastName
```

### 地域別売上（orders + customer + location）
```sql
SELECT l.Region, SUM(o.OrderTotal) as TotalSales
FROM orders o
JOIN customer c ON o.CustomerId = c.CustomerId
JOIN location l ON c.CustomerId = l.CustomerId
GROUP BY l.Region
```

## よく使うクエリパターン

### 売上TOP N製品
```sql
SELECT TOP {N} p.ProductName, SUM(ol.LineTotal) as TotalSales
FROM orders o
JOIN orderline ol ON o.OrderId = ol.OrderId
JOIN product p ON ol.ProductId = p.ProductID
WHERE o.OrderStatus = 'Completed'
GROUP BY p.ProductID, p.ProductName
ORDER BY TotalSales DESC
```

### カテゴリ別売上
```sql
SELECT p.CategoryName, SUM(ol.LineTotal) as TotalSales
FROM orders o
JOIN orderline ol ON o.OrderId = ol.OrderId
JOIN product p ON ol.ProductId = p.ProductID
WHERE o.OrderStatus = 'Completed'
GROUP BY p.CategoryName
ORDER BY TotalSales DESC
```

### 月別売上推移
```sql
SELECT FORMAT(o.OrderDate, 'yyyy-MM') as Month, SUM(o.OrderTotal) as Sales
FROM orders o
WHERE o.OrderStatus = 'Completed'
GROUP BY FORMAT(o.OrderDate, 'yyyy-MM')
ORDER BY Month
```

### 支払い方法別売上
```sql
SELECT o.PaymentMethod, SUM(o.OrderTotal) as TotalSales, COUNT(*) as OrderCount
FROM orders o
WHERE o.OrderStatus = 'Completed'
GROUP BY o.PaymentMethod
ORDER BY TotalSales DESC
```

### 顧客セグメント別売上
```sql
SELECT crt.CustomerRelationshipTypeName as Segment, SUM(o.OrderTotal) as TotalSales
FROM orders o
JOIN customer c ON o.CustomerId = c.CustomerId
JOIN customerrelationshiptype crt ON c.CustomerRelationshipTypeId = crt.CustomerRelationshipTypeId
WHERE o.OrderStatus = 'Completed'
GROUP BY crt.CustomerRelationshipTypeName
ORDER BY TotalSales DESC
```

## グラフ出力（重要）
ユーザーが「グラフ」「チャート」「可視化」「表示して」「見せて」などを要求した場合、
必ず以下のChart.js JSON形式で出力してください（Vega-Liteは使用禁止）:

```json
{
  "type": "bar",
  "data": {
    "labels": ["ラベル1", "ラベル2", "ラベル3"],
    "datasets": [{
      "label": "データセット名",
      "data": [100, 200, 300],
      "backgroundColor": ["#4e79a7", "#f28e2c", "#e15759", "#76b7b2", "#59a14f"]
    }]
  },
  "options": {
    "responsive": true,
    "plugins": {
      "title": { "display": true, "text": "グラフタイトル" }
    }
  }
}
```

### グラフの種類と選択基準
- 棒グラフ("bar"): カテゴリ比較、ランキング
- 横棒グラフ("horizontalBar"): 長いラベル名、多カテゴリ
- 円グラフ("pie"): 構成比、割合（5項目以下推奨）
- ドーナツ("doughnut"): 構成比（中央にサマリー表示可能）
- 折れ線("line"): 時系列、トレンド、推移

## 注意事項
- T-SQL構文を使用してください
- 大量のデータには TOP や集計関数を使用
- OrderStatus = 'Completed' で完了した注文のみをフィルタ
- グラフなしの場合は表形式または要約形式で報告
- グラフ要求時は必ずChart.js JSON形式（Vega-Lite禁止）
- ユーザーの意図を汲み取り、最適なクエリとグラフ形式を選択
""",
        chat_client=chat_client,
        tools=[run_sql_query],
    )

    # Web specialist: Handles web searches
    web_agent = ChatAgent(
        name="web_agent",
        description="ウェブ検索で最新のニュース、市場トレンド、外部情報を取得する専門家",
        instructions="""あなたはウェブ検索を使って最新情報を取得する専門家です。

## タスク
1. リクエストに基づいて適切な検索クエリを作成
2. search_web ツールを使って情報を検索
3. 結果を分かりやすくまとめて報告

## 対応範囲
- 最新ニュースとトレンド
- 市場動向と業界情報
- 競合分析
- その他の外部情報
""",
        chat_client=chat_client,
        tools=[search_web],
    )

    # Document specialist: Handles document searches
    doc_agent = ChatAgent(
        name="doc_agent",
        description="製品仕様書（PDF）を検索する専門家。製品の詳細スペック、機能、技術仕様を調べる場合に使用。注意：売上・注文データの分析にはsql_agentを使用",
        instructions="""あなたはAzure AI Searchを使って製品仕様書PDFから情報を検索する専門家です。

## 重要：役割の明確化
- 売上データ、注文データの「分析」「集計」はsql_agentの担当です
- あなたは「製品仕様書」「技術スペック」「機能説明」の検索を担当します

## 検索対象：製品仕様書PDF（SharePoint → Azure AI Search）

### 利用可能な製品仕様書カテゴリ
1. **バックパック (Backpacks)**
   - Adventurer Pro, SummitClimber

2. **自転車フレーム・パーツ (Bike Parts)**
   - Mountain-100 Silver, Mountain-300 Black
   - Road-150 Red, Road-250 Black
   - Forks (HL, LL)
   - Bike Stands (All Purpose)

3. **ヘルメット (Helmets)**
   - Sport-100 Helmet (Black, Red)

4. **ジャージ (Jerseys)**
   - Long-Sleeve Logo Jersey (S, M)

5. **キャンプ用品 (Camping)**
   - Tents: Alpine Explorer, TrailMaster X4
   - Camping Tables: Adventure Dining, BaseCamp

6. **キッチン用品**
   - Coffee Makers: Drip, Espresso

## タスク
1. ユーザーの質問から製品名やカテゴリを特定
2. search_documents ツールで製品仕様書を検索
3. 仕様書の内容を分かりやすくまとめて報告

## 検索クエリのコツ
- 製品名で検索: "Mountain-100", "Sport-100 Helmet"
- カテゴリで検索: "Backpack", "Tent", "Coffee Maker"
- 機能で検索: "weight", "material", "dimensions", "capacity"
- 日本語でも検索可能: "バックパック 容量", "テント 防水"

## 回答に含めるべき情報（仕様書にある場合）
- 製品名と型番
- 主要スペック（サイズ、重量、素材など）
- 主な機能・特徴
- 使用シーン・推奨用途

## 対応しない範囲（sql_agentに任せる）
- 「この製品の売上は？」→ sql_agent
- 「一番売れている製品は？」→ sql_agent
- 「顧客の購入履歴」→ sql_agent

## 注意
- 検索は1回で十分です。同じ内容を複数回検索しないでください
- 検索結果がない場合は「該当する製品仕様書が見つかりませんでした」と報告
- 仕様書の内容を引用する際は出典を明記
""",
        chat_client=chat_client,
        tools=[search_documents],
    )

    return sql_agent, web_agent, doc_agent


def create_manager_agent(chat_client: AzureOpenAIChatClient) -> ChatAgent:
    """Create the manager agent for MagenticBuilder orchestration.

    Manager Agent の役割:
    1. 複雑なクエリをサブタスクに分解（Plan）
    2. 各スペシャリストへのタスク割り当て
    3. 進捗の監視と必要に応じた再計画
    4. 全スペシャリストの結果を統合して最終回答を生成

    Args:
        chat_client: The AzureOpenAIChatClient to use.

    Returns:
        Manager ChatAgent
    """
    return ChatAgent(
        name="MagenticManager",
        description="チームを調整して複雑なタスクを効率的に完了させるオーケストレーター",
        instructions="""あなたはMagentic Oneのマネージャーエージェントです。
チームを調整して複雑なタスクを効率的に完了させます。

## あなたのチーム
- sql_agent:【最優先】Fabric SQLデータベースでビジネスデータ（売上、注文、顧客、製品）を直接分析
- web_agent: ウェブ検索で最新のニュース、市場トレンド、外部情報を取得
- doc_agent: 製品仕様書PDFから技術スペック・機能情報を検索（対象：バックパック、自転車、ヘルメット、テント、キャンプ用品等）

## クエリ解析と意図理解

### ステップ1: ユーザーの意図を理解
ユーザーのクエリから以下を特定:
1. **何を知りたいか** - 数値、情報、手順など
2. **どのデータが必要か** - 売上データ、外部情報、社内文書など
3. **どう表示したいか** - テキスト、表、グラフなど

### ステップ2: 適切なエージェント選択

#### sql_agent を使う場合（最優先 - データ分析全般）
キーワード例:
- 数値系: 「売上」「注文」「顧客」「製品」「金額」「数量」「件数」
- 集計系: 「合計」「平均」「最大」「最小」「一番」「TOP」「ランキング」
- 比較系: 「比較」「前月比」「前年比」「成長」「推移」「トレンド」
- 分析系: 「内訳」「構成比」「割合」「分布」「相関」
- 可視化: 「グラフ」「チャート」「棒グラフ」「円グラフ」「折れ線」「表示して」「見せて」

#### web_agent を使う場合
キーワード例:
- 「最新」「ニュース」「トレンド」「市場動向」「業界」「競合」
- 「外部」「インターネット」「ウェブ」

#### doc_agent を使う場合
キーワード例:
- 「仕様」「スペック」「機能」「素材」「重量」「サイズ」
- 製品名: 「Mountain-100」「Sport-100 Helmet」「Alpine Explorer」
- カテゴリ: 「バックパック」「テント」「ヘルメット」「コーヒーメーカー」

### ステップ3: 複合クエリの処理
複数のデータソースが必要な場合:
1. まず優先度の高いエージェントから実行
2. 結果を統合して回答

例: 「売上データを分析して、最新の市場トレンドと比較」
→ sql_agent で売上分析 → web_agent で市場トレンド取得 → 統合

## グラフ出力形式（重要）
グラフ表示が要求された場合、必ずChart.js JSON形式で出力。
Vega-Lite形式は使用禁止です。

```json
{
  "type": "bar",
  "data": {
    "labels": ["製品A", "製品B", "製品C"],
    "datasets": [{
      "label": "売上金額",
      "data": [100000, 80000, 60000],
      "backgroundColor": ["#4e79a7", "#f28e2c", "#e15759"]
    }]
  },
  "options": {
    "responsive": true,
    "plugins": {
      "title": { "display": true, "text": "売上TOP3" }
    }
  }
}
```

## 重要な注意
- シンプルな質問は1つのエージェントで回答
- 数値データの質問は必ずsql_agentを最初に使用
- グラフ要求時はChart.js JSON形式（Vega-Lite禁止）
- 日本語で回答
- ユーザーの意図を汲み取り、最適な回答形式を選択
""",
        chat_client=chat_client,
    )


async def stream_multi_agent_response(conversation_id: str, query: str):
    """
    Stream response using MagenticBuilder pattern for true multi-agent collaboration.

    MagenticBuilder (Magentic One Pattern):
    - Manager Agent がタスクを分解し、計画を作成
    - 複数のスペシャリストが並列または順次実行
    - Manager が結果を統合して最終回答を生成

    これにより、複合的なクエリ（例：「売上データを分析して、最新トレンドと比較」）に対応可能。
    """
    try:
        # Use sync credential - SDK requires synchronous token acquisition
        credential = DefaultAzureCredential()

        # Get Azure OpenAI configuration from environment variables
        # SDK 1.0.0b260130 requires explicit deployment_name and endpoint
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_MODEL") or os.getenv(
            "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
        )
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

        logger.info(
            f"Azure OpenAI config: deployment={deployment_name}, endpoint={endpoint}"
        )

        if not deployment_name:
            raise ValueError(
                "Azure OpenAI deployment name is required. "
                "Set AZURE_OPENAI_DEPLOYMENT_MODEL or AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
            )
        if not endpoint:
            raise ValueError(
                "Azure OpenAI endpoint is required. Set AZURE_OPENAI_ENDPOINT"
            )

        # Create chat client with explicit configuration
        chat_client = AzureOpenAIChatClient(
            credential=credential,
            deployment_name=deployment_name,
            endpoint=endpoint,
            api_version=api_version,
        )

        # Create specialist agents
        sql_agent, web_agent, doc_agent = create_specialist_agents(chat_client)

        # Create manager agent
        manager_agent = create_manager_agent(chat_client)

        # Build the MagenticBuilder workflow
        workflow = (
            MagenticBuilder()
            .participants([sql_agent, web_agent, doc_agent])
            .with_manager(
                agent=manager_agent,
                max_round_count=10,  # 最大ラウンド数
                max_stall_count=3,  # ストール検出閾値
            )
            .build()
        )

        logger.info(f"Starting MagenticBuilder workflow with query: {query[:100]}...")
        logger.info("Workflow configured with Manager + 3 Specialists (SQL, Web, Doc)")

        last_message_id: str | None = None
        accumulated_text = ""

        # Stream the workflow execution
        async for event in workflow.run_stream(query):
            if isinstance(event, AgentRunUpdateEvent):
                # ストリーミング更新 - エージェントからのテキスト出力
                update = event.data
                message_id = getattr(update, "message_id", None)

                # 新しいメッセージの場合、区切りを追加
                if message_id and message_id != last_message_id:
                    if last_message_id is not None and accumulated_text:
                        logger.info(f"Agent {event.executor_id} completed response")
                    last_message_id = message_id

                # テキストを出力
                if hasattr(update, "text") and update.text:
                    accumulated_text += update.text
                    yield update.text
                elif isinstance(update, str):
                    accumulated_text += update
                    yield update

            elif isinstance(event, MagenticOrchestratorEvent):
                # Magentic オーケストレーターイベント（計画、進捗など）
                logger.info(f"Orchestrator event: {type(event).__name__}")
                # SDK version によって属性が異なる可能性があるため安全にアクセス
                plan = getattr(event, "plan", None)
                if plan:
                    logger.info(f"Plan created: {plan}")

            elif isinstance(event, WorkflowOutputEvent):
                # ワークフロー完了時の最終出力
                if event.data:
                    output_messages = event.data
                    if isinstance(output_messages, list):
                        for msg in output_messages:
                            if hasattr(msg, "text") and msg.text:
                                # 最終回答が既に蓄積されたテキストと異なる場合のみ出力
                                if msg.text not in accumulated_text:
                                    yield msg.text
                    elif isinstance(output_messages, str):
                        if output_messages not in accumulated_text:
                            yield output_messages
                logger.info("MagenticBuilder workflow completed")

            elif isinstance(event, WorkflowStatusEvent):
                # SDK 1.0.0b260130: WorkflowRunState enum values may differ
                state_name = (
                    str(event.state.name)
                    if hasattr(event.state, "name")
                    else str(event.state)
                )
                logger.info(f"Workflow status: {state_name}")

            elif isinstance(event, GroupChatRequestSentEvent):
                # グループチャットリクエスト（Manager → Specialist）
                logger.info(f"Request sent to: {getattr(event, 'target', 'unknown')}")

            elif isinstance(event, RequestInfoEvent):
                logger.info(f"Request info event: {event}")

    except Exception as e:
        logger.error(f"Error in MagenticBuilder workflow: {e}", exc_info=True)
        raise
    finally:
        global _db_connection
        if _db_connection:
            try:
                _db_connection.close()
            except Exception:
                pass
            _db_connection = None


async def stream_single_agent_response(conversation_id: str, query: str):
    """
    Stream response using single agent mode with AzureOpenAIChatClient.
    """
    try:
        # Use sync credential - SDK requires synchronous token acquisition
        credential = DefaultAzureCredential()

        # Get Azure OpenAI configuration from environment variables
        # SDK 1.0.0b260130 requires explicit deployment_name and endpoint
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_MODEL") or os.getenv(
            "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
        )
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

        logger.info(
            f"Azure OpenAI config: deployment={deployment_name}, endpoint={endpoint}"
        )

        if not deployment_name:
            raise ValueError(
                "Azure OpenAI deployment name is required. "
                "Set AZURE_OPENAI_DEPLOYMENT_MODEL or AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
            )
        if not endpoint:
            raise ValueError(
                "Azure OpenAI endpoint is required. Set AZURE_OPENAI_ENDPOINT"
            )

        # Create chat client with explicit configuration
        chat_client = AzureOpenAIChatClient(
            credential=credential,
            deployment_name=deployment_name,
            endpoint=endpoint,
            api_version=api_version,
        )

        # Create a single agent with SQL tool
        agent = chat_client.as_agent(
            name="data_analyst",
            instructions="""あなたはFabric SQLデータベースを使ってビジネスデータを分析するアシスタントです。

## 利用可能なテーブル（実際のスキーマ）
- orders: 注文ヘッダー (OrderId, CustomerId, OrderDate, OrderStatus, OrderTotal, PaymentMethod)
- orderline: 注文明細 (OrderId, ProductId, Quantity, UnitPrice, LineTotal)
- product: 製品 (ProductID, ProductName, CategoryName, ListPrice, BrandName, Color, ProductCategoryID)
- productcategory: カテゴリ (CategoryID, CategoryName, ParentCategoryId)
- customer: 顧客 (CustomerId, FirstName, LastName, CustomerTypeId, CustomerRelationshipTypeId)
- customerrelationshiptype: 顧客セグメント (CustomerRelationshipTypeId, CustomerRelationshipTypeName)
- location: 所在地 (LocationId, CustomerId, Region, City, StateId)
- invoice: 請求書 (InvoiceId, CustomerId, OrderId, TotalAmount, InvoiceStatus)
- payment: 支払い (PaymentId, InvoiceId, PaymentAmount, PaymentStatus, PaymentMethod)

## 主要なJOINパターン
- 売上分析: orders JOIN orderline ON OrderId JOIN product ON ProductId
- 顧客分析: orders JOIN customer ON CustomerId
- 地域分析: customer JOIN location ON CustomerId
- セグメント分析: customer JOIN customerrelationshiptype ON CustomerRelationshipTypeId

## タスク
1. ユーザーの質問を分析
2. 必要に応じてrun_sql_queryツールでデータを取得
3. 結果を分かりやすく整形して回答

## 回答形式
- データは表形式で見やすく表示
- Chart.js JSONはグラフが適切な場合に含める（Vega-Lite禁止）
""",
            tools=[run_sql_query],
        )

        logger.info(f"Single agent mode: processing query: {query[:100]}...")

        # Stream the agent response
        async for chunk in agent.run_stream(query):
            if chunk and chunk.text:
                yield chunk.text

    except Exception as e:
        logger.error(f"Error in single agent response: {e}", exc_info=True)
        raise
    finally:
        global _db_connection
        if _db_connection:
            try:
                _db_connection.close()
            except Exception:
                pass
            _db_connection = None


# ============================================================================
# Chat API Endpoint
# ============================================================================


async def stream_chat_request(conversation_id: str, query: str):
    """
    Handles streaming chat requests.

    Routes to:
    - Multi-agent mode: Uses MagenticBuilder with Manager + Specialist agents
    - Single-agent mode: Direct ChatAgent with SQL tools
    """

    async def generate():
        try:
            assistant_content = ""

            # Choose streaming function based on mode
            if MULTI_AGENT_MODE:
                logger.info("Using multi-agent mode with HandoffBuilder")
                stream_func = stream_multi_agent_response
            else:
                logger.info("Using single-agent mode")
                stream_func = stream_single_agent_response

            # Stream and accumulate response
            async for chunk in stream_func(conversation_id, query):
                if chunk:
                    assistant_content += str(chunk)
                    response = {
                        "choices": [
                            {
                                "messages": [
                                    {
                                        "role": "assistant",
                                        "content": assistant_content,
                                    }
                                ]
                            }
                        ]
                    }
                    yield json.dumps(response, ensure_ascii=False) + "\n\n"

            # Fallback if no response
            if not assistant_content:
                logger.info("No response received")
                response = {
                    "choices": [
                        {
                            "messages": [
                                {
                                    "role": "assistant",
                                    "content": "申し訳ございませんが、この質問にはお答えできません。質問を変えてお試しください。",
                                }
                            ]
                        }
                    ]
                }
                yield json.dumps(response, ensure_ascii=False) + "\n\n"

        except Exception as e:
            error_message = str(e)
            if "Rate limit" in error_message:
                match = re.search(r"Try again in (\d+) seconds.", error_message)
                retry_after = match.group(1) if match else "sometime"
                logger.error(f"Rate limit error: {error_message}")
                yield (
                    json.dumps(
                        {
                            "error": f"Rate limit is exceeded. Try again in {retry_after} seconds."
                        }
                    )
                    + "\n\n"
                )
            else:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                yield (
                    json.dumps(
                        {"error": "An error occurred while processing the request."}
                    )
                    + "\n\n"
                )

    return generate()


@router.post("/chat")
async def conversation(request: Request):
    """Handle chat requests - streaming text or chart generation based on query keywords."""
    try:
        request_json = await request.json()
        conversation_id = request_json.get("conversation_id")
        query = request_json.get("query")

        if not query:
            return JSONResponse(content={"error": "Query is required"}, status_code=400)

        if not conversation_id:
            return JSONResponse(
                content={"error": "Conversation ID is required"}, status_code=400
            )

        result = await stream_chat_request(conversation_id, query)
        track_event_if_configured(
            "ChatStreamSuccess", {"conversation_id": conversation_id, "query": query}
        )
        return StreamingResponse(result, media_type="application/json-lines")

    except Exception as ex:
        logger.exception(f"Error in conversation endpoint: {str(ex)}")
        span = trace.get_current_span()
        if span is not None:
            span.record_exception(ex)
            span.set_status(Status(StatusCode.ERROR, str(ex)))
        return JSONResponse(
            content={
                "error": "An internal error occurred while processing the conversation."
            },
            status_code=500,
        )
