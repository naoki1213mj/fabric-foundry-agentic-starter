"""
Tests for AgenticRetrievalTool (agentic_retrieval_tool.py).

Covers:
- ReasoningEffort enum values
- AgenticRetrievalTool initialization and property normalization
- create_from_env factory method (env var parsing & validation)
- URL construction (retrieve_url, mcp_url)
- _parse_retrieve_response logic (pure function, most valuable)
- retrieve_formatted output formatting
- agentic_knowledge_retrieve standalone function
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentic_retrieval_tool import AgenticRetrievalTool, ReasoningEffort, agentic_knowledge_retrieve

# ============================================================================
# ReasoningEffort Enum
# ============================================================================


class TestReasoningEffort:
    """Tests for ReasoningEffort enum."""

    def test_enum_values(self):
        """All three effort levels exist."""
        assert ReasoningEffort.MINIMAL == "minimal"
        assert ReasoningEffort.LOW == "low"
        assert ReasoningEffort.MEDIUM == "medium"

    def test_enum_from_string(self):
        """Enum can be created from string value."""
        assert ReasoningEffort("minimal") is ReasoningEffort.MINIMAL
        assert ReasoningEffort("low") is ReasoningEffort.LOW
        assert ReasoningEffort("medium") is ReasoningEffort.MEDIUM

    def test_invalid_value_raises(self):
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError):
            ReasoningEffort("high")


# ============================================================================
# AgenticRetrievalTool Init & Properties
# ============================================================================


class TestAgenticRetrievalToolInit:
    """Tests for AgenticRetrievalTool.__init__ and properties."""

    def test_endpoint_trailing_slash_stripped(self):
        """Trailing slash on endpoint should be stripped."""
        tool = AgenticRetrievalTool(
            search_endpoint="https://search.windows.net/",
            knowledge_base_name="test-kb",
        )
        assert tool.search_endpoint == "https://search.windows.net"

    def test_defaults(self):
        """Default values for optional parameters."""
        tool = AgenticRetrievalTool(
            search_endpoint="https://search.windows.net",
            knowledge_base_name="kb-1",
        )
        assert tool.api_key is None
        assert tool.default_reasoning_effort == ReasoningEffort.LOW
        assert tool._session is None

    def test_retrieve_url(self):
        """retrieve_url property constructs correct URL."""
        tool = AgenticRetrievalTool(
            search_endpoint="https://search.windows.net",
            knowledge_base_name="product-kb",
        )
        expected = (
            "https://search.windows.net/knowledgebases/product-kb"
            "/retrieve?api-version=2025-11-01-preview"
        )
        assert tool.retrieve_url == expected

    def test_mcp_url(self):
        """mcp_url property constructs correct URL."""
        tool = AgenticRetrievalTool(
            search_endpoint="https://search.windows.net",
            knowledge_base_name="product-kb",
        )
        expected = (
            "https://search.windows.net/knowledgebases/product-kb"
            "/mcp?api-version=2025-11-01-preview"
        )
        assert tool.mcp_url == expected

    def test_custom_effort_and_api_key(self):
        """Custom reasoning effort and API key are stored."""
        tool = AgenticRetrievalTool(
            search_endpoint="https://search.windows.net",
            knowledge_base_name="kb",
            api_key="my-key",
            default_reasoning_effort=ReasoningEffort.MEDIUM,
        )
        assert tool.api_key == "my-key"
        assert tool.default_reasoning_effort == ReasoningEffort.MEDIUM


# ============================================================================
# create_from_env
# ============================================================================


class TestCreateFromEnv:
    """Tests for AgenticRetrievalTool.create_from_env factory method."""

    def test_returns_none_without_endpoint(self, monkeypatch):
        """Should return None if AI_SEARCH_ENDPOINT is not set."""
        monkeypatch.delenv("AI_SEARCH_ENDPOINT", raising=False)
        monkeypatch.delenv("AI_SEARCH_KNOWLEDGE_BASE_NAME", raising=False)
        result = AgenticRetrievalTool.create_from_env()
        assert result is None

    def test_returns_none_without_kb_name(self, monkeypatch):
        """Should return None if knowledge base name is not set."""
        monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://search.windows.net")
        monkeypatch.delenv("AI_SEARCH_KNOWLEDGE_BASE_NAME", raising=False)
        result = AgenticRetrievalTool.create_from_env()
        assert result is None

    def test_creates_tool_with_valid_config(self, monkeypatch):
        """Should create instance with all required env vars."""
        monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://search.windows.net")
        monkeypatch.setenv("AI_SEARCH_KNOWLEDGE_BASE_NAME", "test-kb")
        monkeypatch.delenv("AI_SEARCH_API_KEY", raising=False)
        monkeypatch.delenv("AI_SEARCH_REASONING_EFFORT", raising=False)

        tool = AgenticRetrievalTool.create_from_env()
        assert tool is not None
        assert tool.search_endpoint == "https://search.windows.net"
        assert tool.knowledge_base_name == "test-kb"
        assert tool.default_reasoning_effort == ReasoningEffort.LOW

    def test_parses_reasoning_effort_medium(self, monkeypatch):
        """Should parse reasoning effort from env var."""
        monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://search.windows.net")
        monkeypatch.setenv("AI_SEARCH_KNOWLEDGE_BASE_NAME", "kb")
        monkeypatch.setenv("AI_SEARCH_REASONING_EFFORT", "medium")

        tool = AgenticRetrievalTool.create_from_env()
        assert tool.default_reasoning_effort == ReasoningEffort.MEDIUM

    def test_invalid_reasoning_effort_defaults_to_low(self, monkeypatch):
        """Invalid reasoning effort should default to 'low'."""
        monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://search.windows.net")
        monkeypatch.setenv("AI_SEARCH_KNOWLEDGE_BASE_NAME", "kb")
        monkeypatch.setenv("AI_SEARCH_REASONING_EFFORT", "ultra")

        tool = AgenticRetrievalTool.create_from_env()
        assert tool.default_reasoning_effort == ReasoningEffort.LOW

    def test_api_key_passed_through(self, monkeypatch):
        """API key from env should be stored."""
        monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://search.windows.net")
        monkeypatch.setenv("AI_SEARCH_KNOWLEDGE_BASE_NAME", "kb")
        monkeypatch.setenv("AI_SEARCH_API_KEY", "secret-key-123")

        tool = AgenticRetrievalTool.create_from_env()
        assert tool.api_key == "secret-key-123"


# ============================================================================
# _parse_retrieve_response (pure function — highest test value)
# ============================================================================


class TestParseRetrieveResponse:
    """Tests for AgenticRetrievalTool._parse_retrieve_response."""

    def _make_tool(self):
        return AgenticRetrievalTool(
            search_endpoint="https://search.windows.net",
            knowledge_base_name="kb",
        )

    def test_error_in_response_passthrough(self):
        """If response has 'error' key, pass it through."""
        tool = self._make_tool()
        result = tool._parse_retrieve_response(
            {"error": "Something went wrong"}, ReasoningEffort.LOW
        )
        assert result == {"error": "Something went wrong"}

    def test_empty_response(self):
        """Empty response data returns zero sources."""
        tool = self._make_tool()
        result = tool._parse_retrieve_response(
            {"response": [], "activity": [], "references": []},
            ReasoningEffort.LOW,
        )
        assert result["sources"] == []
        assert result["total"] == 0
        assert result["reasoning_effort"] == "low"

    def test_text_content_extracted(self):
        """Text content from response items is extracted."""
        tool = self._make_tool()
        response = {
            "response": [
                {
                    "content": [
                        {"type": "text", "text": "This is a document."},
                    ]
                }
            ],
            "activity": [],
            "references": [],
        }
        result = tool._parse_retrieve_response(response, ReasoningEffort.MINIMAL)
        assert len(result["sources"]) == 1
        assert result["sources"][0]["content"] == "This is a document."

    def test_json_extractive_data_parsed(self):
        """JSON text content (extractiveData format) is parsed into individual docs."""
        tool = self._make_tool()
        docs = [
            {"ref_id": "1", "content": "Doc A"},
            {"ref_id": "2", "content": "Doc B"},
        ]
        response = {
            "response": [
                {
                    "content": [
                        {"type": "text", "text": json.dumps(docs)},
                    ]
                }
            ],
            "activity": [],
            "references": [],
        }
        result = tool._parse_retrieve_response(response, ReasoningEffort.LOW)
        assert len(result["sources"]) == 2
        assert result["sources"][0]["ref_id"] == "1"
        assert result["sources"][1]["content"] == "Doc B"

    def test_reference_scores_merged(self):
        """Reranker scores from references are merged into matching sources."""
        tool = self._make_tool()
        docs = [{"ref_id": "1", "content": "Doc A"}]
        response = {
            "response": [{"content": [{"type": "text", "text": json.dumps(docs)}]}],
            "activity": [],
            "references": [{"id": "1", "rerankerScore": 0.95, "type": "indexDocument"}],
        }
        result = tool._parse_retrieve_response(response, ReasoningEffort.LOW)
        assert result["sources"][0]["reranker_score"] == 0.95
        assert result["sources"][0]["source_type"] == "indexDocument"

    def test_agentic_reasoning_activity(self):
        """Agentic reasoning activity is summarized correctly."""
        tool = self._make_tool()
        response = {
            "response": [],
            "activity": [
                {
                    "type": "agenticReasoning",
                    "retrievalReasoningEffort": {"kind": "medium"},
                    "reasoningTokens": 150,
                }
            ],
            "references": [],
        }
        result = tool._parse_retrieve_response(response, ReasoningEffort.MEDIUM)
        assert len(result["activity"]) == 1
        assert result["activity"][0]["type"] == "agenticReasoning"
        assert result["activity"][0]["reasoning_tokens"] == 150

    def test_search_index_activity(self):
        """Search index activity (e.g., SharePoint) is summarized."""
        tool = self._make_tool()
        response = {
            "response": [],
            "activity": [
                {
                    "type": "indexedSharePoint",
                    "knowledgeSourceName": "product-specs",
                    "count": 5,
                    "elapsedMs": 230,
                }
            ],
            "references": [],
        }
        result = tool._parse_retrieve_response(response, ReasoningEffort.LOW)
        assert result["activity"][0]["knowledge_source"] == "product-specs"
        assert result["activity"][0]["count"] == 5
        assert result["activity"][0]["elapsed_ms"] == 230

    def test_non_text_content_ignored(self):
        """Content items that aren't type='text' should be ignored."""
        tool = self._make_tool()
        response = {
            "response": [
                {
                    "content": [
                        {"type": "image", "url": "https://example.com/img.png"},
                        {"type": "text", "text": "Valid text"},
                    ]
                }
            ],
            "activity": [],
            "references": [],
        }
        result = tool._parse_retrieve_response(response, ReasoningEffort.LOW)
        assert len(result["sources"]) == 1
        assert result["sources"][0]["content"] == "Valid text"


