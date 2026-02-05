"""
Chat API module for handling chat interactions and responses.

Supports multiple agent modes (AGENT_MODE environment variable):

1. sql_only: Fastest - single agent with SQL tool only
   - Best for: Simple SQL queries like "売上TOP3"

2. multi_tool (DEFAULT, RECOMMENDED): Single agent with all tools
   - Best for: Most queries - LLM decides which tools to use
   - Handles complex queries by calling multiple tools sequentially
   - Example: "売上データと製品仕様を比較" → SQL + Doc tools

3. handoff: Multi-agent with HandoffBuilder
   - Best for: Expert delegation pattern
   - Triage → Specialist → Final response (no integration)
   - Note: Does NOT integrate results from multiple specialists

4. magentic: Multi-agent with MagenticBuilder (legacy, slowest)
   - Best for: Complex planning with result integration
   - Manager plans → Specialists execute → Manager integrates

Architecture Decision:
- For result integration from multiple sources → Use multi_tool (single agent calls multiple tools)
- For expert delegation → Use handoff
- For complex planning → Use magentic (slow but powerful)
"""

import asyncio
import json
import logging
import os
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Annotated

from agent_framework import (  # NOTE: HostedWebSearchTool requires OpenAI's web_search_preview tool type; which is not available in Azure OpenAI. Keeping import commented for future use.; HostedWebSearchTool,
    AgentRunUpdateEvent,
    ChatAgent,
    GroupChatRequestSentEvent,
    HandoffAgentUserRequest,
    HandoffBuilder,
    MagenticBuilder,
    MagenticOrchestratorEvent,
    RequestInfoEvent,
    WorkflowOutputEvent,
    WorkflowStatusEvent,
    tool,
)

# AzureOpenAIResponsesClient: Responses API v1 client with base_url support
# - Works natively with APIM Foundry API (/openai/v1/ endpoint format)
# - No api-version required (uses 'preview' or 'latest')
# - Supports Thread management for server-side conversation context
# - Supports Hosted tools (MCP, CodeInterpreter, WebSearch, FileSearch)
from agent_framework.azure import AzureOpenAIChatClient, AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential
from azure.monitor.events.extension import track_event
from azure.monitor.opentelemetry import configure_azure_monitor
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

# Agentic Retrieval with Foundry IQ
from agentic_retrieval_tool import AgenticRetrievalTool, ReasoningEffort

# Local imports - tool handlers
from agents.web_agent import WebAgentHandler
from auth.auth_utils import get_authenticated_user_details

# Use Fabric SQL history instead of CosmosDB for multi-turn conversation support
from history_sql import get_conversation_messages
from knowledge_base_tool import KnowledgeBaseTool

# MCP client for business analytics tools
from mcp_client import get_mcp_tools

# Import prompts from separate module for better maintainability
from prompts import (
    DOC_AGENT_DESCRIPTION,
    DOC_AGENT_PROMPT,
    MANAGER_AGENT_DESCRIPTION,
    MANAGER_AGENT_PROMPT,
    SQL_AGENT_DESCRIPTION,
    SQL_AGENT_PROMPT,
    SQL_AGENT_PROMPT_MINIMAL,
    TRIAGE_AGENT_DESCRIPTION,
    TRIAGE_AGENT_PROMPT,
    UNIFIED_AGENT_PROMPT,
    WEB_AGENT_DESCRIPTION,
    WEB_AGENT_PROMPT,
)

load_dotenv()

# Multi-Agent Configuration
MULTI_AGENT_MODE = os.getenv("MULTI_AGENT_MODE", "false").lower() == "true"

# APIM Gateway Configuration
APIM_GATEWAY_URL = os.getenv("APIM_GATEWAY_URL")
USE_APIM_GATEWAY = bool(APIM_GATEWAY_URL)

# Foundry API (Responses API v1) Configuration
# Format: https://<apim>.azure-api.net/foundry-openai/openai/v1/
# Used by AzureOpenAIResponsesClient for native APIM Foundry API integration
# NOTE: APIM policy strips api-version query param (Responses API v1 doesn't accept it)
AZURE_OPENAI_BASE_URL = os.getenv("AZURE_OPENAI_BASE_URL")
USE_RESPONSES_CLIENT = bool(AZURE_OPENAI_BASE_URL)  # Re-enabled with APIM policy fix

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize tool handlers (singletons)
_web_agent_handler: WebAgentHandler | None = None
_knowledge_base_tool: KnowledgeBaseTool | None = None
_agentic_retrieval_tool: AgenticRetrievalTool | None = None

# Global storage for web citations (per-request, for demo purposes)
_current_web_citations: list = []

# Context variables for reasoning effort and model parameters (thread-safe, per-request scoped)
_reasoning_effort_var: ContextVar[str] = ContextVar("reasoning_effort", default="low")
_model_var: ContextVar[str] = ContextVar("model", default="gpt-5")
_model_reasoning_effort_var: ContextVar[str] = ContextVar(
    "model_reasoning_effort", default="medium"
)
_reasoning_summary_var: ContextVar[str] = ContextVar("reasoning_summary", default="auto")
_temperature_var: ContextVar[float] = ContextVar("temperature", default=0.7)


def get_web_agent_handler() -> WebAgentHandler:
    """Get or create WebAgentHandler singleton."""
    global _web_agent_handler
    if _web_agent_handler is None:
        _web_agent_handler = WebAgentHandler()
    return _web_agent_handler


def get_knowledge_base_tool() -> KnowledgeBaseTool | None:
    """Get or create KnowledgeBaseTool singleton."""
    global _knowledge_base_tool
    if _knowledge_base_tool is None:
        _knowledge_base_tool = KnowledgeBaseTool.create_from_env()
    return _knowledge_base_tool


def get_agentic_retrieval_tool() -> AgenticRetrievalTool | None:
    """Get or create AgenticRetrievalTool singleton."""
    global _agentic_retrieval_tool
    if _agentic_retrieval_tool is None:
        _agentic_retrieval_tool = AgenticRetrievalTool.create_from_env()
    return _agentic_retrieval_tool


def set_reasoning_effort(effort: str):
    """Set the reasoning effort for the current request (thread-safe via ContextVar)."""
    _reasoning_effort_var.set(effort)


def get_reasoning_effort() -> str:
    """Get the current reasoning effort setting (thread-safe via ContextVar)."""
    return _reasoning_effort_var.get()


def set_model_params(model: str, reasoning_effort: str, reasoning_summary: str, temperature: float):
    """Set model parameters for the current request (thread-safe via ContextVar)."""
    _model_var.set(model)
    _model_reasoning_effort_var.set(reasoning_effort)
    _reasoning_summary_var.set(reasoning_summary)
    _temperature_var.set(temperature)


def get_model_params() -> dict:
    """Get the current model parameters (thread-safe via ContextVar)."""
    return {
        "model": _model_var.get(),
        "model_reasoning_effort": _model_reasoning_effort_var.get(),
        "reasoning_summary": _reasoning_summary_var.get(),
        "temperature": _temperature_var.get(),
    }


# ============================================================================
# Tool Event Streaming
# Send real-time tool status updates to the frontend
# ============================================================================


