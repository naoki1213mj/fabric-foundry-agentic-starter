# GitHub Actions CI/CD セットアップガイド

このドキュメントでは、GitHub Actionsを使用してフロントエンド(Web)とバックエンド(API)を自動的にAzure App Serviceにデプロイする方法を説明します。

## 概要

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CI/CD Pipeline Flow                                  │
│                                                                              │
│   Developer                                                                  │
│      │                                                                       │
│      ▼ git push                                                              │
│   ┌──────────────────┐                                                      │
│   │   GitHub Repo    │                                                      │
│   │   (main branch)  │                                                      │
│   └────────┬─────────┘                                                      │
│            │ trigger                                                         │
│            ▼                                                                 │
│   ┌──────────────────┐                                                      │
│   │  GitHub Actions  │                                                      │
│   │  ┌────────────┐  │                                                      │
│   │  │ Detect     │  │                                                      │
│   │  │ Changes    │  │                                                      │
│   │  └─────┬──────┘  │                                                      │
│   │        │         │                                                      │
│   │   ┌────┴────┐    │                                                      │
│   │   ▼         ▼    │                                                      │
│   │ ┌─────┐ ┌─────┐  │                                                      │
│   │ │Build│ │Build│  │                                                      │
│   │ │ Web │ │ API │  │                                                      │
│   │ └──┬──┘ └──┬──┘  │                                                      │
│   │    │       │     │                                                      │
│   │    ▼       ▼     │                                                      │
│   │  ┌───────────┐   │                                                      │
│   │  │   Push    │   │                                                      │
│   │  │ to ACR    │   │                                                      │
│   │  └─────┬─────┘   │                                                      │
│   │        │         │                                                      │
│   │   ┌────┴────┐    │                                                      │
│   │   ▼         ▼    │                                                      │
│   │ ┌─────┐ ┌─────┐  │                                                      │
│   │ │Deploy│ │Deploy│ │                                                      │
│   │ │ Web │ │ API │  │                                                      │
│   │ └──┬──┘ └──┬──┘  │                                                      │
│   │    │       │     │                                                      │
│   │    ▼       ▼     │                                                      │
│   │  ┌───────────┐   │                                                      │
│   │  │  Health   │   │                                                      │
│   │  │  Check    │   │                                                      │
│   │  └───────────┘   │                                                      │
│   └──────────────────┘                                                      │
│            │                                                                 │
│            ▼                                                                 │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                     Azure Resources                                   │  │
│   │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐  │  │
│   │  │     ACR      │   │  App Service │   │     App Service          │  │  │
│   │  │  da-app      │──▶│   Frontend   │   │         API              │  │  │
│   │  │  da-api      │──▶│              │   │                          │  │  │
│   │  └──────────────┘   └──────────────┘   └──────────────────────────┘  │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 前提条件

- GitHubリポジトリへの管理者アクセス
- Azure サブスクリプション
- 以下のAzureリソースがデプロイ済み:
  - Azure Container Registry (ACR)
  - Azure App Service (Frontend)
  - Azure App Service (API)

## 1. GitHub Secrets の設定

リポジトリの **Settings > Secrets and variables > Actions > Secrets** で以下を設定：

| Secret名 | 説明 | 取得方法 |
|----------|------|----------|
| `ACR_LOGIN_SERVER` | ACRのログインサーバー | `az acr show --name <ACR_NAME> --query loginServer -o tsv` |
| `ACR_USERNAME` | ACRのユーザー名 | `az acr credential show --name <ACR_NAME> --query username -o tsv` |
| `ACR_PASSWORD` | ACRのパスワード | `az acr credential show --name <ACR_NAME> --query passwords[0].value -o tsv` |

### Azure CLI でのSecrets取得例

```powershell
# ACR名を設定
$ACR_NAME = "<your-acr-name>"

# Secrets の値を取得
az acr show --name $ACR_NAME --query loginServer -o tsv
az acr credential show --name $ACR_NAME --query username -o tsv
az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv
```

## 2. GitHub Variables の設定

リポジトリの **Settings > Secrets and variables > Actions > Variables** で以下を設定：

| Variable名 | 説明 | 例 |
|------------|------|-----|
| `AZURE_CLIENT_ID` | サービスプリンシパルのClient ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_TENANT_ID` | Azure AD テナント ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_SUBSCRIPTION_ID` | Azure サブスクリプション ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `FRONTEND_APP_NAME` | Frontend App Service名 | `app-<your-suffix>` |
| `API_APP_NAME` | API App Service名 | `api-<your-suffix>` |
| `RESOURCE_GROUP` | リソースグループ名 | `<your-resource-group>` |

## 3. OIDC認証の設定（推奨）

### 3.1 Azure AD アプリ登録の作成

