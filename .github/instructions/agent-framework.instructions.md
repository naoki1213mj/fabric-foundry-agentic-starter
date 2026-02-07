---
applyTo: "src/**/*agent*.{py,cs},src/**/*tool*.{py,cs}"
---

# Microsoft Agent Framework Guidelines

## ChatAgent パターン

```python
from agent_framework import ChatAgent, tool
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential

class SalesAnalystAgent(ChatAgent):
    """売上分析を行うエージェント"""

    def __init__(self):
        super().__init__(
            name="SalesAnalyst",
            instructions="""
            あなたは売上データ分析の専門家です。
            ユーザーの質問に対して、データを分析し、
            インサイトを提供してください。
            """,
            model="gpt-4o"
        )

    @tool(approval_mode="never_require")
    async def query_sales(self, query: str) -> str:
        """Fabricの売上データをクエリする"""
        # SQL Database in Fabric への接続
        result = await self.execute_fabric_query(query)
        return result

    @tool(approval_mode="never_require")
    async def get_top_products(self, limit: int = 10) -> str:
        """トップ製品を取得する"""
        sql = f"SELECT TOP {limit} * FROM products ORDER BY sales DESC"
        return await self.execute_fabric_query(sql)
```

## Tool定義（@tool）

> **Note**: `@ai_function` は `@tool` に改名されました（agent-framework-core 1.0.0b260128 breaking change）

```python
from agent_framework import tool
from typing import Annotated

@tool(approval_mode="never_require")
async def search_documents(
    query: Annotated[str, "検索クエリ"],
    top_k: Annotated[int, "返す結果の数"] = 5,
) -> str:
    """ドキュメントを検索する"""
    # 実装
    return json.dumps(results)
```

## Workflow Orchestration

```python
from agent_framework.workflow import Workflow, Sequential, Concurrent

workflow = Workflow(
    steps=[
        Sequential([
            ("analyze", analyzer_agent),
            ("summarize", summarizer_agent),
        ]),
        Concurrent([
            ("chart", chart_agent),
            ("report", report_agent),
        ])
    ]
)

result = await workflow.run(user_input)
```

## MCP Tool Integration

```python
from agent_framework.tools import MCPTool

# MCP Server からツールをロード
mcp_tools = await MCPTool.from_server("http://mcp-server:8080")

agent = ChatAgent(
    name="MCPAgent",
    tools=mcp_tools
)
```

## OpenTelemetry

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Foundry への接続
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("agent_execution"):
    result = await agent.run(user_input)
```
