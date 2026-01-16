"""
Chat API module for handling chat interactions and responses.

Supports multi-agent orchestration:
- SqlAgent: Database queries using Fabric SQL Database
- WebAgent: Web search using Bing Grounding (if configured)
- OrchestratorAgent: Routes queries to appropriate specialist agents
"""

import asyncio
import json
import logging
import os
import random
import re

from agent_framework import ChatAgent
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
from fastapi import APIRouter, HTTPException, Request, status
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
AGENT_NAME_CHAT = os.getenv("AGENT_NAME_CHAT")  # Legacy single-agent mode

# Handoff tag patterns for multi-agent routing (XML format)
HANDOFF_PATTERNS_XML = {
    "sql": re.compile(r"<handoff_to_sql_agent>(.*?)</handoff_to_sql_agent>", re.DOTALL),
    "web": re.compile(r"<handoff_to_web_agent>(.*?)</handoff_to_web_agent>", re.DOTALL),
}

# Handoff patterns for JSON format
HANDOFF_PATTERNS_JSON = {
    "sql": re.compile(r'"tool"\s*:\s*"handoff_to_sql_agent"', re.IGNORECASE),
    "web": re.compile(r'"tool"\s*:\s*"handoff_to_web_agent"', re.IGNORECASE),
}


def parse_handoff(response_text: str) -> tuple[str | None, dict | None]:
    """
    Parse handoff from orchestrator response (supports both XML and JSON formats).

    Returns:
        tuple: (agent_type, handoff_params) or (None, None) if no handoff detected
    """
    # Try XML format first
    for agent_type, pattern in HANDOFF_PATTERNS_XML.items():
        match = pattern.search(response_text)
        if match:
            try:
                params = json.loads(match.group(1).strip())
                return agent_type, params
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse XML handoff params for {agent_type}")
                return agent_type, {"query": match.group(1).strip()}

    # Try JSON format
    try:
        # Try to parse as JSON object
        data = json.loads(response_text.strip())
        if isinstance(data, dict):
            tool = data.get("tool", "").lower()
            if "sql" in tool:
                return "sql", data
            elif "web" in tool:
                return "web", data
    except json.JSONDecodeError:
        # Check for JSON pattern in text
        for agent_type, pattern in HANDOFF_PATTERNS_JSON.items():
            if pattern.search(response_text):
                # Extract JSON from response
                try:
                    # Find JSON object in response
                    json_match = re.search(r'\{[^{}]*"tool"[^{}]*\}', response_text)
                    if json_match:
                        data = json.loads(json_match.group())
                        return agent_type, data
                except (json.JSONDecodeError, AttributeError):
                    return agent_type, {"query": response_text}

    return None, None


def is_handoff_response(response_text: str) -> bool:
    """Check if response contains handoff indicators (XML or JSON format)."""
    # Check XML patterns
    if any(pattern.search(response_text) for pattern in HANDOFF_PATTERNS_XML.values()):
        return True
    # Check JSON patterns
    if any(pattern.search(response_text) for pattern in HANDOFF_PATTERNS_JSON.values()):
        return True
    # Check for JSON with tool field
    try:
        data = json.loads(response_text.strip())
        if isinstance(data, dict) and "tool" in data:
            tool = data.get("tool", "").lower()
            if "handoff" in tool or "agent" in tool:
                return True
    except (json.JSONDecodeError, TypeError):
        pass
    return False


router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if the Application Insights Instrumentation Key is set in the environment variables
instrumentation_key = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if instrumentation_key:
    # Configure Application Insights if the Instrumentation Key is found
    configure_azure_monitor(connection_string=instrumentation_key)
    logging.info(
        "Application Insights configured with the provided Instrumentation Key"
    )
else:
    # Log a warning if the Instrumentation Key is not found
    logging.warning(
        "No Application Insights Instrumentation Key found. Skipping configuration"
    )

# Configure logging
logging.basicConfig(level=logging.INFO)

# Suppress INFO logs from 'azure.core.pipeline.policies.http_logging_policy'
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.WARNING
)
logging.getLogger("azure.identity.aio._internal").setLevel(logging.WARNING)

