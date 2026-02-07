# マルチツール・マルチターン テストシナリオ

> このドキュメントは、複数のツール（SQL Query, Document Search, Web Search, MCP Tools）を組み合わせたマルチターン会話シナリオを定義します。
> 
> **目的**: エージェントが適切にツールを呼び出し、マルチエージェント連携が機能していることをログから検証できるようにする。

---

## 📊 利用可能なツール一覧

| ツール名 | 説明 | ログキーワード |
|----------|------|---------------|
| `run_sql_query` | Fabric SQL Database からデータを取得 | `Function name: run_sql_query` |
| `search_documents` | AI Search で製品仕様書を検索 | `Function name: search_documents` |
| `search_web` | Web Search tool でWeb検索 | `Function name: search_web` |
| `mcp_*` | MCP ビジネス分析ツール（YoY, RFM等） | `Function name: mcp_*` |

---

## 🧪 テストシナリオ

### シナリオ1: 製品戦略会議（SQL + Doc）

**目的**: 売上データと製品仕様を組み合わせた分析

**会話フロー**:

| ターン | ユーザー入力 | 期待されるツール呼び出し |
|--------|--------------|------------------------|
| 1 | 「Mountain-100の最新の売上データを教えてください」 | `run_sql_query` |
| 2 | 「この製品の仕様を教えてください」 | `search_documents` |
| 3 | 「売上と仕様を比較して、改善ポイントを提案してください」 | LLMによる統合分析 |

**ログ検証ポイント**:
```
INFO:agent_framework:Function name: run_sql_query
INFO:chat:SQL query executed successfully, returned X rows
INFO:agent_framework:Function name: search_documents
INFO:knowledge_base_tool:Search returned X documents
```

---

### シナリオ2: 競合分析（SQL + Web）

**目的**: 内部データと市場トレンドを組み合わせた分析

**会話フロー**:

| ターン | ユーザー入力 | 期待されるツール呼び出し |
|--------|--------------|------------------------|
| 1 | 「自転車カテゴリの売上トップ5を教えてください」 | `run_sql_query` |
| 2 | 「マウンテンバイクの市場トレンドを調べてください」 | `search_web` |
| 3 | 「当社の売上と市場トレンドを比較してください」 | LLMによる統合分析 |

**ログ検証ポイント**:
```
INFO:agent_framework:Function name: run_sql_query
INFO:chat:SQL query executed successfully
INFO:agent_framework:Function name: search_web
INFO:chat:Web search requested: マウンテンバイク 市場トレンド
INFO:agents.web_agent:Performing Web Search via Foundry
```

---

### シナリオ3: 顧客分析（SQL + MCP RFM）

**目的**: SQLデータとMCPビジネス分析ツールの連携

**会話フロー**:

| ターン | ユーザー入力 | 期待されるツール呼び出し |
|--------|--------------|------------------------|
| 1 | 「全顧客の購買履歴を取得してください」 | `run_sql_query` |
| 2 | 「RFM分析を実行して、優良顧客を特定してください」 | `calculate_rfm_score` |
| 3 | 「優良顧客向けのキャンペーン施策を提案してください」 | LLMによる提案 |

**ログ検証ポイント**:
```
INFO:agent_framework:Function name: run_sql_query
INFO:chat:SQL query executed successfully
INFO:agent_framework:Function name: calculate_rfm_score
INFO:mcp_client:MCP tool calculate_rfm_score executed successfully
```

---

### シナリオ4: 新製品企画（Doc + Web + SQL）

**目的**: 3つのツールを複合的に使用

**会話フロー**:

| ターン | ユーザー入力 | 期待されるツール呼び出し |
|--------|--------------|------------------------|
| 1 | 「Sport-100 Helmetの製品仕様を教えてください」 | `search_documents` |
| 2 | 「安全装備の最新トレンドを調べてください」 | `search_web` |
| 3 | 「ヘルメットの過去3ヶ月の売上推移を教えてください」 | `run_sql_query` |
| 4 | 「仕様、トレンド、売上を総合して新製品の提案をしてください」 | LLMによる統合分析 |

