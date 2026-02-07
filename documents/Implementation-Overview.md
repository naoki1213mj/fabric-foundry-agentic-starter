# 実装概要ドキュメント

> **注**: このドキュメントは **Azure 実機環境を確認して** 2026年2月4日に更新されました。
> オリジナルの Solution Accelerator ドキュメントは同フォルダ内に保持されています。

## 1. プロジェクト概要

このプロジェクトは [microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator](https://github.com/microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator) をベースにカスタマイズしたものです。

### 主要な変更点

| 項目 | オリジナル | 現在の実装 |
| ---- | ---------- | ---------- |
| **エージェントモード** | 単一モード | 4モード対応 (sql_only, multi_tool, handoff, magentic) |
| **プロンプト管理** | インライン定義 | モジュール分離 (`prompts/`) |
| **デプロイ方法** | azd up | GitHub Actions 自動デプロイ |
| **パッケージ管理** | pip | uv |

---

## 2. Azure 実機環境（2026年2月確認）

### リソースグループ

| 項目 | 値 |
| ---- | -- |
| **名前** | `<your-resource-group>` |
| **リージョン** | East US |

### デプロイ済みリソース一覧

| リソース | 名前 | 種類 | リージョン | SKU |
| -------- | ---- | ---- | ---------- | --- |
| **App Service (API)** | `api-<your-suffix>` | Linux Container | Australia East | - |
| **App Service (Frontend)** | `app-<your-suffix>` | Linux Container | Australia East | - |
| **App Service Plan** | `asp-<your-suffix>` | - | Australia East | - |
| **Container Registry** | `<your-acr-name>` | ACR | East US | **Premium** |
| **Azure AI Services** | `aisa-<your-suffix>` | AIServices | East US | S0 |
| **AI Foundry Project** | `aifp-<your-suffix>` | - | East US | - |
| **Azure AI Search** | `<your-ai-search-name>` | Cognitive Search | Australia East | **Standard** |
| **Bing Grounding** | `<your-bing-connection-name>` (connection) | Project Connection | - | - |
| **Application Insights** | `appi-<your-suffix>` | APM | East US | - |
| **Log Analytics** | `log-<your-suffix>` | Logs | East US | - |
| **Managed Identity** | `id-<your-suffix>` | User Assigned | Australia East | - |
| **Fabric Capacity** | `<your-fabric-capacity>` | Microsoft Fabric | Australia East | **F4** |
| **API Management** | `apim-<your-suffix>` | AI Gateway | East US | **Consumption** |
| **API Center** | `apic-<your-suffix>` | Tool Catalog | East US | Free |

### 現在の設定値（API App Service）

| 環境変数 | 値 |
| -------- | -- |
| `AGENT_MODE` | **`multi_tool`** |
| `MULTI_AGENT_MODE` | **`true`** |
| `AZURE_OPENAI_DEPLOYMENT_MODEL` | **`gpt-5`** |
| `FABRIC_SQL_SERVER` | `*.database.fabric.microsoft.com` |
| `FABRIC_SQL_DATABASE` | `<your-fabric-sql-database>` |
| `AI_SEARCH_INDEX_NAME` | `product-specs-sharepoint-ks-index` |

### Container Registry イメージ

| リポジトリ | 用途 |
| ---------- | ---- |
| `da-api` | Backend API |
| `da-app` | Frontend App |

---

## 3. 技術スタック

### バックエンド

- **言語**: Python 3.12
- **フレームワーク**: FastAPI
- **AIフレームワーク**: agent-framework-core
- **認証**: Azure Managed Identity (DefaultAzureCredential)

### フロントエンド

- **言語**: TypeScript
- **フレームワーク**: React
- **可視化**: Chart.js

### AI/エージェント

- **LLM**: Azure OpenAI (**GPT-5** - 実機確認)
- **エージェント管理**: Microsoft Foundry Agent Service (`aifp-<your-suffix>`)
- **ドキュメント検索**: Foundry IQ (Agentic Retrieval) + Azure AI Search
- **Web検索**: BingGroundingAgentTool (プロジェクトコネクション: `<your-bing-connection-name>`)
- **安全性**: Foundry Guardrails

### データ

- **プラットフォーム**: Microsoft Fabric (**F4 Capacity**)
- **データベース**: SQL Database in Fabric (`retail_sqldatabase_*`)
- **データレイク**: OneLake
- **会話履歴**: SQL Database in Fabric (`hst_conversations`, `hst_conversation_*`)

### インフラ

- **コンピュート**: Azure App Service (Linux Container)
- **レジストリ**: Azure Container Registry (**Premium SKU**)
- **監視**: Application Insights + Log Analytics
- **シークレット**: Managed Identity (Key Vault不使用)

## 3. リポジトリ構成

```
hackathon-project/
├── .github/
│   ├── workflows/
│   │   └── deploy-app-service.yml   # GitHub Actions CI/CD
│   ├── copilot-instructions.md      # Copilot設定
│   └── instructions/                # 開発ガイドライン
├── documents/                       # ドキュメント（このファイル含む）
├── infra/                           # Bicep IaC
│   ├── main.bicep
│   └── scripts/
│       └── agent_scripts/           # エージェント初期化スクリプト
├── src/
│   ├── api/
│   │   └── python/                  # バックエンドAPI
│   │       ├── chat.py              # メインチャットAPI
│   │       ├── prompts/             # ★NEW: プロンプトモジュール
│   │       ├── agents/              # ツールハンドラー
│   │       └── history_sql.py       # Fabric SQL履歴
│   └── App/                         # Reactフロントエンド
├── AGENTS.md                        # Copilot Agent Mode操作指示
├── ARCHITECTURE.md                  # アーキテクチャ図
└── azure.yaml                       # Azure Developer CLI設定
```

## 4. 環境変数

### 必須環境変数

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `AZURE_OPENAI_ENDPOINT` | Foundry AI Services エンドポイント | `https://aisa-*.services.ai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT_MODEL` | デプロイメント名 | `gpt-5` |
| `FABRIC_SQL_SERVER` | Fabric SQL サーバー | `*.database.fabric.microsoft.com,1433` |
| `FABRIC_SQL_DATABASE` | Fabric SQL データベース名 | `retail_sqldatabase_*` |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Application Insights | `InstrumentationKey=xxx;...` |

### オプション環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `AGENT_MODE` | エージェントモード | `multi_tool` |
| `DEMO_MODE` | デモモード | `false` |
| `MULTI_AGENT_MODE` | マルチエージェント | `false` |

## 5. 開発ワークフロー

### ローカル開発

```powershell
# 仮想環境の有効化
.\.venv\Scripts\Activate.ps1

# 依存関係インストール
uv pip install -r src/api/python/requirements.txt

# APIサーバー起動
cd src/api/python
uvicorn main:app --reload --port 8000

# フロントエンド起動（別ターミナル）
cd src/App
npm install
npm start
```

### デプロイ

```bash
# GitHub Actions 自動デプロイ
git add .
git commit -m "fix: 修正内容"
git push  # 自動でAzureにデプロイ
```


> ⚠️ **重要**: `az webapp` などの手動コマンドは不要です。`git push` だけでデプロイされます。

## 6. 関連ドキュメント

### オリジナルドキュメント（保持）


- [DeploymentGuide.md](./DeploymentGuide.md) - オリジナルのデプロイガイド
- [TechnicalArchitecture.md](./TechnicalArchitecture.md) - オリジナルのアーキテクチャ
- [LocalDevelopmentSetup.md](./LocalDevelopmentSetup.md) - ローカル開発セットアップ

### 新規ドキュメント

- [Agent-Architecture.md](./Agent-Architecture.md) - エージェント構成の詳細
- [Prompts-Module.md](./Prompts-Module.md) - プロンプトモジュールの説明
- [Current-Deployment.md](./Current-Deployment.md) - 現在のデプロイ設定

---
*最終更新: 2026年2月*
