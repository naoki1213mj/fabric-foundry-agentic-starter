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
2. SQL Specialist: Fabric SQLデータベースクエリ
3. Web Specialist: ウェブ検索（最新情報）
4. Doc Specialist: 企業ドキュメント検索

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
    The database contains tables like: SalesOrders, Products, Customers, etc.

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

## 利用可能なテーブル
- SalesOrders: 売上注文データ (OrderID, CustomerID, ProductID, Quantity, TotalAmount, OrderDate)
- Products: 製品データ (ProductID, ProductName, Category, Price)
- Customers: 顧客データ (CustomerID, CustomerName, Region, Segment)

## タスク
1. ユーザーの質問を分析し、適切なSQLクエリを作成
2. run_sql_query ツールを使ってクエリを実行
3. 結果を分かりやすく整形して報告

## よく使うクエリパターン
- 売上高が一番高い商品:
  SELECT TOP 1 p.ProductName, SUM(s.TotalAmount) as TotalSales
  FROM SalesOrders s JOIN Products p ON s.ProductID = p.ProductID
  GROUP BY p.ProductID, p.ProductName ORDER BY TotalSales DESC

- 地域別売上:
  SELECT c.Region, SUM(s.TotalAmount) as TotalSales
  FROM SalesOrders s JOIN Customers c ON s.CustomerID = c.CustomerID
  GROUP BY c.Region ORDER BY TotalSales DESC

## 注意事項
- T-SQL構文を使用してください
- 大量のデータには TOP や集計関数を使用
- 結果は表形式または要約形式で報告
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
        description="企業ドキュメント、製品仕様書、技術マニュアル、社内ナレッジを検索する専門家。注意：売上・注文・製品データの分析にはsql_agentを使用してください",
        instructions="""あなたは企業ドキュメントから情報を検索する専門家です。

## 重要：役割の明確化
- 売上データ、注文データ、製品データの「分析」はsql_agentの担当です
- あなたは「ドキュメント」「マニュアル」「仕様書」「ポリシー」の検索を担当します

## タスク
1. リクエストに基づいて適切な検索クエリを作成
2. search_documents ツールを使って情報を検索（1回の呼び出しで十分）
3. 結果を分かりやすくまとめて報告

## 対応範囲（これらの場合のみ検索）
- 製品仕様書とマニュアルの内容
- 技術ドキュメント
- 社内ナレッジベース記事
- 会社ポリシーと手順書

## 対応しない範囲（sql_agentに任せる）
- 売上高の計算・集計
- 注文データの分析
- 顧客データの分析
- 製品の売上ランキング

## 注意
- 検索は1回で十分です。同じ内容を複数回検索しないでください
- 検索結果がない場合は「関連ドキュメントが見つかりませんでした」と報告
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
- doc_agent: 企業ドキュメント、製品仕様、技術マニュアルを検索

## 重要：エージェント選択ルール

### sql_agent を使う場合（最優先）
- 「売上」「注文」「顧客」「製品」に関する数値分析
- 「一番」「トップ」「合計」「平均」などの集計質問
- 例：「売上高が一番高い商品は？」→ sql_agent
- 例：「地域別の売上は？」→ sql_agent
- 例：「今月の注文数は？」→ sql_agent

### web_agent を使う場合
- 「最新」「ニュース」「トレンド」「市場動向」
- 外部情報、競合情報

### doc_agent を使う場合
- 「マニュアル」「仕様書」「ポリシー」「手順」
- 社内ドキュメントの内容検索

## タスク処理フロー
1. **タスク分析**: ユーザーの質問を分析し、適切なエージェントを1つ選択
2. **シンプルな計画**: 多くの場合、1つのエージェントで回答可能
3. **実行**: 選択したエージェントに依頼
4. **回答**: エージェントの結果をそのまま、または整形して回答

## 重要な注意
- シンプルな質問は1つのエージェントで回答してください
- doc_agentを過剰に使用しないでください
- 数値データの質問は必ずsql_agentを使ってください
- 日本語で回答してください
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
                if hasattr(event, "plan"):
                    logger.info(f"Plan created: {event.plan}")

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

## 利用可能なテーブル
- SalesOrders: 売上注文データ
- Products: 製品データ
- Customers: 顧客データ

## タスク
1. ユーザーの質問を分析
2. 必要に応じてrun_sql_queryツールでデータを取得
3. 結果を分かりやすく整形して回答

## 回答形式
- データは表形式で見やすく表示
- Chart.js JSONはグラフが適切な場合に含める
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
    - Multi-agent mode: Uses HandoffBuilder with specialist agents
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
