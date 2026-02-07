---
mode: agent
description: Agent Framework Toolを追加
---

# Add Agent Tool

Microsoft Agent Framework に新しい Tool を追加します。

## テンプレート

```python
from agent_framework import tool
import json

@tool(approval_mode="never_require")
async def new_tool(param1: str, param2: int = 10) -> str:
    """
    ツールの説明（日本語でOK）

    Args:
        param1: パラメータ1の説明
        param2: パラメータ2の説明（デフォルト: 10）

    Returns:
        結果のJSON文字列
    """
    if DEMO_MODE:
        return json.dumps({"demo": True, "result": "デモ結果"})

    # 実際の処理
    result = await actual_implementation(param1, param2)

    return json.dumps(result)
```

## 登録

```python
agent = ChatAgent(
    name="MyAgent",
    tools=[new_tool, existing_tool]
)
```

## 完了条件

- [ ] @tool デコレータ付き
- [ ] docstring に説明・引数・戻り値
- [ ] DEMO_MODE 対応
- [ ] Agent に登録
