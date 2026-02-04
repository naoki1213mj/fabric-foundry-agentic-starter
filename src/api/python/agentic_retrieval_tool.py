"""
Agentic Retrieval Tool for Azure AI Search Knowledge Base.

This module provides a tool for querying Azure AI Search Knowledge Bases
using the Agentic Retrieval API with Foundry IQ capabilities.

Features:
- Query decomposition and planning (with LLM reasoning)
- Multi-source retrieval with semantic reranking
- Configurable reasoning effort (minimal/low/medium)
- Source attribution and citations
- MCP endpoint support for Foundry Agent Service integration

Reference:
- https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/foundry-iq-connect
- https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-how-to-set-retrieval-reasoning-effort
"""

import json
import logging
import os
from enum import StrEnum
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class ReasoningEffort(StrEnum):
    """Reasoning effort levels for agentic retrieval.

    minimal: No LLM processing, direct search only. Lowest cost/latency.
    low: Single pass LLM query planning. Default, balanced.
    medium: Iterative search with semantic classifier. Highest quality.
    """

    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"


class AgenticRetrievalTool:
    """Tool for querying Azure AI Search Knowledge Base with Agentic Retrieval."""

    def __init__(
        self,
        search_endpoint: str,
        knowledge_base_name: str,
        api_key: str | None = None,
        default_reasoning_effort: ReasoningEffort = ReasoningEffort.LOW,
    ):
        """
        Initialize the Agentic Retrieval Tool.

        Args:
            search_endpoint: The Azure AI Search endpoint URL
            knowledge_base_name: The name of the knowledge base
            api_key: API key for authentication (optional if using managed identity)
            default_reasoning_effort: Default reasoning effort level
        """
        self.search_endpoint = search_endpoint.rstrip("/")
        self.knowledge_base_name = knowledge_base_name
        self.api_key = api_key
        self.default_reasoning_effort = default_reasoning_effort
        self._session: aiohttp.ClientSession | None = None

    @classmethod
    def create_from_env(cls) -> "AgenticRetrievalTool | None":
        """
        Create an AgenticRetrievalTool from environment variables.

        Environment variables:
            AI_SEARCH_ENDPOINT: The Azure AI Search endpoint URL
            AI_SEARCH_KNOWLEDGE_BASE_NAME: The name of the knowledge base
            AI_SEARCH_API_KEY: API key for authentication (optional)
            AI_SEARCH_REASONING_EFFORT: Default reasoning effort (minimal/low/medium)

        Returns:
            AgenticRetrievalTool instance or None if not configured
        """
        search_endpoint = os.getenv("AI_SEARCH_ENDPOINT")
        kb_name = os.getenv("AI_SEARCH_KNOWLEDGE_BASE_NAME")
        api_key = os.getenv("AI_SEARCH_API_KEY")
        reasoning_effort_str = os.getenv("AI_SEARCH_REASONING_EFFORT", "low").lower()

        if not search_endpoint:
            logger.warning("AI_SEARCH_ENDPOINT not configured")
            return None
        if not kb_name:
            logger.warning("AI_SEARCH_KNOWLEDGE_BASE_NAME not configured")
            return None

        # Parse reasoning effort
        try:
            reasoning_effort = ReasoningEffort(reasoning_effort_str)
        except ValueError:
            logger.warning(
                f"Invalid reasoning effort '{reasoning_effort_str}', using 'low'"
            )
            reasoning_effort = ReasoningEffort.LOW

        logger.info(
            f"AgenticRetrievalTool configured: "
            f"endpoint={search_endpoint}, kb={kb_name}, reasoning={reasoning_effort.value}"
        )
        return cls(
            search_endpoint=search_endpoint,
            knowledge_base_name=kb_name,
            api_key=api_key,
            default_reasoning_effort=reasoning_effort,
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["api-key"] = self.api_key
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    @property
    def retrieve_url(self) -> str:
        """Get the retrieve endpoint URL."""
        return (
            f"{self.search_endpoint}/knowledgebases/{self.knowledge_base_name}"
            f"/retrieve?api-version=2025-11-01-preview"
        )

    @property
    def mcp_url(self) -> str:
        """Get the MCP endpoint URL for Foundry Agent Service integration."""
        return (
            f"{self.search_endpoint}/knowledgebases/{self.knowledge_base_name}"
            f"/mcp?api-version=2025-11-01-preview"
        )

    async def retrieve(
        self,
        query: str,
        reasoning_effort: ReasoningEffort | None = None,
        output_mode: str = "extractiveData",
        max_runtime_seconds: int = 30,
        max_output_size: int = 6000,
    ) -> dict[str, Any]:
        """
        Retrieve documents from the knowledge base using agentic retrieval.

        Args:
            query: The user query
            reasoning_effort: Override default reasoning effort (minimal/low/medium)
            output_mode: 'extractiveData' or 'answerSynthesis'
            max_runtime_seconds: Maximum runtime for the retrieval
            max_output_size: Maximum output size in tokens

        Returns:
            dict containing retrieval results with sources, references, and activity log
        """
        session = await self._get_session()
        effort = reasoning_effort or self.default_reasoning_effort

        # Build request based on reasoning effort
        if effort == ReasoningEffort.MINIMAL:
            # Minimal: use intents (direct search, no LLM)
            request_body = {
                "intents": [{"type": "semantic", "search": query}],
            }
        else:
            # Low/Medium: use messages (LLM-based query planning)
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": query}],
                    }
                ],
                "retrievalReasoningEffort": {"kind": effort.value},
                "outputMode": output_mode,
                "maxRuntimeInSeconds": max_runtime_seconds,
                "maxOutputSize": max_output_size,
            }

        try:
            logger.info(
                f"Agentic retrieval: kb={self.knowledge_base_name}, "
                f"query='{query[:50]}...', effort={effort.value}"
            )
            async with session.post(
                self.retrieve_url, json=request_body
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return self._parse_retrieve_response(result, effort)
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Retrieve request failed: {response.status} - {error_text}"
                    )
                    return {"error": f"Retrieve failed: {response.status}"}

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error during retrieve request: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during retrieve request: {e}")
            return {"error": str(e)}

    def _parse_retrieve_response(
        self, response: dict, effort: ReasoningEffort
    ) -> dict[str, Any]:
        """
        Parse agentic retrieval response into a structured format.

        Args:
            response: Raw retrieval response
            effort: The reasoning effort used

        Returns:
            Parsed response with sources, references, and activity
        """
        if "error" in response:
            return {"error": response["error"]}

        # Extract response content
        response_data = response.get("response", [])
        activity = response.get("activity", [])
        references = response.get("references", [])

        # Parse content from response
        sources = []
        for item in response_data:
            content_list = item.get("content", [])
            for content_item in content_list:
                if content_item.get("type") == "text":
                    text = content_item.get("text", "")
                    # Try to parse JSON content (extractiveData format)
                    try:
                        parsed = json.loads(text)
                        if isinstance(parsed, list):
                            for doc in parsed:
                                sources.append(
                                    {
                                        "ref_id": doc.get("ref_id"),
                                        "content": doc.get("content", ""),
                                    }
                                )
                        else:
                            sources.append({"content": text})
                    except json.JSONDecodeError:
                        sources.append({"content": text})

        # Add reference scores
        for ref in references:
            ref_id = ref.get("id")
            score = ref.get("rerankerScore", 0)
            for source in sources:
                if str(source.get("ref_id")) == str(ref_id):
                    source["reranker_score"] = score
                    source["source_type"] = ref.get("type", "unknown")
                    break

        # Extract activity summary
        activity_summary = []
        for act in activity:
            act_type = act.get("type", "unknown")
            if act_type == "agenticReasoning":
                activity_summary.append(
                    {
                        "type": act_type,
                        "reasoning_effort": act.get("retrievalReasoningEffort", {}).get(
                            "kind", effort.value
                        ),
                        "reasoning_tokens": act.get("reasoningTokens", 0),
                    }
                )
            elif act_type in ["indexedSharePoint", "searchIndex"]:
                activity_summary.append(
                    {
                        "type": act_type,
                        "knowledge_source": act.get("knowledgeSourceName", ""),
                        "count": act.get("count", 0),
                        "elapsed_ms": act.get("elapsedMs", 0),
                    }
                )

        logger.info(
            f"Agentic retrieval completed: {len(sources)} sources, "
            f"{len(references)} references, effort={effort.value}"
        )

        return {
            "sources": sources,
            "references": references,
            "activity": activity_summary,
            "total": len(sources),
            "reasoning_effort": effort.value,
        }

    async def retrieve_formatted(
        self,
        query: str,
        reasoning_effort: ReasoningEffort | None = None,
    ) -> str:
        """
        Retrieve documents and format for agent use.

        This is the main function to be used as an agent tool.

        Args:
            query: The search query
            reasoning_effort: Override default reasoning effort

        Returns:
            Formatted string with search results and citations
        """
        result = await self.retrieve(query, reasoning_effort)

        if "error" in result:
            return f"ナレッジベース検索中にエラーが発生しました: {result['error']}"

        sources = result.get("sources", [])
        if not sources:
            return "関連するドキュメントが見つかりませんでした。"

        # Format results with citations and relevance scores
        formatted = []
        for i, source in enumerate(sources):
            ref_id = source.get("ref_id", i)
            score = source.get("reranker_score", 0)
            content = source.get("content", "")

            # Truncate very long content
            if len(content) > 2000:
                content = content[:2000] + "...(truncated)"

            citation = f"【ref_{ref_id}†relevance:{score:.2f}】"
            formatted.append(f"{citation}\n{content}")

        # Add activity summary
        activity = result.get("activity", [])
        activity_info = []
        for act in activity:
            if act.get("type") == "agenticReasoning":
                tokens = act.get("reasoning_tokens", 0)
                activity_info.append(f"推論トークン: {tokens:,}")
            elif act.get("knowledge_source"):
                ks = act.get("knowledge_source", "")
                count = act.get("count", 0)
                ms = act.get("elapsed_ms", 0)
                activity_info.append(f"{ks}: {count}件 ({ms}ms)")

        footer = f"\n\n---\n📊 Reasoning Effort: {result.get('reasoning_effort', 'unknown')}"
        if activity_info:
            footer += f" | {' | '.join(activity_info)}"

        return "\n\n---\n\n".join(formatted) + footer


# Tool function for agent integration
async def agentic_knowledge_retrieve(
    query: str,
    reasoning_effort: str = "low",
) -> str:
    """
    Search the knowledge base using Azure AI Search Agentic Retrieval.

    This tool uses Foundry IQ to provide intelligent document retrieval with:
    - Query decomposition and planning
    - Multi-source retrieval with semantic reranking
    - Configurable reasoning effort for cost/quality tradeoff

    Args:
        query: The search query for finding relevant documents
        reasoning_effort: Level of LLM processing ('minimal', 'low', 'medium')
            - minimal: Direct search, no LLM. Fastest, lowest cost.
            - low: Single-pass LLM query planning. Default, balanced.
            - medium: Iterative search with semantic classifier. Best quality.

    Returns:
        Formatted search results with citations and relevance scores
    """
    tool = AgenticRetrievalTool.create_from_env()
    if not tool:
        return "ナレッジベースが設定されていません。"

    try:
        # Parse reasoning effort
        effort = ReasoningEffort(reasoning_effort.lower())
    except ValueError:
        effort = ReasoningEffort.LOW

    try:
        result = await tool.retrieve_formatted(query, effort)
        return result
    finally:
        await tool.close()