def create_tool_event(tool_name: str, status: str, message: str | None = None) -> str:
    """
    Create a JSON-formatted tool event for streaming to frontend.

    Args:
        tool_name: Name of the tool (e.g., "run_sql_query", "search_documents")
        status: "started", "completed", or "error"
        message: Optional message for additional context

    Returns:
        JSON string with tool event data, prefixed with special marker
    """
    event = {
        "type": "tool_event",
        "tool": tool_name,
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if message:
        event["message"] = message
    # Use special prefix to distinguish from regular text chunks
    return f"__TOOL_EVENT__{json.dumps(event, ensure_ascii=False)}__END_TOOL_EVENT__"


# Thread-safe queue for tool events using asyncio.Queue
# Each request gets its own queue via ContextVar
_tool_event_queue: ContextVar[asyncio.Queue | None] = ContextVar("tool_event_queue", default=None)


def get_tool_event_queue() -> asyncio.Queue | None:
    """Get the current tool event queue."""
    return _tool_event_queue.get()


def set_tool_event_queue(queue: asyncio.Queue | None):
    """Set the tool event queue for the current request."""
    _tool_event_queue.set(queue)


async def emit_tool_event(tool_name: str, status: str, message: str | None = None):
    """Emit a tool event to the current request's queue (non-blocking)."""
    queue = get_tool_event_queue()
    if queue:
        event = create_tool_event(tool_name, status, message)
        try:
            queue.put_nowait(event)  # Non-blocking put
            logger.debug(f"Tool event emitted: {tool_name} - {status}")
        except asyncio.QueueFull:
            logger.warning(f"Tool event queue full, dropping event: {tool_name} - {status}")


async def drain_tool_events(queue: asyncio.Queue) -> list:
    """Drain all pending tool events from the queue (non-blocking)."""
    events = []
    while True:
        try:
            event = queue.get_nowait()
            events.append(event)
        except asyncio.QueueEmpty:
            break
    return events


# Keepalive interval for long-running requests (prevent 230s App Service timeout)
KEEPALIVE_INTERVAL_SECONDS = 15
KEEPALIVE_MARKER = "__KEEPALIVE__"


async def stream_with_tool_events(agent_stream):
    """
    Wrapper generator that interleaves tool events with agent stream chunks.

    This enables real-time tool status updates in the UI while the agent is processing.
    Also handles GPT-5 reasoning content (type="text_reasoning") for thinking visualization.
    Includes keepalive messages to prevent Azure App Service 230s timeout.
    """
    queue = asyncio.Queue(maxsize=100)  # Limit queue size
    set_tool_event_queue(queue)

    last_output_time = asyncio.get_event_loop().time()

    async def keepalive_check():
        """Check if keepalive is needed and yield marker if so."""
        nonlocal last_output_time
        current_time = asyncio.get_event_loop().time()
        if current_time - last_output_time >= KEEPALIVE_INTERVAL_SECONDS:
            last_output_time = current_time
            return KEEPALIVE_MARKER
        return None

    def is_reasoning_content(content):
        """Check if content is GPT-5 reasoning content (type='text_reasoning')."""
        return hasattr(content, "type") and content.type == "text_reasoning"

    try:
        # Send initial keepalive to confirm stream is active
        yield KEEPALIVE_MARKER
        last_output_time = asyncio.get_event_loop().time()

        chunk_count = 0
        async for chunk in agent_stream:
            chunk_count += 1

            # First, drain any pending tool events
            events = await drain_tool_events(queue)
            for event in events:
                yield event
                last_output_time = asyncio.get_event_loop().time()

            # Check if keepalive needed before processing chunk
            keepalive = await keepalive_check()
            if keepalive:
                yield keepalive

            # Log chunk structure for debugging (first few chunks only)
            if chunk_count <= 5:
                chunk_attrs = [a for a in dir(chunk) if not a.startswith("_")]
                logger.info(
                    f"[DEBUG] Chunk #{chunk_count} type={type(chunk).__name__}, attrs={chunk_attrs}"
                )
                # Log all attribute values for deeper inspection
                for attr in ["text", "contents", "type", "role", "summary", "reasoning", "output"]:
                    if hasattr(chunk, attr):
                        val = getattr(chunk, attr)
                        logger.info(f"[DEBUG] Chunk #{chunk_count}.{attr} = {repr(val)[:200]}")

            # Handle reasoning content (GPT-5 thinking)
            # Responses API returns reasoning as output item with type="reasoning"
            # Agent framework SDK converts these to Content with type="text_reasoning"
            # IMPORTANT: SDK sends CUMULATIVE text in content.text, not just delta
            # We need to calculate the actual delta by comparing with previous text

            # Process chunk.contents for reasoning - SINGLE CHECK to avoid duplicates
            if hasattr(chunk, "contents") and chunk.contents:
                for content in chunk.contents:
                    if is_reasoning_content(content) and content.text:
                        # SDK sends CUMULATIVE text in content.text (not delta)
                        # Send it with a REPLACE marker so frontend replaces instead of appends
                        # This handles the case where cumulative text format doesn't allow
                        # simple prefix-based delta calculation
                        reasoning_marker = (
                            f"__REASONING_REPLACE__{content.text}__END_REASONING_REPLACE__"
                        )
                        yield reasoning_marker
                        last_output_time = asyncio.get_event_loop().time()
                        if chunk_count <= 5:  # Log first 5 reasoning chunks
                            logger.info(
                                f"[REASONING] #{chunk_count}: len={len(content.text)}, "
                                f"text={repr(content.text[:80])}..."
                            )

            # Then yield the agent chunk text
            if chunk and chunk.text:
                yield chunk.text
                last_output_time = asyncio.get_event_loop().time()
    finally:
        # Drain any remaining events and clear queue
        events = await drain_tool_events(queue)
        for event in events:
            yield event
        set_tool_event_queue(None)


# Check if the Application Insights Instrumentation Key is set in the environment variables
instrumentation_key = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if instrumentation_key:
    configure_azure_monitor(connection_string=instrumentation_key)
    logging.info("Application Insights configured with the provided Instrumentation Key")
else:
    logging.warning("No Application Insights Instrumentation Key found. Skipping configuration")

# Suppress noisy loggers
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.identity.aio._internal").setLevel(logging.WARNING)
logging.getLogger("azure.monitor.opentelemetry.exporter.export._base").setLevel(logging.WARNING)


def track_event_if_configured(event_name: str, event_data: dict):
    """Track event to Application Insights if configured."""
    instrumentation_key = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if instrumentation_key:
        track_event(event_name, event_data)


def get_openai_endpoint() -> str | None:
    """
    Get the Azure OpenAI endpoint, preferring APIM Gateway if configured.

    APIM Gateway provides:
    - Rate limiting (100 calls/min)
    - Token usage tracking via response headers
    - Circuit breaker for resilience
    - Centralized logging to Application Insights

    Returns:
        str | None: APIM gateway URL or direct Azure OpenAI endpoint
    """
    if USE_APIM_GATEWAY:
        logger.info(f"Using APIM Gateway: {APIM_GATEWAY_URL}")
        return APIM_GATEWAY_URL
    else:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        logger.info(f"Using direct Azure OpenAI: {endpoint}")
        return endpoint


def get_responses_api_base_url() -> str | None:
    """
    Get the base URL for AzureOpenAIResponsesClient (Responses API v1).

    The Responses API v1 uses a different endpoint format (/openai/v1/)
    that works natively with APIM-imported Foundry OpenAI APIs.

    Priority:
    1. AZURE_OPENAI_BASE_URL (explicit Responses API base URL)
    2. Fall back to ChatClient endpoint (not recommended for Foundry API)

    Returns:
        str | None: Base URL ending with /openai/v1/ or None if not configured
    """
    if AZURE_OPENAI_BASE_URL:
        base_url = AZURE_OPENAI_BASE_URL
        # Ensure trailing slash for proper URL construction
        if not base_url.endswith("/"):
            base_url = base_url + "/"
        logger.info(f"Using Responses API base_url: {base_url}")
        return base_url
    else:
        logger.warning("AZURE_OPENAI_BASE_URL not configured. ResponsesClient will not be used.")
        return None


# ============================================================================
# Tool Functions with @tool decorator
# These tools are used by agents in the HandoffBuilder workflow
# ============================================================================

# Global database connection for tools
_db_connection = None


async def get_db_connection():
    """Get or create database connection for tools."""
    global _db_connection
    if _db_connection is None:
        from history_sql import get_fabric_db_connection

        _db_connection = await get_fabric_db_connection()
    return _db_connection


@tool(approval_mode="never_require")
async def run_sql_query(
    sql_query: Annotated[str, "The SQL query to execute against the Fabric database"],
) -> str:
    """Execute a SQL query against the Fabric SQL database and return results as JSON.

    Use this tool to query sales, orders, products, customers, and business data.

    Available tables:
    - orders: Order headers (OrderId, CustomerId, OrderDate, OrderStatus, OrderTotal, PaymentMethod)
    - orderline: Order details (OrderId, ProductId, Quantity, UnitPrice, LineTotal)
    - product: Products (ProductID, ProductName, CategoryName, ListPrice, BrandName)
    - customer: Customers (CustomerId, FirstName, LastName, CustomerTypeId)
    - location: Customer locations (LocationId, CustomerId, Region, City)
    - productcategory: Product categories (CategoryID, CategoryName)
    - customerrelationshiptype: Customer segments (TypeId, TypeName)
    - invoice: Invoices (InvoiceId, CustomerId, OrderId, TotalAmount)
    - payment: Payments (PaymentId, InvoiceId, PaymentAmount, PaymentStatus)

    Args:
        sql_query: The SQL query to execute. Use T-SQL syntax.

    Returns:
        JSON string with query results or error message.
    """
    from datetime import date, datetime
    from decimal import Decimal

    # Emit tool start event
    await emit_tool_event("run_sql_query", "started", "SQLクエリを実行中...")

    try:
        conn = await get_db_connection()
        if not conn:
            await emit_tool_event("run_sql_query", "error", "DB接続エラー")
            return json.dumps({"error": "Database connection not available"}, ensure_ascii=False)

        cursor = conn.cursor()
        cursor.execute(sql_query)
        columns = [desc[0] for desc in cursor.description]
        result = []

        for row in cursor.fetchall():
            row_dict = {}
            for col_name, value in zip(columns, row, strict=False):
                if isinstance(value, (datetime, date)):
                    row_dict[col_name] = value.isoformat()
                elif isinstance(value, Decimal):
                    row_dict[col_name] = float(value)
                else:
                    row_dict[col_name] = value
            result.append(row_dict)

        cursor.close()
        logger.info(f"SQL query executed successfully, returned {len(result)} rows")

        # Emit tool completion event
        await emit_tool_event(
            "run_sql_query", "completed", f"{len(result)}件のデータを取得しました"
        )
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error executing SQL query: {e}")
        await emit_tool_event("run_sql_query", "error", str(e))
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool(approval_mode="never_require")
async def search_web(
    query: Annotated[str, "The search query for web information"],
) -> str:
    """Search the web for real-time information, news, and current events.

    Use this tool for:
    - Latest news and trends
    - Current market information
    - Weather updates
    - External data not in the database

    Args:
        query: The search query string.

    Returns:
        JSON string with search results or error message.
    """
    global _current_web_citations

    # Emit tool start event
    await emit_tool_event("search_web", "started", "Web検索を実行中...")

    try:
        logger.info(f"Web search requested: {query}")
        web_agent = get_web_agent_handler()
        result = await web_agent.bing_grounding(query)

        # Extract and store citations for UI display (Bing terms of use compliance)
        try:
            result_data = json.loads(result)
            if "citations" in result_data and result_data["citations"]:
                _current_web_citations.extend(result_data["citations"])
                logger.info(f"Stored {len(result_data['citations'])} web citations for UI display")
        except json.JSONDecodeError:
            pass

        logger.info(f"Web search completed for query: {query}")

        # Emit tool completion event
        await emit_tool_event("search_web", "completed", "検索結果を取得しました")
        return result  # Already JSON string
    except Exception as e:
        logger.error(f"Error in web search: {e}")
        await emit_tool_event("search_web", "error", str(e))
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool(approval_mode="never_require")
async def search_documents(
    query: Annotated[str, "The search query for enterprise documents"],
) -> str:
    """Search enterprise documents using Agentic Retrieval (Foundry IQ).

    This tool uses Azure AI Search Knowledge Base with intelligent retrieval:
    - Query decomposition and planning (LLM-based)
    - Multi-source retrieval with semantic reranking
    - Source attribution and citations

    IMPORTANT: For data analysis questions (sales, orders, customers, products),
    use run_sql_query instead. This tool is for documentation lookup only.

    Use this tool for:
    - Product specifications and manuals
    - Technical documentation
    - Internal knowledge base articles
    - Company policies and procedures

    Args:
        query: The search query string.

    Returns:
        Formatted string with document search results and citations.
    """
    # Emit tool start event
    await emit_tool_event("search_documents", "started", "製品仕様書を検索中...")

    try:
        logger.info(f"Agentic document search requested: {query}")

        # Try Agentic Retrieval first (with Knowledge Base)
        agentic_tool = get_agentic_retrieval_tool()
        if agentic_tool is not None:
            # Get reasoning effort from global state (set per-request)
            effort_str = get_reasoning_effort()
            try:
                effort = ReasoningEffort(effort_str.lower())
            except ValueError:
                effort = ReasoningEffort.LOW

            logger.info(f"Using Agentic Retrieval with reasoning_effort={effort.value}")
            result = await agentic_tool.retrieve_formatted(query, effort)
            logger.info(f"Agentic document search completed for query: {query}")

            # Emit tool completion event
            await emit_tool_event("search_documents", "completed", "ドキュメントを検索しました")
            return result

        # Fallback to basic search if Agentic Retrieval not configured
        kb_tool = get_knowledge_base_tool()
        if kb_tool is None:
            await emit_tool_event("search_documents", "error", "検索が設定されていません")
            return json.dumps(
                {
                    "message": (
                        "Document search is not configured. "
                        "AI_SEARCH_* environment variables are missing."
                    ),
                    "query": query,
                    "results": [],
                },
                ensure_ascii=False,
            )

        logger.info("Falling back to basic search (Agentic Retrieval not configured)")
        result = await kb_tool.search(query)

        # Limit results to prevent token overflow
        if isinstance(result, dict) and "results" in result:
            result["results"] = result["results"][:3]  # Max 3 documents
            # Truncate long content
            for doc in result["results"]:
                if "content" in doc and len(doc["content"]) > 1000:
                    doc["content"] = doc["content"][:1000] + "...(truncated)"

        logger.info(f"Basic document search completed for query: {query}")

        # Emit tool completion event
        await emit_tool_event("search_documents", "completed", "ドキュメントを検索しました")
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in document search: {e}")
        await emit_tool_event("search_documents", "error", str(e))
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================================
# Multi-Agent Workflow using MagenticBuilder (Magentic One Pattern)
# ============================================================================


def create_specialist_agents(
    chat_client: AzureOpenAIChatClient,
) -> tuple[ChatAgent, ChatAgent, ChatAgent]:
    """Create specialist agents for MagenticBuilder workflow.

    MagenticBuilder の Manager が各スペシャリストを動的に選択・調整するため、
    トリアージエージェントは不要。Manager がその役割を担う。

    プロンプトは prompts/ モジュールから読み込み、疎結合を維持。

    Args:
        chat_client: The AzureOpenAIChatClient to use for creating agents.

    Returns:
        Tuple of (sql_agent, web_agent, doc_agent)
    """
    # SQL specialist: Handles database queries
    # プロンプトは prompts/sql_agent.py から読み込み
    sql_agent = ChatAgent(
        name="sql_agent",
        description=SQL_AGENT_DESCRIPTION,
        instructions=SQL_AGENT_PROMPT,
        chat_client=chat_client,
        tools=[run_sql_query],
    )

    # Web specialist: Handles web searches
    # プロンプトは prompts/web_agent.py から読み込み
    web_agent = ChatAgent(
        name="web_agent",
        description=WEB_AGENT_DESCRIPTION,
        instructions=WEB_AGENT_PROMPT,
        chat_client=chat_client,
        tools=[search_web],
    )

    # Document specialist: Handles document searches
    # プロンプトは prompts/doc_agent.py から読み込み
    doc_agent = ChatAgent(
        name="doc_agent",
        description=DOC_AGENT_DESCRIPTION,
        instructions=DOC_AGENT_PROMPT,
        chat_client=chat_client,
        tools=[search_documents],
    )

    return sql_agent, web_agent, doc_agent


def create_manager_agent(chat_client: AzureOpenAIChatClient) -> ChatAgent:
    """Create the manager agent for MagenticBuilder orchestration.

    Manager Agent の役割:
    1. 複雑なクエリをサブタスクに分解（Plan）
    2. 各スペシャリストへのタスク割り当て
    3. 進捗の監視と必要に応じた再計画
    4. 全スペシャリストの結果を統合して最終回答を生成

    プロンプトは prompts/manager_agent.py から読み込み。

    Args:
        chat_client: The AzureOpenAIChatClient to use.

    Returns:
        Manager ChatAgent
    """
    return ChatAgent(
        name="MagenticManager",
        description=MANAGER_AGENT_DESCRIPTION,
        instructions=MANAGER_AGENT_PROMPT,
        chat_client=chat_client,
    )


async def stream_multi_agent_response(conversation_id: str, query: str, user_id: str = "anonymous"):
    """
    Stream response using MagenticBuilder pattern for true multi-agent collaboration.

    MagenticBuilder (Magentic One Pattern):
    - Manager Agent がタスクを分解し、計画を作成
    - 複数のスペシャリストが並列または順次実行
    - Manager が結果を統合して最終回答を生成

    これにより、複合的なクエリ（例：「売上データを分析して、最新トレンドと比較」）に対応可能。
    """
    try:
        # Get conversation history for multi-turn support (with timeout)
        history_messages = []
        try:
            import asyncio

            # Set a short timeout (3 seconds) to avoid blocking
            messages = await asyncio.wait_for(
                get_conversation_messages(user_id, conversation_id), timeout=3.0
            )
            if messages:
                # Convert to format suitable for agent (last N messages for context)
                # Limit to last 6 messages to reduce token usage
                recent_messages = messages[-6:] if len(messages) > 6 else messages
                for msg in recent_messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if isinstance(content, str) and content:
                        history_messages.append({"role": role, "content": content})
                logger.info(f"Loaded {len(history_messages)} messages from conversation history")
        except TimeoutError:
            logger.warning("Conversation history fetch timed out, continuing without history")
        except Exception as e:
            logger.warning(f"Could not load conversation history: {e}")
            # Continue without history

        # Use sync credential - SDK requires synchronous token acquisition
        credential = DefaultAzureCredential()

        # Get Azure OpenAI configuration from environment variables
        # SDK 1.0.0b260130 requires explicit deployment_name and endpoint
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_MODEL") or os.getenv(
            "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
        )
        endpoint = get_openai_endpoint()
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

        logger.info(
            f"OpenAI config: deploy={deployment_name}, endpoint={endpoint}, apim={USE_APIM_GATEWAY}"
        )

        if not deployment_name:
            raise ValueError(
                "Azure OpenAI deployment name is required. "
                "Set AZURE_OPENAI_DEPLOYMENT_MODEL or AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
            )
        if not endpoint:
            raise ValueError(
                "Azure OpenAI endpoint is required. "
                "Set AZURE_OPENAI_BASE_URL (for Foundry API), "
                "APIM_GATEWAY_URL, or AZURE_OPENAI_ENDPOINT"
            )

        # Create chat client with explicit configuration
        # Note: MagenticBuilder requires AzureOpenAIChatClient (not ResponsesClient)
        chat_client = AzureOpenAIChatClient(
            credential=credential,
            deployment_name=deployment_name,
            endpoint=endpoint,
            api_version=api_version,
        )

        # Create specialist agents
        sql_agent, web_agent, doc_agent = create_specialist_agents(chat_client)

        # Create manager agent
        manager_agent = create_manager_agent(chat_client)

        # Build the MagenticBuilder workflow
        # Note: App Serviceのタイムアウト（230秒）を超えないよう制限
        # 複雑なクエリでも1-2ラウンドで完了するよう設計
        workflow = (
            MagenticBuilder()
            .participants([sql_agent, web_agent, doc_agent])
            .with_manager(
                agent=manager_agent,
                max_round_count=2,  # 504タイムアウト防止: 2ラウンド以内で完了
                max_stall_count=1,  # 停滞したら即終了
            )
            .build()
        )

        logger.info(f"Starting MagenticBuilder workflow with query: {query[:100]}...")
        logger.info("Workflow configured with Manager + 3 Specialists (SQL, Web, Doc)")

        # Build the full prompt with conversation history
        if history_messages:
            # Format history as context for the agent
            history_context = "\n".join(
                [f"{msg['role'].upper()}: {msg['content']}" for msg in history_messages]
            )
            full_query = f"""## 会話履歴（参考にしてください）
{history_context}

## 現在の質問
{query}"""
            logger.info(f"Including {len(history_messages)} messages in context")
        else:
            full_query = query

        last_message_id: str | None = None
        last_executor_id: str | None = None
        specialist_outputs: dict[str, str] = {}  # Specialist別の出力を蓄積
        manager_output = ""  # Managerの最終出力

        # Stream the workflow execution
        # 戦略: Specialistの出力は蓄積のみ、Managerの最終応答のみをリアルタイムストリーム
        # これにより応答サイズを削減しつつ、ユーザーにはストリーミング体験を提供

        async for event in workflow.run_stream(full_query):
            if isinstance(event, AgentRunUpdateEvent):
                update = event.data
                message_id = getattr(update, "message_id", None)
                executor_id = str(getattr(event, "executor_id", "unknown"))
                text_chunk = ""

                if hasattr(update, "text") and update.text:
                    text_chunk = update.text
                elif isinstance(update, str):
                    text_chunk = update

                if not text_chunk:
                    continue

                # executor_idでエージェントを識別
                # MagenticManager または Manager を含む場合はManager
                is_manager = "manager" in executor_id.lower() or "magentic" in executor_id.lower()

                # 新しいメッセージの場合
                if message_id and message_id != last_message_id:
                    if last_executor_id:
                        logger.info(f"Agent {last_executor_id} completed response")
                    last_message_id = message_id
                    last_executor_id = executor_id

                    # Managerの新しいメッセージが始まった
                    if is_manager:
                        logger.info(f"Manager streaming started: {executor_id}")

                if is_manager:
                    # Managerの出力はリアルタイムでストリーム
                    manager_output += text_chunk
                    yield text_chunk
                else:
                    # Specialistの出力は蓄積のみ（ログに記録）
                    if executor_id not in specialist_outputs:
                        specialist_outputs[executor_id] = ""
                    specialist_outputs[executor_id] += text_chunk

            elif isinstance(event, MagenticOrchestratorEvent):
                logger.info(f"Orchestrator event: {type(event).__name__}")
                plan = getattr(event, "plan", None)
                if plan:
                    logger.info(f"Plan created: {plan}")

            elif isinstance(event, WorkflowOutputEvent):
                # ワークフロー完了時の最終出力
                logger.info("WorkflowOutputEvent received")
                if event.data:
                    output_messages = event.data
                    final_text = ""
                    if isinstance(output_messages, list):
                        for msg in output_messages:
                            if hasattr(msg, "text") and msg.text:
                                final_text = msg.text
                    elif isinstance(output_messages, str):
                        final_text = output_messages

                    # まだストリームされていない部分があればyield
                    if final_text and final_text != manager_output:
                        remaining = (
                            final_text[len(manager_output) :]
                            if final_text.startswith(manager_output)
                            else final_text
                        )
                        if remaining:
                            logger.info(f"Yielding remaining final output: {len(remaining)} chars")
                            yield remaining
                            manager_output = final_text

                logger.info("MagenticBuilder workflow completed")

            elif isinstance(event, WorkflowStatusEvent):
                state_name = (
                    str(event.state.name) if hasattr(event.state, "name") else str(event.state)
                )
                logger.info(f"Workflow status: {state_name}")

            elif isinstance(event, GroupChatRequestSentEvent):
                logger.info(f"Request sent to: {getattr(event, 'target', 'unknown')}")

            elif isinstance(event, RequestInfoEvent):
                logger.info(f"Request info event: {event}")

        # ログにSpecialist出力のサマリーを記録
        for agent_id, output in specialist_outputs.items():
            logger.info(f"Specialist {agent_id} output: {len(output)} chars")

        # ストリーミングが全くなかった場合のフォールバック
        if not manager_output:
            logger.warning("No manager output streamed, using accumulated specialist outputs")
            # Specialistの出力を結合して返す
            combined = "\n\n".join(
                f"### {agent_id}\n{output}"
                for agent_id, output in specialist_outputs.items()
                if output
            )
            if combined:
                yield combined

    except Exception as e:
        logger.error(f"Error in MagenticBuilder workflow: {e}", exc_info=True)
        raise
    finally:
        global _db_connection
        if _db_connection:
            import contextlib

            with contextlib.suppress(Exception):
                _db_connection.close()
            _db_connection = None


