---
mode: agent
description: Solution Acceleratorの開発環境をセットアップ
---

# Setup Environment

Solution Accelerator の開発環境をセットアップします。

## Step 1: 前提条件確認

```bash
az --version          # Azure CLI 2.60+
azd version           # Azure Developer CLI 1.21+
docker --version      # Docker
python --version      # Python 3.11+
node --version        # Node.js 18+
```

## Step 2: Azure認証

```bash
az login
azd auth login
```

## Step 3: 環境作成

```bash
azd env new dev
```

## Step 4: デプロイ

```bash
azd up
```

## 完了条件

- [ ] `azd show` でリソースが表示される
- [ ] API ヘルスチェックが成功
- [ ] Frontend が表示される
