"""
Tests for MCP Handler

Unit tests for the MCP protocol handler.
"""

import json

import pytest
from mcp_handler import MCPHandler


class TestMCPHandler:
    """Tests for MCPHandler."""

    @pytest.fixture
    def handler(self):
        """Create MCPHandler instance."""
        return MCPHandler()

    def test_list_tools_returns_all_tools(self, handler):
        """list_tools should return all 16 tools."""
        result = handler.list_tools()
        assert "tools" in result
        # 5 + 4 + 4 + 3 = 16 tools
        assert len(result["tools"]) == 16

    def test_list_tools_contains_required_fields(self, handler):
        """Each tool should have name, description, and inputSchema."""
        result = handler.list_tools()
        for tool in result["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    @pytest.mark.asyncio
    async def test_call_tool_yoy_growth(self, handler):
        """call_tool should execute yoy_growth correctly."""
        result = await handler.call_tool(
            "calculate_yoy_growth", {"current_value": 120000, "previous_value": 100000}
        )
        assert "content" in result
        content = json.loads(result["content"][0]["text"])
        assert content["growth_rate_percent"] == 20.0

    @pytest.mark.asyncio
    async def test_call_tool_rfm_score(self, handler):
        """call_tool should execute rfm_score correctly."""
        result = await handler.call_tool(
            "calculate_rfm_score", {"recency_days": 5, "frequency": 10, "monetary": 200000}
        )
        assert "content" in result
        content = json.loads(result["content"][0]["text"])
        assert "rfm_scores" in content

    @pytest.mark.asyncio
    async def test_call_tool_unknown(self, handler):
        """call_tool should handle unknown tool name."""
        result = await handler.call_tool("unknown_tool", {})
        # The handler returns isError=True with error message in content
        assert result.get("isError") is True
        assert "Unknown tool" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_call_tool_missing_args(self, handler):
        """call_tool should handle missing required arguments."""
        result = await handler.call_tool(
            "calculate_yoy_growth",
            {"current_value": 100000},  # Missing previous_value
        )
        # Should return error or handle gracefully
        assert "content" in result or "error" in result


class TestMCPHandlerToolCategories:
    """Tests for tool categories in MCPHandler."""

    @pytest.fixture
    def handler(self):
        """Create MCPHandler instance."""
        return MCPHandler()

    def test_sales_analysis_tools_registered(self, handler):
        """Sales analysis tools should be registered."""
        result = handler.list_tools()
        tool_names = [t["name"] for t in result["tools"]]
        assert "calculate_yoy_growth" in tool_names
        assert "calculate_mom_growth" in tool_names
        assert "calculate_moving_average" in tool_names
        assert "calculate_abc_analysis" in tool_names
        assert "calculate_sales_forecast" in tool_names

    def test_product_comparison_tools_registered(self, handler):
        """Product comparison tools should be registered."""
        result = handler.list_tools()
        tool_names = [t["name"] for t in result["tools"]]
        assert "compare_products" in tool_names
        assert "calculate_price_performance" in tool_names
        assert "suggest_alternatives" in tool_names
        assert "calculate_bundle_discount" in tool_names

    def test_customer_segment_tools_registered(self, handler):
        """Customer segment tools should be registered."""
        result = handler.list_tools()
        tool_names = [t["name"] for t in result["tools"]]
        assert "calculate_rfm_score" in tool_names
        assert "classify_customer_segment" in tool_names
        assert "calculate_clv" in tool_names
        assert "recommend_next_action" in tool_names

    def test_inventory_analysis_tools_registered(self, handler):
        """Inventory analysis tools should be registered."""
        result = handler.list_tools()
        tool_names = [t["name"] for t in result["tools"]]
        assert "calculate_inventory_turnover" in tool_names
        assert "calculate_reorder_point" in tool_names
        assert "identify_slow_moving_inventory" in tool_names
