# AGENTS.md - Copilot Agent Mode 操作指示

## ミッション

**Microsoft Fabric + Foundry + Agent Framework を活用した Agentic AI アプリで、TDM を10分で納得させる**

## Solution Accelerator をベースにカスタマイズ

このプロジェクトは以下の Solution Accelerator をベースにしています：
https://github.com/microsoft/agentic-applications-for-unified-data-foundation-solution-accelerator

## 🚀 デプロイ方法（重要）

**GitHub Actions で自動デプロイ**: `git push` するだけでAzure側に自動デプロイされます！

```bash
# 変更をコミット
git add .
git commit -m "fix: 修正内容"

# プッシュ = 自動デプロイ（GitHub Actionsが実行される）
git push
```

⚠️ **手動の `az webapp` コマンドは不要です！** pushすれば自動的にデプロイされます。

## 実装前チェック

- [ ] 対象の `.instructions.md` を読んだ
- [ ] Solution Accelerator の既存コードとの一貫性を確認
- [ ] DEMO.md の Wow Path に沿っている
- [ ] Guardrails 統合を計画

## 実装後チェック

- [ ] `git push` でデプロイ開始（GitHub Actionsを確認）
- [ ] API ヘルスチェック成功
- [ ] Frontend 表示確認
- [ ] DEMO_MODE=true で動作確認
- [ ] Guardrails が機能している

## コーディングパターン

### 認証（Managed Identity）

```python
from azure.identity import DefaultAzureCredential
credential = DefaultAzureCredential()
```

### DEMO_MODE

```python
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"
if DEMO_MODE:
    return CACHED_RESPONSE
```

### Agent Tool

```python
from agent_framework import ai_function

@ai_function
async def my_tool(param: str) -> str:
    """ツールの説明"""
    if DEMO_MODE:
        return json.dumps({"demo": True})
    return json.dumps(result)
```

## やってはいけないこと

- ハードコードされたシークレット
- Solution Accelerator のコード構造を大幅に変更
- DEMO_MODE なしの実装
- Guardrails バイパス
- **pip や python -m pip の使用** → 必ず `uv pip` を使う

## Python 開発環境 (uv 必須)

このプロジェクトでは **uv** を使用してPython仮想環境を管理します。

```bash
# 仮想環境の有効化 (PowerShell)
.\.venv\Scripts\Activate.ps1

# パッケージインストール
uv pip install -r requirements.txt

# パッケージ追加
uv pip install <package-name>
```

**重要**: `pip` ではなく必ず `uv pip` を使用してください。

### Copilot Agent Mode でのPython実行

**Copilotへの指示**: Python を実行する際は、必ず uv 仮想環境の Python を使用してください。

```powershell
# プロジェクトルートから実行する場合
& ".\.venv\Scripts\python.exe" <script.py>

# src/api/python から実行する場合
& "../../../.venv/Scripts/python.exe" <script.py>

# 仮想環境を有効化してから実行する場合
.\.venv\Scripts\Activate.ps1
python <script.py>
```

**やってはいけないこと**:
- システムの `python` を直接使用（パッケージが見つからないエラーになる）
- `py_compile` や `python -m` をグローバルPythonで実行

## 📂 ログ管理ルール

デバッグ・エラー分析で取得したログは **必ず `.debug_logs/` フォルダに格納**してください。

```bash
# ログの保存先
.debug_logs/
├── latest/              # 最新のログ（フォルダ）
├── latest.zip           # 最新のログ（圧縮）
├── api_timeout_logs/    # タイムアウト関連
├── error_logs*.zip      # エラー分析用
└── [日付]_[目的].zip    # 命名規則: 2026-02-02_timeout_fix.zip
```

**やってはいけないこと**:
- プロジェクト直下にログファイル/フォルダを放置
- `*_logs/` や `*.zip` をルートに作成

**Copilotへの指示**: ログ取得時は `.debug_logs/` に直接保存してください。

## 審査基準

| 基準 | 対応 |
|------|------|
| Why Microsoft | Fabric + Foundry + Agent Framework |
| Why Now | Agent Framework GA + Guardrails |
| 技術統合 | 5領域カバー |
| ACR | Fabric F2 + OpenAI 従量課金 |
