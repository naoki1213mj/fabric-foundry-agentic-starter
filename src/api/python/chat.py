"""
Chat API module for handling chat interactions and responses.

Supports two modes:
- Single Agent Mode (default): Uses a single ChatAgent for all queries
- Multi Agent Mode (MULTI_AGENT_MODE=true): Uses Agent Framework's native multi-agent capabilities
  - Coordinator with agent-as-tool pattern
  - Automatic tool selection and parallel execution
  - Built-in result synthesis
"""

import asyncio
import json
import logging
import os
import re

from agent_framework import ChatAgent, ChatMessage, Role
from agent_framework.azure import AzureAIClient
from agent_framework.exceptions import ServiceResponseException

# Azure Auth
from auth.azure_credential_utils import get_azure_credential_async

# Azure SDK
from azure.ai.agents.models import TruncationObject
from azure.ai.projects.aio import AIProjectClient
from azure.monitor.events.extension import track_event
from azure.monitor.opentelemetry import configure_azure_monitor
from cachetools import TTLCache
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

load_dotenv()

# Constants
HOST_NAME = "Agentic Applications for Unified Data Foundation"
HOST_INSTRUCTIONS = "Answer questions about Sales, Products and Orders data."

# Multi-Agent Configuration
MULTI_AGENT_MODE = os.getenv("MULTI_AGENT_MODE", "false").lower() == "true"

# Agent Names from environment
AGENT_NAME_ORCHESTRATOR = os.getenv("AGENT_NAME_ORCHESTRATOR")
AGENT_NAME_SQL = os.getenv("AGENT_NAME_SQL")
AGENT_NAME_WEB = os.getenv("AGENT_NAME_WEB")
AGENT_NAME_DOC = os.getenv("AGENT_NAME_DOC")
AGENT_NAME_CHAT = os.getenv("AGENT_NAME_CHAT")  # Legacy single-agent mode


router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if the Application Insights Instrumentation Key is set in the environment variables
instrumentation_key = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if instrumentation_key:
    configure_azure_monitor(connection_string=instrumentation_key)
    logging.info(
        "Application Insights configured with the provided Instrumentation Key"
    )
else:
    logging.warning(
        "No Application Insights Instrumentation Key found. Skipping configuration"
    )

# Suppress noisy loggers
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.WARNING
)
logging.getLogger("azure.identity.aio._internal").setLevel(logging.WARNING)
logging.getLogger("azure.monitor.opentelemetry.exporter.export._base").setLevel(
    logging.WARNING
)


