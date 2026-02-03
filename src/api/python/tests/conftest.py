"""
Pytest configuration and fixtures for Python API unit tests.

This file is automatically loaded by pytest and provides:
- Environment setup for testing
- Mock fixtures for Azure services
- Common test utilities
"""

import os
import sys
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Environment Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch) -> None:
    """
    Set up required environment variables for testing.
    This fixture runs automatically for all tests.
    """
    env_vars = {
        # Azure AI Foundry
        "AZURE_AI_AGENT_ENDPOINT": "https://test-foundry.openai.azure.com/",
        "AZURE_OPENAI_ENDPOINT": "https://test-openai.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test-key-12345",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
        # Agent Configuration
        "AGENT_NAME_TITLE": "Test Agent",
        "AGENT_MODE": "multi_tool",
        "MULTI_AGENT_MODE": "false",
        # Database (Fabric SQL)
        "FABRIC_SQL_CONNECTION_STRING": "Driver={ODBC Driver 18 for SQL Server};Server=test.database.fabric.microsoft.com;Database=testdb;Encrypt=yes;TrustServerCertificate=no;",
        # Application Insights (disabled for tests)
        "APPLICATIONINSIGHTS_CONNECTION_STRING": "",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)


# ============================================================================
# Mock Fixtures for Azure Services
# ============================================================================


@pytest.fixture
def mock_azure_credential():
    """Mock Azure DefaultAzureCredential."""
    with patch("azure.identity.DefaultAzureCredential") as mock:
        mock_credential = MagicMock()
        mock_credential.get_token.return_value = MagicMock(token="test-token")
        mock.return_value = mock_credential
        yield mock_credential


@pytest.fixture
def mock_azure_credential_async():
    """Mock async Azure credential."""
    with patch("auth.azure_credential_utils.get_azure_credential_async") as mock:
        mock_credential = AsyncMock()
        mock_credential.get_token = AsyncMock(return_value=MagicMock(token="test-token"))
        mock.return_value = mock_credential
        yield mock_credential


@pytest.fixture
def mock_pyodbc_connection():
    """Mock pyodbc database connection for Fabric SQL."""
    with patch("pyodbc.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Default: return empty results
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = None
        mock_cursor.description = []

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        yield {
            "connect": mock_connect,
            "connection": mock_conn,
            "cursor": mock_cursor,
        }


@pytest.fixture
def mock_chat_agent():
    """Mock ChatAgent for testing chat functionality."""
    with patch("agent_framework.ChatAgent") as mock:
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value="Test response")
        mock.return_value = mock_agent
        yield mock_agent


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """
    Create a FastAPI test client for API endpoint testing.

    Note: This fixture imports app lazily to avoid import errors
    when environment variables are not set.
    """
    # Import after env vars are set
    from app import build_app

    app = build_app()
    with TestClient(app) as client:
        yield client


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_conversation():
    """Sample conversation data for testing."""
    return {
        "id": "test-conv-123",
        "title": "テスト会話",
        "user_id": "user-456",
        "created_at": "2026-02-03T10:00:00Z",
    }


@pytest.fixture
def sample_message():
    """Sample message data for testing."""
    return {
        "id": "test-msg-789",
        "conversation_id": "test-conv-123",
        "role": "user",
        "content": "売上データを見せてください",
        "created_at": "2026-02-03T10:01:00Z",
    }


@pytest.fixture
def sample_chat_request():
    """Sample chat request payload."""
    return {
        "conversation_id": "test-conv-123",
        "messages": [{"role": "user", "content": "売上TOP5を教えてください"}],
    }
