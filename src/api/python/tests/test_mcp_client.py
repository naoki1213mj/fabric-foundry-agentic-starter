"""
Tests for MCP Client

Unit tests for the MCP client that connects to the Azure Functions MCP server.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from mcp_client import MCP_ENABLED, call_mcp_tool, get_mcp_tools


def create_mock_response(json_data: dict) -> AsyncMock:
    """Create a mock httpx response with proper async support."""
    mock_response = AsyncMock()
    # httpx Response.json() is synchronous, not async
    mock_response.json = lambda: json_data
    # raise_for_status() is also synchronous
    mock_response.raise_for_status = lambda: None
    return mock_response


class TestMCPClient:
    """Tests for MCP client functions."""

    @pytest.mark.asyncio
    async def test_call_mcp_tool_success(self):
        """call_mcp_tool should return tool result on success."""
        mock_response = create_mock_response(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"content": [{"type": "text", "text": '{"result": "success"}'}]},
            }
        )

        with patch("mcp_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = mock_response

            result = await call_mcp_tool("test_tool", {"arg": "value"})
            assert result == '{"result": "success"}'

    @pytest.mark.asyncio
    async def test_call_mcp_tool_error(self):
        """call_mcp_tool should handle errors gracefully."""
        mock_response = create_mock_response(
            {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Method not found"}}
        )

        with patch("mcp_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = mock_response

            result = await call_mcp_tool("unknown_tool", {})
            result_dict = json.loads(result)
            assert "error" in result_dict

    @pytest.mark.asyncio
    async def test_call_mcp_tool_timeout(self):
        """call_mcp_tool should handle timeout."""
        import httpx

        with patch("mcp_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post.side_effect = httpx.TimeoutException("Timeout")

            result = await call_mcp_tool("test_tool", {})
            result_dict = json.loads(result)
            assert "error" in result_dict
            assert "timeout" in result_dict["error"].lower()

    def test_get_mcp_tools_returns_list(self):
        """get_mcp_tools should return a list of tool functions."""
        tools = get_mcp_tools()
        if MCP_ENABLED:
            assert isinstance(tools, list)
            assert len(tools) == 15  # 5 + 4 + 3 + 3 (sales, customer, inventory, product)
        else:
            assert tools == []

    def test_get_mcp_tools_callable(self):
        """All MCP tools should be callable."""
        tools = get_mcp_tools()
        for tool in tools:
            assert callable(tool)


class TestMCPToolWrappers:
    """Tests for individual MCP tool wrappers."""

    @pytest.mark.asyncio
    async def test_calculate_yoy_growth_wrapper(self):
        """calculate_yoy_growth wrapper should call MCP server."""
        from mcp_client import calculate_yoy_growth

        # Directly mock call_mcp_tool to avoid httpx complexity
        with patch("mcp_client.call_mcp_tool") as mock_call:
            mock_call.return_value = '{"growth_rate_percent": 20.0}'

            result = await calculate_yoy_growth(120000, 100000)
            assert result == '{"growth_rate_percent": 20.0}'

            # Verify the correct tool was called
            mock_call.assert_called_once()
            args, kwargs = mock_call.call_args
            assert args[0] == "calculate_yoy_growth"
            assert args[1]["current_value"] == 120000
            assert args[1]["previous_value"] == 100000

    @pytest.mark.asyncio
    async def test_calculate_rfm_score_wrapper(self):
        """calculate_rfm_score wrapper should call MCP server."""
        from mcp_client import calculate_rfm_score

        with patch("mcp_client.call_mcp_tool") as mock_call:
            mock_call.return_value = '{"rfm_scores": {"recency": 5}}'

            result = await calculate_rfm_score(5, 10, 200000)
            assert "rfm_scores" in result

            # Verify the correct tool was called
            mock_call.assert_called_once()
            args, _ = mock_call.call_args
            assert args[0] == "calculate_rfm_score"

    @pytest.mark.asyncio
    async def test_identify_slow_moving_inventory_wrapper(self):
        """identify_slow_moving_inventory wrapper should call MCP server."""
        from mcp_client import identify_slow_moving_inventory

        with patch("mcp_client.call_mcp_tool") as mock_call:
            mock_call.return_value = '{"summary": {"dead_stock_count": 1}}'

            items = [
                {
                    "name": "Item A",
                    "quantity": 100,
                    "unit_cost": 1000,
                    "days_in_stock": 200,
                    "monthly_sales": 0,
                }
            ]
            result = await identify_slow_moving_inventory(items)
            assert "summary" in result

            # Verify the correct tool was called
            mock_call.assert_called_once()
            args, _ = mock_call.call_args
            assert args[0] == "identify_slow_moving_inventory"
