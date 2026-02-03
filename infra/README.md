# Infrastructure as Code (Bicep)

このフォルダには Azure リソースをプロビジョニングするための Bicep テンプレートが含まれています。

## 現在使用中のモジュール

| ファイル | 説明 |
|----------|------|
| `main.bicep` | メインデプロイテンプレート |
| `main.parameters.json` | デプロイパラメータ |
| `deploy_managed_identity.bicep` | Managed Identity |
| `deploy_ai_foundry.bicep` | Azure AI Foundry |
| `deploy_app_service_plan.bicep` | App Service Plan |
| `deploy_backend_docker.bicep` | API (Python) App Service |
| `deploy_frontend_docker.bicep` | Frontend App Service |
| `abbreviations.json` | リソース名略称定義 |
| `existing_foundry_project.bicep` | 既存 Foundry プロジェクト再利用 |

## 未使用モジュール（将来の選択肢）

以下のモジュールは `main.bicep` でコメントアウトされていますが、将来の拡張用に保持しています。

| ファイル | 説明 | 用途 |
|----------|------|------|
| `deploy_cosmos_db.bicep` | Cosmos DB | 会話履歴（現在は Fabric SQL を使用） |
| `deploy_keyvault.bicep` | Key Vault | シークレット管理 |
| `deploy_sql_db.bicep` | Azure SQL Database | Fabric SQL の代替 |
| `deploy_container_registry.bicep` | ACR 新規作成 | 現在は既存 ACR を使用 |
| `deploy_backend_csapi_docker.bicep` | API (C#/.NET) | C# 版バックエンド |
| `deploy_csapi_app_service.bicep` | C# App Service 設定 | C# 版用 |
| `deploy_foundry_role_assignment.bicep` | Foundry ロール割当 | 手動設定の場合 |
| `deploy_appservice-appsettings.bicep` | App Settings 個別設定 | 詳細な設定が必要な場合 |
| `deploy_app_service.bicep` | App Service 単体 | 分離デプロイ用 |
| `create-sql-user-and-role.bicep` | SQL ユーザー作成 | DB アクセス設定 |
| `csapi.parameters.json` | C# 版パラメータ | C# 版デプロイ用 |

## scripts/ フォルダ

| フォルダ | 説明 | 状態 |
|----------|------|------|
| `agent_scripts/` | エージェント作成スクリプト | ✅ 使用中 |
| `fabric_scripts/` | Fabric 設定スクリプト | ✅ 使用中 |
| `add_user_scripts/` | SQL ユーザー追加 | 必要時のみ |
| `copilot_studio_scripts/` | Copilot Studio (Option 1) | Option 1 選択時 |

## vscode_web/ フォルダ

VS Code Web からの `azd deploy` 用。GitHub Actions でデプロイする場合は不要。

## デプロイ方法

### 初回セットアップ

```bash
azd auth login
azd up
```

### 日常のデプロイ

GitHub Actions による自動デプロイ:

```bash
git push  # → 自動でビルド・デプロイ
```

## 注意事項

- `main.json` は Bicep からコンパイルされた ARM テンプレートです（再生成可能なため .gitignore に追加済み）
- C#/.NET 版を使用する場合は `main.parameters.json` の `backendRuntimeStack` を `dotnet` に変更
