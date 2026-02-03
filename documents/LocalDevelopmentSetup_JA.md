# ローカル開発セットアップガイド

[English](./LocalDevelopmentSetup.md) | **日本語**

このガイドでは、Agentic Applications For Unified Data Foundation Solution Accelerator を Windows および Linux プラットフォームでローカル開発用にセットアップするための包括的な手順を提供します。

## 重要なセットアップ注意事項

### アーキテクチャ

このアプリケーションは、独立して実行される **2 つの別々のサービス** で構成されています：

1. **バックエンド API** - フロントエンドアプリケーション用の REST API サーバー（Python と .NET の両方で実装）
2. **フロントエンド** - React ベースのユーザーインターフェース

> **⚠️ 重要: 各サービスは独自のターミナル/コンソールウィンドウで実行する必要があります**
>
> - サービス実行中は**ターミナルを閉じないでください**
> - ローカル開発には **2 つの別々のターミナルウィンドウ** を開いてください
> - 各サービスはターミナルを占有し、ライブログを表示します
>
> **ターミナル構成:**
> - **ターミナル 1**: バックエンド API - ポート 8000 の HTTP サーバー
> - **ターミナル 2**: フロントエンド - ポート 3000 の開発サーバー

### パス規則

**このガイドのすべてのパスはリポジトリルートディレクトリからの相対パスです：**

```bash
agentic-applications-for-unified-data-foundation-solution-accelerator/    ← リポジトリルート（ここから開始）
├── src/
│   ├── api/                         
│   │   ├── python/
│   │   │   ├── .venv/               ← Python 仮想環境
│   │   │   ├── app.py               ← API エントリポイント
│   │   │   └── .env                 ← Python バックエンド API 設定ファイル
│   │   └── dotnet/                   
│   │       ├── Program.cs           ← API エントリポイント
│   │       └── appsettings.json     ← .NET バックエンド API 設定ファイル
│   └── App/                           
│       ├── node_modules/                    
│       └── .env                     ← フロントエンド設定ファイル
└── documents/                       ← ドキュメント（現在地）
```

## ステップ 1: 前提条件 - 必要なツールのインストール

**注意**: バックエンド API には Python または .NET のいずれかを選択できます。お好みに応じて対応する SDK をインストールしてください：
- **Python バックエンド**: Python 3.12 以上が必要
- **.NET バックエンド**: .NET SDK 8.0 以上が必要

### Windows 開発

#### オプション 1: ネイティブ Windows (PowerShell)

```powershell
# Git のインストール
winget install Git.Git

# フロントエンド用 Node.js のインストール
winget install OpenJS.NodeJS.LTS

# Python バックエンド（オプション A）の場合：
winget install Python.Python.3.12

# .NET バックエンド（オプション B）の場合：
winget install Microsoft.DotNet.SDK.8
```

#### オプション 2: WSL2 を使用した Windows（推奨）

```bash
# まず WSL2 をインストール（管理者として PowerShell で実行）：
# wsl --install -d Ubuntu

# 次に WSL2 Ubuntu ターミナルでフロントエンド用：
sudo apt update && sudo apt install git curl nodejs npm -y

# Python バックエンド（オプション A）の場合：
sudo apt install python3.12 python3.12-venv -y

# .NET バックエンド（オプション B）の場合：
wget https://dot.net/v1/dotnet-install.sh -O dotnet-install.sh
chmod +x dotnet-install.sh
./dotnet-install.sh --channel 8.0
echo 'export PATH=$PATH:$HOME/.dotnet' >> ~/.bashrc
source ~/.bashrc
```

### Linux 開発

#### Ubuntu/Debian

```bash
# フロントエンド用：
sudo apt update && sudo apt install git curl nodejs npm -y

# Python バックエンド（オプション A）の場合：
sudo apt install python3.12 python3.12-venv -y

# .NET バックエンド（オプション B）の場合：
wget https://dot.net/v1/dotnet-install.sh -O dotnet-install.sh
chmod +x dotnet-install.sh
./dotnet-install.sh --channel 8.0
echo 'export PATH=$PATH:$HOME/.dotnet' >> ~/.bashrc
source ~/.bashrc
```

#### RHEL/CentOS/Fedora

```bash
# フロントエンド用：
sudo dnf install git curl gcc nodejs npm -y

# Python バックエンド（オプション A）の場合：
sudo dnf install python3.12 python3.12-devel -y

# .NET バックエンド（オプション B）の場合：
wget https://dot.net/v1/dotnet-install.sh -O dotnet-install.sh
chmod +x dotnet-install.sh
./dotnet-install.sh --channel 8.0
echo 'export PATH=$PATH:$HOME/.dotnet' >> ~/.bashrc
source ~/.bashrc
```

### リポジトリのクローン

```bash
git clone https://github.com/microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator.git

cd agentic-applications-for-unified-data-foundation-solution-accelerator
```

**任意のステップを開始する前に、リポジトリルートディレクトリにいることを確認してください：**

