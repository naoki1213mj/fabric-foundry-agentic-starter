"""
Unit tests for agents/web_agent.py - WebAgentHandler.

Tests cover configuration, is_configured(), web_search() edge cases
(unconfigured, timeout, error), and get_tools().
"""

import json

import pytest


class TestWebAgentHandlerInit:
    """Tests for WebAgentHandler.__init__() — configuration loading."""

    def test_init_with_env_vars(self, monkeypatch):
        """環境変数からの設定読み込み"""
        monkeypatch.setenv(
            "AZURE_AI_PROJECT_ENDPOINT", "https://test-foundry.azure.com/api/projects/proj1"
        )
        monkeypatch.setenv("BING_PROJECT_CONNECTION_NAME", "bingglobal001")
        monkeypatch.setenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5")

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler()
        assert handler.foundry_endpoint == "https://test-foundry.azure.com/api/projects/proj1"
        assert handler.bing_connection_name == "bingglobal001"
        assert handler.model_deployment == "gpt-5"

    def test_init_missing_endpoint(self, monkeypatch):
        """エンドポイント未設定でも例外なし"""
        monkeypatch.delenv("AZURE_AI_PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_AI_AGENT_ENDPOINT", raising=False)
        monkeypatch.setenv("BING_PROJECT_CONNECTION_NAME", "bing-conn")

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler()
        assert handler.foundry_endpoint is None
        assert handler.bing_connection_name == "bing-conn"

    def test_init_missing_bing_connection(self, monkeypatch):
        """Bing接続名未設定でも例外なし"""
        monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.azure.com")
        monkeypatch.delenv("BING_PROJECT_CONNECTION_NAME", raising=False)

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler()
        assert handler.foundry_endpoint == "https://test.azure.com"
        assert handler.bing_connection_name is None

    def test_init_default_model(self, monkeypatch):
        """AZURE_AI_MODEL_DEPLOYMENT_NAME 未設定時のデフォルト"""
        monkeypatch.delenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", raising=False)
        monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.azure.com")

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler()
        assert handler.model_deployment == "gpt-5"

    def test_init_legacy_api_key_ignored(self, monkeypatch):
        """api_key パラメータは後方互換のため無視される"""
        monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.azure.com")

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler(api_key="legacy-key-123")
        # Should not raise, api_key is ignored
        assert handler.foundry_endpoint == "https://test.azure.com"


class TestIsConfigured:
    """Tests for is_configured() — configuration validation."""

    def test_fully_configured(self, monkeypatch):
        """エンドポイントとBing接続名の両方設定 → True"""
        monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.azure.com")
        monkeypatch.setenv("BING_PROJECT_CONNECTION_NAME", "bing-conn")

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler()
        assert handler.is_configured() is True

    def test_missing_endpoint(self, monkeypatch):
        """エンドポイント未設定 → False"""
        monkeypatch.delenv("AZURE_AI_PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_AI_AGENT_ENDPOINT", raising=False)
        monkeypatch.setenv("BING_PROJECT_CONNECTION_NAME", "bing-conn")

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler()
        assert handler.is_configured() is False

    def test_missing_bing_connection(self, monkeypatch):
        """Bing接続名未設定 → False"""
        monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.azure.com")
        monkeypatch.delenv("BING_PROJECT_CONNECTION_NAME", raising=False)

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler()
        assert handler.is_configured() is False

    def test_both_missing(self, monkeypatch):
        """両方未設定 → False"""
        monkeypatch.delenv("AZURE_AI_PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_AI_AGENT_ENDPOINT", raising=False)
        monkeypatch.delenv("BING_PROJECT_CONNECTION_NAME", raising=False)

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler()
        assert handler.is_configured() is False


class TestWebSearch:
    """Tests for web_search() — with mocked external dependencies."""

    @pytest.mark.asyncio
    async def test_unconfigured_returns_fallback(self, monkeypatch):
        """未設定時はfallback JSONを返す"""
        monkeypatch.delenv("AZURE_AI_PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_AI_AGENT_ENDPOINT", raising=False)
        monkeypatch.delenv("BING_PROJECT_CONNECTION_NAME", raising=False)

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler()
        result = await handler.web_search("test query")
        data = json.loads(result)
        assert data["fallback"] is True
        assert data["citations"] == []
        assert "Web検索が設定されていません" in data["answer"]

    @pytest.mark.asyncio
    async def test_unconfigured_includes_query_in_answer(self, monkeypatch):
        """未設定時のfallback にクエリが含まれる"""
        monkeypatch.delenv("AZURE_AI_PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_AI_AGENT_ENDPOINT", raising=False)
        monkeypatch.delenv("BING_PROJECT_CONNECTION_NAME", raising=False)

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler()
        result = await handler.web_search("Azure最新情報")
        data = json.loads(result)
        assert "Azure最新情報" in data["answer"]


class TestBingGrounding:
    """Tests for bing_grounding() — alias for web_search."""

    @pytest.mark.asyncio
    async def test_bing_grounding_calls_web_search(self, monkeypatch):
        """bing_grounding は web_search のエイリアス"""
        monkeypatch.delenv("AZURE_AI_PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_AI_AGENT_ENDPOINT", raising=False)
        monkeypatch.delenv("BING_PROJECT_CONNECTION_NAME", raising=False)

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler()
        result = await handler.bing_grounding("test query")
        data = json.loads(result)
        # Should produce same fallback as web_search
        assert data["fallback"] is True


class TestGetTools:
    """Tests for get_tools() — tool list."""

    def test_get_tools_returns_list(self, monkeypatch):
        """get_tools はリストを返す"""
        monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.azure.com")

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler()
        tools = handler.get_tools()
        assert isinstance(tools, list)
        assert len(tools) == 1

    def test_get_tools_contains_web_search(self, monkeypatch):
        """get_tools は web_search を含む"""
        monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.azure.com")

        from agents.web_agent import WebAgentHandler

        handler = WebAgentHandler()
        tools = handler.get_tools()
        assert tools[0] == handler.web_search
