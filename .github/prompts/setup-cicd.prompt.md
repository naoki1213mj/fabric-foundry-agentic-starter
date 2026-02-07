---
mode: agent
description: "GitHub Actions CI/CDパイプラインをセットアップする"
tools: ["terminal", "editFiles", "codebase"]
---

# /setup-cicd - CI/CD パイプラインセットアップ

## 目的

GitHub Actions + Azure OIDC認証でCI/CDパイプラインをセットアップします。

---

## Step 1: Azure OIDC認証の設定

### 1.1 アプリ登録の作成

```bash
# Azure CLI でログイン
az login

# アプリ登録を作成
az ad app create --display-name "github-oidc"

# 出力されるappIdを記録
APP_ID="<出力されたappId>"

# サービスプリンシパルを作成
az ad sp create --id $APP_ID
```

### 1.2 Federated Credentialの追加

```bash
# YOUR_ORG/YOUR_REPO を実際のリポジトリ名に置換

# mainブランチ用
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_ORG/YOUR_REPO:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# staging環境用
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-env-staging",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_ORG/YOUR_REPO:environment:staging",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# prod環境用
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-env-prod",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_ORG/YOUR_REPO:environment:prod",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### 1.3 ロール割り当て

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# リソースグループへのContributor権限
az role assignment create \
  --assignee $APP_ID \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID"

# Azure OpenAI権限（必要な場合）
az role assignment create \
  --assignee $APP_ID \
  --role "Cognitive Services OpenAI User" \
  --scope "/subscriptions/$SUBSCRIPTION_ID"
```

---

## Step 2: GitHub Variables の設定

GitHubリポジトリの Settings > Secrets and variables > Actions > Variables で設定：

| Name | Value | 取得コマンド |
|------|-------|-------------|
| `AZURE_CLIENT_ID` | `<APP_ID>` | `az ad app list --display-name "github-oidc" --query "[0].appId" -o tsv` |
| `AZURE_TENANT_ID` | `<TENANT_ID>` | `az account show --query tenantId -o tsv` |
| `AZURE_SUBSCRIPTION_ID` | `<SUBSCRIPTION_ID>` | `az account show --query id -o tsv` |

---

## Step 3: GitHub Environments の設定

Settings > Environments で以下を作成：

### dev 環境
- Protection rules: なし

### staging 環境
- Protection rules: Required reviewers (1名)

### prod 環境
- Protection rules: Required reviewers (2名)
- Wait timer: 15 minutes（オプション）

---

## Step 4: ワークフローの確認

```bash
# ワークフローファイルの確認
ls -la .github/workflows/

# 期待されるファイル:
# - ci.yml          (PRチェック)
# - deploy.yml      (dev デプロイ)
# - deploy-prod.yml (staging/prod デプロイ)
# - security-scan.yml (セキュリティスキャン)
# - e2e-test.yml    (E2Eテスト)
```

---

## Step 5: 動作確認

### 5.1 手動でワークフロー実行

```bash
# GitHub CLI でワークフロー実行
gh workflow run deploy.yml
gh run list --workflow=deploy.yml
```

### 5.2 PRを作成してCIを確認

```bash
git checkout -b test/ci-check
echo "# Test" >> README.md
git add . && git commit -m "test: CI check"
git push origin test/ci-check
gh pr create --title "Test CI" --body "CI確認用"
```

### 5.3 セキュリティスキャン確認

```bash
gh workflow run security-scan.yml
# GitHub Security タブで結果を確認
```

---

## 完了チェックリスト

- [ ] Azure アプリ登録が作成された
- [ ] Federated Credential が設定された（main, staging, prod）
- [ ] ロール割り当てが完了（Contributor, OpenAI User）
- [ ] GitHub Variables が設定された（3つ）
- [ ] GitHub Environments が作成された（dev, staging, prod）
- [ ] CI ワークフローがPRで動作する
- [ ] Deploy ワークフローがmainプッシュで動作する
- [ ] Security タブにスキャン結果が表示される

---

## トラブルシューティング

### OIDC認証が失敗する

1. Federated Credential の `subject` が正しいか確認
   - リポジトリ名: `repo:OWNER/REPO:ref:refs/heads/main`
   - 環境名: `repo:OWNER/REPO:environment:prod`
2. `permissions.id-token: write` があるか確認

### azd up が失敗する

```bash
# クォータ確認
az vm list-usage --location japaneast --output table

# リソースグループ権限確認
az role assignment list --assignee $APP_ID --output table

# 完全削除して再作成
azd down --purge
azd up
```

### Security スキャンが失敗する

```bash
# 手動でセキュリティツール実行
pip install bandit pip-audit
bandit -r src/api/ -f json
pip-audit -r src/api/requirements.txt
```

---

## 参考コマンド

```bash
# 現在のAzure設定確認
az account show
az ad app list --display-name "hackathon" --output table

# GitHub CLI 設定
gh auth login
gh repo view

# ワークフロー一覧
gh workflow list
gh run list
```