# Suppress info logs from OpenTelemetry exporter
logging.getLogger("azure.monitor.opentelemetry.exporter.export._base").setLevel(
    logging.WARNING
)


class ExpCache(TTLCache):
    """Extended TTLCache that deletes Azure AI agent threads when items expire."""

    def __init__(self, *args, **kwargs):
        """Initialize cache without creating persistent client connections."""
        super().__init__(*args, **kwargs)

    def expire(self, time=None):
        """Remove expired items and delete associated Azure AI threads."""
        items = super().expire(time)
        for key, thread_conversation_id in items:
            try:
                # Create task for async deletion with proper session management
                asyncio.create_task(self._delete_thread_async(thread_conversation_id))
                logger.info("Scheduled thread deletion: %s", thread_conversation_id)
            except Exception as e:
                logger.error(
                    "Failed to schedule thread deletion for key %s: %s", key, e
                )
        return items

    def popitem(self):
        """Remove item using LRU eviction and delete associated Azure AI thread."""
        key, thread_conversation_id = super().popitem()
        try:
            # Create task for async deletion with proper session management
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
        """Asynchronously delete a thread using a properly managed Azure AI Project Client."""
        credential = None
        try:
            if thread_conversation_id:
                # Get credential and use async context managers to ensure proper cleanup
                credential = await get_azure_credential_async()
                async with AIProjectClient(
                    endpoint=os.getenv("AZURE_AI_AGENT_ENDPOINT"), credential=credential
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
            # Close credential to prevent unclosed client session warnings
            if credential is not None:
                await credential.close()


def track_event_if_configured(event_name: str, event_data: dict):
    """Track event to Application Insights if configured."""
    instrumentation_key = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if instrumentation_key:
        track_event(event_name, event_data)
    else:
        logging.warning(
            "Skipping track_event for %s as Application Insights is not configured",
            event_name,
        )


async def call_specialist_agent(
    agent_type: str,
    query: str,
    conversation_id: str,
    handoff_params: dict | None = None,
):
    """
    Call a specialist agent (SQL or Web) after orchestrator handoff.

    Args:
        agent_type: 'sql' or 'web'
        query: The original user query or extracted query from handoff
        conversation_id: Conversation ID for thread management
        handoff_params: Parameters extracted from handoff tag

    Yields:
        Response chunks from the specialist agent
    """
    from history_sql import SqlQueryTool, get_fabric_db_connection

    # Determine which agent to use
    if agent_type == "sql":
        agent_name = AGENT_NAME_SQL
    elif agent_type == "web":
        agent_name = AGENT_NAME_WEB
    else:
        logger.error(f"Unknown agent type: {agent_type}")
        yield f"Unknown agent type: {agent_type}"
        return

    if not agent_name:
        logger.error(f"Agent name not configured for type: {agent_type}")
        yield f"Agent {agent_type} is not configured"
        return

    logger.info(f"Handoff to {agent_type} agent: {agent_name}")
    logger.info(f"Handoff params: {handoff_params}")

    # Use query from handoff params if available
    actual_query = handoff_params.get("query", query) if handoff_params else query

    credential = None
    custom_tool = None

    try:
        credential = await get_azure_credential_async()

        async with AIProjectClient(
            endpoint=os.getenv("AZURE_AI_AGENT_ENDPOINT"), credential=credential
        ) as project_client:
            # Set up tools for SQL agent
            my_tools = []
            if agent_type == "sql":
                db_connection = await get_fabric_db_connection()
                if db_connection:
                    custom_tool = SqlQueryTool.create_with_connection(db_connection)
                    my_tools = [custom_tool.run_sql_query]

            model_deployment_name = os.getenv(
                "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"
            ) or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

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
                # Create new thread for specialist agent
                openai_client = project_client.get_openai_client()
                conversation = await openai_client.conversations.create()
                thread = chat_agent.get_new_thread(service_thread_id=conversation.id)

                truncation_strategy = TruncationObject(type="auto")

                async for chunk in chat_agent.run_stream(
                    messages=actual_query,
                    thread=thread,
                    truncation_strategy=truncation_strategy,
                ):
                    if chunk is not None and chunk.text != "":
                        yield chunk.text

    except Exception as e:
        logger.error(f"Error calling specialist agent {agent_type}: {e}")
        yield f"Error processing request with {agent_type} agent"
    finally:
        if custom_tool:
            custom_tool.close_connection()
        if credential:
            await credential.close()


# Global thread cache
thread_cache = None


def get_thread_cache():
    """Get or create the global thread cache."""
    global thread_cache
    if thread_cache is None:
        thread_cache = ExpCache(maxsize=1000, ttl=3600.0)
    return thread_cache


async def stream_openai_text(conversation_id: str, query: str) -> StreamingResponse:
    """
    Get a streaming text response from OpenAI.

    Supports two modes:
    - Single Agent Mode (default): Uses AGENT_NAME_CHAT for SQL queries
    - Multi Agent Mode (MULTI_AGENT_MODE=true): Routes via OrchestratorAgent to SqlAgent/WebAgent
    """
    thread = None
    complete_response = ""
    credential = None
    custom_tool = None

    try:
        if not query:
            query = "Please provide a query."

        credential = await get_azure_credential_async()

        async with AIProjectClient(
            endpoint=os.getenv("AZURE_AI_AGENT_ENDPOINT"), credential=credential
        ) as project_client:
            cache = get_thread_cache()
            thread_conversation_id = cache.get(conversation_id, None)
            truncation_strategy = TruncationObject(
                type="last_messages", last_messages=4
            )

            from history_sql import SqlQueryTool, get_fabric_db_connection

            db_connection = await get_fabric_db_connection()
            if not db_connection:
                logger.error("Failed to establish database connection")
                raise Exception("Database connection failed")

            # Create pickle-safe SqlQueryTool using connection cache
            # The tool manages its own connection lifecycle
            custom_tool = SqlQueryTool.create_with_connection(db_connection)
            my_tools = [custom_tool.run_sql_query]

            # Determine which agent to use based on mode
            if MULTI_AGENT_MODE and AGENT_NAME_ORCHESTRATOR:
                # Multi-agent mode: Use Orchestrator for intelligent routing
                # Orchestrator will handoff to SqlAgent or WebAgent as needed
                agent_name = AGENT_NAME_ORCHESTRATOR
                logger.info(
                    f"Multi-agent mode: Using Orchestrator Agent '{agent_name}'"
                )
                logger.info(
                    f"  Available agents: SQL='{AGENT_NAME_SQL}', Web='{AGENT_NAME_WEB}'"
                )
            elif MULTI_AGENT_MODE and AGENT_NAME_SQL:
                # Fallback to SQL Agent if Orchestrator not configured
                agent_name = AGENT_NAME_SQL
                logger.info(
                    f"Multi-agent mode (no orchestrator): Using SQL Agent '{agent_name}'"
                )
            else:
                # Single agent mode: Use legacy AGENT_NAME_CHAT
                agent_name = AGENT_NAME_CHAT
                logger.info(f"Single agent mode: Using Chat Agent '{agent_name}'")

            # Create chat client with existing agent
            # model_deployment_name is required in agent-framework 1.0.0b260114+
            model_deployment_name = os.getenv(
                "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"
            ) or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
            if not model_deployment_name:
                raise ValueError(
                    "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME or AZURE_AI_MODEL_DEPLOYMENT_NAME environment variable is required"
                )

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
                # Note: 'store' parameter removed - not supported in agent-framework 1.0.0b260114
            ) as chat_agent:
                if thread_conversation_id:
                    thread = chat_agent.get_new_thread(
                        service_thread_id=thread_conversation_id
                    )
                    assert thread.is_initialized
                else:
                    # Create a conversation using openAI client
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
                    if chunk is not None and chunk.text != "":
                        complete_response += chunk.text
                        yield chunk.text

    except ServiceResponseException as e:
        complete_response = str(e)
        if "Rate limit is exceeded" in str(e):
            logger.error("Rate limit error: %s", e)
            raise ServiceResponseException(f"Rate limit is exceeded. {str(e)}") from e
        else:
            logger.error("RuntimeError: %s", e)
            raise ServiceResponseException(
                f"An unexpected runtime error occurred: {str(e)}"
            ) from e

    except Exception as e:
        complete_response = str(e)
        logger.error("Error in stream_openai_text: %s", e)
        cache = get_thread_cache()
        thread_conversation_id = cache.pop(conversation_id, None)
        if thread_conversation_id is not None:
            corrupt_key = f"{conversation_id}_corrupt_{random.randint(1000, 9999)}"
            cache[corrupt_key] = thread_conversation_id
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error streaming OpenAI text",
        ) from e

    finally:
        if custom_tool:
            custom_tool.close_connection()
        if credential is not None:
            await credential.close()
        # Provide a fallback response when no data is received from OpenAI.
        if complete_response == "":
            logger.info("No response received from OpenAI.")
            yield "I cannot answer this question with the current data. Please rephrase or add more details."


