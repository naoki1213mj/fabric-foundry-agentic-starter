---
applyTo: "src/**/*agent*.{py,cs},infra/**/*foundry*.bicep"
---

# Foundry Agent Service Guidelines

## Agent 定義 (YAML)

```yaml
# agent.yaml
name: sales-analyst
description: 売上データを分析するエージェント
model:
  name: gpt-5
  deployment: gpt-5
instructions: |
  あなたは売上データ分析の専門家です。
  Fabricのデータを使って質問に回答してください。
tools:
  - type: function
    name: query_sales
    description: 売上データをクエリする
  - type: code_interpreter
    enabled: true
guardrails:
  task_adherence: true
  prompt_shields: true
  groundedness: true
```

## Python SDK

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# クライアント初期化
client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint="https://ai-xxx.services.ai.azure.com"
)

# エージェント作成
agent = client.agents.create_agent(
    model="gpt-5",
    name="SalesAnalyst",
    instructions="売上分析の専門家として回答してください",
    tools=[
        {"type": "code_interpreter"},
        {"type": "function", "function": query_sales_function}
    ]
)

# スレッド作成
thread = client.agents.create_thread()

# メッセージ送信
message = client.agents.create_message(
    thread_id=thread.id,
    role="user",
    content="今月のトップ製品は？"
)

# 実行
run = client.agents.create_and_process_run(
    thread_id=thread.id,
    agent_id=agent.id
)

# 結果取得
messages = client.agents.list_messages(thread_id=thread.id)
```

## Hosted Agent (azd deploy)

```bash
# azd での Hosted Agent デプロイ
azd ai agent init -m agent.yaml
azd up
```

## Guardrails 統合

```python
# Guardrails設定
guardrails = {
    "task_adherence": {
        "enabled": True,
        "blocked_topics": ["政治", "宗教"]
    },
    "prompt_shields": {
        "enabled": True,
        "jailbreak_detection": True,
        "indirect_attack_detection": True
    },
    "groundedness": {
        "enabled": True,
        "threshold": 0.7
    }
}

agent = client.agents.create_agent(
    model="gpt-5",
    guardrails=guardrails,
    ...
)
```
