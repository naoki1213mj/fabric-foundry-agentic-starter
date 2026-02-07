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

## 2. 訴求ポイント確認

| ポイント | 確認事項 | チェック |
|----------|----------|----------|
| Why MS | Fabric + Foundry + Agent Framework | [ ] |
| Why Now | Agent Framework GA / Guardrails | [ ] |
| 統合 | AI + Data + Infra + Security + GitHub | [ ] |
| 即時 PoC | azd up 一発でエンドツーエンド環境構築 | [ ] |

## 3. デモシナリオ

- [ ] デモシナリオ確認
- [ ] 自然言語クエリのデモ
- [ ] Guardrails発動デモ
- [ ] DEMO_MODE確認

## 4. バックアップ

```bash
export DEMO_MODE=true
# ネットワーク障害時でも動作確認
```
