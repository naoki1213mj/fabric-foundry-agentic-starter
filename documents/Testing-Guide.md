# テスト運用ガイド

このドキュメントでは、プロジェクトのテスト運用方法について説明します。

## 📋 目次

- [テストの全体像](#テストの全体像)
- [ローカルでのテスト実行](#ローカルでのテスト実行)
- [CI/CDでの自動テスト](#cicdでの自動テスト)
- [テストの書き方](#テストの書き方)
- [トラブルシューティング](#トラブルシューティング)

---

## テストの全体像

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        開発フロー                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. ローカル開発                                                         │
│     ├─ コードを書く                                                      │
│     ├─ ローカルでテスト実行 (.\scripts\test.ps1)                         │
│     └─ Lintチェック (ruff check)                                        │
│                                                                         │
│  2. Pull Request作成                                                    │
│     └─ GitHub Actionsが自動実行                                          │
│        ├─ Python Lint (Ruff) ───────→ ❌ 失敗するとマージ不可           │
│        ├─ Python Unit Tests ────────→ ❌ 失敗するとマージ不可           │
│        └─ Frontend Lint (ESLint) ───→ ⚠️ 警告のみ（参考）              │
│                                                                         │
│  3. main マージ後                                                        │
│     └─ deploy-app-service.yml が自動デプロイ                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### テストの種類

| 種類 | 場所 | 実行タイミング | 説明 |
|------|------|----------------|------|
| **Unit Tests** | `src/api/python/tests/` | PR時、手動 | APIの個別機能テスト |
| **E2E Tests** | `tests/e2e-test/` | 手動 | ブラウザを使った統合テスト |
| **Lint** | - | PR時、手動 | コード品質チェック |

---

## ローカルでのテスト実行

### 前提条件

```powershell
# 仮想環境の有効化
.\.venv\Scripts\Activate.ps1

# テスト用パッケージのインストール（初回のみ）
uv pip install -r src/api/python/requirements-test.txt
```

### 方法1: スクリプトを使う（推奨）

```powershell
# すべてのテストを実行
.\scripts\test.ps1

# Lintのみ実行
.\scripts\test.ps1 -LintOnly

# テストのみ実行
.\scripts\test.ps1 -TestOnly
```

### 方法2: コマンドを直接実行

```powershell
# ディレクトリ移動
cd src/api/python

# テスト実行
pytest tests/ -v

# カバレッジ付きで実行
pytest tests/ -v --cov=. --cov-report=term-missing

# 特定のテストファイルのみ
pytest tests/test_app.py -v
```

### 方法3: VS Code で実行

1. テストエクスプローラーを開く（左サイドバーのフラスコアイコン）
2. テストを検出（更新ボタン）
3. 実行したいテストをクリック

---

## CI/CDでの自動テスト

### ワークフロー一覧

| ワークフロー | ファイル | トリガー | 説明 |
|--------------|----------|----------|------|
| **Test and Lint** | `test.yml` | PR, push to main | テストとLintを実行 |
| **Deploy** | `deploy-app-service.yml` | push to main | Azureへデプロイ |
| **Security Scan** | `security-scan.yml` | 定期実行 | セキュリティスキャン |

### PR時のチェック

PRを作成すると、以下が自動実行されます：

```
┌────────────────────────────────────────────────────────────┐
│ Pull Request: feature/my-feature → main                    │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ✅ Python Lint (Ruff)          必須                       │
│     └─ コードスタイルと潜在的なバグをチェック              │
│                                                            │
│  ✅ Python Unit Tests           必須                       │
│     └─ ユニットテストを実行                                 │
│                                                            │
│  ⚠️ Frontend Lint (ESLint)      参考                       │
│     └─ TypeScript/Reactのコードチェック                    │
│                                                            │
│  ─────────────────────────────────────────────────────     │
│  📊 カバレッジレポートがPRコメントに投稿されます            │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### テスト結果の確認方法

1. **GitHub PR画面**: 下部の「Checks」タブで結果を確認
2. **Actions タブ**: 詳細なログを確認
3. **Artifacts**: テスト結果ファイルをダウンロード

---

## テストの書き方

### ファイル構成

```
src/api/python/
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # 共通のフィクスチャ
│   ├── test_app.py       # app.py のテスト
│   ├── test_history_sql.py  # history_sql.py のテスト
│   └── test_utils.py     # ユーティリティのテスト
├── app.py
├── chat.py
└── history_sql.py
```

### テストの命名規則

```python
# ファイル名: test_対象モジュール.py
test_app.py
test_history_sql.py

# クラス名: Test機能カテゴリ
class TestHealthEndpoints:
class TestDatabaseConnection:

# メソッド名: test_何をテストするか
def test_health_endpoint_returns_ok(self):
def test_create_conversation_generates_id(self):
```

### テスト例

```python
# 基本的なテスト
class TestMyFeature:
    def test_success_case(self):
        """正常系のテスト"""
        result = my_function("valid input")
        assert result == expected_value

    def test_error_case(self):
        """エラー系のテスト"""
        with pytest.raises(ValueError):
            my_function("invalid input")

# フィクスチャを使ったテスト
class TestWithDatabase:
    def test_with_mocked_db(self, mock_pyodbc_connection):
        """データベースをモックしたテスト"""
        mock_pyodbc_connection["cursor"].fetchall.return_value = [("data",)]
        # テストロジック

# 非同期テスト
class TestAsyncFunction:
    @pytest.mark.asyncio
    async def test_async_operation(self):
        """非同期関数のテスト"""
        result = await async_function()
        assert result is not None
```

### フィクスチャの使い方

`conftest.py` で定義されたフィクスチャは、引数に指定するだけで使えます：

```python
# conftest.py で定義
@pytest.fixture
def sample_conversation():
    return {"id": "test-123", "title": "Test"}

# テストで使用（引数に書くだけ）
def test_with_sample_data(sample_conversation):
    assert sample_conversation["id"] == "test-123"
```

---

## トラブルシューティング

### よくある問題

#### 1. テストがインポートエラーで失敗する

```
ModuleNotFoundError: No module named 'agents'
```

**解決策**: 正しいディレクトリでテストを実行してください。

```powershell
cd src/api/python
pytest tests/
```

#### 2. Ruff Lintエラーが出る

```
E501: Line too long (xxx > 100 characters)
```

**解決策**: Ruffの自動フォーマットを使用してください。

```powershell
ruff format src/api/python
```

#### 3. テストがタイムアウトする

**解決策**: `@pytest.mark.slow` マーカーを付けて、CIではスキップします。

```python
@pytest.mark.slow
def test_long_running_operation(self):
    # ...
```

#### 4. 環境変数が設定されていない

**解決策**: `conftest.py` の `mock_env_vars` フィクスチャが自動で環境変数を設定します。
追加が必要な場合は `conftest.py` を編集してください。

### CI が失敗した場合

1. **GitHub Actions のログを確認**
   - Actions タブ → 失敗したワークフロー → 該当ジョブをクリック

2. **ローカルで再現**
   ```powershell
   # CIと同じコマンドを実行
   ruff check src/api/python
   cd src/api/python && pytest tests/ -v
   ```

3. **修正してプッシュ**
   ```powershell
   git add .
   git commit -m "fix: テストエラーを修正"
   git push
   ```

---

## 関連ドキュメント

- [ローカル開発セットアップ](LocalDevelopmentSetup.md)
- [デプロイメントガイド](DeploymentGuide.md)
- [GitHub Actions セットアップ](GitHubActionsSetup.md)
