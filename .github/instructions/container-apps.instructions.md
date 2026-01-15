---
applyTo: "src/api/**/*.{py,cs},src/web/**/*.{ts,tsx,js}"
---

# Azure Container Apps Guidelines

## 構成

Solution Accelerator では以下の Container Apps を使用：

- `ca-{project}-api`: Backend API (Python/FastAPI)
- `ca-{project}-web`: Frontend (React/TypeScript)

## Python API パターン

```python
from fastapi import FastAPI, HTTPException
from azure.identity import DefaultAzureCredential
import os

app = FastAPI()
credential = DefaultAzureCredential()

DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if DEMO_MODE:
        return {"response": "デモモードのレスポンス"}
    # 実際の処理
```

## 環境変数

```bash
AZURE_OPENAI_ENDPOINT=https://oai-xxx.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
FABRIC_CONNECTION_STRING=...
DEMO_MODE=false
```

## スケーリング

```yaml
scale:
  minReplicas: 0
  maxReplicas: 10
  rules:
    - name: http-scaling
      http:
        metadata:
          concurrentRequests: "100"
```

## ローカル開発

```bash
# API
cd src/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd src/web
npm install
npm run dev
```
