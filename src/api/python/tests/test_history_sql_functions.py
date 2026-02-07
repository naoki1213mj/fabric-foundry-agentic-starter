"""
Tests for history_sql.py business logic functions.

Unlike test_history_sql.py (which tests mock structures), these tests
validate the *actual* functions in history_sql.py:
- track_event_if_configured
- SqlQueryTool (cache, connection, run_sql_query)
- generate_fallback_title / _generate_fallback_title_from_message
- get_conversations, get_conversation_messages (with mocked DB)
- delete_conversation, rename_conversation (authorization checks)
"""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import history_sql
from history_sql import (
    SqlQueryTool,
    _generate_fallback_title_from_message,
    generate_fallback_title,
    track_event_if_configured,
)

# ============================================================================
# track_event_if_configured
# ============================================================================


class TestTrackEventIfConfigured:
    """Tests for track_event_if_configured."""

    def test_skips_when_not_configured(self, monkeypatch):
        """Should not call track_event if APPLICATIONINSIGHTS_CONNECTION_STRING is empty."""
        monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
        with patch("history_sql.track_event") as mock_track:
            track_event_if_configured("test_event", {"key": "value"})
            mock_track.assert_not_called()

    def test_calls_track_event_when_configured(self, monkeypatch):
        """Should call track_event when connection string is set."""
        monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test-key")
        with patch("history_sql.track_event") as mock_track:
            track_event_if_configured("test_event", {"key": "value"})
            mock_track.assert_called_once_with("test_event", {"key": "value"})


# ============================================================================
# generate_fallback_title / _generate_fallback_title_from_message
# ============================================================================


class TestGenerateFallbackTitle:
    """Tests for generate_fallback_title."""

    def test_extracts_from_first_user_message(self):
        """Should use first user message to generate title."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "売上 TOP5 を教えてください"},
            {"role": "assistant", "content": "こちらが売上TOP5です..."},
        ]
        title = generate_fallback_title(messages)
        assert "売上" in title

    def test_returns_default_when_no_user_messages(self):
        """Should return 'New Conversation' when there are no user messages."""
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "assistant", "content": "Hello"},
        ]
        title = generate_fallback_title(messages)
        assert title == "New Conversation"

    def test_empty_messages_returns_default(self):
        """Should return 'New Conversation' for empty list."""
        assert generate_fallback_title([]) == "New Conversation"


class TestGenerateFallbackTitleFromMessage:
    """Tests for _generate_fallback_title_from_message."""

    def test_short_message_used_fully(self):
        """Short message (≤4 words) should be used as-is."""
        result = _generate_fallback_title_from_message("Hello World")
        assert result == "Hello World"

    def test_long_message_truncated_to_4_words(self):
        """Long message should be truncated to first 4 words."""
        result = _generate_fallback_title_from_message("one two three four five six")
        assert result == "one two three four"

    def test_empty_string_returns_default(self):
        """Empty string should return default title."""
        result = _generate_fallback_title_from_message("")
        assert result == "New Conversation"

    def test_none_returns_default(self):
        """None should return default title."""
        result = _generate_fallback_title_from_message(None)
        assert result == "New Conversation"

    def test_dict_content_converted_to_string(self):
        """Dict content should be stringified."""
        result = _generate_fallback_title_from_message({"text": "hello"})
        # Should produce something (not crash)
        assert isinstance(result, str)
        assert result != "New Conversation"

    def test_whitespace_only_returns_default(self):
        """Whitespace-only string should return default title."""
        result = _generate_fallback_title_from_message("   ")
        assert result == "New Conversation"


# ============================================================================
# SqlQueryTool
# ============================================================================


class TestSqlQueryTool:
    """Tests for SqlQueryTool with connection caching."""

    def test_create_with_connection_caches(self):
        """Connection should be stored in global cache."""
        mock_conn = MagicMock()
        tool = SqlQueryTool.create_with_connection(mock_conn)
        assert tool.connection_id != ""
        assert tool.get_connection() is mock_conn

    def test_get_connection_returns_none_for_invalid_id(self):
        """get_connection should return None for unknown connection_id."""
        tool = SqlQueryTool(connection_id="nonexistent-id")
        assert tool.get_connection() is None

    def test_close_connection_removes_from_cache(self):
        """close_connection should remove from cache and close."""
        mock_conn = MagicMock()
        tool = SqlQueryTool.create_with_connection(mock_conn)
        tool.close_connection()
        assert tool.get_connection() is None
        mock_conn.close.assert_called_once()

    def test_close_connection_nonexistent_noop(self):
        """close_connection on missing id should not raise."""
        tool = SqlQueryTool(connection_id="nonexistent-id")
        tool.close_connection()  # Should not raise

    @pytest.mark.asyncio
    async def test_run_sql_query_success(self):
        """Should return JSON list of rows for successful query."""
        mock_cursor = MagicMock()
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchall.return_value = [(1, "Alice"), (2, "Bob")]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        tool = SqlQueryTool.create_with_connection(mock_conn)
        result = await tool.run_sql_query("SELECT id, name FROM users")
        data = json.loads(result)
        assert len(data) == 2
        assert data[0]["name"] == "Alice"
        # Cleanup
        tool.close_connection()

    @pytest.mark.asyncio
    async def test_run_sql_query_no_connection(self):
        """Should return error when connection is not available."""
        tool = SqlQueryTool(connection_id="missing")
        result = await tool.run_sql_query("SELECT 1")
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_run_sql_query_handles_datetime(self):
        """datetime values should be converted to ISO format."""
        mock_cursor = MagicMock()
        mock_cursor.description = [("created_at",)]
        dt = datetime(2026, 2, 7, 10, 30, 0)
        mock_cursor.fetchall.return_value = [(dt,)]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        tool = SqlQueryTool.create_with_connection(mock_conn)
        result = await tool.run_sql_query("SELECT created_at FROM t")
        data = json.loads(result)
        assert data[0]["created_at"] == "2026-02-07T10:30:00"
        tool.close_connection()

    @pytest.mark.asyncio
    async def test_run_sql_query_handles_decimal(self):
        """Decimal values should be converted to float."""
        mock_cursor = MagicMock()
        mock_cursor.description = [("amount",)]
        mock_cursor.fetchall.return_value = [(Decimal("123.45"),)]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        tool = SqlQueryTool.create_with_connection(mock_conn)
        result = await tool.run_sql_query("SELECT amount FROM t")
        data = json.loads(result)
        assert data[0]["amount"] == 123.45
        tool.close_connection()

    @pytest.mark.asyncio
    async def test_run_sql_query_error_returns_json(self):
        """Query errors should return error JSON, not raise."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Table not found")

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        tool = SqlQueryTool.create_with_connection(mock_conn)
        result = await tool.run_sql_query("SELECT * FROM nonexistent")
        data = json.loads(result)
        assert "error" in data
        assert "Table not found" in data["error"]
        tool.close_connection()


