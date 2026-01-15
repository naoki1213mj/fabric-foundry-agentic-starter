---
mode: agent
description: デモ前の最終チェック
---

# Final Check

## 1. ヘルスチェック

```bash
# API
curl $API_ENDPOINT/health

# Frontend
curl $FRONTEND_ENDPOINT
```

## 2. 審査基準確認

| 基準 | 確認事項 | チェック |
|------|----------|----------|
| Why MS | Fabric + Foundry + Agent Framework | [ ] |
| Why Now | Agent Framework GA / Guardrails | [ ] |
| 統合 | AI + Data + Infra + Security + GitHub | [ ] |
| ACR | Fabric F2 + OpenAI 従量課金 | [ ] |

## 3. デモシナリオ

- [ ] 30秒ピッチ暗記
- [ ] 自然言語クエリのデモ
- [ ] Guardrails発動デモ
- [ ] DEMO_MODE確認

## 4. バックアップ

```bash
export DEMO_MODE=true
# ネットワーク障害時でも動作確認
```
