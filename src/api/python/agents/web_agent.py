"""
Web Agent Handler

Handles web search queries using Bing Grounding via Azure AI Foundry (New API).
Uses the Foundry Agent Service with create_version() and responses API.

Best Practice Reference:
- https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-tools
"""

import json
import logging
import os
from typing import List, Optional

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    BingGroundingAgentTool,
    BingGroundingSearchConfiguration,
    BingGroundingSearchToolParameters,
    PromptAgentDefinition,
)
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)


class WebAgentHandler:
    """Handler for Web Agent tool execution using Bing Grounding via Foundry (New API)."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Web Agent Handler.

        Args:
            api_key: Bing Search API key (optional, kept for backward compatibility)
        """
        self.api_key = api_key or os.getenv("BING_SEARCH_API_KEY")
        self.foundry_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        self.bing_connection_id = os.getenv("BING_PROJECT_CONNECTION_ID")
        # Use gpt-4o-mini for web search agent (lighter weight, faster)
        self.model_deployment = os.getenv(
            "AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini"
        )
        self._project_client = None
        self._credential = None

    def _get_project_client(self) -> Optional[AIProjectClient]:
        """Get or create the AIProjectClient."""
        if self._project_client is None:
            if not self.foundry_endpoint:
                return None
            self._credential = DefaultAzureCredential()
            self._project_client = AIProjectClient(
                endpoint=self.foundry_endpoint, credential=self._credential
            )
        return self._project_client

    async def bing_grounding(self, query: str) -> str:
        """
        Search the web using Bing Grounding via Foundry Agent Service (New API).

        Uses the recommended pattern:
        - agents.create_version() for agent creation
        - openai_client.responses.create() for responses

        Args:
            query: The search query to send to Bing

        Returns:
            JSON string containing search results with citations
        """
        # Check if Foundry Bing Grounding is configured
        if not self.foundry_endpoint or not self.bing_connection_id:
            logger.warning(
                "Foundry Bing Grounding not configured "
                "(missing AZURE_AI_PROJECT_ENDPOINT or BING_PROJECT_CONNECTION_ID)"
            )
            return json.dumps(
                {
                    "answer": f"[Web検索が設定されていません] '{query}'についての情報は、"
                    f"私の学習データに基づいて回答します。\n\n"
                    f"注: 以下は私の知識（2024年までの情報）に基づく回答です。",
                    "citations": [],
                    "fallback": True,
                    "note": "Foundry Bing Grounding is not configured.",
                },
                ensure_ascii=False,
            )

        try:
            project_client = self._get_project_client()
            if not project_client:
                raise ValueError("Failed to create AIProjectClient")

            logger.info(
                f"Performing Bing Grounding search via Foundry (New API): {query[:100]}..."
            )

            # Get OpenAI client for responses API
            openai_client = project_client.get_openai_client()

            # Create Bing Grounding tool with New API
            bing_grounding_tool = BingGroundingAgentTool(
                bing_grounding=BingGroundingSearchToolParameters(
                    search_configurations=[
                        BingGroundingSearchConfiguration(
                            project_connection_id=self.bing_connection_id,
                            count=5,  # Number of search results
                            market="ja-JP",  # Japanese market
                            freshness="Week",  # Recent results
                        )
                    ]
                )
            )

            with project_client:
                # Create agent version with New API (create_version)
                agent = project_client.agents.create_version(
                    agent_name="web-search-agent",
                    definition=PromptAgentDefinition(
                        model=self.model_deployment,
                        instructions=(
                            "You are a web search assistant. Search the web and return "
                            "relevant information with citations. Focus on current trends "
                            "and recent data. Always cite your sources."
                        ),
                        tools=[bing_grounding_tool],
                    ),
                    description="Agent for web search with Bing Grounding",
                )
                logger.info(
                    f"Created Bing search agent: id={agent.id}, "
                    f"name={agent.name}, version={agent.version}"
                )

                try:
                    # Use responses API (recommended pattern)
                    response = openai_client.responses.create(
                        input=f"Search the web for: {query}",
                        tool_choice="required",  # Force the model to use Bing search
                        extra_body={
                            "agent": {"name": agent.name, "type": "agent_reference"}
                        },
                    )

                    # Extract answer and citations
                    answer_text = response.output_text if response.output_text else ""
                    citations = []

                    # Extract URL citations from output items
                    if hasattr(response, "output") and response.output:
                        for item in response.output:
                            if hasattr(item, "content"):
                                for content in item.content:
                                    if hasattr(content, "annotations"):
                                        for annotation in content.annotations:
                                            if annotation.type == "url_citation":
                                                citations.append(
                                                    {
                                                        "url": annotation.url,
                                                        "title": getattr(
                                                            annotation, "title", ""
                                                        ),
                                                    }
                                                )

                finally:
                    # Clean up the agent version
                    project_client.agents.delete_version(
                        agent_name=agent.name, agent_version=agent.version
                    )
                    logger.info(
                        f"Deleted Bing search agent: {agent.name} v{agent.version}"
                    )

            if answer_text:
                logger.info(
                    f"Bing Grounding completed. Found {len(citations)} citations."
                )
                return json.dumps(
                    {
                        "answer": answer_text,
                        "citations": citations,
                        "source": "bing_grounding_foundry_new_api",
                    },
                    ensure_ascii=False,
                )
            else:
                logger.warning("Bing Grounding returned empty response")
                return json.dumps(
                    {
                        "answer": f"[Web検索結果が空でした] '{query}'についての情報は、"
                        f"私の学習データに基づいて回答します。",
                        "citations": [],
                        "fallback": True,
                        "note": "Bing search returned empty results.",
                    },
                    ensure_ascii=False,
                )

        except Exception as e:
            logger.error(f"Bing Grounding error: {e}", exc_info=True)
            return json.dumps(
                {
                    "answer": f"[Web検索でエラーが発生しました] '{query}'についての情報は、"
                    f"私の学習データに基づいて回答します。\n\n"
                    f"エラー詳細: {str(e)[:200]}",
                    "citations": [],
                    "fallback": True,
                    "note": f"Bing Grounding failed: {str(e)}",
                },
                ensure_ascii=False,
            )

    def get_tools(self) -> List[callable]:
        """Return the list of tools for the Web Agent."""
        return [self.bing_grounding]
