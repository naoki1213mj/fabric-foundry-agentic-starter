"""
Web Agent Handler

Handles web search queries using Bing Grounding via Azure AI Foundry.
Uses the Foundry Agent Service to perform real-time web searches.
"""

import json
import logging
import os
from typing import List, Optional

from azure.ai.agents.models import BingGroundingTool
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)


class WebAgentHandler:
    """Handler for Web Agent tool execution using Bing Grounding via Foundry."""

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
        self.model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")
        self._project_client = None
        self._credential = None

    def _get_project_client(self):
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
        Search the web using Bing Grounding via Foundry Agent Service.

        Args:
            query: The search query to send to Bing

        Returns:
            JSON string containing search results with citations
        """
        # Check if Foundry Bing Grounding is configured
        if not self.foundry_endpoint or not self.bing_connection_id:
            logger.warning(
                "Foundry Bing Grounding not configured (missing AZURE_AI_PROJECT_ENDPOINT or BING_PROJECT_CONNECTION_ID)"
            )
            return json.dumps(
                {
                    "answer": f"[Web検索が設定されていません] '{query}'についての情報は、私の学習データに基づいて回答します。\n\n"
                    f"注: 以下は私の知識（2024年までの情報）に基づく回答です。最新のトレンド情報については参考程度にお考えください。",
                    "citations": [],
                    "fallback": True,
                    "note": "Foundry Bing Grounding is not configured. Please use LLM knowledge to answer.",
                },
                ensure_ascii=False,
            )

        try:
            project_client = self._get_project_client()
            if not project_client:
                raise ValueError("Failed to create AIProjectClient")

            logger.info(
                f"Performing Bing Grounding search via Foundry: {query[:100]}..."
            )

            # Initialize the Bing Grounding tool
            bing_tool = BingGroundingTool(connection_id=self.bing_connection_id)

            # Create a temporary agent with Bing Grounding tool
            agents_client = project_client.agents

            agent = agents_client.create_agent(
                model=self.model_deployment,
                name="web-search-agent",
                instructions=f"You are a web search assistant. Search the web for: {query}. Return the search results with relevant information and citations. Focus on current trends and recent data.",
                tools=bing_tool.definitions,
            )
            logger.info(f"Created Bing search agent: {agent.id}")

            try:
                # Create a thread and run the search
                thread = agents_client.threads.create()

                # Add a message to the thread
                agents_client.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=f"Search the web for: {query}",
                )

                # Run the agent and wait for completion
                run = agents_client.runs.create_and_process(
                    thread_id=thread.id, agent_id=agent.id
                )

                # Get the response messages
                messages = agents_client.messages.list(thread_id=thread.id)

                # Extract the assistant's response
                answer_text = ""
                citations = []

                for msg in messages:
                    if msg.role == "assistant":
                        for content_item in msg.content:
                            if hasattr(content_item, "text"):
                                answer_text = content_item.text.value
                                # Extract annotations (citations)
                                if hasattr(content_item.text, "annotations"):
                                    for annotation in content_item.text.annotations:
                                        if hasattr(annotation, "url_citation"):
                                            citations.append(
                                                {
                                                    "url": annotation.url_citation.url,
                                                    "title": annotation.url_citation.title
                                                    if hasattr(
                                                        annotation.url_citation, "title"
                                                    )
                                                    else "",
                                                }
                                            )
                                break
                        break

                # Clean up thread
                agents_client.threads.delete(thread_id=thread.id)

            finally:
                # Clean up the agent
                agents_client.delete_agent(agent_id=agent.id)
                logger.info(f"Deleted Bing search agent: {agent.id}")

            if answer_text:
                logger.info(
                    f"Bing Grounding completed. Found {len(citations)} citations."
                )
                return json.dumps(
                    {
                        "answer": answer_text,
                        "citations": citations,
                        "source": "bing_grounding_foundry",
                    },
                    ensure_ascii=False,
                )
            else:
                logger.warning("Bing Grounding returned empty response")
                return json.dumps(
                    {
                        "answer": f"[Web検索結果が空でした] '{query}'についての情報は、私の学習データに基づいて回答します。",
                        "citations": [],
                        "fallback": True,
                        "note": "Bing search returned empty results. Please use LLM knowledge to answer.",
                    },
                    ensure_ascii=False,
                )

        except Exception as e:
            logger.error(f"Bing Grounding error: {e}", exc_info=True)
            return json.dumps(
                {
                    "answer": f"[Web検索でエラーが発生しました] '{query}'についての情報は、私の学習データに基づいて回答します。\n\nエラー詳細: {str(e)[:200]}",
                    "citations": [],
                    "fallback": True,
                    "note": f"Bing Grounding failed: {str(e)}. Please use LLM knowledge to answer.",
                },
                ensure_ascii=False,
            )

    def get_tools(self) -> List[callable]:
        """Return the list of tools for the Web Agent."""
        return [self.bing_grounding]
