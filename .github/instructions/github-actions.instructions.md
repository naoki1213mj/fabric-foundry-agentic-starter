---
applyTo: "**/.github/workflows/*.yml,**/azure.yaml,**/*.bicep"
---

# GitHub Actions & CI/CD Instructions

## 概要

このプロジェクトのCI/CDパイプラインは以下で構成されています：

- **GitHub Actions**: CI/CD ワークフロー
- **Azure Developer CLI (azd)**: デプロイオーケストレーション
- **OIDC認証**: シークレットレスなAzure認証
- **Microsoft Defender for DevOps**: セキュリティスキャン

## ワークフロー構成

```
.github/workflows/
├── test.yml                # PRチェック（lint, test）
├── deploy-app-service.yml  # App Serviceデプロイ（mainブランチ）
└── security-scan.yml       # セキュリティスキャン
```

## OIDC認証の設定

### 前提条件

```bash
# Azure CLI でログイン
az login

# アプリ登録を作成
az ad app create --display-name "github-oidc"

# 出力されたappIdを記録
APP_ID="<出力されたappId>"

# サービスプリンシパルを作成
az ad sp create --id $APP_ID
```

### Federated Credentialの追加

```bash
# mainブランチ用
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_ORG/YOUR_REPO:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# PR用（オプション）
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-pr",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_ORG/YOUR_REPO:pull_request",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# 環境用（staging, prod）
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-env-staging",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_ORG/YOUR_REPO:environment:staging",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### ロール割り当て

```bash
# リソースグループへのContributor権限
az role assignment create \
  --assignee $APP_ID \
  --role "Contributor" \
  --scope "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP>"

# Azure OpenAI権限
az role assignment create \
  --assignee $APP_ID \
  --role "Cognitive Services OpenAI User" \
  --scope "/subscriptions/<SUBSCRIPTION_ID>"
```

### GitHub Variables 設定

リポジトリの Settings > Secrets and variables > Actions > Variables で設定：

| Name | Value |
|------|-------|
| `AZURE_CLIENT_ID` | `<APP_ID>` |
| `AZURE_TENANT_ID` | `<TENANT_ID>` |
| `AZURE_SUBSCRIPTION_ID` | `<SUBSCRIPTION_ID>` |

## ワークフロートリガー

### test.yml
```yaml
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
```

### deploy-app-service.yml
```yaml
on:
  push:
    branches: [main]
  workflow_dispatch:
```

## GitHub Environments の設定

Settings > Environments で以下を作成：

### dev 環境
- Variables: `AZURE_ENV_NAME=dev`
- Protection rules: なし

### staging 環境
- Variables: `AZURE_ENV_NAME=staging`
- Protection rules: Required reviewers (1名)

### prod 環境
- Variables: `AZURE_ENV_NAME=prod`
- Protection rules: Required reviewers (2名)
- Wait timer: 15 minutes

## azd との連携

### GitHub Actions での azd 使用

```yaml
- name: Install azd
  uses: Azure/setup-azd@v2

- name: Azure Login (OIDC)
  uses: azure/login@v2
  with:
    client-id: ${{ vars.AZURE_CLIENT_ID }}
    tenant-id: ${{ vars.AZURE_TENANT_ID }}
    subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

- name: azd auth login
  run: azd auth login --client-id ${{ vars.AZURE_CLIENT_ID }} --federated-credential-provider github

- name: Deploy
  run: azd up --no-prompt
  env:
    AZURE_ENV_NAME: ${{ github.event.inputs.environment || 'dev' }}
```

## セキュリティスキャン統合

### Microsoft Security DevOps

```yaml
- name: Run Microsoft Security DevOps
  uses: microsoft/security-devops-action@v1
  id: msdo
  with:
    tools: bandit,eslint,trivy,terrascan

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: ${{ steps.msdo.outputs.sarifFile }}
```

### GitHub Advanced Security 連携

- SARIF ファイルをアップロードすると Security タブに表示
- コードスキャン結果がPRにコメント
- 脆弱性アラートが自動生成

## ベストプラクティス

### 1. キャッシュの活用

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'  # pip キャッシュ

- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'  # npm キャッシュ
```

### 2. 並列実行

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
  test:
    runs-on: ubuntu-latest
  build:
    runs-on: ubuntu-latest
  # 全ジョブ完了後にサマリー
  summary:
    needs: [lint, test, build]
    if: always()
```

### 3. 条件付き実行

```yaml
- name: Deploy to prod
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
```

### 4. ステップサマリー

```yaml
- name: Summary
  run: |
    echo "## Deploy Results" >> $GITHUB_STEP_SUMMARY
    echo "- Environment: $ENV" >> $GITHUB_STEP_SUMMARY
    echo "- URL: $URL" >> $GITHUB_STEP_SUMMARY
```

## トラブルシューティング

### OIDC認証エラー

```
AADSTS700024: Client assertion is not within its valid time range.
```
→ GitHub Actions の時刻同期問題。リトライで解決。

### azd up タイムアウト

```yaml
- name: Deploy
  run: azd up --no-prompt
  timeout-minutes: 30  # タイムアウト延長
```

### 権限エラー

```yaml
permissions:
  id-token: write      # OIDC認証に必要
  contents: read       # checkout に必要
  security-events: write  # SARIF アップロードに必要
```

## 参考リンク

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Azure Login Action](https://github.com/azure/login)
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [Microsoft Security DevOps](https://learn.microsoft.com/azure/defender-for-cloud/github-action)
