# MCP Server for Business Analytics

Azure Functions ベースの Model Context Protocol (MCP) サーバー。
エージェントにビジネス分析ツールを提供します。

## 🛠️ 提供ツール（16種類）

### 売上分析（5ツール）
| ツール名 | 説明 |
|---------|------|
| `calculate_yoy_growth` | 前年同期比（YoY）成長率を計算 |
| `calculate_mom_growth` | 前月比（MoM）成長率を計算 |
| `calculate_moving_average` | 移動平均を計算 |
| `calculate_abc_analysis` | ABC分析（パレート分析）を実行 |
| `calculate_sales_forecast` | 線形回帰による売上予測 |

### 製品比較（4ツール）
| ツール名 | 説明 |
|---------|------|
| `compare_products` | 2製品の比較表を生成 |
| `calculate_price_performance` | 価格性能比（コスパ）を計算 |
| `suggest_alternatives` | 代替製品をスコアリング |
| `calculate_bundle_discount` | バンドル割引を計算 |

### 顧客セグメント（4ツール）
| ツール名 | 説明 |
|---------|------|
| `calculate_rfm_score` | RFM分析スコアを計算 |
| `classify_customer_segment` | RFMに基づくセグメント分類 |
| `calculate_clv` | 顧客生涯価値（CLV）を計算 |
| `recommend_next_action` | Next Best Actionを提案 |

### 在庫分析（3ツール）
| ツール名 | 説明 |
|---------|------|
| `calculate_inventory_turnover` | 在庫回転率を計算 |
| `calculate_reorder_point` | 発注点（リオーダーポイント）を算出 |
| `identify_slow_moving_inventory` | 滞留在庫を特定 |

## 🚀 使い方

### ローカル開発

```bash
# 依存関係のインストール
cd src/mcp
pip install -r requirements.txt

# Azure Functions Core Tools でローカル実行
func start
```

### ローカル統合テスト（FastAPI ラッパー使用）

Windows ARM64 環境などで Azure Functions Core Tools が動作しない場合：

```bash
# プロジェクトルートから実行
python run_integration_test.py
```

これにより MCP サーバーが FastAPI で起動し、自動的に統合テストが実行されます。

### Azure Functions へのデプロイ

#### 1. リソースグループの作成（既存の場合はスキップ）

```bash
az group create --name rg-mcp-prod-jpe --location japaneast
```

#### 2. Azure Functions リソースをデプロイ（Bicep）

```bash
az deployment group create \
  --resource-group rg-mcp-prod-jpe \
  --template-file infra/deploy_mcp_function.bicep \
  --parameters \
    location=japaneast \
    functionAppName=func-mcp-aiagent-prod \
    appServicePlanName=plan-mcp-aiagent-prod \
    storageAccountName=stmcpaiagentprod
```

#### 3. コードをデプロイ

```bash
cd src/mcp
func azure functionapp publish func-mcp-aiagent-prod
```

#### 4. API サーバーの環境変数を設定

デプロイ後、API サーバーの環境変数を更新：

```bash
MCP_SERVER_URL=https://func-mcp-aiagent-prod.azurewebsites.net/api/mcp
MCP_ENABLED=true
```

### テスト実行

```bash
cd src/mcp
pytest tests/ -v
```

### MCP エンドポイント

```
POST /api/mcp
Content-Type: application/json

# ツール一覧取得
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}

# ツール実行
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "calculate_yoy_growth",
    "arguments": {
      "current_value": 120000,
      "previous_value": 100000
    }
  }
}
```

## 📁 ファイル構成

```
src/mcp/
├── function_app.py       # Azure Functions エントリポイント
├── mcp_handler.py        # MCP プロトコル処理
├── tools/                # ツール実装
│   ├── __init__.py
│   ├── sales_analysis.py
│   ├── product_comparison.py
│   ├── customer_segment.py
│   └── inventory_analysis.py
├── tests/                # テスト
│   ├── conftest.py
│   ├── test_tools.py
│   └── test_handler.py
├── host.json             # Azure Functions 設定
├── local.settings.json   # ローカル設定
└── requirements.txt      # 依存関係
```

## 🔗 エージェント統合

既存のエージェント（chat.py）との統合：

```python
from semantic_kernel.connectors.mcp import MCPTool

# MCP サーバーに接続
mcp_tools = MCPTool.from_server("http://localhost:7071/api/mcp")

# エージェントにツールを追加
agent = ChatCompletionAgent(
    kernel=kernel,
    plugins=[mcp_tools]
)
```

## 📈 今後の拡張（Phase 2-3）

- [ ] AI Gateway（API Management）統合
- [ ] Fabric SQL Database との直接連携
- [ ] ツール使用ログの Application Insights 出力
- [ ] レート制限とキャッシュ
