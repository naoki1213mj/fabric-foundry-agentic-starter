# マルチツール統合テストシナリオ

> **目的**: エージェントが1ターン内で複数のツール（SQL + MCP分析ツール）を組み合わせて回答できることを検証する
>
> **作成日**: 2026-02-04

---

## 📊 利用可能なツール一覧

### 1. データ取得ツール

| ツール | 機能 |
|--------|------|
| `run_sql_query` | Fabric SQLからビジネスデータを取得 |
| `search_web` | Web検索で最新情報を取得 |
| `search_documents` | 製品仕様書PDFから情報を取得 |

### 2. MCP分析ツール（計算・分析）

| カテゴリ | ツール | 機能 |
|----------|--------|------|
| **売上分析** | `calculate_yoy_growth` | 前年同期比成長率 |
|  | `calculate_mom_growth` | 前月比成長率 |
|  | `calculate_moving_average` | 移動平均（トレンド） |
|  | `calculate_abc_analysis` | ABC分析（重点商品特定） |
|  | `calculate_sales_forecast` | 売上予測 |
| **顧客分析** | `calculate_rfm_score` | RFM分析スコアリング |
|  | `classify_customer_segment` | 顧客セグメント分類 |
|  | `calculate_clv` | 顧客生涯価値 |
|  | `recommend_next_action` | Next Best Action |
| **在庫分析** | `calculate_inventory_turnover` | 在庫回転率 |
|  | `calculate_reorder_point` | 発注点計算 |
|  | `identify_slow_moving_inventory` | 滞留在庫特定 |
| **製品分析** | `compare_products` | 製品比較 |
|  | `calculate_price_performance` | コスパ分析 |
|  | `calculate_bundle_discount` | バンドル割引計算 |

---

## 🎯 テストシナリオ

### シナリオ 1: 重点商品分析（SQL → ABC分析）

**難易度**: ⭐⭐（中級）

**クエリ**:

```
Mountain Bikeカテゴリの全製品について、売上データを取得してABC分析を行い、
A・B・Cランクごとの売上比率と重点管理すべき製品を特定してください。
```

**期待される処理フロー**:

1. `run_sql_query`: Mountain Bikeカテゴリの製品別売上を取得
2. `calculate_abc_analysis`: 取得データでABC分析を実行

**期待される回答内容**:

- A ランク商品（売上上位80%）: 製品名、売上、構成比
- B ランク商品（売上次の15%）: 製品名、売上、構成比
- C ランク商品（売上下位5%）: 製品名、売上、構成比
- 経営への示唆（Aランクは在庫切れ防止、Cランクは見直し等）

---

### シナリオ 2: 成長率分析（SQL → YoY/MoM成長率計算）

**難易度**: ⭐⭐（中級）

**クエリ**:

```
2024年と2025年のRoad Bikeカテゴリの売上を比較して、
前年同期比成長率（YoY）を計算し、成長要因を分析してください。
グラフも付けてください。
```

**期待される処理フロー**:

1. `run_sql_query`: 2024年のRoad Bike売上を取得
2. `run_sql_query`: 2025年のRoad Bike売上を取得
3. `calculate_yoy_growth`: 年間成長率を計算
4. `calculate_mom_growth`: 月別成長率を計算（オプション）

**期待される回答内容**:

- 2024年 vs 2025年の売上比較表
- YoY成長率（%）
- 月別の成長トレンドグラフ（Chart.js JSON）
- 成長/減少の要因分析

---

### シナリオ 3: 顧客価値分析（SQL → RFM → セグメント → CLV）

**難易度**: ⭐⭐⭐（上級）

**クエリ**:

```
過去1年間で最も購入頻度が高い顧客TOP10を特定し、
それぞれのRFMスコア、顧客セグメント、顧客生涯価値（CLV）を計算して、
優良顧客維持のためのNext Best Actionを提案してください。
```

**期待される処理フロー**:

1. `run_sql_query`: 顧客別の購入データを取得（Recency, Frequency, Monetary）
2. `calculate_rfm_score`: 各顧客のRFMスコアを計算
3. `classify_customer_segment`: セグメント分類（Champions, Loyal, At Risk等）
4. `calculate_clv`: 顧客生涯価値を計算
5. `recommend_next_action`: 各セグメントへのアクション提案

**期待される回答内容**:

| 顧客 | Recency | Frequency | Monetary | RFMスコア | セグメント | CLV | 推奨アクション |
|------|---------|-----------|----------|-----------|------------|-----|----------------|
| A氏 | 5日前 | 15回 | $5,000 | 555 | Champion | $15,000 | VIPプログラム招待 |
| B氏 | 30日前 | 8回 | $2,500 | 443 | Loyal | $8,000 | クロスセル提案 |
| ... | ... | ... | ... | ... | ... | ... | ... |

