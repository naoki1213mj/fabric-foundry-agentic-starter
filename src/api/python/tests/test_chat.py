"""
Unit tests for chat.py - Core chat module.

Tests cover pure functions, ContextVar management, endpoint URL logic,
input validation, and demo mode responses.
"""

import json


class TestCreateToolEvent:
    """Tests for create_tool_event() — pure function generating JSON markers."""

    def test_basic_tool_event(self):
        """正常系: started ステータスのツールイベント生成"""
        from chat import create_tool_event

        result = create_tool_event("run_sql_query", "started")
        assert result.startswith("__TOOL_EVENT__")
        assert result.endswith("__END_TOOL_EVENT__")
        payload = json.loads(
            result.removeprefix("__TOOL_EVENT__").removesuffix("__END_TOOL_EVENT__")
        )
        assert payload["type"] == "tool_event"
        assert payload["tool"] == "run_sql_query"
        assert payload["status"] == "started"
        assert "timestamp" in payload
        assert "message" not in payload

    def test_tool_event_with_message(self):
        """メッセージ付きのツールイベント"""
        from chat import create_tool_event

        result = create_tool_event("search_documents", "completed", "3件取得しました")
        payload = json.loads(
            result.removeprefix("__TOOL_EVENT__").removesuffix("__END_TOOL_EVENT__")
        )
        assert payload["message"] == "3件取得しました"
        assert payload["tool"] == "search_documents"
        assert payload["status"] == "completed"

    def test_tool_event_error_status(self):
        """error ステータスのツールイベント"""
        from chat import create_tool_event

        result = create_tool_event("search_web", "error", "Timeout")
        payload = json.loads(
            result.removeprefix("__TOOL_EVENT__").removesuffix("__END_TOOL_EVENT__")
        )
        assert payload["status"] == "error"
        assert payload["message"] == "Timeout"

    def test_tool_event_none_message_excluded(self):
        """message=None の場合は JSON に message キーなし"""
        from chat import create_tool_event

        result = create_tool_event("run_sql_query", "started", None)
        payload = json.loads(
            result.removeprefix("__TOOL_EVENT__").removesuffix("__END_TOOL_EVENT__")
        )
        assert "message" not in payload

    def test_tool_event_json_is_valid(self):
        """JSON として valid であること"""
        from chat import create_tool_event

        result = create_tool_event("test_tool", "completed", "日本語メッセージ")
        inner = result.removeprefix("__TOOL_EVENT__").removesuffix("__END_TOOL_EVENT__")
        parsed = json.loads(inner)
        assert isinstance(parsed, dict)


class TestSelectAgentMode:
    """Tests for select_agent_mode() — query-based mode selection."""

    def test_greeting_returns_sql_only(self):
        """挨拶クエリ → sql_only"""
        from chat import select_agent_mode

        assert select_agent_mode("こんにちは") == "sql_only"
        assert select_agent_mode("hello") == "sql_only"
        assert select_agent_mode("ありがとう") == "sql_only"

    def test_simple_sql_query_returns_sql_only(self):
        """単純なSQL系クエリ → sql_only"""
        from chat import select_agent_mode

        assert select_agent_mode("売上TOP5を見せて") == "sql_only"
        assert select_agent_mode("顧客一覧を出して") == "sql_only"
        assert select_agent_mode("注文何件ある？") == "sql_only"

    def test_complex_query_returns_multi_tool(self):
        """複合クエリ → multi_tool"""
        from chat import select_agent_mode

        assert select_agent_mode("売上データとスペックを比較して") == "multi_tool"
        assert select_agent_mode("最新のトレンドを教えて") == "multi_tool"

    def test_general_query_returns_multi_tool(self):
        """汎用クエリ → multi_tool (デフォルト)"""
        from chat import select_agent_mode

        assert select_agent_mode("製品について教えてください") == "multi_tool"
        assert select_agent_mode("Why is revenue declining?") == "multi_tool"


