"""
Chart Instructions

全エージェント共通のグラフ出力ルール。
Chart.js JSON形式でのグラフ生成指示を一元管理。
"""

CHART_INSTRUCTIONS = """
## グラフ出力ルール（Chart.js JSON形式）

### 基本形式（単一グラフ）
回答の最後にMarkdownコードブロック（```json```）で出力:

```json
{
  "type": "bar",
  "data": {
    "labels": ["A", "B", "C"],
    "datasets": [{
      "label": "売上",
      "data": [100, 200, 300],
      "backgroundColor": ["#4e79a7", "#f28e2c", "#e15759"]
    }]
  },
  "options": {
    "responsive": true,
    "plugins": { "title": { "display": true, "text": "タイトル" } }
  }
}
```

### 複数グラフ形式（レポート・ダッシュボード型の回答時）
複合的なレポートやダッシュボードを求められた場合は、複数のグラフをまとめて出力可能:

```json
{
  "charts": [
    {
      "id": "chart1",
      "type": "line",
      "data": { "labels": [...], "datasets": [...] },
      "options": { ... }
    },
    {
      "id": "chart2",
      "type": "bar",
      "data": { "labels": [...], "datasets": [...] },
      "options": { ... }
    },
    {
      "id": "chart3",
      "type": "doughnut",
      "data": { "labels": [...], "datasets": [...] },
      "options": { ... }
    }
  ]
}
```

### グラフタイプの選び方

| タイプ | type値 | 推奨用途 |
|--------|--------|----------|
| 棒グラフ | `"bar"` | カテゴリ比較、ランキング |
| 横棒グラフ | `"bar"` + `"indexAxis": "y"` | 長いラベル名、多カテゴリ |
| 円グラフ | `"pie"` | 構成比（5項目以下推奨） |
| ドーナツ | `"doughnut"` | 構成比（中央にサマリー） |
| 折れ線 | `"line"` | 時系列、トレンド、推移 |
| 複合 | datasets内で `type` 指定 | 棒+折れ線の組み合わせ |

### カラーパレット（推奨）
- メイン: `#3b82f6`（青）, `#10b981`（緑）, `#f59e0b`（黄）, `#ef4444`（赤）, `#8b5cf6`（紫）
- サブ: `#6366f1`, `#14b8a6`, `#f97316`, `#ec4899`, `#06b6d4`

### 判断基準
- 単純な質問（TOP5、月別推移など） → 単一グラフ
- レポート、ダッシュボード、エグゼクティブサマリー → 複数グラフ（`"charts"` 配列）
- 「グラフを多用して」「視覚的にわかりやすく」→ 複数グラフ

### 禁止事項
- Vega-Lite形式は使用禁止（Chart.js JSON形式のみ）
- 同じデータの重複グラフは出力しない
"""
