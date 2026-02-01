"""
Multi-Agent Orchestration Module using Microsoft Agent Framework.

This module leverages Agent Framework's native multi-agent capabilities:
- ConcurrentBuilder for parallel agent execution
- WorkflowBuilder for sequential pipelines
- GroupChatBuilder for dynamic agent collaboration
- agent.as_tool() for agent-as-tool patterns

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                     MultiAgentOrchestrator                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ GroupChat / ConcurrentBuilder                           │    │
│  │  ├─ SqlAgent (Database queries, Chart.js)              │    │
│  │  ├─ WebAgent (Bing Grounding, real-time info)          │    │
│  │  └─ DocAgent (RAG with Azure AI Search)                │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Orchestrator (Speaker Selection / Synthesis)            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
"""

import logging
import os
from typing import AsyncIterator

from agent_framework import (
    ChatAgent,
    ChatMessage,
    ConcurrentBuilder,
    Role,
    WorkflowBuilder,
)
from agent_framework.azure import AzureAIClient
from auth.azure_credential_utils import get_azure_credential_async
from azure.ai.projects.aio import AIProjectClient

logger = logging.getLogger(__name__)

# Agent Names from environment
AGENT_NAME_ORCHESTRATOR = os.getenv("AGENT_NAME_ORCHESTRATOR")
AGENT_NAME_SQL = os.getenv("AGENT_NAME_SQL")
AGENT_NAME_WEB = os.getenv("AGENT_NAME_WEB")
AGENT_NAME_DOC = os.getenv("AGENT_NAME_DOC")


class AgentFactory:
    """Factory for creating specialist agents with proper configuration."""

    def __init__(self, project_client: AIProjectClient, model_deployment_name: str):
        self.project_client = project_client
        self.model_deployment_name = model_deployment_name
        self._agents: dict[str, ChatAgent] = {}

    async def get_sql_agent(self, tools: list | None = None) -> ChatAgent:
        """Create SQL Agent with database query tools."""
        if "sql" in self._agents:
            return self._agents["sql"]

        chat_client = AzureAIClient(
            project_client=self.project_client,
            agent_name=AGENT_NAME_SQL,
            model_deployment_name=self.model_deployment_name,
            use_latest_version=True,
        )

        agent = ChatAgent(
            name="SqlAgent",
            description="Executes SQL queries against Fabric database and generates Chart.js visualizations",
            chat_client=chat_client,
            tools=tools or [],
            tool_choice="auto",
        )
        self._agents["sql"] = agent
        return agent

    async def get_web_agent(self) -> ChatAgent:
        """Create Web Agent with Bing Grounding."""
        if "web" in self._agents:
            return self._agents["web"]

        chat_client = AzureAIClient(
            project_client=self.project_client,
            agent_name=AGENT_NAME_WEB,
            model_deployment_name=self.model_deployment_name,
            use_latest_version=True,
        )

        agent = ChatAgent(
            name="WebAgent",
            description="Searches the web for real-time information using Bing Grounding",
            chat_client=chat_client,
            tools=[],
        )
        self._agents["web"] = agent
        return agent

    async def get_doc_agent(self, knowledge_base_tool=None) -> ChatAgent:
        """Create Document Agent with RAG capabilities."""
        if "doc" in self._agents:
            return self._agents["doc"]

        chat_client = AzureAIClient(
            project_client=self.project_client,
            agent_name=AGENT_NAME_DOC,
            model_deployment_name=self.model_deployment_name,
            use_latest_version=True,
        )

        tools = []
        if knowledge_base_tool:
            tools = [knowledge_base_tool.search]

        agent = ChatAgent(
            name="DocAgent",
            description="Searches enterprise documents and product specifications using Azure AI Search",
            chat_client=chat_client,
            tools=tools,
        )
        self._agents["doc"] = agent
        return agent

    async def get_orchestrator_agent(self) -> ChatAgent:
        """Create Orchestrator Agent for coordination."""
        if "orchestrator" in self._agents:
            return self._agents["orchestrator"]

        chat_client = AzureAIClient(
            project_client=self.project_client,
            agent_name=AGENT_NAME_ORCHESTRATOR,
            model_deployment_name=self.model_deployment_name,
            use_latest_version=True,
        )

        agent = ChatAgent(
            name="Orchestrator",
            description="Coordinates multi-agent collaboration by selecting speakers and synthesizing results",
            chat_client=chat_client,
            tools=[],
        )
        self._agents["orchestrator"] = agent
        return agent