# ============================================================================
# get_conversations (with mocked DB layer)
# ============================================================================


class TestGetConversations:
    """Tests for get_conversations function."""

    @pytest.mark.asyncio
    async def test_returns_conversations_for_user(self):
        """Should return list of conversations for a user."""
        mock_result = [
            {
                "conversation_id": "c1",
                "title": "Chat 1",
                "createdAt": "2026-01-01",
                "updatedAt": "2026-01-02",
            },
        ]
        with patch(
            "history_sql.run_query_params", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await history_sql.get_conversations("user-1", limit=10)
            assert len(result) == 1
            assert result[0]["conversation_id"] == "c1"

    @pytest.mark.asyncio
    async def test_returns_all_conversations_without_user(self):
        """Without user_id, should query without user filter."""
        with patch(
            "history_sql.run_query_params", new_callable=AsyncMock, return_value=[]
        ) as mock_run:
            result = await history_sql.get_conversations(None, limit=10)
            assert result == []
            # Check that query does NOT contain "userId = ?"
            call_args = mock_run.call_args
            assert "userId = ?" not in call_args[0][0]


# ============================================================================
# get_conversation_messages (citation deserialization)
# ============================================================================


class TestGetConversationMessages:
    """Tests for get_conversation_messages citation processing."""

    @pytest.mark.asyncio
    async def test_returns_none_without_conversation_id(self):
        """Should return None if conversation_id is empty."""
        result = await history_sql.get_conversation_messages("user-1", "")
        assert result is None

    @pytest.mark.asyncio
    async def test_deserializes_citations_json(self):
        """Citations stored as JSON string should be deserialized."""
        citations_json = json.dumps([{"url": "https://example.com", "title": "Test"}])
        mock_result = [
            {
                "role": "assistant",
                "content": "Answer text",
                "citations": citations_json,
                "feedback": None,
            },
        ]
        with patch(
            "history_sql.run_query_params", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await history_sql.get_conversation_messages("user-1", "conv-1")
            assert isinstance(result[0]["citations"], list)
            assert result[0]["citations"][0]["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_empty_citations_becomes_empty_list(self):
        """Empty/null citations should become empty list."""
        mock_result = [
            {"role": "user", "content": "Hello", "citations": None, "feedback": None},
        ]
        with patch(
            "history_sql.run_query_params", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await history_sql.get_conversation_messages("user-1", "conv-1")
            assert result[0]["citations"] == []

    @pytest.mark.asyncio
    async def test_invalid_citations_json_becomes_empty_list(self):
        """Invalid JSON in citations should fallback to empty list."""
        mock_result = [
            {
                "role": "assistant",
                "content": "text",
                "citations": "not valid json{",
                "feedback": None,
            },
        ]
        with patch(
            "history_sql.run_query_params", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await history_sql.get_conversation_messages("user-1", "conv-1")
            assert result[0]["citations"] == []


# ============================================================================
# delete_conversation (authorization checks)
# ============================================================================


class TestDeleteConversation:
    """Tests for delete_conversation authorization and flow."""

    @pytest.mark.asyncio
    async def test_returns_false_without_conversation_id(self):
        """Should return False when conversation_id is empty."""
        result = await history_sql.delete_conversation("user-1", "")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_conversation_not_found(self):
        """Should return False when conversation doesn't exist."""
        with patch("history_sql.run_query_params", new_callable=AsyncMock, return_value=[]):
            result = await history_sql.delete_conversation("user-1", "nonexistent")
            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_user_not_authorized(self):
        """Should return False when user doesn't own the conversation."""
        with patch(
            "history_sql.run_query_params",
            new_callable=AsyncMock,
            return_value=[{"userId": "other-user", "conversation_id": "conv-1"}],
        ):
            result = await history_sql.delete_conversation("user-1", "conv-1")
            assert result is False

    @pytest.mark.asyncio
    async def test_deletes_messages_and_conversation(self):
        """Should delete messages first, then conversation, and return True."""
        with (
            patch(
                "history_sql.run_query_params",
                new_callable=AsyncMock,
                return_value=[{"userId": "user-1", "conversation_id": "conv-1"}],
            ),
            patch("history_sql.run_nonquery_params", new_callable=AsyncMock) as mock_nonquery,
        ):
            result = await history_sql.delete_conversation("user-1", "conv-1")
            assert result is True
            # Should be called twice: once for messages, once for conversation
            assert mock_nonquery.call_count == 2


# ============================================================================
# rename_conversation (validation)
# ============================================================================


class TestRenameConversation:
    """Tests for rename_conversation validation and authorization."""

    @pytest.mark.asyncio
    async def test_raises_on_empty_conversation_id(self):
        """Should raise ValueError when conversation_id is empty."""
        # The function catches the ValueError and returns False
        result = await history_sql.rename_conversation("user-1", "", "New Title")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_title_is_none(self):
        """Should return False when title is None."""
        result = await history_sql.rename_conversation("user-1", "conv-1", None)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_conversation_not_found(self):
        """Should return False when conversation doesn't exist."""
        with patch("history_sql.run_query_params", new_callable=AsyncMock, return_value=[]):
            result = await history_sql.rename_conversation("user-1", "conv-1", "Title")
            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_user_not_authorized(self):
        """Should return False when user doesn't own the conversation."""
        with patch(
            "history_sql.run_query_params",
            new_callable=AsyncMock,
            return_value=[{"userId": "other-user", "conversation_id": "conv-1"}],
        ):
            result = await history_sql.rename_conversation("user-1", "conv-1", "Title")
            assert result is False

    @pytest.mark.asyncio
    async def test_renames_successfully(self):
        """Should update title and return True for authorized user."""
        with (
            patch(
                "history_sql.run_query_params",
                new_callable=AsyncMock,
                return_value=[{"userId": "user-1", "conversation_id": "conv-1"}],
            ),
            patch("history_sql.run_nonquery_params", new_callable=AsyncMock) as mock_nonquery,
        ):
            result = await history_sql.rename_conversation("user-1", "conv-1", "New Title")
            assert result is True
            mock_nonquery.assert_called_once()
            # Verify the title was passed
            call_args = mock_nonquery.call_args
            assert "New Title" in call_args[0][1]