async def stream_single_agent_response(
    conversation_id: str, query: str, user_id: str = "anonymous"
):
    """
    Stream response using single agent mode with AzureOpenAIResponsesClient (preferred)
    or AzureOpenAIChatClient (fallback).

    This is the PRIMARY mode - a single intelligent agent with multiple tools.
    The LLM automatically selects which tools to use based on the query.

    AzureOpenAIResponsesClient advantages:
    - Native compatibility with APIM Foundry API (/openai/v1/ endpoint)
    - No api-version required (uses 'preview' or 'latest')
    - Supports Thread management for server-side conversation context
    - Supports Hosted tools (MCP, CodeInterpreter, WebSearch, FileSearch)
    """
    try:
        # Load conversation history for multi-turn support
        history_messages = []
        try:
            import asyncio

            messages = await asyncio.wait_for(
                get_conversation_messages(user_id, conversation_id), timeout=3.0
            )
            if messages:
                # Last 6 messages for context
                recent_messages = messages[-6:] if len(messages) > 6 else messages
                for msg in recent_messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if isinstance(content, str) and content:
                        history_messages.append({"role": role, "content": content})
                logger.info(f"Loaded {len(history_messages)} messages from conversation history")
        except TimeoutError:
            logger.warning("Conversation history fetch timed out, continuing without history")
        except Exception as e:
            logger.warning(f"Could not load conversation history: {e}")

        # Use sync credential - SDK requires synchronous token acquisition
        credential = DefaultAzureCredential()

        # Get Azure OpenAI configuration from environment variables
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_MODEL") or os.getenv(
            "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
        )

        # Determine which client to use based on configuration
        base_url = get_responses_api_base_url()
        use_responses_client = USE_RESPONSES_CLIENT and base_url is not None

        if use_responses_client:
            # Use AzureOpenAIResponsesClient for APIM Foundry API
            logger.info(
                f"Using AzureOpenAIResponsesClient: deployment={deployment_name}, "
                f"base_url={base_url}"
            )

            if not deployment_name:
                raise ValueError(
                    "Azure OpenAI deployment name is required. "
                    "Set AZURE_OPENAI_DEPLOYMENT_MODEL or AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
                )

            # Create ResponsesClient with base_url (no api-version needed)
            responses_client = AzureOpenAIResponsesClient(
                base_url=base_url,
                deployment_name=deployment_name,
                credential=credential,
            )
            client = responses_client
        else:
            # Fallback to AzureOpenAIChatClient (Chat Completions API)
            endpoint = get_openai_endpoint()
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

            logger.info(
                f"Using AzureOpenAIChatClient (fallback): deployment={deployment_name}, "
                f"endpoint={endpoint}, via_apim={USE_APIM_GATEWAY}"
            )

            if not deployment_name:
                raise ValueError(
                    "Azure OpenAI deployment name is required. "
                    "Set AZURE_OPENAI_DEPLOYMENT_MODEL or AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
                )
            if not endpoint:
                raise ValueError(
                    "Azure OpenAI endpoint is required. "
                    "Set AZURE_OPENAI_BASE_URL (preferred for Foundry API), "
                    "APIM_GATEWAY_URL, or AZURE_OPENAI_ENDPOINT"
                )

            # Create ChatClient with explicit configuration
            client = AzureOpenAIChatClient(
                credential=credential,
                deployment_name=deployment_name,
                endpoint=endpoint,
                api_version=api_version,
            )

        # Initialize tool handlers (ensure singletons are created)
        web_handler = get_web_agent_handler()
        kb_tool = get_knowledge_base_tool()

        # Collect all available tools
        all_tools = [run_sql_query]  # Always available

        # Add web search tool
        # NOTE: HostedWebSearchTool requires OpenAI's web_search_preview which is not
        # available in Azure OpenAI. Using custom search_web for now.
        # When Azure OpenAI supports web_search_preview, we can enable HostedWebSearchTool.
        if web_handler:
            all_tools.append(search_web)
            logger.info("Web search tool enabled (custom implementation via WebAgentHandler)")

        # Add document search if configured
        if kb_tool:
            all_tools.append(search_documents)
            logger.info("Document search tool enabled")
        else:
            logger.warning(
                "Document search tool NOT available - AI_SEARCH_* env vars may be missing"
            )

        # Add MCP business analytics tools
        mcp_tools = get_mcp_tools()
        if mcp_tools:
            all_tools.extend(mcp_tools)
            logger.info(f"MCP business analytics tools enabled: {len(mcp_tools)} tools")

        logger.info(f"Available tools: {len(all_tools)} tools configured")

        # Create a single intelligent agent with ALL tools
        # This is the RECOMMENDED mode for most queries because:
        # 1. Single LLM call handles tool selection
        # 2. Can call multiple tools and INTEGRATE results
        # 3. Fast and flexible
        # プロンプトは prompts/unified_agent.py から読み込み

        # Build reasoning options for GPT-5 models
        model_params = get_model_params()
        reasoning_options = {}
        if model_params["model"] == "gpt-5":
            reasoning_opts = {}
            if model_params["model_reasoning_effort"]:
                reasoning_opts["effort"] = model_params["model_reasoning_effort"]
            if model_params["reasoning_summary"] and model_params["reasoning_summary"] != "off":
                reasoning_opts["summary"] = model_params["reasoning_summary"]
            if reasoning_opts:
                reasoning_options["reasoning"] = reasoning_opts
                logger.info(f"GPT-5 reasoning options: {reasoning_opts}")

        agent = client.as_agent(
            name="unified_assistant",
            instructions=UNIFIED_AGENT_PROMPT,
            tools=all_tools,
            default_options=reasoning_options if reasoning_options else None,
        )

        # Build the full prompt with conversation history for multi-turn support
        if history_messages:
            # Format history as context for the agent
            history_context = "\n".join(
                [f"{msg['role'].upper()}: {msg['content']}" for msg in history_messages]
            )
            full_query = f"""## 会話履歴（参考にしてください）
{history_context}

## 現在の質問
{query}"""
            logger.info(f"Including {len(history_messages)} messages in context")
        else:
            full_query = query

        logger.info(f"Unified agent processing query: {query[:100]}...")

        # Stream the agent response with tool events interleaved
        async for output in stream_with_tool_events(agent.run_stream(full_query)):
            yield output

    except Exception as e:
        logger.error(f"Error in single agent response: {e}", exc_info=True)
        raise
    finally:
        global _db_connection
        if _db_connection:
            import contextlib

            with contextlib.suppress(Exception):
                _db_connection.close()
            _db_connection = None


