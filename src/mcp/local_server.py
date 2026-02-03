"""
Local MCP Server for Development

This is a FastAPI wrapper for local testing of the MCP server.
In production, use Azure Functions.
"""

import os
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_handler import MCPHandler

app = FastAPI(title="MCP Server (Local)", version="1.0.0")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize handler
handler = MCPHandler()


@app.post("/api/mcp")
async def mcp_endpoint(request: Request):
    """Handle MCP JSON-RPC requests."""
    body = await request.json()

    # Parse JSON-RPC request
    method = body.get("method", "")
    params = body.get("params", {})
    request_id = body.get("id", 1)

    if method == "tools/list":
        result = handler.list_tools()
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = await handler.call_tool(tool_name, arguments)
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"},
        }

    return {"jsonrpc": "2.0", "id": request_id, "result": result}


@app.get("/api/mcp/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "tools_count": len(handler._tool_definitions)}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "MCP Server (Local)",
        "version": "1.0.0",
        "endpoints": {
            "mcp": "/api/mcp",
            "health": "/api/mcp/health",
        },
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("MCP_PORT", "7071"))
    print(f"Starting MCP Server on http://localhost:{port}")
    print("Press Ctrl+C to stop")
    uvicorn.run(app, host="0.0.0.0", port=port)