---

### シナリオ 4: 在庫最適化分析（SQL → 回転率 → 発注点 → 滞留在庫）

**難易度**: ⭐⭐⭐（上級）

**クエリ**:

```
全カテゴリの在庫状況を分析して、
在庫回転率が低い製品を特定し、適正な発注点と滞留在庫のリスクを評価してください。
改善提案も含めてレポートにまとめてください。
```

**期待される処理フロー**:

1. `run_sql_query`: 製品別の販売数量と在庫データを取得
2. `calculate_inventory_turnover`: 在庫回転率を計算
3. `calculate_reorder_point`: 適正発注点を計算
4. `identify_slow_moving_inventory`: 滞留在庫を特定

**期待される回答内容**:

- 在庫回転率ランキング（高い順/低い順）
- 滞留在庫リスト（回転率 < 2.0 の製品）
- 発注点の見直し提案
- 在庫削減による財務インパクト試算

---

### シナリオ 5: 総合ダッシュボード（SQL × 複数MCP）

**難易度**: ⭐⭐⭐⭐（エキスパート）

**クエリ**:

```
経営会議向けに、以下の内容を含む月次レポートを作成してください：

1. 売上サマリー（前年比、前月比の成長率付き）
2. カテゴリ別ABC分析
3. 顧客セグメント分布とCLV上位顧客
4. 在庫健全性スコア

グラフを多用して視覚的にわかりやすくしてください。
```

**期待される処理フロー**:

1. `run_sql_query`: 月次売上データを取得
2. `calculate_yoy_growth`: 前年比成長率
3. `calculate_mom_growth`: 前月比成長率
4. `run_sql_query`: カテゴリ別売上を取得
5. `calculate_abc_analysis`: ABC分析
6. `run_sql_query`: 顧客購買データを取得
7. `calculate_rfm_score`: RFMスコア計算
8. `classify_customer_segment`: セグメント分類
9. `calculate_clv`: CLV計算
10. `run_sql_query`: 在庫データを取得
11. `calculate_inventory_turnover`: 在庫回転率

**期待される回答内容**:

```markdown
# 📊 月次経営レポート（2025年1月）

## 1. 売上サマリー
- 当月売上: $XXX,XXX
- 前年同月比: +XX.X%（↑成長）
- 前月比: +X.X%

[売上推移グラフ - Chart.js]

## 2. カテゴリ別ABC分析
| ランク | カテゴリ数 | 売上構成比 | 主要カテゴリ |
|--------|-----------|------------|--------------|
| A | 3 | 80% | Mountain Bike, Road Bike, E-Bike |
| B | 5 | 15% | Accessories, Clothing... |
| C | 10 | 5% | Parts, Tools... |

[ABC分析グラフ - Chart.js]

## 3. 顧客分析
### セグメント分布
[円グラフ - Champions: 15%, Loyal: 25%, ...]

### CLV上位顧客
| 顧客 | セグメント | CLV | 推奨アクション |
|------|------------|-----|----------------|
| ... | ... | ... | ... |

## 4. 在庫健全性
- 在庫回転率（平均）: X.X回/年
- 滞留在庫: X製品（$XX,XXX相当）
- 発注点見直し推奨: X製品

[在庫健全性ヒートマップ]

## 5. 経営への提言
1. ...
2. ...
3. ...
```

---

### シナリオ 6: 製品比較＋コスパ分析（SQL → 比較 → コスパ）

**難易度**: ⭐⭐（中級）

**クエリ**:

```
Mountain-100とMountain-200を比較して、
売上実績、価格帯、コストパフォーマンスを分析し、
どちらを重点的に販促すべきか提案してください。
```

**期待される処理フロー**:

1. `run_sql_query`: Mountain-100の売上・価格データを取得
2. `run_sql_query`: Mountain-200の売上・価格データを取得
3. `compare_products`: 製品スペック・売上比較
4. `calculate_price_performance`: コスパ指標計算

**期待される回答内容**:

| 項目 | Mountain-100 | Mountain-200 | 優位性 |
|------|--------------|--------------|--------|
| 単価 | $3,399 | $2,499 | Mountain-200 |
| 売上数量 | 150台 | 280台 | Mountain-200 |
| 売上金額 | $509,850 | $699,720 | Mountain-200 |
| 利益率 | 25% | 20% | Mountain-100 |
| コスパスコア | 8.2 | 9.1 | Mountain-200 |

**結論**: Mountain-200は数量・売上で優位だが、利益率はMountain-100が高い。
→ 利益重視ならMountain-100、シェア拡大ならMountain-200を推奨。