```bash
# 正しい場所にいることを確認
pwd  # Linux/macOS - 表示されるべき: .../agentic-applications-for-unified-data-foundation-solution-accelerator
Get-Location  # Windows PowerShell - 表示されるべき: ...\agentic-applications-for-unified-data-foundation-solution-accelerator

# そうでない場合は、リポジトリルートに移動
cd path/to/agentic-applications-for-unified-data-foundation-solution-accelerator
```

## ステップ 2: 開発ツールのセットアップ

### Visual Studio Code（推奨）

#### 必要な拡張機能

ワークスペースルートに `.vscode/extensions.json` を作成し、以下の JSON をコピー：

```json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.pylint",
        "ms-python.black-formatter",
        "ms-python.isort",
        "ms-vscode-remote.remote-wsl",
        "ms-vscode-remote.remote-containers",
        "redhat.vscode-yaml",
        "ms-vscode.azure-account",
        "ms-python.mypy-type-checker"
    ]
}
```

VS Code はワークスペースを開くと、これらの推奨拡張機能のインストールを促します。

#### 設定の構成

`.vscode/settings.json` を作成し、以下の JSON をコピー：

```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "files.associations": {
        "*.yaml": "yaml",
        "*.yml": "yaml"
    }
}
```

## ステップ 3: 認証のセットアップ

サービスを構成する前に、Azure で認証します：

```bash
# Azure CLI にログイン
az login

# サブスクリプションを設定
az account set --subscription "your-subscription-id"

# 認証を確認
az account show
```

### 必要な Azure RBAC 権限

アプリケーションをローカルで実行するには、デプロイされたリソースに対して Azure アカウントに以下のロール割り当てが必要です：

#### AI Foundry アクセス

**Linux/macOS/WSL (Bash):**
```bash
# プリンシパル ID を取得
PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv)

# Azure AI User ロールを割り当て
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Azure AI User" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.CognitiveServices/accounts/<ai-foundry-account>"
```

**Windows (PowerShell):**
```powershell
# プリンシパル ID を取得
$PRINCIPAL_ID = az ad signed-in-user show --query id -o tsv

# Azure AI User ロールを割り当て
az role assignment create `
  --assignee $PRINCIPAL_ID `
  --role "Azure AI User" `
  --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.CognitiveServices/accounts/<ai-foundry-account>"
```

### Fabric ワークスペースアクセス

アクセス要件は、デプロイするかローカルで実行するかによって異なります：

- **デプロイの場合**: リソースのプロビジョニングと構成に Fabric ワークスペースの Admin ロールが必要
- **ローカル開発の場合**: アプリケーションをローカルで実行するには Fabric ワークスペースの Contributor ロールで十分

必要な権限がない場合は、ワークスペース管理者に適切なロールの割り当てを依頼してください。

**注意**: RBAC 権限の変更が反映されるまで 5〜10 分かかる場合があります。ロールを割り当てた後に「Forbidden」エラーが発生した場合は、数分待ってから再試行してください。

## ステップ 4: バックエンド API のセットアップと実行手順

> **📋 ターミナルリマインダー**: バックエンド API 用に**ターミナルウィンドウ（ターミナル 1）**を開いてください。すべてのコマンドは**リポジトリルートディレクトリ**から開始することを前提としています。

バックエンド API は、フロントエンドに REST エンドポイントを提供し、API リクエストを処理します。このソリューションは **2 つのバックエンド実装**をサポートしています：

- **オプション A: Python バックエンド** (FastAPI) - `src/api/python/` にあります
- **オプション B: .NET バックエンド** (ASP.NET Core) - `src/api/dotnet/` にあります

**ステップ 1 でインストールした SDK に基づいて、お好みのバックエンドを選択して実行してください。**

---

### オプション A: Python バックエンドのセットアップ

#### 4A.1. Python API ディレクトリに移動

```bash
# リポジトリルートから
cd src/api/python
```

#### 4A.2. Python API 環境変数の設定

`src/api/python` ディレクトリに `.env` ファイルを作成：

```bash
# サンプルファイルをコピー
cp .env.sample .env  # Linux
# または
Copy-Item .env.sample .env  # Windows PowerShell
```

API リソースから Azure 構成値で `.env` ファイルを編集します。

#### 4A.3. Python API 依存関係のインストール

```bash
# 仮想環境を作成してアクティブ化
python -m venv .venv

# 仮想環境をアクティブ化
source .venv/bin/activate  # Linux
# または
.venv\Scripts\activate  # Windows PowerShell

# 依存関係をインストール
pip install -r requirements.txt
```

#### 4A.4. Python バックエンド API の実行

```bash
# アプリケーションエントリポイントで実行
python app.py
```

Python バックエンド API は以下で起動します：
- API: `http://localhost:8000`
- API ドキュメント: `http://localhost:8000/docs`

---

### オプション B: .NET バックエンドのセットアップ

#### 4B.1. .NET API ディレクトリに移動

```bash
# リポジトリルートから
cd src/api/dotnet
```

#### 4B.2. .NET API 設定の構成

`src/api/dotnet` ディレクトリに `appsettings.json` ファイルを作成：

```bash
# サンプルファイルをコピー
cp appsettings.json.sample appsettings.json  # Linux
# または
Copy-Item appsettings.json.sample appsettings.json  # Windows PowerShell
```

