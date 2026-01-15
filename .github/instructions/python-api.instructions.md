---
applyTo: "src/api/**/*.py"
---

# Python API Guidelines (Solution Accelerator)

## FastAPI 構造

```python
# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel
import os

app = FastAPI(title="Agentic AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 環境変数
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"

# 認証
credential = DefaultAzureCredential()
```

## リクエスト/レスポンスモデル

```python
from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    context: Optional[dict] = None

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    sources: Optional[List[str]] = None
```

## エンドポイント

```python
@app.get("/health")
async def health():
    return {"status": "healthy", "demo_mode": DEMO_MODE}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if DEMO_MODE:
        return ChatResponse(
            response="デモモードのレスポンスです。",
            thread_id="demo-thread-001"
        )
    
    # Agent Framework を使用
    agent = get_agent()
    result = await agent.run(request.message)
    
    return ChatResponse(
        response=result.content,
        thread_id=result.thread_id
    )

@app.post("/api/query")
async def query_data(query: str):
    if DEMO_MODE:
        return {"data": DEMO_DATA}
    
    result = await execute_fabric_query(query)
    return {"data": result}
```

## Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
