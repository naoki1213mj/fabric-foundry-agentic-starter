# Next Steps after Initial Setup

## Table of Contents

1. [Deployment Methods](#deployment-methods)
2. [What was added](#what-was-added)
3. [Billing](#billing)
4. [Troubleshooting](#troubleshooting)

## Deployment Methods

### Option 1: GitHub Actions (推奨)

このプロジェクトでは **GitHub Actions** による自動デプロイを使用しています。

```bash
# コード変更をコミット
git add .
git commit -m "feat: 機能追加"

# プッシュ = 自動デプロイ
git push
```

デプロイワークフロー:
- `src/App/**` 変更 → Frontend (App Service) デプロイ
- `src/api/python/**` 変更 → API (App Service) デプロイ

詳細: [GitHubActionsSetup.md](./documents/GitHubActionsSetup.md)

### Option 2: azd up (初回セットアップ用)

インフラのプロビジョニングには `azd up` を使用します。

```bash
azd auth login
azd up
```

## What was added

### Infrastructure configuration

```yaml
- azure.yaml        # azd project configuration
- infra/            # Infrastructure-as-code Bicep files
  - main.bicep      # Main deployment template
  - main.parameters.json  # Deployment parameters
  - deploy_*.bicep  # Module files
```

The resources declared in [main.bicep](./infra/main.bicep) are provisioned when running `azd up` or `azd provision`.
This includes:

- **Azure App Service** (Frontend) - React アプリケーション
- **Azure App Service** (API) - Python FastAPI バックエンド
- **Azure Container Registry** - Docker イメージ管理
- **Azure AI Foundry** - エージェントサービス
- **Azure AI Services** - GPT-5 モデル
- **Application Insights** - 監視・ログ

More information about [Bicep](https://aka.ms/bicep) language.

### Build with Docker

Frontend と API は Docker イメージとしてビルドされ、Azure Container Registry にプッシュされます。

```bash
# ローカルでDockerイメージをビルド
docker build -t frontend -f src/App/WebApp.Dockerfile src/App
docker build -t api -f src/api/python/app.Dockerfile src/api/python
```

## Billing

Visit the *Cost Management + Billing* page in Azure Portal to track current spend. For more information about how you're billed, and how you can monitor the costs incurred in your Azure subscriptions, visit [billing overview](https://learn.microsoft.com/azure/developer/intro/azure-developer-billing).

## Troubleshooting

Q: I visited the service endpoint listed, and I'm seeing a blank page, a generic welcome page, or an error page.

A: Your service may have failed to start, or it may be missing some configuration settings. To investigate further:

1. Run `azd show`. Click on the link under "View in Azure Portal" to open the resource group in Azure Portal.
2. Navigate to the specific **App Service** that is failing to deploy.
3. Check **Deployment Center** for deployment logs.
4. Review **Log stream** for runtime errors.
5. Check **Application Insights** for detailed traces and exceptions.

For more troubleshooting information, visit [App Service troubleshooting](https://learn.microsoft.com/azure/app-service/troubleshoot-diagnostic-logs).

### Additional information

For additional information about setting up your `azd` project, visit our official [docs](https://learn.microsoft.com/azure/developer/azure-developer-cli/make-azd-compatible?pivots=azd-convert).
