"""
Web Agent Handler

Handles web search queries using Bing Grounding via Azure AI Foundry (New API).
Uses the Foundry Agent Service with create_version() and responses API.

Best Practice Reference:
- https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-tools

Pattern follows official Microsoft sample:
- Create AIProjectClient with DefaultAzureCredential
- Get openai_client from project_client.get_openai_client()
- Use `with project_client:` context manager
- Create agent with agents.create_version()
- Send query with openai_client.responses.create()
- Extract citations from response.output items
- Clean up with agents.delete_version()
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
        # Use gpt-5 for web search agent (best quality)
        self.model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5")

    async def bing_grounding(self, query: str) -> str:
        """
        Search the web using Bing Grounding via Foundry Agent Service (New API).

        Uses the recommended pattern from Microsoft official documentation:
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
            logger.info(
                f"Performing Bing Grounding search via Foundry (New API): {query[:100]}..."
            )

            # Create fresh client for each request (best practice to avoid transport issues)
            # Following official pattern from Microsoft docs
            project_client = AIProjectClient(
                endpoint=self.foundry_endpoint,
                credential=DefaultAzureCredential(),
            )

            # Get OpenAI client BEFORE entering context manager
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

            # Use context manager for proper resource management
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

                    # Extract answer text safely
                    answer_text = ""
                    if hasattr(response, "output_text") and response.output_text:
                        answer_text = response.output_text

                    # Extract URL citations from output items with proper null checks
                    citations = []
                    if hasattr(response, "output") and response.output:
                        for item in response.output:
                            # Check if item has content attribute and it's not None
                            if not hasattr(item, "content") or item.content is None:
                                continue

                            for content in item.content:
                                # Check if content has annotations and it's not None
                                if (
                                    not hasattr(content, "annotations")
                                    or content.annotations is None
                                ):
                                    continue

                                for annotation in content.annotations:
                                    if (
                                        hasattr(annotation, "type")
                                        and annotation.type == "url_citation"
                                    ):
                                        citations.append(
                                            {
                                                "url": getattr(annotation, "url", ""),
                                                "title": getattr(
                                                    annotation, "title", ""
                                                ),
                                            }
                                        )

                    logger.info(
                        f"Bing Grounding response received. "
                        f"Answer length: {len(answer_text)}, Citations: {len(citations)}"
                    )

                finally:
                    # Clean up the agent version
                    try:
                        project_client.agents.delete_version(
                            agent_name=agent.name, agent_version=agent.version
                        )
                        logger.info(
                            f"Deleted Bing search agent: {agent.name} v{agent.version}"
                        )
                    except Exception as cleanup_error:
                        logger.warning(
                            f"Failed to delete agent (non-critical): {cleanup_error}"
                        )

            # Return results
            if answer_text:
                logger.info(
                    f"Bing Grounding completed successfully. "
                    f"Found {len(citations)} citations."
                )
                # Format citations for UI display (Bing terms of use compliance)
                # Each citation must have url and title for proper display
                formatted_citations = []
                for i, cit in enumerate(citations):
                    formatted_citations.append(
                        {
                            "id": f"web-{i + 1}",
                            "title": cit.get("title") or f"Web Source {i + 1}",
                            "url": cit.get("url", ""),
                            "filepath": cit.get(
                                "url", ""
                            ),  # UI uses filepath for display
                            "content": "",  # No content for web citations
                            "metadata": None,
                            "chunk_id": None,
                            "reindex_id": None,
                        }
                    )

                return json.dumps(
                    {
                        "answer": answer_text,
                        "citations": formatted_citations,
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
