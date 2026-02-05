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
                # Insert inline citation markers into the answer text
                # Sort annotations by start position in reverse to avoid index shifting
                if annotations_with_position:
                    # Create URL to index mapping
                    url_to_idx: dict[str, int] = {}
                    for i, cit in enumerate(citations):
                        url = cit.get("url", "")
                        if url and url not in url_to_idx:
                            url_to_idx[url] = i + 1

                    # Sort by end position descending to insert from back to front
                    sorted_annotations = sorted(
                        annotations_with_position,
                        key=lambda x: x["end"],
                        reverse=True,
                    )

                    # Insert inline citations at annotation positions
                    for ann in sorted_annotations:
                        url = ann.get("url", "")
                        end_pos = ann.get("end", 0)
                        if url in url_to_idx and end_pos <= len(answer_text):
                            idx = url_to_idx[url]
                            # Insert markdown link reference after the cited text
                            citation_link = f" [[{idx}]]({url})"
                            answer_text = (
                                answer_text[:end_pos] + citation_link + answer_text[end_pos:]
                            )

                    logger.info(f"Inserted {len(sorted_annotations)} inline citations")
                elif citations:
                    # Fallback: Bing API does not provide start_index/end_index
                    # Add reference numbers at the end of each paragraph
                    logger.info("No position data from Bing API, using fallback inline citation")
                    # Add reference superscripts at the end of answer
                    # Create a simple reference list inline
                    ref_markers = ", ".join(
                        [
                            f"[[{i + 1}]]({cit.get('url', '')})"
                            for i, cit in enumerate(citations[:5])
                        ]
                    )
                    if ref_markers:
                        answer_text = answer_text.rstrip() + f"\n\n*参照: {ref_markers}*"

                formatted_citations = []
                for i, cit in enumerate(citations):
                    formatted_citations.append(
                        {
                            "id": f"web-{i + 1}",
                            "title": cit.get("title") or f"Web Source {i + 1}",
                            "url": cit.get("url", ""),
                            "filepath": cit.get("url", ""),
                            "content": "",
                            "metadata": None,
                            "chunk_id": None,
                            "reindex_id": None,
                        }
                    )

                # Add inline source links at the end of the answer for web search results
                if citations:
                    source_links = "\n\n**情報源:**\n"
                    seen_urls = set()
                    for i, cit in enumerate(citations):
                        url = cit.get("url", "")
                        title = cit.get("title") or f"Web Source {i + 1}"
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            source_links += f"- [{title}]({url})\n"
                    if seen_urls:
                        answer_text = answer_text.rstrip() + source_links

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