class TestIsChartRequest:
    """Tests for is_chart_request() — chart keyword detection."""

    def test_japanese_chart_keywords(self):
        """日本語チャートキーワード検出"""
        from chat import is_chart_request

        assert is_chart_request("売上をグラフで見せて") is True
        assert is_chart_request("チャートを作成して") is True
        assert is_chart_request("円グラフで表示") is True
        assert is_chart_request("折れ線グラフで") is True

    def test_english_chart_keywords(self):
        """英語チャートキーワード検出"""
        from chat import is_chart_request

        assert is_chart_request("Show me a chart") is True
        assert is_chart_request("Visualize the data") is True
        assert is_chart_request("plot a graph") is True

    def test_non_chart_queries(self):
        """チャート以外のクエリ → False"""
        from chat import is_chart_request

        assert is_chart_request("売上TOP5を教えて") is False
        assert is_chart_request("顧客分析をして") is False
        assert is_chart_request("hello") is False


class TestGetDemoResponse:
    """Tests for get_demo_response() — demo mode response generation."""

    def test_basic_demo_response(self):
        """通常クエリの DEMO レスポンス"""
        from chat import get_demo_response

        text, events, reasoning = get_demo_response("売上を教えて")
        assert "トップ3" in text or "Adventure" in text
        assert isinstance(events, list)
        assert reasoning is not None

    def test_chart_demo_response(self):
        """チャートクエリの DEMO レスポンス → JSON 形式"""
        from chat import get_demo_response

        text, events, reasoning = get_demo_response("売上をグラフで見せて")
        parsed = json.loads(text)
        assert parsed["type"] == "bar"
        assert "datasets" in parsed["data"]
        assert len(events) >= 2  # started + completed

    def test_demo_response_returns_tuple(self):
        """戻り値は (str, list, str|None) のタプル"""
        from chat import get_demo_response

        result = get_demo_response("テスト")
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], str)
        assert isinstance(result[1], list)


class TestBuildQueryWithHistory:
    """Tests for _build_query_with_history() — pure function."""

    def test_no_history(self):
        """履歴なし → クエリそのまま"""
        from chat import _build_query_with_history

        result = _build_query_with_history("売上は？", [])
        assert result == "売上は？"

    def test_with_history(self):
        """履歴あり → フォーマット付きクエリ"""
        from chat import _build_query_with_history

        history = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "お手伝いします"},
        ]
        result = _build_query_with_history("売上TOP5は？", history)
        assert "会話履歴" in result
        assert "USER: こんにちは" in result
        assert "ASSISTANT: お手伝いします" in result
        assert "売上TOP5は？" in result

    def test_with_empty_list(self):
        """空リスト → クエリそのまま"""
        from chat import _build_query_with_history

        result = _build_query_with_history("test", [])
        assert result == "test"


class TestContextVarManagement:
    """Tests for ContextVar-based state: reasoning effort, model params, citations."""

    def test_reasoning_effort_default(self):
        """デフォルト reasoning effort → 'low'"""
        from chat import get_reasoning_effort

        assert get_reasoning_effort() == "low"

    def test_set_and_get_reasoning_effort(self):
        """reasoning effort のセットと取得"""
        from chat import get_reasoning_effort, set_reasoning_effort

        set_reasoning_effort("medium")
        assert get_reasoning_effort() == "medium"
        # Restore default
        set_reasoning_effort("low")

    def test_model_params_default(self):
        """デフォルト model params"""
        from chat import get_model_params

        params = get_model_params()
        assert isinstance(params, dict)
        assert "model" in params
        assert "model_reasoning_effort" in params
        assert "reasoning_summary" in params
        assert "temperature" in params

    def test_set_and_get_model_params(self):
        """model params のセットと取得"""
        from chat import get_model_params, set_model_params

        set_model_params("gpt-5", "high", "detailed", 0.5)
        params = get_model_params()
        assert params["model"] == "gpt-5"
        assert params["model_reasoning_effort"] == "high"
        assert params["reasoning_summary"] == "detailed"
        assert params["temperature"] == 0.5

    def test_web_citations_default(self):
        """デフォルト web citations → 空リスト"""
        from chat import get_web_citations

        citations = get_web_citations()
        assert isinstance(citations, list)

    def test_set_and_get_web_citations(self):
        """web citations のセットと取得"""
        from chat import get_web_citations, set_web_citations

        test_citations = [{"url": "https://example.com", "title": "Test"}]
        set_web_citations(test_citations)
        assert get_web_citations() == test_citations
        # Cleanup
        set_web_citations([])


