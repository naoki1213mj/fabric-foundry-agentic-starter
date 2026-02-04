"""
Web Agent Handler

Handles web search queries using Web Search tool (preview) via Azure AI Foundry.
Uses the Foundry Agent Service with create_version() and responses API.

Best Practice Reference:
- https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/web-search

Pattern follows official Microsoft sample:
- Create AIProjectClient with DefaultAzureCredential
- Get openai_client from project_client.get_openai_client()
- Use `with project_client:` context manager
- Create agent with agents.create_version()
- Send query with openai_client.responses.create()
- Extract citations from response.output items
- Clean up with agents.delete_version()

Note: Web Search tool (preview) is recommended over Bing Grounding because:
- Bing Grounding does NOT support gpt-4o-mini (2024-07-18) and gpt-5 models
- Web Search tool supports all models including gpt-5
"""

import asyncio
import json
import logging
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    ApproximateLocation,
    PromptAgentDefinition,
    WebSearchPreviewTool,
)
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

# Timeout configuration for Web Search tool (preview)
# Foundry Agent Service may take longer due to web search operations
WEB_SEARCH_TIMEOUT_SECONDS = 60  # Total timeout for web search operation


class WebAgentHandler:
    """Handler for Web Agent tool execution using Web Search tool (preview) via Foundry."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize the Web Agent Handler.

        Args:
            api_key: Bing Search API key (optional, kept for backward compatibility)
        """
        self.api_key = api_key or os.getenv("BING_SEARCH_API_KEY")
        # Support both AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_AGENT_ENDPOINT for compatibility
        self.foundry_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv(
            "AZURE_AI_AGENT_ENDPOINT"
        )
        # Note: BING_PROJECT_CONNECTION_ID is no longer required for Web Search tool
        self.bing_connection_id = os.getenv("BING_PROJECT_CONNECTION_ID")
        # gpt-5 is now supported with Web Search tool (preview)
        self.model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5")

    async def web_search(self, query: str) -> str:
        """
        Search the web using Web Search tool (preview) via Foundry Agent Service.

        Uses the recommended pattern from Microsoft official documentation:
        - agents.create_version() for agent creation
        - openai_client.responses.create() for responses

        Note: Web Search tool is preferred over Bing Grounding because it supports
        all models including gpt-5.

        Args:
            query: The search query to send to the web

        Returns:
            JSON string containing search results with citations
        """
        # Check if Foundry endpoint is configured
        if not self.foundry_endpoint:
            logger.warning(
                "Foundry Web Search not configured "
                "(missing AZURE_AI_PROJECT_ENDPOINT or AZURE_AI_AGENT_ENDPOINT)"
            )
            return json.dumps(
                {
                    "answer": f"[Web検索が設定されていません] '{query}'についての情報は、"
                    f"私の学習データに基づいて回答します。\n\n"
                    f"注: 以下は私の知識（2024年までの情報）に基づく回答です。",
                    "citations": [],
                    "fallback": True,
                    "note": "Foundry Web Search is not configured.",
                },
                ensure_ascii=False,
            )

        try:
            logger.info(f"Performing Web Search via Foundry (Web Search tool): {query[:100]}...")

            # Create fresh client for each request (best practice to avoid transport issues)
            # Following official pattern from Microsoft docs
            project_client = AIProjectClient(
                endpoint=self.foundry_endpoint,
                credential=DefaultAzureCredential(),
            )

            # Get OpenAI client BEFORE entering context manager
            openai_client = project_client.get_openai_client()

            # Create Web Search tool (preview) - new recommended API
            # user_location helps return results relevant to user's geography
            web_search_tool = WebSearchPreviewTool(
                user_location=ApproximateLocation(
                    country="JP",
                    city="Tokyo",
                    region="Kanto",
                )
            )

            # Use context manager for proper resource management
            with project_client:
                # Create agent version with Web Search tool
                agent = project_client.agents.create_version(
                    agent_name="web-search-agent",
                    definition=PromptAgentDefinition(
                        model=self.model_deployment,
                        instructions=(
                            "You are a web search assistant. Search the web and return "
                            "relevant information with citations. Focus on current trends "
                            "and recent data. Always cite your sources. "
                            "Respond in Japanese when the query is in Japanese."
                        ),
                        tools=[web_search_tool],
                    ),
                    description="Agent for web search with Web Search tool (preview)",
                )
                logger.info(
                    f"Created Web Search agent: id={agent.id}, "
                    f"name={agent.name}, version={agent.version}"
                )

                try:
                    # Use responses API (recommended pattern)
                    # Wrap in asyncio.to_thread with timeout to handle 408 errors
                    logger.info(
                        f"Calling responses.create with timeout={WEB_SEARCH_TIMEOUT_SECONDS}s"
                    )

                    def _create_response():
                        return openai_client.responses.create(
                            input=f"Search the web for: {query}",
                            tool_choice="required",  # Force the model to use web search
                            extra_body={
                                "agent": {"name": agent.name, "type": "agent_reference"}
                            },
                        )

                    try:
                        response = await asyncio.wait_for(
                            asyncio.to_thread(_create_response),
                            timeout=WEB_SEARCH_TIMEOUT_SECONDS,
                        )
                    except TimeoutError:
                        logger.error(
                            f"Web search timed out after {WEB_SEARCH_TIMEOUT_SECONDS}s"
                        )
                        raise TimeoutError(
                            f"Web search operation timed out after "
                            f"{WEB_SEARCH_TIMEOUT_SECONDS} seconds"
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
                                                "title": getattr(annotation, "title", ""),
                                            }
                                        )

                    logger.info(
                        f"Web Search response received. "
                        f"Answer length: {len(answer_text)}, Citations: {len(citations)}"
                    )

                finally:
                    # Clean up the agent version
                    try:
                        project_client.agents.delete_version(
                            agent_name=agent.name, agent_version=agent.version
                        )
                        logger.info(f"Deleted Web Search agent: {agent.name} v{agent.version}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to delete agent (non-critical): {cleanup_error}")

            # Return results
            if answer_text:
                logger.info(
                    f"Web Search completed successfully. Found {len(citations)} citations."
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
                            "filepath": cit.get("url", ""),  # UI uses filepath for display
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
                        "source": "web_search_preview_tool",
                    },
                    ensure_ascii=False,
                )
            else:
                logger.warning("Web Search returned empty response")
                return json.dumps(
                    {
                        "answer": f"[Web検索結果が空でした] '{query}'についての情報は、"
                        f"私の学習データに基づいて回答します。",
                        "citations": [],
                        "fallback": True,
                        "note": "Web search returned empty results.",
                    },
                    ensure_ascii=False,
                )

        except TimeoutError as te:
            # Handle timeout specifically with user-friendly message
            logger.error(f"Web Search timeout: {te}")
            return json.dumps(
                {
                    "answer": f"[Web検索がタイムアウトしました] '{query}'についての情報は、"
                    f"私の学習データに基づいて回答します。\n\n"
                    f"Web検索サービスが混雑しているため、後でもう一度お試しください。",
                    "citations": [],
                    "fallback": True,
                    "timeout": True,
                    "note": f"Web search timed out after {WEB_SEARCH_TIMEOUT_SECONDS}s",
                },
                ensure_ascii=False,
            )

        except Exception as e:
            logger.error(f"Web Search error: {e}", exc_info=True)
            return json.dumps(
                {
                    "answer": f"[Web検索でエラーが発生しました] '{query}'についての情報は、"
                    f"私の学習データに基づいて回答します。\n\n"
                    f"エラー詳細: {str(e)[:200]}",
                    "citations": [],
                    "fallback": True,
                    "note": f"Web Search failed: {str(e)}",
                },
                ensure_ascii=False,
            )

    # Backward compatibility alias
    async def bing_grounding(self, query: str) -> str:
        """
        Backward compatibility alias for web_search.

        Note: This method now uses Web Search tool (preview) instead of Bing Grounding
        because Bing Grounding does not support gpt-5 models.
        """
        return await self.web_search(query)

    def get_tools(self) -> list[callable]:
        """Return the list of tools for the Web Agent."""
        return [self.web_search]
