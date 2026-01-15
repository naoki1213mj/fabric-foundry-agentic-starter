# GitHub DevOps Skill

## 概要

GitHub Actions + Azure OIDC を活用した DevSecOps パイプライン構築スキル。

## パイプライン構成

```
                    ┌─────────────┐
                    │   PR作成    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   ci.yml    │
                    │  Lint/Test  │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────▼──────┐          ┌──────▼──────┐
       │ security-   │          │   マージ    │
       │ scan.yml    │          │   (main)    │
       └─────────────┘          └──────┬──────┘
                                       │
                                ┌──────▼──────┐
                                │ deploy.yml  │
                                │    (dev)    │
                                └──────┬──────┘
                                       │
                                ┌──────▼──────┐
                                │ e2e-test.yml│
                                └──────┬──────┘
                                       │
                      ┌────────────────┴────────────────┐
                      │      手動 or タグプッシュ       │
                      └────────────────┬────────────────┘
                                       │
                                ┌──────▼──────┐
                                │deploy-prod  │
                                │  (staging)  │
                                └──────┬──────┘
                                       │
                                ┌──────▼──────┐
                                │   承認待ち  │
                                └──────┬──────┘
                                       │
                                ┌──────▼──────┐
                                │deploy-prod  │
                                │   (prod)    │
                                └─────────────┘
```

## OIDC認証パターン

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write    # OIDC必須
      contents: read
    
    steps:
      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      
      - name: azd auth login
        run: |
          azd auth login \
            --client-id ${{ vars.AZURE_CLIENT_ID }} \
            --federated-credential-provider github
```

## セキュリティスキャンパターン

### Microsoft Security DevOps

```yaml
- uses: microsoft/security-devops-action@v1
  with:
    tools: bandit,eslint,trivy,terrascan
```

### 依存関係スキャン

```yaml
# Python
- run: pip-audit -r requirements.txt

# Node.js
- run: npm audit --json
```

### コンテナスキャン

```yaml
- uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'myapp:latest'
    format: 'sarif'
    severity: 'CRITICAL,HIGH'
```

### IaCスキャン

```yaml
- uses: bridgecrewio/checkov-action@v12
  with:
    directory: infra/
    framework: bicep,arm
```

## GitHub Environments

```yaml
# 承認フロー付きデプロイ
jobs:
  deploy:
    environment:
      name: prod
      url: ${{ steps.deploy.outputs.url }}
```

### 環境設定

| 環境 | 承認者 | Wait Timer |
|------|--------|------------|
| dev | なし | なし |
| staging | 1名 | なし |
| prod | 2名 | 15分 |

## ステップサマリー

```yaml
- name: Summary
  run: |
    echo "## 🚀 Deploy Results" >> $GITHUB_STEP_SUMMARY
    echo "| Item | Value |" >> $GITHUB_STEP_SUMMARY
    echo "|------|-------|" >> $GITHUB_STEP_SUMMARY
    echo "| Environment | $ENV |" >> $GITHUB_STEP_SUMMARY
    echo "| URL | $URL |" >> $GITHUB_STEP_SUMMARY
```

## azd コマンド

```bash
# 認証
azd auth login --client-id $CLIENT_ID --federated-credential-provider github

# デプロイ
azd up --no-prompt

# 環境変数取得
azd env get-values | grep API_URI
```

## Federated Credential Subject

| トリガー | Subject形式 |
|----------|-------------|
| ブランチ | `repo:OWNER/REPO:ref:refs/heads/BRANCH` |
| タグ | `repo:OWNER/REPO:ref:refs/tags/TAG` |
| PR | `repo:OWNER/REPO:pull_request` |
| 環境 | `repo:OWNER/REPO:environment:ENV_NAME` |

## ベストプラクティス

1. **シークレットレス**: OIDC認証でシークレット不要
2. **最小権限**: 必要なロールのみ割り当て
3. **環境分離**: dev/staging/prodを分離
4. **承認フロー**: 本番は複数承認必須
5. **セキュリティスキャン**: 全PRでスキャン実行
6. **SARIF統合**: GitHub Security タブに結果表示
