# Microsoft Agent Framework Skill

## 概要

Microsoft Agent Framework を使った Agentic AI 開発。

## パターン

### 1. ChatAgent

```python
from agent_framework import ChatAgent, ai_function

class MyAgent(ChatAgent):
    @ai_function
    async def my_tool(self, query: str) -> str:
        """ツールの説明"""
        return result
```

### 2. Workflow Orchestration

```python
from agent_framework.workflow import Workflow, Sequential

workflow = Workflow(
    steps=[
        Sequential([
            ("step1", agent1),
            ("step2", agent2),
        ])
    ]
)
```

### 3. MCP Integration

```python
from agent_framework.tools import MCPTool

mcp_tools = await MCPTool.from_server("http://mcp:8080")
```

## Foundry 連携

```python
# Hosted Agent としてデプロイ
# azure.yaml で定義 → azd up
```
