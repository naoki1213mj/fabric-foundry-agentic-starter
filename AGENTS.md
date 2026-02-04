# AGENTS.md - Copilot Agent Mode 操作指示

## ミッション

**Microsoft Fabric + Foundry + Agent Framework を活用した Agentic AI アプリで、TDM を10分で納得させる**

## Solution Accelerator をベースにカスタマイズ

このプロジェクトは以下の Solution Accelerator をベースにしています：
https://github.com/microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator

## 🚀 デプロイ方法（重要）

**GitHub Actions で自動デプロイ**: `git push` するだけでAzure側に自動デプロイされます！

```bash
# 変更をコミット
git add .
git commit -m "fix: 修正内容"

# プッシュ = 自動デプロイ（GitHub Actionsが実行される）
git push
```

⚠️ **手動の `az webapp` コマンドは不要です！** pushすれば自動的にデプロイされます。

---

## 🔄 GitHub Actions 確認ワークフロー（必須）

**push後は必ずワークフロー状況を確認する。**

### 確認コマンド

```powershell
# 最新のワークフロー状況を確認
gh run list --limit 5

# 特定のワークフロー詳細を確認（ID指定）
gh run view <run-id>

# 失敗したジョブのログを確認
gh run view --job=<job-id> --log-failed

# ワークフロー完了まで待機して結果確認
gh run watch <run-id>
```

### ワークフロー一覧

| ワークフロー | トリガー | 必須 | 説明 |
|--------------|----------|------|------|
| **Test and Lint** | PR, push | ✅ | Python Lint + Unit Tests |
| **Build and Deploy** | push to main | ✅ | Docker Build → Azure デプロイ |
| **Security Scan** | push | - | Trivy 脆弱性スキャン |

### Copilot Agent への指示

**push後のワークフロー：**

1. `git push` 実行
2. `gh run list --limit 3` でワークフロー状況を確認
3. 失敗した場合：
   - `gh run view <run-id>` で詳細確認
   - `gh run view --job=<job-id> --log-failed` でエラーログ取得
   - エラーを修正して再push
4. 全ワークフロー成功を確認してから次のタスクへ

**よくある失敗パターン：**

| エラー | 原因 | 対処 |
|--------|------|------|
| TypeScript TS2802 | `matchAll` 互換性 | `Array.from()` でラップ |
| Python lint failed | Ruff エラー | `ruff check --fix` |
| Docker build failed | 依存関係 | requirements.txt 確認 |
| Deploy failed | Azure認証 | Secrets 確認 |

---

## 実装前チェック

- [ ] 対象の `.instructions.md` を読んだ
- [ ] Solution Accelerator の既存コードとの一貫性を確認
- [ ] DEMO.md の Wow Path に沿っている
- [ ] Guardrails 統合を計画

## 実装後チェック

- [ ] **ローカルでテスト実行** (`.\scripts\test.ps1`)
- [ ] **Lintエラーがないことを確認** (`ruff check src/api/python`)
- [ ] `git push` でデプロイ開始（GitHub Actionsを確認）
- [ ] API ヘルスチェック成功
- [ ] Frontend 表示確認
- [ ] DEMO_MODE=true で動作確認
- [ ] Guardrails が機能している

---

## 🧪 テスト運用（重要）

### 基本ルール

**コード変更後は必ずテストを実行してからコミットする。**

```powershell
# 1. テスト + Lint を実行
.\scripts\test.ps1

# 2. すべてパスしたらコミット
git add .
git commit -m "feat: 機能追加"
git push
```

### テストコマンド早見表

| コマンド | 用途 |
|----------|------|
| `.\scripts\test.ps1` | テスト + Lint（推奨） |
| `.\scripts\test.ps1 -LintOnly` | Lintのみ |
| `.\scripts\test.ps1 -LintOnly -Fix` | Lint自動修正 |
| `.\scripts\test.ps1 -TestOnly` | テストのみ |
| `.\scripts\test.ps1 -TestOnly -Coverage` | カバレッジ付き |

