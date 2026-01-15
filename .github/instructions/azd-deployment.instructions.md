---
applyTo: "azure.yaml,infra/**/*.bicep,.azure/**/*"
---

# Azure Developer CLI (azd) Guidelines

## azure.yaml 構造

```yaml
name: agentic-unified-data-foundation
metadata:
  template: microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator

services:
  api:
    project: src/api
    host: containerapp
    language: python
    docker:
      path: ./Dockerfile
      context: .
      remoteBuild: true
    config:
      container:
        resources:
          cpu: "1"
          memory: 2Gi
        scale:
          minReplicas: 0
          maxReplicas: 10
  
  web:
    project: src/web
    host: containerapp
    language: typescript

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
azd deploy                # アプリのみ
azd deploy --service api  # 特定サービスのみ

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
