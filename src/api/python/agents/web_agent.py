"""Web Agent Handler using Grounding with Bing Search via Azure AI Foundry.

Uses the Foundry Agent Service with create_version() and responses API.
Best Practice Reference: https://learn.microsoft.com/azure/ai-foundry/agents/how-to/tools/bing-tools
"""

import asyncio
import json
import logging
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    BingGroundingAgentTool,
    BingGroundingSearchConfiguration,
    BingGroundingSearchToolParameters,
    PromptAgentDefinition,
)
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

WEB_SEARCH_TIMEOUT_SECONDS = 90


class WebAgentHandler:
    """Handler for Web Agent using Grounding with Bing Search via Foundry."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Web Agent Handler.

        Args:
            api_key: Legacy parameter (kept for backward compatibility, not used)
        """
        self.foundry_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv(
            "AZURE_AI_AGENT_ENDPOINT"
        )
        self.bing_connection_name = os.getenv("BING_PROJECT_CONNECTION_NAME")
        self.model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5")

        if not self.foundry_endpoint:
            logger.warning("Foundry Web Search not configured (missing AZURE_AI_PROJECT_ENDPOINT)")
        if not self.bing_connection_name:
            logger.warning("Bing Grounding not configured (missing BING_PROJECT_CONNECTION_NAME)")
        else:
            logger.info(
                f"WebAgentHandler configured: endpoint={self.foundry_endpoint}, "
                f"bing_connection={self.bing_connection_name}"
            )

    def is_configured(self) -> bool:
        """Check if the handler is properly configured."""
        return bool(self.foundry_endpoint and self.bing_connection_name)

    async def web_search(self, query: str) -> str:
        """Search the web using Grounding with Bing Search via Foundry Agent Service.

        Args:
            query: The search query to send to the web

        Returns:
            JSON string containing search results with citations
        """
        if not self.is_configured():
            logger.warning("Bing Grounding not properly configured")
            return json.dumps(
                {
                    "answer": f"[Web検索が設定されていません] '{query}'についての情報は、"
                    f"私の学習データに基づいて回答します。",
                    "citations": [],
                    "fallback": True,
                    "note": "Bing Grounding is not configured.",
                },
                ensure_ascii=False,
            )

        try:
            logger.info(f"Performing Bing Grounding search: {query[:100]}...")

            credential = DefaultAzureCredential()
            project_client = AIProjectClient(
                endpoint=self.foundry_endpoint,
                credential=credential,
            )

            with project_client:
                try:
                    bing_connection = project_client.connections.get(self.bing_connection_name)
                    bing_connection_id = bing_connection.id
                    logger.info(f"Bing connection ID: {bing_connection_id}")
                except Exception as conn_error:
                    logger.error(f"Failed to get Bing connection: {conn_error}")
                    return json.dumps(
                        {
                            "answer": f"[Bing接続エラー] '{query}'についての情報は、"
                            f"私の学習データに基づいて回答します。",
                            "citations": [],
                            "fallback": True,
                            "note": f"Bing connection error: {str(conn_error)}",
                        },
                        ensure_ascii=False,
                    )

                openai_client = project_client.get_openai_client()

                bing_grounding_tool = BingGroundingAgentTool(
                    bing_grounding=BingGroundingSearchToolParameters(
                        search_configurations=[
                            BingGroundingSearchConfiguration(
                                project_connection_id=bing_connection_id,
                            )
                        ]
                    )
                )

                agent = project_client.agents.create_version(
                    agent_name="web-search-agent-bing",
                    definition=PromptAgentDefinition(
                        model=self.model_deployment,
                        instructions=(
                            "You are a web search assistant with access to Bing Search. "
                            "Search the web and return relevant information with citations. "
                            "Respond in Japanese when the query is in Japanese."
                        ),
                        tools=[bing_grounding_tool],
                    ),
                    description="Web search agent with Bing Grounding",
                )
                logger.info(f"Created Bing agent: {agent.name} v{agent.version}")

                try:

                    def _create_response():
                        return openai_client.responses.create(
                            input=f"Search the web for: {query}",
                            tool_choice="required",
                            extra_body={
                                "agent": {
                                    "name": agent.name,
                                    "type": "agent_reference",
                                }
                            },
                        )

                    response = await asyncio.wait_for(
                        asyncio.to_thread(_create_response),
                        timeout=WEB_SEARCH_TIMEOUT_SECONDS,
                    )

                    answer_text = ""
                    if hasattr(response, "output_text") and response.output_text:
                        answer_text = response.output_text

                    citations = []
                    annotations_with_position = []
                    if hasattr(response, "output") and response.output:
                        for item in response.output:
                            if not hasattr(item, "content") or item.content is None:
                                continue
                            for content in item.content:
                                if hasattr(content, "annotations") and content.annotations:
                                    for annotation in content.annotations:
                                        if getattr(annotation, "type", "") == "url_citation":
                                            url = getattr(annotation, "url", "")
                                            title = getattr(annotation, "title", "")
                                            start_idx = getattr(annotation, "start_index", None)
                                            end_idx = getattr(annotation, "end_index", None)
                                            citations.append({"url": url, "title": title})
                                            if start_idx is not None and end_idx is not None:
                                                annotations_with_position.append(
                                                    {
                                                        "url": url,
                                                        "title": title,
                                                        "start": start_idx,
                                                        "end": end_idx,
                                                    }
                                                )

                    logger.info(
                        f"Bing response: len={len(answer_text)}, citations={len(citations)}, with_position={len(annotations_with_position)}"
                    )

                finally:
                    try:
                        project_client.agents.delete_version(
                            agent_name=agent.name, agent_version=agent.version
                        )
                        logger.info(f"Deleted agent: {agent.name} v{agent.version}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to delete agent: {cleanup_error}")

            if answer_text:
                # Build structured citations for UI display
                # (inline markers removed - Citations UI component handles display)
                formatted_citations = []
                seen_urls: set[str] = set()
                for i, cit in enumerate(citations):
                    url = cit.get("url", "")
                    # Deduplicate by URL
                    if url and url in seen_urls:
                        continue
                    if url:
                        seen_urls.add(url)
                    formatted_citations.append(
                        {
                            "id": f"web-{i + 1}",
                            "title": cit.get("title") or f"Web Source {i + 1}",
                            "url": url,
                            "filepath": url,
                            "content": "",
                            "metadata": None,
                            "chunk_id": None,
                            "reindex_id": None,
                        }
                    )

                logger.info(f"Prepared {len(formatted_citations)} citations for UI display")

                return json.dumps(
                    {
                        "answer": answer_text,
                        "citations": formatted_citations,
                        "source": "bing_grounding_tool",
                    },
                    ensure_ascii=False,
                )
            else:
                return json.dumps(
                    {
                        "answer": f"[Web検索結果が空でした] '{query}'について回答します。",
                        "citations": [],
                        "fallback": True,
                    },
                    ensure_ascii=False,
                )

        except TimeoutError:
            logger.error(f"Bing Grounding timeout after {WEB_SEARCH_TIMEOUT_SECONDS}s")
            return json.dumps(
                {
                    "answer": f"[Web検索タイムアウト] '{query}'について回答します。",
                    "citations": [],
                    "fallback": True,
                    "timeout": True,
                },
                ensure_ascii=False,
            )

        except Exception as e:
            logger.error(f"Bing Grounding error: {e}", exc_info=True)
            return json.dumps(
                {
                    "answer": f"[Web検索エラー] '{query}'について回答します。",
                    "citations": [],
                    "fallback": True,
                    "note": f"Error: {str(e)[:200]}",
                },
                ensure_ascii=False,
            )

    async def bing_grounding(self, query: str) -> str:
        """Backward compatibility alias for web_search."""
        return await self.web_search(query)

    def get_tools(self) -> list[callable]:
        """Return the list of tools for the Web Agent."""
        return [self.web_search]
