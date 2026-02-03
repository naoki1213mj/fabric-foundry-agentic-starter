"""
Azure Functions MCP Server

Business Analytics MCP Server for the Agentic AI application.
Provides tools for sales analysis, product comparison, customer segmentation, and inventory analysis.
"""

import json
import logging

import azure.functions as func
from mcp_handler import MCPHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Function App (ANONYMOUS for internal use, secured by network isolation)
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Initialize MCP Handler
mcp_handler = MCPHandler()


@app.route(route="mcp", methods=["POST"])
async def mcp_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    MCP Protocol endpoint.

    Handles:
    - tools/list: Returns available tools
    - tools/call: Executes a specific tool

    Request format:
    {
        "jsonrpc": "2.0",
        "id": "request-id",
        "method": "tools/list" | "tools/call",
        "params": { ... }
    }
    """
    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error: Invalid JSON"},
                    }
                ),
                status_code=400,
                mimetype="application/json",
            )

        # Validate JSON-RPC structure
        if "method" not in body:
            return func.HttpResponse(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "error": {"code": -32600, "message": "Invalid Request: method is required"},
                    }
                ),
                status_code=400,
                mimetype="application/json",
            )

        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id", "unknown")

        logger.info(f"MCP Request: method={method}, id={request_id}")

        # Handle methods
        if method == "tools/list":
            result = mcp_handler.list_tools()
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if not tool_name:
                return func.HttpResponse(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32602,
                                "message": "Invalid params: tool name is required",
                            },
                        }
                    ),
                    status_code=400,
                    mimetype="application/json",
                )

            result = await mcp_handler.call_tool(tool_name, tool_args)
        else:
            return func.HttpResponse(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                    }
                ),
                status_code=404,
                mimetype="application/json",
            )

        # Return success response
        return func.HttpResponse(
            json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"MCP Error: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": body.get("id") if "body" in dir() else None,
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                }
            ),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        json.dumps(
            {
                "status": "healthy",
                "service": "Business Analytics MCP Server",
                "version": "1.0.0",
                "tools_count": len(mcp_handler.list_tools().get("tools", [])),
            }
        ),
        status_code=200,
        mimetype="application/json",
    )