class MultiAgentOrchestrator:
    """
    Multi-agent orchestrator using Agent Framework's native capabilities.

    Supports three orchestration patterns:
    1. GroupChat: Dynamic agent selection by Orchestrator
    2. Concurrent: Parallel execution of multiple agents
    3. Sequential: Pipeline-style agent collaboration
    """

    def __init__(
        self,
        project_client: AIProjectClient,
        model_deployment_name: str,
        sql_tools: list | None = None,
        knowledge_base_tool=None,
    ):
        self.factory = AgentFactory(project_client, model_deployment_name)
        self.sql_tools = sql_tools or []
        self.knowledge_base_tool = knowledge_base_tool
        self._workflow = None
        self._agents_initialized = False

    async def initialize(self):
        """Initialize all agents."""
        if self._agents_initialized:
            return

        self.sql_agent = await self.factory.get_sql_agent(self.sql_tools)
        self.web_agent = await self.factory.get_web_agent()
        self.doc_agent = await self.factory.get_doc_agent(self.knowledge_base_tool)
        self.orchestrator_agent = await self.factory.get_orchestrator_agent()

        self._agents_initialized = True
        logger.info("All agents initialized successfully")

    async def build_group_chat_workflow(self):
        """
        Build a GroupChat workflow where Orchestrator selects speakers.

        This is the most flexible pattern - Orchestrator dynamically decides
        which agent should respond based on conversation context.
        """
        await self.initialize()

        # Convert specialist agents to tools for the orchestrator
        sql_tool = self.sql_agent.as_tool(
            name="query_database",
            description="Query the database for sales, orders, products, and customer data. Returns data and optional Chart.js visualizations.",
            argument_description="The natural language query about database information",
        )

        web_tool = self.web_agent.as_tool(
            name="search_web",
            description="Search the web for real-time information, news, current events, and external data.",
            argument_description="The search query for web information",
        )

        doc_tool = self.doc_agent.as_tool(
            name="search_documents",
            description="Search enterprise documents, product specifications, and technical documentation.",
            argument_description="The search query for document information",
        )

        # Create coordinator with agent tools
        coordinator = ChatAgent(
            name="Coordinator",
            description="Intelligent coordinator that routes queries to appropriate specialists",
            instructions="""You are an intelligent coordinator that helps users by routing their questions to the right specialist tools.

## Available Tools
- **query_database**: Use for questions about sales, orders, products, customers, or any data analysis
- **search_web**: Use for current events, news, external information, or real-time data
- **search_documents**: Use for product specifications, technical documentation, or enterprise knowledge

## Guidelines
1. Analyze the user's question to determine which tool(s) are needed
2. For complex questions requiring multiple sources, call multiple tools
3. Synthesize the results from all tools into a coherent response
4. Always provide helpful, accurate answers based on the tool results

## Examples
- "売上データを見せて" → Use query_database
- "最新のAIニュース" → Use search_web
- "製品Aのスペック" → Use search_documents
- "売上とその関連ニュース" → Use both query_database AND search_web
""",
            chat_client=self.orchestrator_agent._chat_client,
            tools=[sql_tool, web_tool, doc_tool],
            tool_choice="auto",
        )

        return coordinator

    async def build_concurrent_workflow(self, agent_types: list[str]):
        """
        Build a concurrent workflow for parallel execution of specified agents.

        Args:
            agent_types: List of agent types to run in parallel ('sql', 'web', 'doc')

        Returns:
            Workflow that runs agents in parallel
        """
        await self.initialize()

        agents = []
        if "sql" in agent_types:
            agents.append(self.sql_agent)
        if "web" in agent_types:
            agents.append(self.web_agent)
        if "doc" in agent_types:
            agents.append(self.doc_agent)

        if not agents:
            raise ValueError("No valid agent types specified")

        workflow = ConcurrentBuilder().participants(agents).build()

        # Convert to workflow agent for unified interface
        return workflow.as_agent(name="ParallelAgents")

    async def build_sequential_workflow(self, agent_sequence: list[str]):
        """
        Build a sequential workflow (pipeline) of agents.

        Args:
            agent_sequence: Ordered list of agent types to execute

        Returns:
            Workflow that runs agents sequentially
        """
        await self.initialize()

        agent_map = {
            "sql": self.sql_agent,
            "web": self.web_agent,
            "doc": self.doc_agent,
            "orchestrator": self.orchestrator_agent,
        }

        agents = [agent_map[t] for t in agent_sequence if t in agent_map]

        if len(agents) < 2:
            raise ValueError("Sequential workflow requires at least 2 agents")

        builder = WorkflowBuilder()
        builder.set_start_executor(agents[0])

        for i in range(len(agents) - 1):
            builder.add_edge(agents[i], agents[i + 1])

        workflow = builder.build()
        return workflow.as_agent(name="SequentialPipeline")

    async def run_stream(
        self, query: str, thread=None, pattern: str = "group_chat"
    ) -> AsyncIterator[str]:
        """
        Run multi-agent orchestration with streaming output.

        Args:
            query: User's query
            thread: Optional conversation thread for context
            pattern: Orchestration pattern ('group_chat', 'concurrent', 'sequential')

        Yields:
            Response chunks from the agents
        """
        try:
            if pattern == "group_chat":
                coordinator = await self.build_group_chat_workflow()

                async with coordinator:
                    if thread is None:
                        thread = coordinator.get_new_thread()

                    messages = [ChatMessage(role=Role.USER, content=query)]

                    async for update in coordinator.run_stream(messages, thread=thread):
                        if update.text:
                            yield update.text

            elif pattern == "concurrent":
                # For concurrent, run all agents
                workflow_agent = await self.build_concurrent_workflow(
                    ["sql", "web", "doc"]
                )

                async with workflow_agent:
                    if thread is None:
                        thread = workflow_agent.get_new_thread()

                    messages = [ChatMessage(role=Role.USER, content=query)]

                    async for update in workflow_agent.run_stream(
                        messages, thread=thread
                    ):
                        if update.text:
                            yield update.text

            elif pattern == "sequential":
                # Sequential: Orchestrator → relevant specialist → Orchestrator (synthesis)
                workflow_agent = await self.build_sequential_workflow(
                    ["orchestrator", "sql", "orchestrator"]
                )

                async with workflow_agent:
                    if thread is None:
                        thread = workflow_agent.get_new_thread()

                    messages = [ChatMessage(role=Role.USER, content=query)]

                    async for update in workflow_agent.run_stream(
                        messages, thread=thread
                    ):
                        if update.text:
                            yield update.text

            else:
                raise ValueError(f"Unknown orchestration pattern: {pattern}")

        except Exception as e:
            logger.error(f"Error in multi-agent orchestration: {e}")
            yield f"エラーが発生しました: {str(e)}"


async def create_multi_agent_orchestrator(
    sql_tools: list | None = None, knowledge_base_tool=None
) -> MultiAgentOrchestrator:
    """
    Factory function to create a configured MultiAgentOrchestrator.

    Args:
        sql_tools: List of SQL tools for database queries
        knowledge_base_tool: Knowledge base tool for document search

    Returns:
        Configured MultiAgentOrchestrator instance
    """
    endpoint = os.getenv("AZURE_AI_AGENT_ENDPOINT")
    if not endpoint:
        raise ValueError("AZURE_AI_AGENT_ENDPOINT not configured")

    credential = await get_azure_credential_async()

    project_client = AIProjectClient(endpoint=endpoint, credential=credential)

    model_deployment_name = os.getenv(
        "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"
    ) or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

    if not model_deployment_name:
        raise ValueError("Model deployment name not configured")

    orchestrator = MultiAgentOrchestrator(
        project_client=project_client,
        model_deployment_name=model_deployment_name,
        sql_tools=sql_tools,
        knowledge_base_tool=knowledge_base_tool,
    )

    await orchestrator.initialize()

    return orchestrator