# ============================================================================
# retrieve_formatted
# ============================================================================


class TestRetrieveFormatted:
    """Tests for AgenticRetrievalTool.retrieve_formatted."""

    @pytest.mark.asyncio
    async def test_error_result_returns_error_message(self):
        """When retrieve returns error, formatted message is returned."""
        tool = AgenticRetrievalTool(
            search_endpoint="https://search.windows.net",
            knowledge_base_name="kb",
        )
        with patch.object(tool, "retrieve", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = {"error": "Connection failed"}
            result = await tool.retrieve_formatted("test query")
            assert "エラー" in result

    @pytest.mark.asyncio
    async def test_no_sources_returns_not_found_message(self):
        """When no sources found, appropriate message is returned."""
        tool = AgenticRetrievalTool(
            search_endpoint="https://search.windows.net",
            knowledge_base_name="kb",
        )
        with patch.object(tool, "retrieve", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = {"sources": [], "activity": [], "reasoning_effort": "low"}
            result = await tool.retrieve_formatted("test query")
            assert "見つかりません" in result

    @pytest.mark.asyncio
    async def test_formatted_output_contains_citations(self):
        """Formatted output should contain ref citations and scores."""
        tool = AgenticRetrievalTool(
            search_endpoint="https://search.windows.net",
            knowledge_base_name="kb",
        )
        with patch.object(tool, "retrieve", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = {
                "sources": [
                    {"ref_id": "1", "content": "Product A specs", "reranker_score": 0.92},
                ],
                "activity": [],
                "reasoning_effort": "low",
            }
            result = await tool.retrieve_formatted("product specs")
            assert "ref_1" in result
            assert "0.92" in result
            assert "Product A specs" in result

    @pytest.mark.asyncio
    async def test_long_content_truncated(self):
        """Content longer than 2000 chars should be truncated."""
        tool = AgenticRetrievalTool(
            search_endpoint="https://search.windows.net",
            knowledge_base_name="kb",
        )
        with patch.object(tool, "retrieve", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = {
                "sources": [
                    {"ref_id": "1", "content": "x" * 3000, "reranker_score": 0.5},
                ],
                "activity": [],
                "reasoning_effort": "low",
            }
            result = await tool.retrieve_formatted("query")
            assert "(truncated)" in result


# ============================================================================
# agentic_knowledge_retrieve standalone function
# ============================================================================


class TestAgenticKnowledgeRetrieve:
    """Tests for the module-level agentic_knowledge_retrieve function."""

    @pytest.mark.asyncio
    async def test_returns_not_configured_without_env(self, monkeypatch):
        """Should return 'not configured' message when env vars are missing."""
        monkeypatch.delenv("AI_SEARCH_ENDPOINT", raising=False)
        monkeypatch.delenv("AI_SEARCH_KNOWLEDGE_BASE_NAME", raising=False)

        # Also mock the chat import to fail (no singleton available)
        with patch.dict("sys.modules", {"chat": None}):
            result = await agentic_knowledge_retrieve("test query")
            assert "設定されていません" in result

    @pytest.mark.asyncio
    async def test_invalid_reasoning_effort_defaults_to_low(self, monkeypatch):
        """Invalid reasoning effort string should default to 'low'."""
        monkeypatch.setenv("AI_SEARCH_ENDPOINT", "https://search.windows.net")
        monkeypatch.setenv("AI_SEARCH_KNOWLEDGE_BASE_NAME", "kb")

        mock_tool = MagicMock(spec=AgenticRetrievalTool)
        mock_tool.retrieve_formatted = AsyncMock(return_value="formatted result")
        mock_tool.close = AsyncMock()

        with (
            patch.dict("sys.modules", {"chat": None}),
            patch.object(AgenticRetrievalTool, "create_from_env", return_value=mock_tool),
        ):
            result = await agentic_knowledge_retrieve("query", reasoning_effort="ultra_high")
            assert result == "formatted result"
            # Verify close was called since we own the tool
            mock_tool.close.assert_called_once()