---

### シナリオ 7: 売上予測＋移動平均（SQL → 予測）

**難易度**: ⭐⭐⭐（上級）

**クエリ**:

```
E-Bikeカテゴリの過去24ヶ月の売上推移から、
3ヶ月移動平均でトレンドを分析し、
今後6ヶ月の売上を予測してください。
予測の根拠も説明してください。
```

**期待される処理フロー**:

1. `run_sql_query`: E-Bikeの過去24ヶ月売上データを取得
2. `calculate_moving_average`: 3ヶ月移動平均を計算
3. `calculate_sales_forecast`: 今後6ヶ月の売上予測

**期待される回答内容**:

- 過去24ヶ月の売上推移グラフ（実績 + 移動平均線）
- トレンド分析（上昇/下降/横ばい）
- 今後6ヶ月の予測値（月別）
- 予測の信頼区間
- 予測に影響する要因（季節性、市場動向等）

---

## 📋 マルチターンシナリオ

### マルチターン 1: 深掘り分析

**ターン1**:

```
ユーザー: Mountain Bikeカテゴリの2024年売上を教えて
```

→ `run_sql_query` で売上データ取得

**ターン2**:

```
ユーザー: その中でABC分析をして、Aランク製品を特定して
```

→ `calculate_abc_analysis` で分析（前ターンのデータを活用）

**ターン3**:

```
ユーザー: Aランク製品の在庫回転率も確認して、発注点を計算して
```

→ `run_sql_query` + `calculate_inventory_turnover` + `calculate_reorder_point`

**ターン4**:

```
ユーザー: これらをまとめて経営レポートにして
```

→ 全ての結果を統合してレポート生成

---

### マルチターン 2: 顧客分析の深掘り

**ターン1**:

```
ユーザー: 過去1年間の顧客別購入金額TOP20を教えて
```

→ `run_sql_query`

**ターン2**:

```
ユーザー: それぞれのRFMスコアとセグメントを分析して
```

→ `calculate_rfm_score` + `classify_customer_segment`

**ターン3**:

```
ユーザー: セグメントごとのCLVと推奨アクションを提案して
```

→ `calculate_clv` + `recommend_next_action`

**ターン4**:

```
ユーザー: At Riskセグメントの顧客に対するリテンション施策を詳しく教えて
```

→ 分析結果を踏まえた施策提案

---

## ✅ 検証チェックリスト

各シナリオで以下を確認：

- [ ] 複数ツールが正しく呼び出されている
- [ ] ツール間でデータが正しく受け渡されている
- [ ] 結果が1つの統合された回答にまとまっている
- [ ] グラフ（Chart.js JSON）が適切に生成されている
- [ ] 経営判断に役立つ示唆が含まれている
- [ ] レスポンス時間が許容範囲内（目安: 30秒以内）

---

## 🚀 クイックテストコマンド

### PowerShellでテスト

```powershell
# シナリオ1: ABC分析テスト
$body = @{
    query = "Mountain Bikeカテゴリの全製品について売上データを取得してABC分析を行い、Aランク製品を特定してください"
    conversation_id = "test-abc-001"
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "https://api-daj6dri4yf3k3z.azurewebsites.net/api/chat" `
    -Method POST -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 120
```

```powershell
# シナリオ3: 顧客RFM分析テスト
$body = @{
    query = "過去1年間で最も購入頻度が高い顧客TOP10のRFMスコアとセグメントを分析し、CLVを計算してください"
    conversation_id = "test-rfm-001"
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "https://api-daj6dri4yf3k3z.azurewebsites.net/api/chat" `
    -Method POST -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 120
```

```powershell
# シナリオ5: 総合ダッシュボードテスト
$body = @{
    query = "経営会議向けに、売上サマリー（前年比・前月比の成長率付き）、カテゴリ別ABC分析、顧客セグメント分布、在庫健全性を含む月次レポートを作成してください"
    conversation_id = "test-dashboard-001"
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "https://api-daj6dri4yf3k3z.azurewebsites.net/api/chat" `
    -Method POST -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 180
```

---

## 📝 注意事項

1. **タイムアウト設定**: 複雑なシナリオは処理に時間がかかるため、タイムアウトを120〜180秒に設定
2. **トークン制限**: 大量のデータを扱う場合、結果が切り詰められる可能性あり
3. **MCP依存**: MCPサーバーが停止していると分析ツールが使用不可
4. **コスト考慮**: GPT-5の複数回呼び出しはトークンコストが高い

---

## 関連ドキュメント

- [Testing-Guide.md](Testing-Guide.md)
- [TechnicalArchitecture.md](TechnicalArchitecture.md)
- [DEMO.md](../DEMO.md)