### テストファイルの場所

```
src/api/python/
├── tests/
│   ├── conftest.py       # 共通フィクスチャ
│   ├── test_app.py       # app.py のテスト
│   ├── test_history_sql.py  # DB操作テスト
│   └── test_utils.py     # ユーティリティテスト
├── pyproject.toml        # pytest設定
└── requirements-test.txt # テスト用パッケージ
```

### 新機能追加時のテスト

新しい関数やエンドポイントを追加したら、対応するテストも追加する：

```python
# src/api/python/tests/test_my_feature.py
class TestMyNewFeature:
    def test_success_case(self):
        """正常系"""
        result = my_function("valid")
        assert result == expected

    def test_error_case(self):
        """エラー系"""
        with pytest.raises(ValueError):
            my_function("invalid")
```

### CI/CD でのテスト

PRを作成すると GitHub Actions が自動実行：

1. **Python Lint (Ruff)** - ❌失敗するとマージ不可
2. **Python Unit Tests** - ❌失敗するとマージ不可
3. **Frontend Lint** - ⚠️参考（ブロックしない）

### Copilot Agent への指示

**コード変更時は以下を必ず実行：**

1. 変更に関連するテストがあれば実行
2. 新機能の場合はテストを追加
3. `.\scripts\test.ps1` で全体チェック
4. Lintエラーがあれば `-Fix` で修正
5. すべてパスしてからコミット

**やってはいけないこと：**
- テストを実行せずにコミット
- 失敗するテストを放置
- Lintエラーを無視

---

## コーディングパターン

### 認証（Managed Identity）

```python
from azure.identity import DefaultAzureCredential
credential = DefaultAzureCredential()
```

### DEMO_MODE

```python
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"
if DEMO_MODE:
    return CACHED_RESPONSE
```

### Agent Tool

```python
from agent_framework import ai_function

@ai_function
async def my_tool(param: str) -> str:
    """ツールの説明"""
    if DEMO_MODE:
        return json.dumps({"demo": True})
    return json.dumps(result)
```

## やってはいけないこと

- ハードコードされたシークレット
- Solution Accelerator のコード構造を大幅に変更
- DEMO_MODE なしの実装
- Guardrails バイパス
- **pip や python -m pip の使用** → 必ず `uv pip` を使う

## Python 開発環境 (uv 必須)

このプロジェクトでは **uv** を使用してPython仮想環境を管理します。

```bash
# 仮想環境の有効化 (PowerShell)
.\.venv\Scripts\Activate.ps1

# パッケージインストール
uv pip install -r requirements.txt

# パッケージ追加
uv pip install <package-name>
```

**重要**: `pip` ではなく必ず `uv pip` を使用してください。

### Copilot Agent Mode でのPython実行

**Copilotへの指示**: Python を実行する際は、必ず uv 仮想環境の Python を使用してください。

```powershell
# プロジェクトルートから実行する場合
& ".\.venv\Scripts\python.exe" <script.py>

# src/api/python から実行する場合
& "../../../.venv/Scripts/python.exe" <script.py>

# 仮想環境を有効化してから実行する場合
.\.venv\Scripts\Activate.ps1
python <script.py>
```

**やってはいけないこと**:
- システムの `python` を直接使用（パッケージが見つからないエラーになる）
- `py_compile` や `python -m` をグローバルPythonで実行

## 📂 ログ管理ルール

デバッグ・エラー分析で取得したログは **必ず `.debug_logs/` フォルダに格納**してください。

```bash
# ログの保存先
.debug_logs/
├── latest/              # 最新のログ（フォルダ）
├── latest.zip           # 最新のログ（圧縮）
├── api_timeout_logs/    # タイムアウト関連
├── error_logs*.zip      # エラー分析用
└── [日付]_[目的].zip    # 命名規則: 2026-02-02_timeout_fix.zip
```

