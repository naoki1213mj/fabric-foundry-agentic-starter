"""
Multi-Agent Orchestrator

Provides utilities for managing multiple agents in the chat system.
Currently uses single-agent mode with intelligent routing via instructions.

For future HandoffBuilder support when Agent Framework reaches GA,
this module can be extended with proper workflow orchestration.
"""

import logging
import os
from typing import List, Optional

from azure.ai.projects.aio import AIProjectClient

from .sql_agent import SqlAgentHandler
from .web_agent import WebAgentHandler

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """
    Orchestrates multi-agent workflow.

    Currently uses a single intelligent agent (SqlAgent) with enhanced
    instructions for handling various query types. Future versions will
    support true HandoffBuilder pattern when Agent Framework GA.
    """

    def __init__(
        self,
        project_client: AIProjectClient,
        sql_handler: SqlAgentHandler,
        web_handler: Optional[WebAgentHandler] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            project_client: Azure AI Projects client
            sql_handler: SQL query handler with database connection
            web_handler: Optional web search handler
        """
        self.project_client = project_client
        self.sql_handler = sql_handler
        self.web_handler = web_handler or WebAgentHandler()

    def get_tools(self) -> List[callable]:
        """
        Get all available tools for the agent.

        Returns:
            List of tool functions
        """
        tools = []

        # Add SQL tools
        tools.extend(self.sql_handler.get_tools())

        # Add Web tools if configured
        if os.getenv("BING_SEARCH_API_KEY"):
            tools.extend(self.web_handler.get_tools())
            logger.info("Web search tools enabled (Bing API configured)")
        else:
            logger.info("Web search tools disabled (no Bing API key)")

        return tools

    def get_agent_name(self) -> str:
        """
        Get the appropriate agent name based on configuration.

        Returns:
            Agent name string
        """
        # In multi-agent mode, prefer SQL agent (main chat agent)
        # Orchestrator and WebAgent will be used in future HandoffBuilder
        if os.getenv("MULTI_AGENT_MODE", "false").lower() == "true":
            return os.getenv("AGENT_NAME_SQL", os.getenv("AGENT_NAME_CHAT"))
        else:
            return os.getenv("AGENT_NAME_CHAT")


async def create_orchestrator(
    project_client: AIProjectClient,
    db_connection,
) -> MultiAgentOrchestrator:
    """
    Factory function to create the multi-agent orchestrator.

    Args:
        project_client: Azure AI Projects client
        db_connection: Database connection for SQL agent

    Returns:
        Configured MultiAgentOrchestrator instance
    """
    sql_handler = SqlAgentHandler(db_connection)
    web_handler = WebAgentHandler()

    return MultiAgentOrchestrator(
        project_client=project_client,
        sql_handler=sql_handler,
        web_handler=web_handler,
    )


# Legacy exports for backward compatibility
create_handoff_workflow = create_orchestrator