```bash
# アプリ登録を作成
az ad app create --display-name "github-actions-cicd"

# 出力されたappIdを記録
APP_ID="<出力されたappId>"

# サービスプリンシパルを作成
az ad sp create --id $APP_ID
```

### 3.2 Federated Credential の追加

```bash
# mainブランチ用
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<YOUR_ORG>/<YOUR_REPO>:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# environment用 (dev)
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-env-dev",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<YOUR_ORG>/<YOUR_REPO>:environment:dev",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### 3.3 ロール割り当て

```bash
# リソースグループへのContributor権限
az role assignment create \
  --assignee $APP_ID \
  --role "Contributor" \
  --scope "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<your-resource-group>"

# ACRへのPush権限
az role assignment create \
  --assignee $APP_ID \
  --role "AcrPush" \
  --scope "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<your-resource-group>/providers/Microsoft.ContainerRegistry/registries/<ACR_NAME>"
```

## 4. GitHub Environment の設定（オプション）

本番デプロイの承認フローを設定する場合：

### Settings > Environments で作成：

| Environment | 保護ルール |
|-------------|-----------|
| `dev` | なし（自動デプロイ） |
| `staging` | Required reviewers: 1名 |
| `prod` | Required reviewers: 2名 + Wait timer: 15分 |

## 5. ワークフローのトリガー

### 自動トリガー
- `main` ブランチへのプッシュ時
- `src/App/**` または `src/api/python/**` 配下のファイル変更時

### 手動トリガー
1. GitHub の **Actions** タブに移動
2. **Build and Deploy to Azure App Service** ワークフローを選択
3. **Run workflow** をクリック
4. オプションを選択して実行

## 6. ワークフローファイル

`.github/workflows/deploy-app-service.yml` に完全なワークフローが定義されています。

### 主要なジョブ：

| ジョブ | 説明 |
|--------|------|
| `detect-changes` | 変更されたファイルを検出 |
| `build-frontend` | Frontend Dockerイメージをビルド・プッシュ |
| `build-api` | API Dockerイメージをビルド・プッシュ |
| `deploy-frontend` | Frontend App Serviceにデプロイ |
| `deploy-api` | API App Serviceにデプロイ |
| `health-check` | デプロイ後のヘルスチェック |

## 7. クイックスタート（現在の環境用）

現在デプロイ済みのリソースでCI/CDを有効にする手順：

### Step 1: ACR Secrets を取得

```powershell
# PowerShellで実行
$ACR_NAME = "<your-acr-name>"

Write-Host "ACR_LOGIN_SERVER:" -ForegroundColor Cyan
az acr show --name $ACR_NAME --query loginServer -o tsv

Write-Host "`nACR_USERNAME:" -ForegroundColor Cyan
az acr credential show --name $ACR_NAME --query username -o tsv

Write-Host "`nACR_PASSWORD:" -ForegroundColor Cyan
az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv
```

### Step 2: Azure情報を取得

```powershell
Write-Host "AZURE_SUBSCRIPTION_ID:" -ForegroundColor Cyan
az account show --query id -o tsv

Write-Host "`nAZURE_TENANT_ID:" -ForegroundColor Cyan
az account show --query tenantId -o tsv
```

### Step 3: GitHubで設定

1. リポジトリの **Settings > Secrets and variables > Actions** に移動
2. **Secrets** タブで `ACR_LOGIN_SERVER`, `ACR_USERNAME`, `ACR_PASSWORD` を追加
3. **Variables** タブで以下を追加:
   - `FRONTEND_APP_NAME`: `app-<your-suffix>`
   - `API_APP_NAME`: `api-<your-suffix>`
   - `RESOURCE_GROUP`: `<your-resource-group>`

### Step 4: ワークフローをプッシュ

```bash
git add .github/workflows/deploy-app-service.yml
git commit -m "Add CI/CD workflow for Azure App Service deployment"
git push origin main
```

## 8. トラブルシューティング

### ACRログインエラー
```
Error: Failed to login to Azure Container Registry
```
→ `ACR_LOGIN_SERVER`, `ACR_USERNAME`, `ACR_PASSWORD` の値を確認

### App Service デプロイエラー
```
Error: Failed to deploy to App Service
```
→ OIDC認証のFederated Credentialの `subject` が正しいか確認

### ヘルスチェック失敗
→ App Serviceの起動には1-2分かかる場合があります。ログを確認してください。

## 9. 関連リソース

- [GitHub Actions documentation](https://docs.github.com/en/actions)
- [Azure Web Apps Deploy action](https://github.com/Azure/webapps-deploy)
- [Azure Login action](https://github.com/Azure/login)
- [Docker Build and Push action](https://github.com/docker/build-push-action)
