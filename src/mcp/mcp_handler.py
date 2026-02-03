"""
MCP Protocol Handler

Handles MCP protocol operations and dispatches tool calls to appropriate handlers.
"""

import logging
from typing import Any

from tools.customer_segment import CustomerSegmentTools
from tools.inventory_analysis import InventoryAnalysisTools
from tools.product_comparison import ProductComparisonTools
from tools.sales_analysis import SalesAnalysisTools

logger = logging.getLogger(__name__)


class MCPHandler:
    """
    MCP Protocol Handler.

    Manages tool registration and dispatches tool calls to appropriate handlers.
    """

    def __init__(self):
        """Initialize MCP Handler with all tool modules."""
        # Initialize tool modules
        self.sales_tools = SalesAnalysisTools()
        self.product_tools = ProductComparisonTools()
        self.customer_tools = CustomerSegmentTools()
        self.inventory_tools = InventoryAnalysisTools()

        # Build tool registry
        self._tool_registry: dict[str, tuple[Any, callable]] = {}
        self._tool_definitions: list[dict] = []

        self._register_tools()

    def _register_tools(self):
        """Register all tools from all modules."""
        modules = [
            self.sales_tools,
            self.product_tools,
            self.customer_tools,
            self.inventory_tools,
        ]

        for module in modules:
            for tool_def in module.get_tool_definitions():
                tool_name = tool_def["name"]
                self._tool_definitions.append(tool_def)
                self._tool_registry[tool_name] = (module, tool_name)
                logger.info(f"Registered tool: {tool_name}")

        logger.info(f"Total tools registered: {len(self._tool_definitions)}")

    def list_tools(self) -> dict:
        """
        Return list of available tools (MCP tools/list response).

        Returns:
            dict: {"tools": [tool_definitions]}
        """
        return {"tools": self._tool_definitions}

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        Execute a tool by name (MCP tools/call response).

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            dict: {"content": [{"type": "text", "text": "result"}]}
        """
        if tool_name not in self._tool_registry:
            return {
                "content": [{"type": "text", "text": f"Error: Unknown tool '{tool_name}'"}],
                "isError": True,
            }

        module, method_name = self._tool_registry[tool_name]

        try:
            # Get the method from the module
            method = getattr(module, method_name)

            # Call the method with arguments
            result = method(**arguments)

            return {
                "content": [
                    {"type": "text", "text": result if isinstance(result, str) else str(result)}
                ]
            }

        except TypeError as e:
            logger.error(f"Tool argument error: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Invalid arguments for tool '{tool_name}': {str(e)}",
                    }
                ],
                "isError": True,
            }
        except Exception as e:
            logger.error(f"Tool execution error: {e}", exc_info=True)
            return {
                "content": [
                    {"type": "text", "text": f"Error executing tool '{tool_name}': {str(e)}"}
                ],
                "isError": True,
            }
