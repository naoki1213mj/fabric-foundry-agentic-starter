---
applyTo: "azure.yaml,infra/**/*.bicep,.azure/**/*"
---

# Azure Developer CLI (azd) Guidelines

## azure.yaml 構造

> **重要**: azure.yaml に `services` セクションはありません。
> デプロイは GitHub Actions (`deploy-app-service.yml`) で実施します。
> `azd provision` でインフラのみデプロイ可能です。

```yaml
name: agentic-applications-for-unified-data-foundation
metadata:
  template: microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator

# Note: services セクションはなし。
# デプロイは GitHub Actions（deploy-app-service.yml）で実施。
# azd provision でインフラのみデプロイ可能。

infra:
  provider: bicep
  path: ./infra
  module: main
```

## コマンド一覧

```bash
# 認証
azd auth login

# 環境作成
azd env new dev
azd env select dev

# デプロイ
 azd up                    # 全て（provision + deploy）
azd provision             # インフラのみ
# azd deploy は services セクションがないため使用不可。
# アプリデプロイは git push → GitHub Actions で自動実行されます。

# 確認
azd show                  # リソース一覧
azd monitor               # ログ確認

# クリーンアップ
azd down                  # 全リソース削除
azd down --purge          # 完全削除（Soft Delete含む）
```

## 環境変数

```bash
# .azure/{env}/.env
AZURE_LOCATION=japaneast
AZURE_SUBSCRIPTION_ID=xxx
AZURE_RESOURCE_GROUP=rg-aiagent-dev-jpe
AZURE_OPENAI_ENDPOINT=https://oai-xxx.openai.azure.com/
```

## Bicep との連携

```bicep
// infra/main.bicep
param name string
param location string = resourceGroup().location

// azd が自動的に環境変数をパラメータとして渡す
module api './modules/container-app.bicep' = {
  name: 'api'
  params: {
    name: '${name}-api'
    location: location
  }
}

output API_ENDPOINT string = api.outputs.endpoint
```
