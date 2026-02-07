"""
Tests for SqlAgentHandler (agents/sql_agent.py).

Covers:
- Initialization and connection handling
- SQL query execution with type conversion
- Error handling (no connection, query failure)
- get_tools method
"""

import json
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from agents.sql_agent import SqlAgentHandler


class TestSqlAgentInit:
    """Tests for SqlAgentHandler initialization."""

    def test_init_stores_connection(self):
        """Connection object is stored on init."""
        mock_conn = MagicMock()
        handler = SqlAgentHandler(mock_conn)
        assert handler.conn is mock_conn

    def test_init_with_none_connection(self):
        """None connection is accepted at init time."""
        handler = SqlAgentHandler(None)
        assert handler.conn is None


class TestSqlAgentRunQuery:
    """Tests for SqlAgentHandler.run_sql_query."""

    @pytest.mark.asyncio
    async def test_returns_error_when_no_connection(self):
        """Should return error JSON when connection is None."""
        handler = SqlAgentHandler(None)
        result = await handler.run_sql_query("SELECT 1")
        data = json.loads(result)
        assert "error" in data
        assert "not available" in data["error"]

    @pytest.mark.asyncio
    async def test_basic_query_returns_json(self):
        """Should return list of row dicts for a normal query."""
        mock_cursor = MagicMock()
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchall.return_value = [(1, "Alice"), (2, "Bob")]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        handler = SqlAgentHandler(mock_conn)
        result = await handler.run_sql_query("SELECT id, name FROM users")
        data = json.loads(result)

        assert len(data) == 2
        assert data[0] == {"id": 1, "name": "Alice"}
        assert data[1] == {"id": 2, "name": "Bob"}

    @pytest.mark.asyncio
    async def test_empty_result_set(self):
        """Should return empty list for query with no rows."""
        mock_cursor = MagicMock()
        mock_cursor.description = [("id",)]
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        handler = SqlAgentHandler(mock_conn)
        result = await handler.run_sql_query("SELECT id FROM empty_table")
        data = json.loads(result)
        assert data == []

    @pytest.mark.asyncio
    async def test_none_values_preserved(self):
        """NULL values should be preserved as None/null in JSON."""
        mock_cursor = MagicMock()
        mock_cursor.description = [("id",), ("value",)]
        mock_cursor.fetchall.return_value = [(1, None)]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        handler = SqlAgentHandler(mock_conn)
        result = await handler.run_sql_query("SELECT id, value FROM t")
        data = json.loads(result)
        assert data[0]["value"] is None

    @pytest.mark.asyncio
    async def test_non_primitive_types_converted_to_string(self):
        """Non-primitive types (e.g., Decimal, bytes) should be str-converted."""
        mock_cursor = MagicMock()
        mock_cursor.description = [("amount",), ("data",)]
        mock_cursor.fetchall.return_value = [(Decimal("99.99"), b"\x00\x01")]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        handler = SqlAgentHandler(mock_conn)
        result = await handler.run_sql_query("SELECT amount, data FROM t")
        data = json.loads(result)
        assert data[0]["amount"] == "99.99"
        assert isinstance(data[0]["data"], str)

    @pytest.mark.asyncio
    async def test_query_execution_error_returns_error_json(self):
        """Query execution failures should return error JSON, not raise."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Syntax error near 'SELEC'")

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        handler = SqlAgentHandler(mock_conn)
        result = await handler.run_sql_query("SELEC 1")
        data = json.loads(result)
        assert "error" in data
        assert "Syntax error" in data["error"]

    @pytest.mark.asyncio
    async def test_cursor_closed_after_query(self):
        """Cursor should be closed after successful query."""
        mock_cursor = MagicMock()
        mock_cursor.description = [("x",)]
        mock_cursor.fetchall.return_value = [(1,)]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        handler = SqlAgentHandler(mock_conn)
        await handler.run_sql_query("SELECT 1 AS x")
        mock_cursor.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_japanese_content_preserved(self):
        """Japanese characters should be preserved (ensure_ascii=False)."""
        mock_cursor = MagicMock()
        mock_cursor.description = [("商品名",)]
        mock_cursor.fetchall.return_value = [("テスト商品",)]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        handler = SqlAgentHandler(mock_conn)
        result = await handler.run_sql_query("SELECT 商品名 FROM products")
        assert "テスト商品" in result
        data = json.loads(result)
        assert data[0]["商品名"] == "テスト商品"


class TestSqlAgentGetTools:
    """Tests for SqlAgentHandler.get_tools."""

    def test_returns_list_of_callables(self):
        """get_tools should return a list containing run_sql_query."""
        handler = SqlAgentHandler(MagicMock())
        tools = handler.get_tools()
        assert isinstance(tools, list)
        assert len(tools) == 1

    def test_tool_is_run_sql_query(self):
        """The tool should be the bound run_sql_query method."""
        handler = SqlAgentHandler(MagicMock())
        tools = handler.get_tools()
        assert tools[0].__name__ == "run_sql_query"
