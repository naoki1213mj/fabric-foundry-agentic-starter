# プロンプトモジュール

> **注**: このドキュメントは `src/api/python/prompts/` モジュールについて説明します。

## 1. 概要

プロンプト定義を `chat.py` から分離し、独立したモジュールとして管理しています。

### メリット

- **保守性向上**: プロンプト修正が容易
- **再利用性**: 他のコードからインポート可能
- **テスト容易性**: プロンプト単体でのテスト可能
- **Git差分明確化**: プロンプト変更の追跡が容易

## 2. ファイル構成

```
src/api/python/prompts/
├── __init__.py          # モジュールエクスポート
├── sql_agent.py         # SQLエージェント用プロンプト
├── web_agent.py         # Webエージェント用プロンプト
├── doc_agent.py         # ドキュメントエージェント用プロンプト
├── manager_agent.py     # マネージャーエージェント用プロンプト
├── unified_agent.py     # 統合エージェント用プロンプト
└── triage_agent.py      # トリアージエージェント用プロンプト
```

## 3. エクスポート一覧

### `__init__.py`

```python
from .sql_agent import (
    SQL_AGENT_PROMPT,
    SQL_AGENT_DESCRIPTION,
    SQL_AGENT_PROMPT_MINIMAL,
)
from .web_agent import (
    WEB_AGENT_PROMPT,
    WEB_AGENT_DESCRIPTION,
)
from .doc_agent import (
    DOC_AGENT_PROMPT,
    DOC_AGENT_DESCRIPTION,
)
from .manager_agent import (
    MANAGER_AGENT_PROMPT,
    MANAGER_AGENT_DESCRIPTION,
)
from .unified_agent import (
    UNIFIED_AGENT_PROMPT,
)
from .triage_agent import (
    TRIAGE_AGENT_PROMPT,
    TRIAGE_AGENT_DESCRIPTION,
)
```

## 4. 各プロンプトの説明

### sql_agent.py

| 定数 | 用途 |
| ---- | ---- |
| `SQL_AGENT_PROMPT` | SQLエージェントのフル指示 |
| `SQL_AGENT_DESCRIPTION` | SQLエージェントの説明（ハンドオフ用） |
| `SQL_AGENT_PROMPT_MINIMAL` | 軽量版（sql_onlyモード用） |

**内容例**:

- データベーススキーマ情報
- SQL生成ルール
- 出力フォーマット指示
- チャート生成ルール

### web_agent.py

| 定数 | 用途 |
| ---- | ---- |
| `WEB_AGENT_PROMPT` | Webエージェントの指示 |
| `WEB_AGENT_DESCRIPTION` | Webエージェントの説明 |

**内容例**:

- 検索クエリ生成ルール
- 引用フォーマット
- 信頼性評価基準

### doc_agent.py

| 定数 | 用途 |
| ---- | ---- |
| `DOC_AGENT_PROMPT` | ドキュメントエージェントの指示 |
| `DOC_AGENT_DESCRIPTION` | ドキュメントエージェントの説明 |

**内容例**:

- AI Search検索パターン
- ドキュメント引用ルール
- コンテキスト抽出方法

### manager_agent.py

| 定数 | 用途 |
| ---- | ---- |
| `MANAGER_AGENT_PROMPT` | マネージャーの計画・統合指示 |
| `MANAGER_AGENT_DESCRIPTION` | マネージャーの説明 |

**用途**: magentic モードでの計画立案と結果統合

### unified_agent.py

| 定数 | 用途 |
| ---- | ---- |
| `UNIFIED_AGENT_PROMPT` | 統合エージェントの指示 |

**用途**: multi_tool モードで全ツールを使用する際の指示

### triage_agent.py

| 定数 | 用途 |
| ---- | ---- |
| `TRIAGE_AGENT_PROMPT` | トリアージの判断基準 |
| `TRIAGE_AGENT_DESCRIPTION` | トリアージの説明 |

**用途**: handoff モードでの委譲先判断

## 5. 使用方法

### chat.py での使用

```python
from prompts import (
    SQL_AGENT_PROMPT,
    WEB_AGENT_PROMPT,
    DOC_AGENT_PROMPT,
    UNIFIED_AGENT_PROMPT,
)

# エージェント作成時に使用
agent = ChatAgent(
    name="unified_agent",
    instructions=UNIFIED_AGENT_PROMPT,
    tools=[sql_tool, web_tool, doc_tool],
)
```

### テストでの使用

```python
from prompts import SQL_AGENT_PROMPT

def test_sql_prompt_contains_schema():
    assert "SalesData" in SQL_AGENT_PROMPT
    assert "Products" in SQL_AGENT_PROMPT
```

## 6. カスタマイズ

### プロンプト変更手順

1. 該当ファイルを編集（例: `prompts/sql_agent.py`）
2. 変更内容をテスト
3. `git push` でデプロイ

### 新規プロンプト追加

1. `prompts/` に新規ファイル作成
2. `__init__.py` にエクスポート追加
3. `chat.py` でインポート

```python
# prompts/new_agent.py
NEW_AGENT_PROMPT = """
あなたは新しいエージェントです...
"""

# prompts/__init__.py
from .new_agent import NEW_AGENT_PROMPT
```

## 7. ベストプラクティス

### プロンプト設計

- **明確な役割定義**: エージェントの責務を明記
- **具体的な例示**: 期待する出力形式を例示
- **制約条件**: やってはいけないことを明記
- **エラーハンドリング**: 不明確な入力への対応を記載

### コード管理

- **変数名**: `{ROLE}_AGENT_PROMPT` 形式で統一
- **docstring**: 各定数の用途を記載
- **バージョン管理**: Git履歴で変更追跡

---

**関連ドキュメント**:

- [Agent-Architecture.md](./Agent-Architecture.md) - エージェント構成
- [Implementation-Overview.md](./Implementation-Overview.md) - 実装概要