class ExpCache(TTLCache):
    """Extended TTLCache that deletes Azure AI agent threads when items expire."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def expire(self, time=None):
        items = super().expire(time)
        for key, thread_conversation_id in items:
            try:
                asyncio.create_task(self._delete_thread_async(thread_conversation_id))
                logger.info("Scheduled thread deletion: %s", thread_conversation_id)
            except Exception as e:
                logger.error(
                    "Failed to schedule thread deletion for key %s: %s", key, e
                )
        return items

    def popitem(self):
        key, thread_conversation_id = super().popitem()
        try:
            asyncio.create_task(self._delete_thread_async(thread_conversation_id))
            logger.info(
                "Scheduled thread deletion (LRU evict): %s", thread_conversation_id
            )
        except Exception as e:
            logger.error(
                "Failed to schedule thread deletion for key %s (LRU evict): %s", key, e
            )
        return key, thread_conversation_id

    async def _delete_thread_async(self, thread_conversation_id: str):
        credential = None
        endpoint = os.getenv("AZURE_AI_AGENT_ENDPOINT")
        if not endpoint:
            logger.warning("AZURE_AI_AGENT_ENDPOINT not configured")
            return
        try:
            if thread_conversation_id:
                credential = await get_azure_credential_async()
                async with AIProjectClient(
                    endpoint=endpoint, credential=credential
                ) as project_client:
                    openai_client = project_client.get_openai_client()
                    await openai_client.conversations.delete(
                        conversation_id=thread_conversation_id
                    )
                    logger.info(
                        "Thread deleted successfully: %s", thread_conversation_id
                    )
        except Exception as e:
            logger.error("Failed to delete thread %s: %s", thread_conversation_id, e)
        finally:
            if credential is not None:
                await credential.close()


def track_event_if_configured(event_name: str, event_data: dict):
    """Track event to Application Insights if configured."""
    instrumentation_key = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if instrumentation_key:
        track_event(event_name, event_data)


# Global thread cache
thread_cache = None


def get_thread_cache():
    """Get or create the global thread cache."""
    global thread_cache
    if thread_cache is None:
        thread_cache = ExpCache(maxsize=1000, ttl=3600.0)
    return thread_cache


async def create_specialist_agent(
    project_client: AIProjectClient,
    agent_type: str,
    model_deployment_name: str,
    tools: list | None = None,
) -> ChatAgent:
    """
    Create a specialist agent instance.

    Args:
        project_client: Azure AI Project client
        agent_type: Type of agent ('sql', 'web', 'doc')
        model_deployment_name: Model deployment name
        tools: Optional list of tools for the agent

    Returns:
        Configured ChatAgent instance
    """
    agent_names = {
        "sql": AGENT_NAME_SQL,
        "web": AGENT_NAME_WEB,
        "doc": AGENT_NAME_DOC,
    }

    agent_name = agent_names.get(agent_type)
    if not agent_name:
        raise ValueError(f"Unknown agent type: {agent_type}")

    chat_client = AzureAIClient(
        project_client=project_client,
        agent_name=agent_name,
        model_deployment_name=model_deployment_name,
        use_latest_version=True,
    )

    descriptions = {
        "sql": "Executes SQL queries and generates Chart.js visualizations",
        "web": "Searches the web for real-time information",
        "doc": "Searches enterprise documents and specifications",
    }

    return ChatAgent(
        name=f"{agent_type.capitalize()}Agent",
        description=descriptions.get(agent_type, ""),
        chat_client=chat_client,
        tools=tools or [],
        tool_choice="auto" if tools else "none",
    )


async def stream_multi_agent_response(conversation_id: str, query: str):
    """
    Stream response using Agent Framework's agent-as-tool pattern.

    This leverages:
    - agent.as_tool() to convert agents into callable tools
    - Automatic tool selection by the coordinator
    - Built-in parallel execution when multiple tools are called
    """
    from history_sql import SqlQueryTool, get_fabric_db_connection

    credential = None
    custom_tool = None
    kb_tool = None

    endpoint = os.getenv("AZURE_AI_AGENT_ENDPOINT")
    if not endpoint:
        raise ValueError("AZURE_AI_AGENT_ENDPOINT not configured")

    try:
        credential = await get_azure_credential_async()

        async with AIProjectClient(
            endpoint=endpoint, credential=credential
        ) as project_client:
            model_deployment_name = os.getenv(
                "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"
            ) or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

            if not model_deployment_name:
                raise ValueError("Model deployment name not configured")

            # Set up SQL tools
            sql_tools = []
            db_connection = await get_fabric_db_connection()
            if db_connection:
                custom_tool = SqlQueryTool.create_with_connection(db_connection)
                sql_tools = [custom_tool.run_sql_query]

            # Create specialist agents
            sql_agent = await create_specialist_agent(
                project_client, "sql", model_deployment_name, sql_tools
            )
            web_agent = await create_specialist_agent(
                project_client, "web", model_deployment_name
            )

            # For doc agent, we'll handle RAG inline
            doc_agent = await create_specialist_agent(
                project_client, "doc", model_deployment_name
            )

            # Convert agents to tools using agent.as_tool()
            # This is the key Agent Framework pattern!
            sql_tool = sql_agent.as_tool(
                name="query_database",
                description="Query the database for sales, orders, products, customers, and business data. Can generate Chart.js visualizations. Input: Natural language query about database information.",
            )

            web_tool = web_agent.as_tool(
                name="search_web",
                description="Search the web for real-time information, news, current events, weather, and external data not in the database. Input: Search query for web information.",
            )

            doc_tool = doc_agent.as_tool(
                name="search_documents",
                description="Search enterprise documents, product specifications, technical documentation, and internal knowledge base. Input: Search query for document information.",
            )

            # Create coordinator agent with specialist agents as tools
            coordinator_client = AzureAIClient(
                project_client=project_client,
                agent_name=AGENT_NAME_ORCHESTRATOR,
                model_deployment_name=model_deployment_name,
                use_latest_version=True,
            )

            async with ChatAgent(
                name="Coordinator",
                description="Intelligent coordinator that routes queries to specialists",
                instructions="""You are an intelligent coordinator that helps users by routing their questions to the right specialist tools.