async def stream_chat_request(conversation_id, query):
    """
    Handles streaming chat requests with multi-agent handoff support.

    In multi-agent mode:
    1. Orchestrator receives the query first
    2. If orchestrator returns handoff tags, route to specialist agent
    3. Stream specialist agent's response to the client
    """

    async def generate():
        try:
            assistant_content = ""
            orchestrator_response = ""
            handoff_detected = False

            # First, collect response from orchestrator (or single agent)
            async for chunk in stream_openai_text(conversation_id, query):
                if isinstance(chunk, dict):
                    chunk = json.dumps(chunk)
                orchestrator_response += str(chunk)

                # Check if this is a handoff response (in multi-agent mode)
                if MULTI_AGENT_MODE and is_handoff_response(orchestrator_response):
                    handoff_detected = True
                    # Continue collecting until we have the complete handoff tag
                    continue

            # If handoff detected, route to specialist agent
            if handoff_detected and MULTI_AGENT_MODE:
                agent_type, handoff_params = parse_handoff(orchestrator_response)
                if agent_type:
                    logger.info(f"Processing handoff to {agent_type} agent")
                    logger.info(f"Handoff params: {handoff_params}")

                    # Stream response from specialist agent
                    async for specialist_chunk in call_specialist_agent(
                        agent_type=agent_type,
                        query=query,
                        conversation_id=conversation_id,
                        handoff_params=handoff_params,
                    ):
                        assistant_content += str(specialist_chunk)
                        if assistant_content:
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
                else:
                    # Handoff tag detected but couldn't parse - return original response
                    logger.warning("Handoff detected but couldn't parse agent type")
                    assistant_content = orchestrator_response
                    response = {
                        "choices": [
                            {
                                "messages": [
                                    {"role": "assistant", "content": assistant_content}
                                ]
                            }
                        ]
                    }
                    yield json.dumps(response, ensure_ascii=False) + "\n\n"
            else:
                # No handoff - stream the orchestrator/single agent response directly
                assistant_content = orchestrator_response
                if assistant_content:
                    response = {
                        "choices": [
                            {
                                "messages": [
                                    {"role": "assistant", "content": assistant_content}
                                ]
                            }
                        ]
                    }
                    yield json.dumps(response, ensure_ascii=False) + "\n\n"

        except ServiceResponseException as e:
            error_message = str(e)
            retry_after = "sometime"
            if "Rate limit is exceeded" in error_message:
                match = re.search(r"Try again in (\d+) seconds.", error_message)
                if match:
                    retry_after = f"{match.group(1)} seconds"
                logger.error("Rate limit error: %s", error_message)
                yield (
                    json.dumps(
                        {
                            "error": f"Rate limit is exceeded. Try again in {retry_after}."
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
            error_response = {
                "error": "An error occurred while processing the request."
            }
            yield json.dumps(error_response) + "\n\n"

    return generate()


@router.post("/chat")
async def conversation(request: Request):
    """Handle chat requests - streaming text or chart generation based on query keywords."""
    try:
        # Get the request JSON with optimized payload (only conversation_id and query)
        request_json = await request.json()
        conversation_id = request_json.get("conversation_id")
        query = request_json.get("query")

        # Validate required parameters
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