**ログ検証ポイント**:
```
INFO:agent_framework:Function name: search_documents
INFO:knowledge_base_tool:Search returned X documents
INFO:agent_framework:Function name: search_web
INFO:agents.web_agent:Performing Web Search
INFO:agent_framework:Function name: run_sql_query
INFO:chat:SQL query executed successfully
```

---

### シナリオ5: 包括的ビジネスレビュー（全ツール）

**目的**: すべてのツールを1つの会話で使用

**会話フロー**:

| ターン | ユーザー入力 | 期待されるツール呼び出し |
|--------|--------------|------------------------|
| 1 | 「先月の売上トップ10製品を教えてください」 | `run_sql_query` |
| 2 | 「1位の製品の仕様を教えてください」 | `search_documents` |
| 3 | 「この製品カテゴリの市場動向を調べてください」 | `search_web` |
| 4 | “前年同月比を計算してください」 | `calculate_yoy_growth` |
| 5 | 「すべての情報を統合してエグゼクティブサマリーを作成してください」 | LLMによる統合分析 |

**ログ検証ポイント**:
```
INFO:agent_framework:Function name: run_sql_query
INFO:agent_framework:Function name: search_documents
INFO:agent_framework:Function name: search_web
INFO:agent_framework:Function name: calculate_yoy_growth
```

---

## 📋 ログ検証スクリプト

ログからツール呼び出しを確認するためのスクリプト:

```powershell
# ログをダウンロード
$ts = Get-Date -Format "yyyyMMddHHmmss"
$logPath = ".debug_logs/test_logs_$ts.zip"
az webapp log download --name api-<your-suffix> --resource-group <your-resource-group> --log-file $logPath
Expand-Archive -Path $logPath -DestinationPath ".debug_logs/test_logs_$ts" -Force

# ツール呼び出しをフィルタ
Get-Content ".debug_logs/test_logs_$ts/LogFiles/*docker.log" | 
    Select-String -Pattern "Function name:|Function.*succeeded|SQL query executed|Search returned|Web search" |
    ForEach-Object { $_.Line }
```

---

## ✅ 検証チェックリスト

### 各シナリオ実行後に確認すること

- [ ] **ツール選択の適切性**: クエリに対して正しいツールが選択されたか
- [ ] **ツール呼び出し成功**: `Function xxx succeeded` ログが出力されたか
- [ ] **エラーハンドリング**: エラー時に適切にフォールバックしたか
- [ ] **マルチターン文脈**: 前のターンの情報を保持して回答しているか
- [ ] **応答品質**: 複数ツールの結果を適切に統合しているか

### ツール別成功条件

| ツール | 成功ログ | 失敗ログ |
|--------|----------|----------|
| SQL | `SQL query executed successfully, returned X rows` | `SQL query failed` |
| Doc Search | `Search returned X documents` | `AI_SEARCH_* not configured` |
| Web Search | `Web search completed` | `Web search timed out after 90s` |
| MCP | `MCP tool xxx executed successfully` | `MCP server connection failed` |

---

## 🔧 テスト実行方法

### 1. curlを使用したテスト

```bash
# シナリオ1 - ターン1
curl -X POST https://api-<your-suffix>.azurewebsites.net/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Mountain-100の最新の売上データを教えてください",
    "conversation_id": "test-scenario1",
    "stream": false
  }'
```

### 2. PowerShellを使用したテスト

```powershell
$body = @{
    query = "Mountain-100の最新の売上データを教えてください"
    conversation_id = "test-scenario1"
    stream = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://api-<your-suffix>.azurewebsites.net/api/chat" `
    -Method POST -Body $body -ContentType "application/json" -TimeoutSec 120
```

### 3. UIからのテスト

1. https://app-<your-suffix>.azurewebsites.net にアクセス
2. シナリオの各ターンを順番に入力
3. 応答を確認後、ログスクリプトを実行して検証

---

## 📝 備考

- **Web Search タイムアウト**: 現在90秒に設定。タイムアウトした場合は「検索結果を取得できませんでした」と回答
- **SQL 0件返却**: データが存在しない場合でもツール呼び出しは成功扱い
- **AI Search 認証**: Managed Identity を使用

---

**Last Updated**: 2026/02/04