async def stream_sql_only_response(conversation_id: str, query: str, user_id: str = "anonymous"):
    """
    Stream response using single agent mode with SQL tool only.
    This is the FASTEST mode - optimized for simple SQL queries.

    Uses AzureOpenAIResponsesClient (preferred) or AzureOpenAIChatClient (fallback).
    """
    try:
        # Load conversation history for multi-turn support
        history_messages = []
        try:
            import asyncio

            messages = await asyncio.wait_for(
                get_conversation_messages(user_id, conversation_id), timeout=3.0
            )
            if messages:
                recent_messages = messages[-6:] if len(messages) > 6 else messages
                for msg in recent_messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if isinstance(content, str) and content:
                        history_messages.append({"role": role, "content": content})
                logger.info(f"SQL-only: Loaded {len(history_messages)} messages from history")
        except TimeoutError:
            logger.warning("SQL-only: History fetch timed out")
        except Exception as e:
            logger.warning(f"SQL-only: Could not load history: {e}")

        credential = DefaultAzureCredential()
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_MODEL") or os.getenv(
            "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
        )

        # Determine which client to use based on configuration
        base_url = get_responses_api_base_url()
        use_responses_client = USE_RESPONSES_CLIENT and base_url is not None

        if use_responses_client:
            # Use AzureOpenAIResponsesClient for APIM Foundry API
            logger.info(f"SQL-only: Using ResponsesClient with base_url={base_url}")

            if not deployment_name:
                raise ValueError(
                    "Azure OpenAI deployment name is required. "
                    "Set AZURE_OPENAI_DEPLOYMENT_MODEL or AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
                )

            client = AzureOpenAIResponsesClient(
                base_url=base_url,
                deployment_name=deployment_name,
                credential=credential,
            )
        else:
            # Fallback to AzureOpenAIChatClient
            endpoint = get_openai_endpoint()
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

            if not deployment_name or not endpoint:
                raise ValueError(
                    "Azure OpenAI configuration missing. "
                    "Set deployment name and AZURE_OPENAI_BASE_URL, APIM_GATEWAY_URL, "
                    "or AZURE_OPENAI_ENDPOINT"
                )

            logger.info(f"SQL-only: Using ChatClient with endpoint={endpoint}")

            client = AzureOpenAIChatClient(
                credential=credential,
                deployment_name=deployment_name,
                endpoint=endpoint,
                api_version=api_version,
            )

        # Build reasoning options for GPT-5 models
        model_params = get_model_params()
        reasoning_options = {}
        if model_params["model"] == "gpt-5":
            reasoning_opts = {}
            if model_params["model_reasoning_effort"]:
                reasoning_opts["effort"] = model_params["model_reasoning_effort"]
            if model_params["reasoning_summary"] and model_params["reasoning_summary"] != "off":
                reasoning_opts["summary"] = model_params["reasoning_summary"]
            if reasoning_opts:
                reasoning_options["reasoning"] = reasoning_opts
                logger.info(f"SQL-only GPT-5 reasoning options: {reasoning_opts}")

        # SQL-only agent - fastest mode
        # プロンプトは prompts/sql_agent.py から読み込み（簡易版）
        agent = client.as_agent(
            name="sql_analyst",
            instructions=SQL_AGENT_PROMPT_MINIMAL,
            tools=[run_sql_query],
            default_options=reasoning_options if reasoning_options else None,
        )

        # Build the full prompt with conversation history for multi-turn support
        if history_messages:
            history_context = "\n".join(
                [f"{msg['role'].upper()}: {msg['content']}" for msg in history_messages]
            )
            full_query = f"""## 会話履歴（参考にしてください）
{history_context}

## 現在の質問
{query}"""
            logger.info(f"SQL-only: Including {len(history_messages)} messages in context")
        else:
            full_query = query

        logger.info(f"SQL-only agent processing query: {query[:100]}...")

        # Stream with tool events
        async for output in stream_with_tool_events(agent.run_stream(full_query)):
            yield output

    except Exception as e:
        logger.error(f"Error in SQL-only response: {e}", exc_info=True)
        raise
    finally:
        global _db_connection
        if _db_connection:
            import contextlib

            with contextlib.suppress(Exception):
                _db_connection.close()
            _db_connection = None


