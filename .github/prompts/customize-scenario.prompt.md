---
mode: agent
description: 業界シナリオをカスタマイズ
---

# Customize Scenario

Sales Analyst シナリオを業界特化にカスタマイズします。

## 対象

1. **製造業**: 品質管理・予知保全
2. **金融**: リスク分析・コンプライアンス
3. **小売**: 在庫最適化・需要予測
4. **ヘルスケア**: 患者分析・治療推奨

## カスタマイズ箇所

1. `src/api/agents/` - Agent定義
2. `src/api/tools/` - 業界固有Tool
3. `infra/` - 必要に応じてリソース追加
4. `documents/` - シナリオ説明

## 手順

1. 業界を選択
2. Agent の instructions を更新
3. 業界固有の Tool を追加
4. サンプルデータを更新
5. UI のラベルを更新
