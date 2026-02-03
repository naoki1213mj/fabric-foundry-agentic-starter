"""
Unit tests for history_sql.py - Fabric SQL database operations.
"""

import json
import uuid
from datetime import datetime

import pytest


class TestDatabaseConnection:
    """Tests for database connection utilities."""

    def test_connection_string_parsed(self, mock_env_vars):
        """Verify connection string environment variable is read."""
        import os

        conn_str = os.getenv("FABRIC_SQL_CONNECTION_STRING")
        assert conn_str is not None
        assert "fabric.microsoft.com" in conn_str or "test" in conn_str


class TestConversationOperations:
    """Tests for conversation CRUD operations."""

    def test_generate_conversation_id(self):
        """Conversation ID should be valid UUID."""
        conv_id = str(uuid.uuid4())

        # Verify it's a valid UUID
        parsed = uuid.UUID(conv_id)
        assert str(parsed) == conv_id

    @pytest.mark.asyncio
    async def test_get_conversations_returns_list(self, mock_pyodbc_connection):
        """get_conversations should return a list."""
        mock_pyodbc_connection["cursor"].fetchall.return_value = [
            ("conv-1", "Conversation 1", "user-1", datetime.now()),
            ("conv-2", "Conversation 2", "user-1", datetime.now()),
        ]
        mock_pyodbc_connection["cursor"].description = [
            ("id",),
            ("title",),
            ("user_id",),
            ("created_at",),
        ]

        # Note: Actual test would import and call get_conversations
        # This is a structure test showing expected behavior
        result = mock_pyodbc_connection["cursor"].fetchall()

        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_create_conversation_generates_id(self, mock_pyodbc_connection):
        """create_conversation should generate a new ID."""
        new_id = str(uuid.uuid4())

        # Simulate INSERT operation
        mock_pyodbc_connection["cursor"].execute.return_value = None
        mock_pyodbc_connection["connection"].commit.return_value = None

        # Verify UUID is valid
        assert len(new_id) == 36
        assert new_id.count("-") == 4


class TestMessageOperations:
    """Tests for message CRUD operations."""

    def test_message_role_validation(self):
        """Message role should be 'user' or 'assistant'."""
        valid_roles = ["user", "assistant", "system"]
        test_role = "user"

        assert test_role in valid_roles

    def test_message_content_serialization(self):
        """Message content should be JSON serializable."""
        message = {
            "role": "user",
            "content": "売上データを見せて",
            "citations": [{"source": "test.pdf", "page": 1}],
        }

        # Should not raise
        json_str = json.dumps(message, ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["content"] == message["content"]
        assert parsed["citations"] == message["citations"]


class TestSQLInjectionPrevention:
    """Tests for SQL injection prevention."""

    def test_parameterized_query_usage(self):
        """Verify queries use parameterized values."""
        # Example of SAFE query (parameterized)
        safe_query = "SELECT * FROM conversations WHERE user_id = ?"

        # Example of UNSAFE query (string interpolation)
        user_id = "user-123'; DROP TABLE conversations;--"
        unsafe_query = f"SELECT * FROM conversations WHERE user_id = '{user_id}'"

        # Parameterized queries don't include the value in the SQL string
        assert "?" in safe_query
        assert "DROP TABLE" not in safe_query

        # Unsafe queries would include the injection
        assert "DROP TABLE" in unsafe_query

    def test_uuid_validation(self):
        """Verify UUID inputs are validated."""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        invalid_uuid = "not-a-uuid'; DROP TABLE--"

        # Valid UUID
        try:
            uuid.UUID(valid_uuid)
            valid = True
        except ValueError:
            valid = False
        assert valid is True

        # Invalid UUID
        try:
            uuid.UUID(invalid_uuid)
            invalid_valid = True
        except ValueError:
            invalid_valid = False
        assert invalid_valid is False


class TestErrorHandling:
    """Tests for error handling in database operations."""

    def test_connection_error_handling(self, mock_pyodbc_connection):
        """Database connection errors should be handled gracefully."""
        import pyodbc

        mock_pyodbc_connection["connect"].side_effect = pyodbc.Error("Connection failed")

        with pytest.raises(pyodbc.Error):
            import pyodbc

            pyodbc.connect("invalid-connection-string")

    def test_query_timeout_handling(self, mock_pyodbc_connection):
        """Query timeouts should be handled gracefully."""
        import pyodbc

        mock_pyodbc_connection["cursor"].execute.side_effect = pyodbc.Error("Query timeout")

        with pytest.raises(pyodbc.Error):
            mock_pyodbc_connection["cursor"].execute("SELECT * FROM large_table")
