# Agentic AI PoC Starter Kit - Fabric + Foundry Configuration

> **Mission**: Microsoft Fabric + Foundry + Agent Framework を活用した Agentic AI の PoC を即座に開始できるリファレンスアーキテクチャ＆デモ環境を提供する
>
> **用途**: PoC スターターキット / リファレンスアーキテクチャ / デモ環境
>
> **Base**: [microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator](https://github.com/microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator)
>
> **Last Updated**: 2026/2/7

---

## 📝 開発ログ運用（必須）

**セッション開始時**:
1. `.dev-logs/project-understanding.md` を読んでプロジェクト全体を把握
2. `.dev-logs/sessions/` の最新ログを読んで直近の作業を確認

**セッション終了時**:
1. `.dev-logs/sessions/YYYY-MM-DD_session-name.md` にログを保存
2. 重要な変更があれば `project-understanding.md` を更新

詳細は AGENTS.md の「開発ログ運用ルール」セクションを参照。

---

## 📊 サービス状態（2026年2月時点）

| サービス | 状態 | 備考 |
|----------|------|------|
| **Microsoft Agent Framework** | Public Preview | GA予定: 2026年Q1 |
| **Foundry Agent Service** | GA | 2025年5月〜 |
| **Hosted Agents** | GA | azd deploy対応 |
| **Foundry Guardrails** | Public Preview | Task Adherence, Prompt Shields, PII |
| **Foundry IQ (Agentic Retrieval)** | GA | Knowledge Base + Reasoning Effort |
| **SQL Database in Fabric** | GA | 2025年11月〜 |
| **OneLake Security** | Preview | RLS/CLS対応 |
| **Web Search tool** | Public Preview | Bing Groundingの後継（gpt-5対応） |

---

## 🏛️ Azure Cloud Adoption Framework (CAF) 準拠

### 命名規則

```
{resource-type}-{workload}-{environment}[-{region}][-{instance}]

Solution Accelerator 構成例:
├── rg-aiagent-prod-jpe                    # リソースグループ
├── ai-aiagent-prod-jpe                    # Microsoft Foundry
├── oai-aiagent-prod-jpe                   # Azure OpenAI
├── app-aiagent-api-prod-jpe               # App Service (API)
├── app-aiagent-web-prod-jpe               # App Service (Frontend)
├── func-aiagent-mcp-prod-jpe              # Functions (MCP Server)
├── acr-aiagent-prod-jpe                   # Container Registry
├── apim-aiagent-prod-jpe                  # API Management
├── fabric-aiagent-prod                    # Fabric Workspace
├── sqldb-aiagent-prod                     # SQL Database in Fabric
├── log-aiagent-prod-jpe                   # Log Analytics
├── appi-aiagent-prod-jpe                  # Application Insights
└── kv-aiagent-prod-jpe                    # Key Vault
```

### CAF標準リソース略称

| サービス | 略称 | 用途 |
|----------|------|------|
| Microsoft Foundry | ai | AI基盤・エージェント管理 |
| Azure OpenAI | oai | LLM (GPT-5, GPT-4o-mini) |
| App Service | app | API / Frontend ホスティング |
| Functions | func | MCP Server |
| API Management | apim | AI Gateway |
| Container Registry | acr | コンテナイメージ管理 |
| Fabric Workspace | fabric | データ統合基盤 |
| SQL Database (Fabric) | sqldb | 構造化データ |
| Log Analytics | log | ログ収集・分析 |
| Application Insights | appi | APM・分散トレーシング |

### 必須タグ

```bicep
var tags = {
  workload: 'aiagent'
  environment: 'prod'
  costCenter: 'CC-POC'
  owner: 'team-ai@contoso.com'
  architecture: 'fabric-foundry'
  solutionAccelerator: 'unified-data-foundation'
  dataClassification: 'confidential'
}
```

---

## 🎯 PoC 提案時の訴求ポイント

| 訴求点 | 説明 | 技術要素 |
|--------|------|----------|
| **Why Microsoft** | 統合データ基盤 + AI を一気通貫で提供 | Fabric + Foundry + Agent Framework |
| **Why Now** | Agentic AI が GA 水準に到達 | Agent Framework GA + Foundry Agent Service |
| **即時 PoC 開始** | azd up 一発でエンドツーエンド環境が立ち上がる | Bicep IaC + GitHub Actions |
| **業界カスタマイズ** | 様々な業界シナリオに容易に横展開可能 | プロンプト・スキーマ・ツール差替え |
| **エンタープライズ Ready** | セキュリティ・ガバナンス・可観測性を内蔵 | Guardrails + APIM + App Insights |

---

## 🏗️ Solution Accelerator アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Client Layer                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Azure App Service - Frontend (app-daj6dri4yf3k3z)                   │    │
│  │ ├─ React + TypeScript                                               │    │
│  │ ├─ Natural Language Query Interface                                 │    │
│  │ ├─ Agent Mode Selector (sql_only/multi_tool/handoff/magentic)      │    │
│  │ ├─ Doc Search Reasoning Effort (minimal/low/medium)                │    │
│  │ └─ Built-in Auth (Entra ID EasyAuth)                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ HTTPS
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                          API Layer                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Azure App Service - API (api-daj6dri4yf3k3z)                        │    │
│  │ ├─ Python FastAPI + Microsoft Agent Framework                       │    │
│  │ ├─ AzureOpenAIResponsesClient (sql_only, multi_tool)               │    │
│  │ ├─ AzureOpenAIChatClient (handoff, magentic - SDK制約)             │    │
│  │ ├─ REST API: /api/chat, /api/conversations, /health                │    │
│  │ └─ Tool Invocation / MCP Integration                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Azure API Management (apim-daj6dri4yf3k3z) - AI Gateway             │    │
│  │ ├─ /openai → Azure OpenAI (legacy)                                 │    │
│  │ ├─ /foundry-openai/openai/v1/ → Foundry AI Services ★ Primary     │    │
│  │ ├─ /mcp → MCP Server (func-mcp-*)                                  │    │
│  │ ├─ /foundry-agents → Foundry Agent Service                         │    │
│  │ ├─ Circuit Breaker: 429/500-599 → 30s trip                         │    │
│  │ ├─ Token Headers: x-openai-{prompt,completion,total}-tokens        │    │
│  │ └─ Managed Identity Authentication                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Azure API Center (apic-daj6dri4yf3k3z) - Tool Catalog               │    │
│  │ ├─ Business Analytics MCP Server (16 tools / 4 categories)          │    │
│  │ │   ├─ 売上分析 (5): calculate_yoy_growth 等                       │    │
│  │ │   ├─ 顧客分析 (4): calculate_rfm_score 等                       │    │
│  │ │   ├─ 在庫分析 (3): calculate_inventory_turnover 等               │    │
│  │ │   └─ 製品比較 (4): compare_products 等                           │    │
│  │ └─ Azure OpenAI API                                                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                       AI / Agent Layer                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Microsoft Foundry (aisa-daj6dri4yf3k3z / aifp-daj6dri4yf3k3z)      │    │
│  │ ├─ Azure OpenAI Models                                              │    │
│  │ │   ├─ gpt-5 (500K TPM) - Primary                                  │    │
│  │ │   ├─ gpt-4o-mini (30K TPM) - Cost Optimized                      │    │
│  │ │   └─ text-embedding-3-large (500K TPM)                           │    │
│  │ ├─ Foundry IQ (Agentic RAG)                                        │    │
│  │ │   ├─ Knowledge Base: product-specs-kb                            │    │
│  │ │   ├─ Index: product-specs-sharepoint-ks-index                    │    │
│  │ │   └─ Reasoning Effort: minimal/low/medium                        │    │
│  │ ├─ Bing Grounding (Web Search)                                     │    │
│  │ │   ├─ Connection: bingglobal00149elbd                             │    │
│  │ │   └─ Tool: BingGroundingAgentTool                                │    │
│  │ └─ Foundry Guardrails                                               │    │
│  │     ├─ Task Adherence                                               │    │
│  │     ├─ Prompt Shields + Spotlighting                               │    │
│  │     └─ Groundedness Detection                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Microsoft Agent Framework                                           │    │
│  │ ├─ ChatAgent (Multi-turn Conversation)                             │    │
│  │ ├─ Tools (@ai_function decorator)                                  │    │
│  │ │   ├─ SQL Tool → Fabric SQL Database                              │    │
│  │ │   ├─ Doc Tool → Foundry IQ (Agentic Retrieval)                  │    │
│  │ │   ├─ Web Tool → Bing Grounding                                   │    │
│  │ │   └─ MCP Tools → Business Analytics (16 tools)                  │    │
│  │ ├─ Workflow Orchestration                                           │    │
│  │ │   ├─ HandoffBuilder (専門家委譲)                                 │    │
│  │ │   └─ MagenticBuilder (マネージャー統合)                          │    │
│  │ └─ Conversation History → Fabric SQL DB                            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Azure AI Search (search-sp-rag-australiaeast-001)                   │    │
│  │ ├─ Standard SKU                                                     │    │
│  │ └─ Index: product-specs-sharepoint-ks-index                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                       Data Layer (Unified Data Foundation)                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Microsoft Fabric (capagentunifieddata001) - F4 Capacity             │    │
│  │ ├─ SQL Database in Fabric                                           │    │
│  │ │   └─ retail_sqldatabase_daj6dri4yf3k3z-*                         │    │
│  │ │       ├─ Business Tables: customers, products, orders, inventory │    │
│  │ │       └─ History Tables: hst_conversations, hst_conversation_*   │    │
│  │ ├─ OneLake (Unified Data Lake)                                     │    │
│  │ │   ├─ Bronze: Raw Data                                             │    │
│  │ │   ├─ Silver: Validated/Cleansed                                  │    │
│  │ │   └─ Gold: Business-Ready                                         │    │
│  │ └─ Power BI Semantic Models                                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                    Observability & Security Layer                            │
│  ┌──────────────────────────────┐  ┌────────────────────────────────────┐   │
│  │ Azure Monitor               │  │ Microsoft Defender for Cloud       │   │
│  │ ├─ Application Insights    │  │ ├─ AI Security Posture            │   │
│  │ │   (appi-daj6dri4yf3k3z) │  │ └─ Container Security             │   │
│  │ ├─ Log Analytics          │  └────────────────────────────────────┘   │
│  │ │   (log-daj6dri4yf3k3z)  │                                          │
│  │ └─ OpenTelemetry          │  ┌────────────────────────────────────┐   │
│  └──────────────────────────────┘  │ Managed Identity                   │   │
│  ┌──────────────────────────────┐  │ └─ DefaultAzureCredential         │   │
│  │ Key Vault                   │  │     RBAC (最小権限)                │   │
│  │ └─ Secrets / Keys          │  └────────────────────────────────────┘   │
│  └──────────────────────────────┘                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Azure Developer CLI (azd) デプロイ

### 基本コマンド

```bash
# 認証
azd auth login

# 初期化（既存リポジトリの場合はスキップ）
azd init

# 全リソースデプロイ（推奨）
azd up

# 個別操作
azd provision      # インフラのみ
azd deploy         # アプリのみ

# クリーンアップ
azd down
```

### azure.yaml 構造

```yaml
name: agentic-applications-for-unified-data-foundation
metadata:
  template: microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator

# Note: services セクションはなし。デプロイは GitHub Actions（deploy-app-service.yml）で実施。
# azd provision でインフラのみデプロイ可能。

infra:
  provider: bicep
  path: ./infra
  module: main
```

---

## 🔐 セキュリティ設計

### 認証・認可

```yaml
authentication:
  frontend:
    provider: "Entra ID (App Service EasyAuth)"

  api:
    method: "Managed Identity (SystemAssigned)"
    credential: "DefaultAzureCredential"

  foundry:
    method: "Entra ID + RBAC"
    roles:
      - "Azure AI Developer"
      - "Cognitive Services OpenAI User"

  fabric:
    method: "Entra ID"
    roles:
      - "Fabric Workspace Contributor"
```

### Foundry Guardrails

```python
guardrails_config = {
    "task_adherence": {
        "enabled": True,
        "action": "block",
        "description": "エージェントの目的逸脱を防止"
    },
    "prompt_shields": {
        "enabled": True,
        "spotlighting": True,
        "jailbreak_detection": True
    },
    "groundedness_detection": {
        "enabled": True,
        "threshold": 0.7,
        "description": "ハルシネーション防止"
    }
}
```

---

## 🔧 技術スタック詳細

### Compute

| コンポーネント | サービス | 特徴 |
|----------------|----------|------|
| API Server | Azure App Service | Linux Container (da-api:main) |
| Frontend | Azure App Service | Linux Container (da-app:main) |
| MCP Server | Azure Functions | Python 3.12 |
| Container Registry | Azure Container Registry | Premium SKU |

### AI/Agent

| コンポーネント | サービス | 状態 (2026/2) |
|----------------|----------|---------------|
| Agent Framework | Microsoft Agent Framework | Public Preview (GA: Q1 2026) |
| Agent Service | Foundry Agent Service | GA |
| Hosted Agents | Foundry Hosted Agents | GA |
| LLM | Azure OpenAI | GPT-5, GPT-4o-mini |
| Web Search | Web Search tool (preview) | Preview |
| Guardrails | Foundry Guardrails | Public Preview |

### Data

| コンポーネント | サービス | 状態 (2026/2) |
|----------------|----------|---------------|
| Data Platform | Microsoft Fabric | F4 Capacity |
| Database | SQL Database in Fabric | GA |
| Data Lake | OneLake | Medallion Architecture |
| AI Search | Azure AI Search | 製品仕様書検索 |
| Security | OneLake Security | Preview (RLS/CLS) |

---

## 📐 カスタマイズガイド

### 1. 業界シナリオのカスタマイズ

```
元のシナリオ: Sales Analyst（汎用）
        ↓
カスタマイズ例:
├─ 製造業: 品質管理 + 予知保全 Agent
├─ 金融: リスク分析 + コンプライアンス Agent
├─ 小売: 在庫最適化 + 需要予測 Agent
└─ ヘルスケア: 患者分析 + 治療推奨 Agent
```

### 2. Agent Tool のカスタマイズ

```python
from agent_framework import ChatAgent, tool
from typing import Annotated

class CustomSalesAgent(ChatAgent):
    @tool(approval_mode="never_require")
    async def query_sales_data(
        self,
        query: Annotated[str, "売上データのSQLクエリ"],
    ) -> str:
        """売上データをクエリする"""
        # Fabric SQL Database への接続
        result = await self.fabric_client.execute_sql(query)
        return result

    @tool(approval_mode="never_require")
    async def get_customer_insights(
        self,
        customer_id: Annotated[str, "顧客ID"],
    ) -> str:
        """顧客インサイトを取得する"""
        # カスタムロジック
        return insights
```

> **Note**: `@ai_function` は `@tool` に改名されました（agent-framework-core 1.0.0b260128 breaking change）

### 3. Guardrails のカスタマイズ

```python
# 業界固有のGuardrails追加
industry_guardrails = {
    "pii_detection": {
        "enabled": True,
        "categories": ["医療情報", "金融情報", "個人識別情報"],
        "action": "redact"
    },
    "compliance_check": {
        "enabled": True,
        "regulations": ["GDPR", "HIPAA", "金融商品取引法"],
        "action": "warn"
    }
}
```

---

## 📁 Solution Accelerator ファイル構成

```
agentic-applications-for-unified-data-foundation-solution-accelerator/
├── .azdo/pipelines/           # Azure DevOps CI/CD
├── .devcontainer/             # Dev Container設定
├── .github/                   # GitHub設定
│   ├── copilot-instructions.md  ← このファイルを追加
│   ├── instructions/            ← 追加
│   ├── prompts/                 ← 追加
│   ├── agents/                  ← 追加
│   ├── chatmodes/               ← 追加
│   └── skills/                  ← 追加
├── documents/                 # ドキュメント
├── infra/                     # Bicep IaC
├── src/                       # ソースコード
│   ├── api/                   # Backend API (Python)
│   └── web/                   # Frontend (React)
├── tests/                     # テスト
├── azure.yaml                 # azd設定
├── AGENTS.md                  ← 追加
├── DEMO.md                    ← 追加
└── README.md
```

---

## 💰 コスト見積もり

### 必須コスト

| サービス | SKU | 月額概算 |
|----------|-----|----------|
| Microsoft Fabric | F4 | ¥30,000〜 |
| Azure OpenAI | S0 (Pay-per-token) | ¥10,000〜 |
| App Service | B1/S1 × 2 | ¥5,000〜 |
| Functions | Consumption | ¥500〜 |
| Container Registry | Premium | ¥5,000 |
| API Management | Consumption | ¥500〜 |
| Application Insights | Pay-as-you-go | ¥1,000〜 |
| **合計** | | **約¥50,000〜/月** |

### 注意事項

- Fabric F4 Capacity は固定コスト（使用量に関わらず発生）
- OpenAI はトークン数に応じた従量課金
- App Service は常時稼働（Always On設定）

---

## 🧪 テスト運用ガイドライン

### CI/CD パイプライン

```
コード変更 → ローカルテスト → git push → GitHub Actions → Azure デプロイ
              .\scripts\test.ps1    (自動)        (自動)
```

### 必須ワークフロー

| ワークフロー | ファイル | トリガー | 必須 |
|--------------|----------|----------|------|
| Test and Lint | `test.yml` | PR, push to main | ✅ |
| Deploy | `deploy-app-service.yml` | push to main | ✅ |
| Security Scan | `security-scan.yml` | 定期実行 | - |

### コード品質ルール

```yaml
# PR マージ条件
python_lint: required      # Ruff lint must pass
python_tests: required     # pytest must pass
frontend_lint: optional    # ESLint (warning only)
```

### テストコマンド

```powershell
# 推奨: すべてのチェック
.\scripts\test.ps1

# Lint のみ
.\scripts\test.ps1 -LintOnly

# Lint 自動修正
.\scripts\test.ps1 -LintOnly -Fix

# テストのみ（カバレッジ付き）
.\scripts\test.ps1 -TestOnly -Coverage
```

### テストファイル構成

```
src/api/python/
├── tests/
│   ├── conftest.py                  # 共通フィクスチャ・モック
│   ├── test_app.py                  # FastAPI アプリテスト (8件)
│   ├── test_app_advanced.py         # Health DB分岐・CORS・スキーマ (9件)
│   ├── test_agentic_retrieval.py    # Agentic Retrieval Tool (27件)
│   ├── test_chat.py                 # チャットロジックテスト (37件)
│   ├── test_history_sql.py          # Fabric SQL テスト (10件)
│   ├── test_history_sql_functions.py # 履歴業務ロジック (30件)
│   ├── test_mcp_client.py           # MCP クライアントテスト (8件)
│   ├── test_sql_agent.py            # SQL Agent テスト (12件)
│   ├── test_utils.py                # ユーティリティテスト (11件)
│   └── test_web_agent.py            # Web Agent テスト (14件)
├── pyproject.toml                   # pytest/ruff 設定
└── requirements-test.txt            # テスト依存パッケージ
```

### 新機能追加時の必須事項

1. **テストを先に書く（TDD推奨）** または機能実装後すぐにテスト追加
2. **ローカルで `.\scripts\test.ps1` を実行**
3. **すべてパスしてからコミット**

詳細は [documents/Testing-Guide.md](../documents/Testing-Guide.md) を参照。

---

## 🔗 参照リソース

| リソース | URL |
|----------|-----|
| Solution Accelerator | https://github.com/microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator |
| Microsoft Agent Framework | https://learn.microsoft.com/agent-framework/ |
| Foundry Agent Service | https://learn.microsoft.com/azure/ai-foundry/agents/ |
| Microsoft Fabric | https://learn.microsoft.com/fabric/ |
| Azure Developer CLI | https://learn.microsoft.com/azure/developer/azure-developer-cli/ |
| Azure CAF Naming | https://learn.microsoft.com/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming |
