"""
Knowledge Base Tool for Azure AI Search integration.

This module provides a tool for querying the Azure AI Search index
to retrieve product documentation and specifications.
"""

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class KnowledgeBaseTool:
    """Tool for querying Azure AI Search Knowledge Base."""

    def __init__(
        self,
        search_endpoint: str,
        index_name: str,
        api_key: str,
    ):
        """
        Initialize the Knowledge Base Tool.

        Args:
            search_endpoint: The Azure AI Search endpoint URL
            index_name: The name of the search index
            api_key: API key for authentication
        """
        self.search_endpoint = search_endpoint.rstrip("/")
        self.index_name = index_name
        self.api_key = api_key
        self._session: aiohttp.ClientSession | None = None

    @classmethod
    def create_from_env(cls) -> "KnowledgeBaseTool | None":
        """
        Create a KnowledgeBaseTool from environment variables.

        Environment variables:
            AI_SEARCH_ENDPOINT: The Azure AI Search endpoint URL
            AI_SEARCH_INDEX_NAME: The name of the search index
            AI_SEARCH_API_KEY: API key for authentication

        Returns:
            KnowledgeBaseTool instance or None if not configured
        """
        search_endpoint = os.getenv("AI_SEARCH_ENDPOINT")
        index_name = os.getenv("AI_SEARCH_INDEX_NAME")
        api_key = os.getenv("AI_SEARCH_API_KEY")

        if not search_endpoint:
            logger.warning("AI_SEARCH_ENDPOINT not configured")
            return None
        if not index_name:
            logger.warning("AI_SEARCH_INDEX_NAME not configured")
            return None
        if not api_key:
            logger.warning("AI_SEARCH_API_KEY not configured")
            return None

        logger.info(f"KnowledgeBaseTool configured: endpoint={search_endpoint}, index={index_name}")
        return cls(search_endpoint=search_endpoint, index_name=index_name, api_key=api_key)

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
        Search the knowledge base using Azure AI Search.

        Args:
            query: The search query
            top: Maximum number of results to return

        Returns:
            dict containing search results with sources and citations
        """
        session = await self._get_session()

        # Azure AI Search request format
        search_url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search?api-version=2025-11-01-preview"
        search_request = {
            "search": query,
            "top": top,
            "select": "snippet,doc_url,uid",
        }

        try:
            logger.info(f"Searching index {self.index_name} for: {query}")
            async with session.post(search_url, json=search_request) as response:
                if response.status == 200:
                    result = await response.json()
                    return self._parse_search_response(result)
                else:
                    error_text = await response.text()
                    logger.error(f"Search request failed: {response.status} - {error_text}")
                    return {"error": f"Search failed: {response.status}"}

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error during search request: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during search request: {e}")
            return {"error": str(e)}

    def _parse_search_response(self, response: dict) -> dict[str, Any]:
        """
        Parse Azure AI Search response into a structured format.

        Args:
            response: Raw search response

        Returns:
            Parsed response with sources and citations
        """
        if "error" in response:
            return {"error": response["error"]}

        documents = response.get("value", [])
        logger.info(f"Found {len(documents)} documents")

        sources = []
        for i, doc in enumerate(documents):
            snippet = doc.get("snippet", "")
            doc_url = doc.get("doc_url", "")

            # Extract title from doc_url or snippet
            title = ""
            if doc_url:
                # Extract filename from URL path
                parts = doc_url.split("/")
                if parts:
                    title = parts[-1].replace(".pdf", "").replace("_", " ")

            source = {
                "index": i + 1,
                "content": snippet,
                "source": doc_url,
                "title": title,
                "url": doc_url,
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