async def stream_handoff_response(conversation_id: str, query: str, user_id: str = "anonymous"):
    """
    Stream response using HandoffBuilder for expert delegation pattern.

    HandoffBuilder Design:
    - Triage agent analyzes query and hands off to the RIGHT specialist
    - Specialist provides the FINAL answer (no integration step)
    - Fast because: no central planner, direct handoffs

    Use Case:
    - "売上TOP3" → Triage → SQL Agent → Final SQL-based answer
    - "最新のトレンド" → Triage → Web Agent → Final web-based answer

    NOT for:
    - Queries needing multiple sources combined → Use multi_tool mode instead

    Topology: User → Triage → Specialist → Response
    """
    try:
        # Load conversation history for multi-turn support
        history_messages = []
        try:
            import asyncio

            messages = await asyncio.wait_for(
                get_conversation_messages(user_id, conversation_id), timeout=3.0
            )
            if messages:
                recent_messages = messages[-6:] if len(messages) > 6 else messages
                for msg in recent_messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if isinstance(content, str) and content:
                        history_messages.append({"role": role, "content": content})
                logger.info(f"Handoff: Loaded {len(history_messages)} messages from history")
        except TimeoutError:
            logger.warning("Handoff: History fetch timed out")
        except Exception as e:
            logger.warning(f"Handoff: Could not load history: {e}")

        # Initialize tool handlers (ensure singletons are created)
        web_handler = get_web_agent_handler()
        kb_tool = get_knowledge_base_tool()
        logger.info(
            f"Handoff mode: web_handler={web_handler is not None}, kb_tool={kb_tool is not None}"
        )

        credential = DefaultAzureCredential()
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_MODEL") or os.getenv(
            "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
        )
        endpoint = get_openai_endpoint()
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

        if not deployment_name or not endpoint:
            raise ValueError(
                "Azure OpenAI configuration missing. "
                "Set AZURE_OPENAI_DEPLOYMENT_MODEL and APIM_GATEWAY_URL or AZURE_OPENAI_ENDPOINT"
            )

        # Note: HandoffBuilder requires AzureOpenAIChatClient (not ResponsesClient)
        chat_client = AzureOpenAIChatClient(
            credential=credential,
            deployment_name=deployment_name,
            endpoint=endpoint,
            api_version=api_version,
        )

        # Create triage agent - routes to the RIGHT specialist
        # プロンプトは prompts/triage_agent.py から読み込み
        triage_agent = chat_client.as_agent(
            name="triage_agent",
            description=TRIAGE_AGENT_DESCRIPTION,
            instructions=TRIAGE_AGENT_PROMPT,
        )

        # SQL specialist - comprehensive instructions for final answer
        # プロンプトは prompts/sql_agent.py から読み込み
        sql_agent = chat_client.as_agent(
            name="sql_agent",
            description=SQL_AGENT_DESCRIPTION,
            instructions=SQL_AGENT_PROMPT,
            tools=[run_sql_query],
        )

        # Web search specialist
        # プロンプトは prompts/web_agent.py から読み込み
        web_agent = chat_client.as_agent(
            name="web_agent",
            description=WEB_AGENT_DESCRIPTION,
            instructions=WEB_AGENT_PROMPT,
            tools=[search_web] if web_handler else [],
        )

        # Document search specialist
        # プロンプトは prompts/doc_agent.py から読み込み
        doc_agent = chat_client.as_agent(
            name="doc_agent",
            description=DOC_AGENT_DESCRIPTION,
            instructions=DOC_AGENT_PROMPT,
            tools=[search_documents] if kb_tool else [],
        )

        # Collect active agents
        participants = [triage_agent, sql_agent]
        if web_handler:
            participants.append(web_agent)
        if kb_tool:
            participants.append(doc_agent)

        logger.info(f"Handoff workflow with {len(participants)} agents")

        # Build handoff workflow
        builder = HandoffBuilder(
            name="data_analysis_handoff",
            participants=participants,
        ).with_start_agent(triage_agent)

        # Configure handoff routes: triage can handoff to all specialists
        specialist_agents = [sql_agent]
        if web_handler:
            specialist_agents.append(web_agent)
        if kb_tool:
            specialist_agents.append(doc_agent)

        builder = builder.add_handoff(triage_agent, specialist_agents)

        # Specialists can handoff back to triage if needed
        for specialist in specialist_agents:
            builder = builder.add_handoff(specialist, [triage_agent])

        # Enable autonomous mode for all agents
        builder = builder.with_autonomous_mode()

        # Terminate when a specialist has responded
        builder = builder.with_termination_condition(
            lambda msgs: len(msgs) >= 2
            and any(
                hasattr(m, "author_name")
                and m.author_name in ["sql_agent", "web_agent", "doc_agent"]
                for m in msgs
            )
        )

        workflow = builder.build()

        # Build the full prompt with conversation history for multi-turn support
        if history_messages:
            history_context = "\n".join(
                [f"{msg['role'].upper()}: {msg['content']}" for msg in history_messages]
            )
            full_query = f"""## 会話履歴（参考にしてください）
{history_context}

## 現在の質問
{query}"""
            logger.info(f"Handoff: Including {len(history_messages)} messages in context")
        else:
            full_query = query

        logger.info(f"Handoff workflow processing query: {query[:100]}...")

        # Stream the workflow response
        streamed_content = ""
        async for event in workflow.run_stream(full_query):
            if isinstance(event, AgentRunUpdateEvent):
                # Stream agent responses in real-time
                if event.data:
                    text = str(event.data)
                    if text and text not in streamed_content:
                        streamed_content += text
                        yield text
            elif isinstance(event, RequestInfoEvent):
                # Handle user input requests (shouldn't happen with autonomous mode)
                if isinstance(event.data, HandoffAgentUserRequest):
                    logger.info(f"Handoff request from {event.source_executor_id}")
            elif isinstance(event, WorkflowOutputEvent) and event.data:
                # Final output - extract the specialist's response
                messages = event.data
                # Find the last specialist message
                for msg in reversed(messages):
                    if hasattr(msg, "author_name") and msg.author_name in [
                        "sql_agent",
                        "web_agent",
                        "doc_agent",
                    ]:
                        if hasattr(msg, "text") and msg.text and msg.text not in streamed_content:
                            yield msg.text
                        break

    except Exception as e:
        logger.error(f"Error in Handoff workflow: {e}", exc_info=True)
        raise
    finally:
        global _db_connection
        if _db_connection:
            import contextlib

            with contextlib.suppress(Exception):
                _db_connection.close()
            _db_connection = None