class TestEndpointURLLogic:
    """Tests for get_openai_endpoint() and get_responses_api_base_url()."""

    def test_get_openai_endpoint_direct(self, monkeypatch):
        """APIM 未使用時は直接エンドポイントを返す"""
        import chat

        monkeypatch.setattr(chat, "USE_APIM_GATEWAY", False)
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://direct.openai.azure.com/")
        result = chat.get_openai_endpoint()
        assert result == "https://direct.openai.azure.com/"

    def test_get_openai_endpoint_apim(self, monkeypatch):
        """APIM 使用時は Gateway URL を返す"""
        import chat

        monkeypatch.setattr(chat, "USE_APIM_GATEWAY", True)
        monkeypatch.setattr(chat, "APIM_GATEWAY_URL", "https://apim.azure-api.net/openai")
        result = chat.get_openai_endpoint()
        assert result == "https://apim.azure-api.net/openai"

    def test_get_responses_api_base_url_configured(self, monkeypatch):
        """AZURE_OPENAI_BASE_URL 設定時は正規化された URL を返す"""
        import chat

        monkeypatch.setattr(
            chat, "AZURE_OPENAI_BASE_URL", "https://apim.azure-api.net/foundry-openai/openai/v1"
        )
        result = chat.get_responses_api_base_url()
        assert result is not None
        assert result.endswith("/")

    def test_get_responses_api_base_url_with_trailing_slash(self, monkeypatch):
        """末尾 / 付きの URL"""
        import chat

        monkeypatch.setattr(
            chat, "AZURE_OPENAI_BASE_URL", "https://apim.azure-api.net/foundry-openai/openai/v1/"
        )
        result = chat.get_responses_api_base_url()
        assert result == "https://apim.azure-api.net/foundry-openai/openai/v1/"

    def test_get_responses_api_base_url_not_configured(self, monkeypatch):
        """AZURE_OPENAI_BASE_URL 未設定時は None"""
        import chat

        monkeypatch.setattr(chat, "AZURE_OPENAI_BASE_URL", "")
        result = chat.get_responses_api_base_url()
        assert result is None


class TestBuildReasoningOptions:
    """Tests for _build_reasoning_options() — reasoning configuration builder."""

    def test_non_gpt5_returns_empty(self):
        """GPT-5 以外のモデルでは空 dict"""
        from chat import _build_reasoning_options, set_model_params

        set_model_params("gpt-4o-mini", "", "", 0.7)
        result = _build_reasoning_options()
        assert result == {}

    def test_gpt5_with_reasoning(self):
        """GPT-5 + reasoning effort → reasoning dict を含む"""
        from chat import _build_reasoning_options, set_model_params

        set_model_params("gpt-5", "high", "detailed", 0.0)
        result = _build_reasoning_options()
        assert "reasoning" in result
        assert result["reasoning"]["effort"] == "high"
        assert result["reasoning"]["summary"] == "detailed"

    def test_gpt5_reasoning_summary_off(self):
        """reasoning_summary='off' の場合は summary を含まない"""
        from chat import _build_reasoning_options, set_model_params

        set_model_params("gpt-5", "medium", "off", 0.0)
        result = _build_reasoning_options()
        assert "reasoning" in result
        assert result["reasoning"]["effort"] == "medium"
        assert "summary" not in result["reasoning"]


class TestChatEndpointValidation:
    """Tests for /chat endpoint input validation."""

    def test_empty_body_returns_error(self, test_client):
        """空ボディ → 422 または 400 エラー"""
        response = test_client.post("/api/chat", json={})
        assert response.status_code in [400, 422]

    def test_missing_messages_returns_error(self, test_client):
        """messages なし → エラー"""
        response = test_client.post(
            "/api/chat",
            json={"conversation_id": "test-123"},
        )
        assert response.status_code in [400, 422]

    def test_empty_messages_returns_error(self, test_client):
        """空 messages → エラー"""
        response = test_client.post(
            "/api/chat",
            json={"conversation_id": "test-123", "messages": []},
        )
        assert response.status_code in [400, 422]

    def test_invalid_conversation_id_format(self, test_client):
        """不正な UUID → 400"""
        response = test_client.post(
            "/api/chat",
            json={
                "conversation_id": "not-a-uuid",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        assert response.status_code == 400

    def test_query_too_long(self, test_client):
        """クエリが長すぎる → 400"""
        response = test_client.post(
            "/api/chat",
            json={
                "conversation_id": "00000000-0000-0000-0000-000000000000",
                "messages": [{"role": "user", "content": "x" * 11000}],
            },
        )
        assert response.status_code == 400