API リソースから Azure 構成値で `appsettings.json` ファイルを編集します。

#### 4B.3. .NET 依存関係の復元

```bash
# NuGet パッケージを復元
dotnet restore
```

#### 4B.4. .NET バックエンド API の実行

```bash
# アプリケーションを実行
dotnet run
```

**代替**: 開発中のホットリロード用：

```bash
dotnet watch run
```

.NET バックエンド API は以下で起動します：
- API: `http://localhost:8000`
- Swagger ドキュメント: `http://localhost:8000/swagger`

---

## ステップ 5: フロントエンド (UI) のセットアップと実行手順

> **📋 ターミナルリマインダー**: フロントエンド用に **2 番目の専用ターミナルウィンドウ（ターミナル 2）**を開いてください。ターミナル 1（バックエンド API）は実行したままにしてください。すべてのコマンドは**リポジトリルートディレクトリ**から開始することを前提としています。

UI は `src/App` にあります。

### 5.1. フロントエンドディレクトリに移動

```bash
# リポジトリルートから
cd src/App
```

### 5.2. UI 依存関係のインストール

```bash
npm install
```

### 5.3. 開発サーバーの起動

```bash
npm start
```

アプリは以下で起動します：

```
http://localhost:3000
```

## ステップ 6: サービスが実行中であることを確認

アプリケーションを使用する前に、別々のターミナルでサービスが実行中であることを確認：

### ターミナルステータスチェックリスト

| ターミナル | サービス | コマンド | 期待される出力 | URL |
|----------|---------|---------|--------------|-----|
| **ターミナル 1** | バックエンド API (Python または .NET) | `python app.py` または `dotnet run` | サーバー起動メッセージ | http://localhost:8000 |
| **ターミナル 2** | フロントエンド | `npm start` | `Local: http://localhost:3000/` | http://localhost:3000 |

### クイック確認

**1. バックエンド API の確認:**
```bash
# 新しいターミナル（ターミナル 3）で
# Python バックエンドの場合：
curl http://localhost:8000/health

# .NET バックエンドの場合：
curl http://localhost:8000/health
```

**2. フロントエンドの確認:**
- ブラウザで http://localhost:3000 を開く
- アプリケーション UI が表示されるはず

## トラブルシューティング

### よくある問題

#### サービスが起動しない場合
- 正しいディレクトリにいることを確認
- 仮想環境がアクティブ化されていることを確認（Python バックエンド）
- ポートが既に使用されていないことを確認（バックエンドは 8000、フロントエンドは 3000）
- ターミナルのエラーメッセージを確認

#### サービスにアクセスできない場合
- ファイアウォールが必要なポートをブロックしていないことを確認
- `http://127.0.0.1:port` の代わりに `http://localhost:port` を試す
- サービスが「startup complete」メッセージを表示していることを確認

#### Python バージョンの問題

```bash
# 利用可能な Python バージョンを確認
python3 --version
python3.12 --version

# python3.12 が見つからない場合はインストール：
# Ubuntu: sudo apt install python3.12
# Windows: winget install Python.Python.3.12
```

#### .NET バージョンの問題

```bash
# .NET SDK バージョンを確認
dotnet --version

# 8.0.x 以上が表示されるはず
# インストールされていない場合：
# Windows: winget install Microsoft.DotNet.SDK.8
# Linux: ステップ 1 の .NET インストール手順に従う
```

#### 仮想環境の問題

```bash
# 仮想環境を再作成
rm -rf .venv  # Linux
# または Remove-Item -Recurse .venv  # Windows PowerShell

python -m venv .venv
# アクティブ化して再インストール
source .venv/bin/activate  # Linux
# または .venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
```

#### 権限の問題 (Linux)

```bash
# ファイルの所有権を修正
sudo chown -R $USER:$USER .
```

#### Windows 固有の問題

```powershell
# PowerShell 実行ポリシー
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 長いパスのサポート（Windows 10 1607 以降、管理者として実行）
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force

# SSL 証明書の問題
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org uv
```

### 環境変数の問題

```bash
# 環境変数が読み込まれているか確認
env | grep AZURE  # Linux
Get-ChildItem Env:AZURE*  # Windows PowerShell

# .env ファイル形式を検証
cat .env | grep -v '^#' | grep '='  # key=value ペアが表示されるはず
```

## ステップ 7: 次のステップ

すべてのサービスが実行中であることを確認したら（ステップ 6 で確認）、以下ができます：

1. **アプリケーションにアクセス**: ブラウザで `http://localhost:3000` を開いてフロントエンド UI を探索
2. **コードベースを探索**: 
   - Python バックエンド: `src/api/python`
   - .NET バックエンド: `src/api/dotnet`
   - フロントエンド: `src/App`
3. **API エンドポイントをテスト**: バックエンド URL で利用可能な API ドキュメントを使用

## 関連ドキュメント

- [デプロイガイド](DeploymentGuide_JA.md) - 本番デプロイ手順
- [技術アーキテクチャ](TechnicalArchitecture_JA.md) - システムアーキテクチャ概要