# ============================================================================
# Chat API Endpoint
# ============================================================================

# Agent Mode Configuration
# AGENT_MODE options:
#   - "sql_only": Fastest - single agent with SQL tool only
#   - "multi_tool": Default, RECOMMENDED - single agent with all tools (SQL, Web, Doc)
#                   Best for: most queries, including complex multi-source queries
#   - "handoff": Multi-agent with HandoffBuilder (expert delegation, no result integration)
#   - "magentic": Multi-agent with MagenticBuilder (slowest, complex planning)
AGENT_MODE = os.getenv("AGENT_MODE", "multi_tool").lower()


def select_agent_mode(query: str) -> str:
    """
    Select the best agent mode based on query complexity.

    Design Principles:
    - multi_tool is the DEFAULT and RECOMMENDED for most queries
    - multi_tool handles result integration (single agent calls multiple tools)
    - handoff is for expert delegation (no result integration)
    - sql_only is for simple SQL-only queries
    - magentic is legacy (slow but powerful planning)

    Returns:
        "sql_only" | "multi_tool" | "handoff" | "magentic"
    """
    # If explicitly configured to a specific mode, use that
    if AGENT_MODE in ["sql_only", "handoff", "magentic"]:
        return AGENT_MODE

    # Auto-select based on query (default: multi_tool)
    query_lower = query.lower()

    # Simple greetings → sql_only (fastest, no tools needed)
    greeting_patterns = [
        "こんにちは",
        "ありがとう",
        "hello",
        "hi",
        "よろしく",
        "はじめまして",
    ]
    if any(p in query_lower for p in greeting_patterns):
        return "sql_only"

    # Simple SQL-only patterns → sql_only
    sql_only_patterns = [
        "売上top",
        "売上ランキング",
        "一覧",
        "何件",
        "総数",
        "合計金額",
    ]
    if any(p in query_lower for p in sql_only_patterns) and not any(
        p in query_lower for p in ["仕様", "スペック", "トレンド", "最新"]
    ):
        return "sql_only"

    # Everything else → multi_tool (handles single and multi-source queries)
    # multi_tool can:
    # - Use SQL only if needed
    # - Use Web only if needed
    # - Use Doc only if needed
    # - Use MULTIPLE tools and INTEGRATE results
    return "multi_tool"


