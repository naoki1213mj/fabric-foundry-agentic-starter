"""
Web Agent Handler

Handles web search queries using Bing Grounding.
Provides the bing_grounding tool implementation.
"""

import json
import logging
import os
from typing import List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class WebAgentHandler:
    """Handler for Web Agent tool execution using Bing Grounding."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Web Agent Handler.

        Args:
            api_key: Bing Search API key (optional, uses env var if not provided)
        """
        self.api_key = api_key or os.getenv("BING_SEARCH_API_KEY")
        self.endpoint = os.getenv(
            "BING_SEARCH_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search"
        )

    async def bing_grounding(self, query: str) -> str:
        """
        Search the web using Bing to find current information.

        Args:
            query: The search query to send to Bing

        Returns:
            JSON string containing search results with citations
        """
        try:
            if not self.api_key:
                # Fallback: Return a message indicating Bing is not configured
                logger.warning("Bing Search API key not configured")
                return json.dumps(
                    {
                        "answer": f"Web search for '{query}' is not available. Bing Search API is not configured.",
                        "citations": [],
                    }
                )

            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Accept": "application/json",
            }

            params = {
                "q": query,
                "count": 5,
                "mkt": "ja-JP",  # Japanese market
                "safeSearch": "Strict",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.endpoint, headers=headers, params=params
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"Bing Search API error: {response.status} - {error_text}"
                        )
                        return json.dumps(
                            {
                                "answer": f"Web search failed with status {response.status}",
                                "citations": [],
                            }
                        )

                    data = await response.json()

            # Extract web pages
            web_pages = data.get("webPages", {}).get("value", [])

            # Format results
            citations = []
            snippets = []

            for page in web_pages[:5]:
                citations.append(
                    {"url": page.get("url", ""), "title": page.get("name", "")}
                )
                snippets.append(f"- {page.get('name', '')}: {page.get('snippet', '')}")

            answer = f"Search results for '{query}':\n\n" + "\n".join(snippets)

            logger.info(f"Bing search completed. Results: {len(web_pages)}")
            return json.dumps(
                {"answer": answer, "citations": citations}, ensure_ascii=False
            )

        except Exception as e:
            logger.error(f"Bing search error: {e}")
            return json.dumps(
                {"answer": f"Web search failed: {str(e)}", "citations": []}
            )

    def get_tools(self) -> List[callable]:
        """Return the list of tools for the Web Agent."""
        return [self.bing_grounding]