## Available Tools
- **query_database**: Use for questions about sales, orders, products, customers, or any data analysis
- **search_web**: Use for current events, news, external information, or real-time data
- **search_documents**: Use for product specifications, technical documentation, or enterprise knowledge

## Guidelines
1. Analyze the user's question to determine which tool(s) are needed
2. For complex questions requiring multiple sources, call multiple tools
3. Synthesize the results from all tools into a coherent response
4. Always provide helpful, accurate answers based on the tool results

## Response Format
- Present data clearly with appropriate formatting
- Include Chart.js JSON when visualizations are requested
- Cite sources when using document search results
- Provide actionable insights when analyzing data
""",
                chat_client=coordinator_client,
                tools=[sql_tool, web_tool, doc_tool],
                tool_choice="auto",
            ) as coordinator:
                # Get or create thread
                cache = get_thread_cache()
                thread_conversation_id = cache.get(conversation_id, None)

                if thread_conversation_id:
                    thread = coordinator.get_new_thread(
                        service_thread_id=thread_conversation_id
                    )
                else:
                    openai_client = project_client.get_openai_client()
                    conversation = await openai_client.conversations.create()
                    thread_conversation_id = conversation.id
                    thread = coordinator.get_new_thread(
                        service_thread_id=thread_conversation_id
                    )
                    cache[conversation_id] = thread_conversation_id

                # Stream response from coordinator
                # The coordinator will automatically:
                # 1. Analyze the query
                # 2. Call appropriate tool(s)
                # 3. Synthesize results
                messages = [ChatMessage(role=Role.USER, content=query)]

                async for update in coordinator.run_stream(messages, thread=thread):
                    if update.text:
                        yield update.text

    except ServiceResponseException as e:
        logger.error("Service error in multi-agent: %s", e)
        raise
    except Exception as e:
        logger.error("Error in multi-agent response: %s", e)
        raise
    finally:
        if custom_tool:
            custom_tool.close_connection()
        if kb_tool:
            await kb_tool.close()
        if credential:
            await credential.close()


async def stream_single_agent_response(conversation_id: str, query: str):
    """
    Stream response using single agent mode (legacy behavior).
    """
    from history_sql import SqlQueryTool, get_fabric_db_connection

    credential = None
    custom_tool = None

    endpoint = os.getenv("AZURE_AI_AGENT_ENDPOINT")
    if not endpoint:
        raise ValueError("AZURE_AI_AGENT_ENDPOINT not configured")

    try:
        credential = await get_azure_credential_async()

        async with AIProjectClient(
            endpoint=endpoint, credential=credential
        ) as project_client:
            cache = get_thread_cache()
            thread_conversation_id = cache.get(conversation_id, None)
            truncation_strategy = TruncationObject(
                type="last_messages", last_messages=4
            )

            db_connection = await get_fabric_db_connection()
            if not db_connection:
                logger.error("Failed to establish database connection")
                raise Exception("Database connection failed")

            custom_tool = SqlQueryTool.create_with_connection(db_connection)
            my_tools = [custom_tool.run_sql_query]

            agent_name = AGENT_NAME_CHAT
            logger.info(f"Single agent mode: Using Chat Agent '{agent_name}'")

            model_deployment_name = os.getenv(
                "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"
            ) or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

            if not model_deployment_name:
                raise ValueError("Model deployment name not configured")

            chat_client = AzureAIClient(
                project_client=project_client,
                agent_name=agent_name,
                model_deployment_name=model_deployment_name,
                use_latest_version=True,
            )

            async with ChatAgent(
                chat_client=chat_client,
                tools=my_tools,
                tool_choice="auto",
            ) as chat_agent:
                if thread_conversation_id:
                    thread = chat_agent.get_new_thread(
                        service_thread_id=thread_conversation_id
                    )
                else:
                    openai_client = project_client.get_openai_client()
                    conversation = await openai_client.conversations.create()
                    thread_conversation_id = conversation.id
                    thread = chat_agent.get_new_thread(
                        service_thread_id=thread_conversation_id
                    )
                    cache[conversation_id] = thread_conversation_id

                async for chunk in chat_agent.run_stream(
                    messages=query,
                    thread=thread,
                    truncation_strategy=truncation_strategy,
                ):
                    if chunk is not None and chunk.text:
                        yield chunk.text

    except ServiceResponseException as e:
        logger.error("Service error: %s", e)
        raise
    except Exception as e:
        logger.error("Error in single agent response: %s", e)
        raise
    finally:
        if custom_tool:
            custom_tool.close_connection()
        if credential:
            await credential.close()


async def stream_chat_request(conversation_id: str, query: str):
    """
    Handles streaming chat requests.

    Routes to:
    - Multi-agent mode: Uses agent-as-tool pattern with coordinator
    - Single-agent mode: Direct ChatAgent with SQL tools
    """

    async def generate():
        try:
            assistant_content = ""

            # Choose streaming function based on mode
            if MULTI_AGENT_MODE and AGENT_NAME_ORCHESTRATOR:
                logger.info("Using multi-agent mode with agent-as-tool pattern")
                stream_func = stream_multi_agent_response
            else:
                logger.info("Using single-agent mode")
                stream_func = stream_single_agent_response

            # Stream and accumulate response
            async for chunk in stream_func(conversation_id, query):
                assistant_content += str(chunk)
                response = {
                    "choices": [
                        {
                            "messages": [
                                {
                                    "role": "assistant",
                                    "content": assistant_content,
                                }
                            ]
                        }
                    ]
                }
                yield json.dumps(response, ensure_ascii=False) + "\n\n"

            # Fallback if no response
            if not assistant_content:
                logger.info("No response received")
                response = {
                    "choices": [
                        {
                            "messages": [
                                {
                                    "role": "assistant",
                                    "content": "I cannot answer this question with the current data. Please rephrase or add more details.",
                                }
                            ]
                        }
                    ]
                }
                yield json.dumps(response, ensure_ascii=False) + "\n\n"

        except ServiceResponseException as e:
            error_message = str(e)
            if "Rate limit is exceeded" in error_message:
                match = re.search(r"Try again in (\d+) seconds.", error_message)
                retry_after = match.group(1) if match else "sometime"
                logger.error("Rate limit error: %s", error_message)
                yield (
                    json.dumps(
                        {
                            "error": f"Rate limit is exceeded. Try again in {retry_after} seconds."
                        }
                    )
                    + "\n\n"
                )
            else:
                logger.error("ServiceResponseException: %s", error_message)
                yield (
                    json.dumps({"error": "An error occurred. Please try again later."})
                    + "\n\n"
                )

        except Exception as e:
            logger.error("Unexpected error: %s", e)
            yield (
                json.dumps({"error": "An error occurred while processing the request."})
                + "\n\n"
            )

    return generate()


@router.post("/chat")
async def conversation(request: Request):
    """Handle chat requests - streaming text or chart generation based on query keywords."""
    try:
        request_json = await request.json()
        conversation_id = request_json.get("conversation_id")
        query = request_json.get("query")

        if not query:
            return JSONResponse(content={"error": "Query is required"}, status_code=400)

        if not conversation_id:
            return JSONResponse(
                content={"error": "Conversation ID is required"}, status_code=400
            )

        result = await stream_chat_request(conversation_id, query)
        track_event_if_configured(
            "ChatStreamSuccess", {"conversation_id": conversation_id, "query": query}
        )
        return StreamingResponse(result, media_type="application/json-lines")

    except Exception as ex:
        logger.exception("Error in conversation endpoint: %s", str(ex))
        span = trace.get_current_span()
        if span is not None:
            span.record_exception(ex)
            span.set_status(Status(StatusCode.ERROR, str(ex)))
        return JSONResponse(
            content={
                "error": "An internal error occurred while processing the conversation."
            },
            status_code=500,
        )