async def stream_chat_request(
    conversation_id: str,
    query: str,
    user_id: str = "anonymous",
    agent_mode: str | None = None,
):
    """
    Handles streaming chat requests with dynamic mode selection.

    Modes:
    - sql_only: Fastest, SQL queries only
    - multi_tool: Single agent with all tools (default)
    - handoff: Multi-agent with HandoffBuilder
    - magentic: Multi-agent with MagenticBuilder (legacy)
    """
    # Regex to extract tool events from streaming chunks
    TOOL_EVENT_PATTERN = re.compile(r"__TOOL_EVENT__(.*?)__END_TOOL_EVENT__")

    async def generate():
        global _current_web_citations
        # Clear any previous citations at the start of each request
        _current_web_citations = []

        try:
            assistant_content = ""

            # Use request agent_mode if provided, otherwise auto-select
            if agent_mode and agent_mode in [
                "sql_only",
                "multi_tool",
                "handoff",
                "magentic",
            ]:
                mode = agent_mode
                logger.info(f"Using requested mode '{mode}' for query: {query[:50]}...")
            else:
                mode = select_agent_mode(query)
                logger.info(f"Auto-selected mode '{mode}' for query: {query[:50]}...")

            # Choose stream function based on mode
            if mode == "sql_only":

                async def sql_wrapper(cid: str, q: str):
                    async for chunk in stream_sql_only_response(cid, q, user_id):
                        yield chunk

                stream_func = sql_wrapper
            elif mode == "handoff":

                async def handoff_wrapper(cid: str, q: str):
                    async for chunk in stream_handoff_response(cid, q, user_id):
                        yield chunk

                stream_func = handoff_wrapper
            elif mode == "magentic":
                # Magentic requires user_id parameter
                async def magentic_wrapper(cid: str, q: str):
                    async for chunk in stream_multi_agent_response(cid, q, user_id):
                        yield chunk

                stream_func = magentic_wrapper
            else:  # multi_tool (default)

                async def multi_tool_wrapper(cid: str, q: str):
                    async for chunk in stream_single_agent_response(cid, q, user_id):
                        yield chunk

                stream_func = multi_tool_wrapper

            # Stream and accumulate response
            async for chunk in stream_func(conversation_id, query):
                if chunk:
                    chunk_str = str(chunk)

                    # Check if this chunk is a tool event
                    if chunk_str.startswith("__TOOL_EVENT__"):
                        # Extract and send tool event separately
                        match = TOOL_EVENT_PATTERN.search(chunk_str)
                        if match:
                            tool_event_json = match.group(1)
                            # Send tool event as a special message type
                            yield f"__TOOL_EVENT__{tool_event_json}__END_TOOL_EVENT__\n\n"
                        continue  # Don't add to assistant_content

                    # Regular text chunk - accumulate and send
                    assistant_content += chunk_str
                    # Include web citations in the response for UI display (Bing terms of use)
                    citations_json = (
                        json.dumps(_current_web_citations) if _current_web_citations else None
                    )
                    response = {
                        "choices": [
                            {
                                "messages": [
                                    {
                                        "role": "assistant",
                                        "content": assistant_content,
                                        "citations": citations_json,
                                    }
                                ]
                            }
                        ]
                    }
                    yield json.dumps(response, ensure_ascii=False) + "\n\n"

            # Fallback if no response
            if not assistant_content:
                logger.info("No response received")
                fallback_msg = (
                    "申し訳ございませんが、この質問にはお答えできません。"
                    "質問を変えてお試しください。"
                )
                response = {
                    "choices": [
                        {
                            "messages": [
                                {
                                    "role": "assistant",
                                    "content": fallback_msg,
                                }
                            ]
                        }
                    ]
                }
                yield json.dumps(response, ensure_ascii=False) + "\n\n"

        except Exception as e:
            error_message = str(e)
            if "Rate limit" in error_message:
                match = re.search(r"Try again in (\d+) seconds.", error_message)
                retry_after = match.group(1) if match else "sometime"
                logger.error(f"Rate limit error: {error_message}")
                yield (
                    json.dumps(
                        {"error": f"Rate limit is exceeded. Try again in {retry_after} seconds."}
                    )
                    + "\n\n"
                )
            else:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                yield (
                    json.dumps({"error": "An error occurred while processing the request."})
                    + "\n\n"
                )

    return generate()