**やってはいけないこと**:
- プロジェクト直下にログファイル/フォルダを放置
- `*_logs/` や `*.zip` をルートに作成

**Copilotへの指示**: ログ取得時は `.debug_logs/` に直接保存してください。

## 審査基準

| 基準 | 対応 |
|------|------|
| Why Microsoft | Fabric + Foundry + Agent Framework |
| Why Now | Agent Framework GA + Guardrails |
| 技術統合 | 5領域カバー |
| ACR | Fabric F4 + OpenAI PTU/従量課金 |

---

## 🌐 Azure 実機環境情報（2026/2/5 更新）

### リソース一覧

| 項目 | 値 | 備考 |
|------|-----|------|
| **Resource Group** | `rg-agent-unified-data-acce-eastus-001` | East US |
| **API App Service** | `api-daj6dri4yf3k3z` | Linux Container (da-api:main) |
| **Frontend App** | `app-daj6dri4yf3k3z` | Linux Container (da-app:main) |
| **MCP Function** | `func-mcp-daj6dri4yf3k3z` | Python 3.12 |
| **ACR** | `crda672axowukix3.azurecr.io` | Premium SKU |
| **AI Foundry** | `aisa-daj6dri4yf3k3z` | AIServices |
| **Foundry Project** | `aifp-daj6dri4yf3k3z` | |
| **AI Search** | `search-sp-rag-australiaeast-001` | Standard SKU (Australia East) |
| **Fabric Capacity** | `capagentunifieddata001` | F4 SKU |
| **API Management** | `apim-daj6dri4yf3k3z` | Consumption SKU |
| **API Center** | `apic-daj6dri4yf3k3z` | Free SKU - ツールカタログ |
| **App Insights** | `appi-daj6dri4yf3k3z` | |
| **Log Analytics** | `log-daj6dri4yf3k3z` | |

### モデルデプロイメント

| モデル | バージョン | TPM |
|--------|-----------|-----|
| `gpt-5` | 2025-08-07 | 500K |
| `gpt-4o-mini` | 2024-07-18 | 30K |
| `text-embedding-3-large` | 1 | 500K |
| `text-embedding-3-small` | 1 | 120K |

### API Management (AI Gateway)

| API | Path | Backend |
|-----|------|---------|
| Azure OpenAI API | `/openai` | `aisa-daj6dri4yf3k3z.openai.azure.com` |
| **Foundry OpenAI API** | `/foundry-openai/openai/v1/` | `aisa-daj6dri4yf3k3z.services.ai.azure.com` |
| MCP Server API | `/mcp` | `func-mcp-daj6dri4yf3k3z.azurewebsites.net` |
| Foundry Agent API | `/foundry-agents` | Foundry Agent Service |

**AzureOpenAIResponsesClient 設定（推奨）:**

```bash
# Responses API v1 を使用するための環境変数
AZURE_OPENAI_BASE_URL=https://apim-daj6dri4yf3k3z.azure-api.net/foundry-openai/openai/v1/
AZURE_OPENAI_DEPLOYMENT_MODEL=gpt-5
```

> **ResponsesClient vs ChatClient:**
> - `AZURE_OPENAI_BASE_URL` が設定されている場合 → `AzureOpenAIResponsesClient` を使用
> - 設定されていない場合 → `AzureOpenAIChatClient` にフォールバック
> - multi_tool / sql_only モードは ResponsesClient に移行済み
> - handoff / magentic モードは ChatClient を維持（WorkflowBuilder SDK制約）

**AI Gateway機能:**

- トークン使用量ヘッダー: `x-openai-prompt-tokens`, `x-openai-completion-tokens`, `x-openai-total-tokens`
- Circuit Breaker: 429/500-599エラー時の自動フェイルオーバー（30秒trip duration）
- Managed Identity認証
- レイテンシ計測: `x-gateway-latency-ms` ヘッダー

