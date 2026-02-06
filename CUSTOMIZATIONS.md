# カスタマイズ・追加開発サマリー

> **ベースリポジトリ**: [microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator](https://github.com/microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator)
>
> 元のSolution Acceleratorに対して **235コミット、src/ +20,189行、infra/ +30,982行** の追加開発を行いました。

---

## 🏗️ アーキテクチャの大幅拡張

### 元のSolution Accelerator
- 単一エージェント（SQL クエリのみ）
- CosmosDB で会話履歴管理
- 基本的なチャットUI

### 追加開発後
```
Client (React) → APIM (AI Gateway) → FastAPI → Agent Framework → 4ツール統合
                                                                    ├─ SQL Tool (Fabric SQL DB)
                                                                    ├─ Doc Tool (Foundry IQ / Agentic RAG)
                                                                    ├─ Web Tool (Bing Grounding)
                                                                    └─ MCP Tools (5つのビジネス分析)
```

---

## ✨ 主な追加機能

### 1. マルチエージェント・マルチツール統合

| 機能 | 説明 |
|------|------|
| **4つのエージェントモード** | `sql_only` / `multi_tool` / `handoff` / `magentic` を UI から切替可能 |
| **SQL Tool** | Fabric SQL Database への自然言語クエリ（スキーマ自動認識） |
| **Doc Tool (Foundry IQ)** | Agentic Retrieval による製品仕様書 RAG 検索。Reasoning Effort を UI で調整可能（minimal/low/medium） |
| **Web Tool** | Bing Grounding によるリアルタイム Web 検索。出典リンク付き |
| **MCP Tools** | Azure Functions 上の MCP Server（前年比/RFM/在庫/季節性/地域分析の5ツール） |
| **マルチターン会話** | Fabric SQL DB での会話履歴永続化（CosmosDB から移行） |

### 2. GPT-5 対応

| 機能 | 説明 |
|------|------|
| **Reasoning 可視化** | GPT-5 の思考プロセス（reasoning content）をリアルタイムストリーミング表示 |
| **Reasoning Effort 設定** | UI から推論の深さ（low/medium/high）を調整 |
| **`__REASONING_REPLACE__` マーカー** | バックエンドで差分計算し、フロントエンドで正確に表示 |

### 3. AI Gateway (API Management)

| 機能 | 説明 |
|------|------|
| **APIM 統合** | Azure API Management を AI Gateway として導入 |
| **Foundry OpenAI API** | `/foundry-openai/openai/v1/` パスで Responses API v1 対応 |
| **Circuit Breaker** | 429/500-599 エラー時の自動フェイルオーバー（30秒 trip） |
| **トークンメトリクス** | ヘッダーベースでプロンプト/完了/合計トークン数を計測 |
| **API Center** | MCP ツールカタログとして API Center を導入 |

### 4. フロントエンド全面刷新

| 機能 | 説明 |
|------|------|
| **ダークモード** | 完全なダーク/ライトモード対応（CSS Variables） |
| **仮想化リスト** | react-window による大量メッセージのパフォーマンス最適化 |
| **Chart.js 統合** | エージェントが生成した JSON からグラフを自動レンダリング（ダークモード対応） |
| **ツール使用状況表示** | SQL/Doc/Web/MCP のツール呼び出しをリアルタイム可視化 |
| **質問サジェスト** | 初期画面にサンプルクエリを表示 |
| **停止ボタン** | ストリーミング中の応答を途中停止 |
| **メッセージ編集/再送** | 送信済みメッセージの編集と再送信 |
| **チャット検索** | 会話内のテキスト検索 |
| **エクスポート** | 会話内容のテキストファイルダウンロード |
| **コピーボタン** | メッセージ単位のクリップボードコピー |
| **出典リンク** | Web 検索結果の Citations UI（番号付き展開パネル） |
| **日本語ローカライズ** | UI ラベル・タイムスタンプの日本語化（JST表示） |
| **自動スクロール制御** | ストリーミング中のスクロール位置ジャンプ防止 |
| **レスポンシブ対応** | 設定パネル・2カラムレイアウトのモバイル対応 |

### 5. セキュリティ・品質

| 機能 | 説明 |
|------|------|
| **XSS 対策** | DOMPurify による HTML サニタイズ |
| **ErrorBoundary** | React ErrorBoundary でクラッシュ防止 |
| **リトライ・バックオフ** | API 通信の自動リトライ |
| **Keepalive** | 15秒間隔で Azure App Service 230秒タイムアウトを回避 |
| **Managed Identity** | 全サービス間を DefaultAzureCredential で認証 |
| **Foundry Guardrails** | Task Adherence / Prompt Shields / Groundedness Detection |

### 6. インフラ (Bicep IaC)

| リソース | 説明 |
|----------|------|
| **APIM** | Consumption SKU、Circuit Breaker ポリシー |
| **API Center** | Free SKU、MCP ツールカタログ |
| **Azure Functions** | MCP Server（Python 3.12） |
| **Application Insights** | OpenTelemetry 統合 |
| **SQL Database in Fabric** | 会話履歴 + ビジネスデータ |

### 7. CI/CD & テスト

| 機能 | 説明 |
|------|------|
| **GitHub Actions** | Build & Deploy（Docker → ACR → App Service）、Test & Lint、Security Scan |
| **Python テスト** | 37 ユニットテスト（pytest、4ファイル） |
| **Ruff Lint** | PR マージ条件として必須 |
| **テストスクリプト** | `.\scripts\test.ps1` でワンコマンド実行 |

### 8. コードリファクタリング

| 対象 | 内容 |
|------|------|
| **Chat.tsx** | 1ファイル → 5サブコンポーネントに分割 |
| **ChatMessage.tsx** | 529行 → 77行（AssistantMessage/UserMessage 分離） |
| **useChatAPI.ts** | Chat.tsx から API ロジックを分離 |
| **chatHistoryUtils.ts** | ChatHistoryListItemCell からユーティリティ関数を抽出 |
| **LazyImage / Chart.js** | React.lazy + Suspense で遅延読み込み |

---

## 📊 数字で見る追加開発

| 指標 | 値 |
|------|-----|
| 追加コミット数 | 235 |
| src/ 変更行数 | +20,189 / -7,773 |
| infra/ 変更行数 | +30,982 / -16,311 |
| 変更ファイル数 | src/ 195ファイル、infra/ 91ファイル |
| ユニットテスト | 37テスト / 4ファイル |
| エージェントモード | 4種類 |
| 統合ツール | 8個（SQL + Doc + Web + MCP×5） |

---

## 🎯 デモのポイント

「**1つのチャット画面から、SQLデータ・社内文書・Web情報・高度分析を横断的に使って、経営レベルのレポートを自動生成する**」

```
ユーザー: 「経営会議向けのエグゼクティブレポートを作成して」

エージェント:
  1. SQL → 売上・顧客・在庫データ取得
  2. MCP → 前年比/RFM/在庫分析を実行
  3. Doc → 製品仕様書を RAG 検索
  4. Web → 市場動向・競合情報をリアルタイム検索
  5. 統合レポート + グラフを生成
```

詳細なテストシナリオは [TestScenarios-MultiTool.md](documents/TestScenarios-MultiTool.md) を参照。
