---
mode: agent
description: azd を使用してAzureにデプロイ
---

# Deploy with azd

## Step 1: 認証

```bash
az login
azd auth login
```

## Step 2: 環境設定

```bash
azd env new prod
azd env set AZURE_LOCATION japaneast
```

## Step 3: デプロイ

```bash
azd up
```

## Step 4: 確認

```bash
# リソース確認
azd show

# ログ確認
azd monitor

# API テスト
curl $(azd env get-values | grep API_ENDPOINT | cut -d= -f2)/health
```

## トラブルシューティング

```bash
# 再デプロイ
azd deploy --service api

# インフラのみ再作成
azd provision

# 完全削除して再作成
azd down --purge
azd up
```