@router.post("/chat")
async def conversation(request: Request):
    """Handle chat requests - streaming text or chart generation based on query keywords."""
    try:
        # Get authenticated user for conversation history
        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        user_id = authenticated_user.get("user_principal_id", "anonymous")

        request_json = await request.json()
        conversation_id = request_json.get("conversation_id")
        query = request_json.get("query")

        if not query:
            return JSONResponse(content={"error": "Query is required"}, status_code=400)

        if not conversation_id:
            return JSONResponse(content={"error": "Conversation ID is required"}, status_code=400)

        agent_mode = request_json.get(
            "agent_mode"
        )  # Optional: sql_only, multi_tool, handoff, magentic

        # Set reasoning effort for Agentic Retrieval (minimal/low/medium)
        reasoning_effort = request_json.get("reasoning_effort", "low")
        if reasoning_effort not in ["minimal", "low", "medium"]:
            reasoning_effort = "low"
        set_reasoning_effort(reasoning_effort)
        logger.info(f"Reasoning effort set to: {reasoning_effort}")

        # Set model parameters for GPT-5 / GPT-4o-mini
        model = request_json.get("model", "gpt-5")
        model_reasoning_effort = request_json.get("model_reasoning_effort", "medium")
        reasoning_summary = request_json.get("reasoning_summary", "auto")
        temperature = float(request_json.get("temperature", 0.7))
        set_model_params(model, model_reasoning_effort, reasoning_summary, temperature)
        logger.info(
            f"Model params set: model={model}, reasoning_effort={model_reasoning_effort}, "
            f"reasoning_summary={reasoning_summary}, temperature={temperature}"
        )

        # stream_chat_request returns an async generator, so we need to wrap it in StreamingResponse
        stream_generator = await stream_chat_request(conversation_id, query, user_id, agent_mode)
        track_event_if_configured(
            "ChatStreamSuccess",
            {
                "conversation_id": conversation_id,
                "query": query,
                "agent_mode": agent_mode,
                "reasoning_effort": reasoning_effort,
            },
        )
        return StreamingResponse(
            stream_generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as ex:
        logger.error(f"Error in conversation endpoint: {ex}", exc_info=True)
        return JSONResponse(
            content={"error": "An internal error occurred while processing the conversation."},
            status_code=500,
        )