> **Note**: `llm-emit-token-metric` ポリシーは Consumption SKU では非対応。ヘッダーベースでメトリクス収集。

### API Center (ツールカタログ)

| API | 説明 |
|-----|------|
| Business Analytics MCP Server | 5つのビジネス分析ツール (YoY, RFM等) |
| Azure OpenAI API | Chat Completions, Embeddings |

### エンドポイント

| サービス | URL |
|----------|-----|
| Frontend | https://app-daj6dri4yf3k3z.azurewebsites.net |
| API | https://api-daj6dri4yf3k3z.azurewebsites.net |
| Health Check | https://api-daj6dri4yf3k3z.azurewebsites.net/health |
| APIM Gateway | https://apim-daj6dri4yf3k3z.azure-api.net |
| MCP Server | https://func-mcp-daj6dri4yf3k3z.azurewebsites.net/api/mcp |

### ツール対応状況（実機確認済み 2026/2/5）

| ツール | 状態 | 備考 |
|--------|------|------|
| SQL Query (Fabric) | ✅ 動作 | 売上データ、顧客データ |
| Doc Search (Foundry IQ) | ✅ 動作 | Agentic Retrieval 対応 |
| Web Search (Bing Grounding) | ✅ 実装済み | BingGroundingAgentTool + プロジェクトコネクション |
| MCP Tools | ✅ 動作 | YoY, RFM, 在庫分析 (APIM経由) |

### Web Search 設定（Bing Grounding）

| 項目 | 値 |
|------|-----|
| Connection Name | `bingglobal00149elbd` |
| Tool Pattern | `BingGroundingAgentTool` |
| Timeout | 90秒 |

**環境変数**:
```
BING_PROJECT_CONNECTION_NAME=bingglobal00149elbd
AZURE_AI_PROJECT_ENDPOINT=https://aisa-daj6dri4yf3k3z.services.ai.azure.com/api/projects/aifp-daj6dri4yf3k3z
```

### Agentic Retrieval (Foundry IQ) 設定

| 項目 | 値 |
|------|-----|
| Knowledge Base | `product-specs-kb` |
| Knowledge Source Index | `product-specs-sharepoint-ks-index` |
| Reasoning Effort | `minimal` / `low` / `medium` |
| API Version | `2025-11-01-preview` |

**UIでの設定方法**:
- フロントエンド左側の「🔍 Doc Search (Foundry IQ)」ドロップダウンで Reasoning Effort を選択
- `minimal`: 高速・直接検索（LLMなし）
- `low`: シングルパス推論（バランス型、デフォルト）
- `medium`: 反復検索（最高品質）

**環境変数**:
```
AI_SEARCH_ENDPOINT=https://search-sp-rag-australiaeast-001.search.windows.net
AI_SEARCH_KNOWLEDGE_BASE_NAME=product-specs-kb
AI_SEARCH_INDEX_NAME=product-specs-sharepoint-ks-index
AI_SEARCH_REASONING_EFFORT=low
```

### Fabric SQL Database 設定

| 項目 | 値 |
|------|-----|
| Database | `retail_sqldatabase_daj6dri4yf3k3z-c9a4f960-6dfe-4e75-8ef6-ac9ef3f35e44` |
| Server | `l3mc2ebyyfwejehdghpbjlhnw4-moiagz2ftahudlx3khcgjqxfqa.database.fabric.microsoft.com,1433` |

**環境変数**:
```
FABRIC_SQL_DATABASE=retail_sqldatabase_daj6dri4yf3k3z-c9a4f960-6dfe-4e75-8ef6-ac9ef3f35e44
FABRIC_SQL_SERVER=l3mc2ebyyfwejehdghpbjlhnw4-moiagz2ftahudlx3khcgjqxfqa.database.fabric.microsoft.com,1433
```
