"""
Knowledge Base Tool for MCP integration with Azure AI Search.

This module provides a tool for querying the Azure AI Search Knowledge Base
via MCP (Model Context Protocol) endpoint.
"""

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class KnowledgeBaseTool:
    """Tool for querying MCP Knowledge Base."""

    def __init__(self, mcp_endpoint: str, api_key: str | None = None):
        """
        Initialize the Knowledge Base Tool.

        Args:
            mcp_endpoint: The MCP endpoint URL for the knowledge base
            api_key: Optional API key for authentication
        """
        self.mcp_endpoint = mcp_endpoint
        self.api_key = api_key
        self._session: aiohttp.ClientSession | None = None

    @classmethod
    def create_from_env(cls) -> "KnowledgeBaseTool | None":
        """
        Create a KnowledgeBaseTool from environment variables.

        Environment variables:
            AI_SEARCH_MCP_ENDPOINT: The MCP endpoint URL
            AI_SEARCH_API_KEY: Optional API key

        Returns:
            KnowledgeBaseTool instance or None if not configured
        """
        mcp_endpoint = os.getenv("AI_SEARCH_MCP_ENDPOINT")
        if not mcp_endpoint:
            logger.warning("AI_SEARCH_MCP_ENDPOINT not configured")
            return None

        api_key = os.getenv("AI_SEARCH_API_KEY")
        return cls(mcp_endpoint=mcp_endpoint, api_key=api_key)

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

    async def search(self, query: str, top: int = 5) -> dict[str, Any]:
        """
        Search the knowledge base using MCP.

        Args:
            query: The search query
            top: Maximum number of results to return

        Returns:
            dict containing search results with sources and citations
        """
        session = await self._get_session()

        # MCP request format for knowledge_base_retrieve
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "knowledge_base_retrieve",
                "arguments": {"query": query, "top": top},
            },
        }

        try:
            async with session.post(self.mcp_endpoint, json=mcp_request) as response:
                if response.status == 200:
                    result = await response.json()
                    return self._parse_mcp_response(result)
                else:
                    error_text = await response.text()
                    logger.error(
                        f"MCP request failed: {response.status} - {error_text}"
                    )
                    return {"error": f"Search failed: {response.status}"}

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error during MCP request: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during MCP request: {e}")
            return {"error": str(e)}

    def _parse_mcp_response(self, response: dict) -> dict[str, Any]:
        """
        Parse MCP response into a structured format.

        Args:
            response: Raw MCP response

        Returns:
            Parsed response with sources and citations
        """
        if "error" in response:
            return {"error": response["error"]}

        result = response.get("result", {})
        content = result.get("content", [])

        sources = []
        for i, item in enumerate(content):
            if item.get("type") == "text":
                text = item.get("text", "")
                # Parse source metadata if available
                annotations = item.get("annotations", {})
                source = {
                    "index": i,
                    "content": text,
                    "source": annotations.get("source", f"source_{i}"),
                    "title": annotations.get("title", ""),
                    "url": annotations.get("url", ""),
                }
                sources.append(source)

        return {"sources": sources, "total": len(sources)}

    async def retrieve_documents(self, query: str) -> str:
        """
        Retrieve documents from knowledge base and format for agent use.

        This is the main function to be used as an agent tool.

        Args:
            query: The search query

        Returns:
            Formatted string with search results and citations
        """
        result = await self.search(query)

        if "error" in result:
            return f"検索中にエラーが発生しました: {result['error']}"

        sources = result.get("sources", [])
        if not sources:
            return "関連するドキュメントが見つかりませんでした。"

        # Format results with citations
        formatted = []
        for source in sources:
            citation = f"【{source['index']}†{source.get('source', 'unknown')}】"
            content = source.get("content", "")
            title = source.get("title", "")

            if title:
                formatted.append(f"## {title} {citation}\n{content}")
            else:
                formatted.append(f"{citation}\n{content}")

        return "\n\n---\n\n".join(formatted)


# Tool function for agent integration
async def knowledge_base_retrieve(query: str) -> str:
    """
    Search the product documentation knowledge base.

    This tool retrieves relevant documents from the SharePoint-indexed
    knowledge base to answer questions about products, specifications,
    and technical documentation.

    Args:
        query: The search query for finding relevant documents

    Returns:
        Formatted search results with citations
    """
    tool = KnowledgeBaseTool.create_from_env()
    if not tool:
        return "ナレッジベースが設定されていません。"

    try:
        result = await tool.retrieve_documents(query)
        return result
    finally:
        await tool.close()
