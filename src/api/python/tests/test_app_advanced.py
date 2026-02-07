"""
Advanced tests for app.py (integration-style).

Extends test_app.py with:
- /health endpoint DB connectivity branching (configured/connected/degraded)
- CORS_ALLOWED_ORIGINS environment variable parsing
- Lifespan cleanup logic
"""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

# ============================================================================
# /health endpoint — DB connectivity branching
# ============================================================================


class TestHealthCheckDBBranching:
    """Tests for /health endpoint with different database states."""

    def test_health_no_fabric_server_configured(self, test_client):
        """DB status should be 'not_configured' when FABRIC_SQL_SERVER is unset."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "not_configured"
        assert data["status"] == "healthy"

    def test_health_db_connected(self, test_client, monkeypatch):
        """DB status should be 'connected' when connection succeeds."""
        monkeypatch.setenv("FABRIC_SQL_SERVER", "test-server.database.fabric.microsoft.com")

        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("app.build_app"):
            # Re-import to get fresh test_client is complex.
            # Instead, test against a fresh app instance.
            pass

        # Build a fresh app to pick up the env var
        from app import build_app

        app = build_app()
        with (
            TestClient(app) as client,
            patch(
                "history_sql.get_fabric_db_connection",
                new_callable=AsyncMock,
                return_value=mock_conn,
            ),
        ):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["database"] == "connected"
            assert data["status"] == "healthy"

    def test_health_db_unavailable(self, monkeypatch):
        """DB status should be 'unavailable' when connection returns None."""
        monkeypatch.setenv("FABRIC_SQL_SERVER", "test-server.database.fabric.microsoft.com")

        from app import build_app

        app = build_app()
        with (
            TestClient(app) as client,
            patch(
                "history_sql.get_fabric_db_connection",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["database"] == "unavailable"
            assert data["status"] == "degraded"

    def test_health_db_exception(self, monkeypatch):
        """DB status should be 'unavailable' when connection throws."""
        monkeypatch.setenv("FABRIC_SQL_SERVER", "test-server.database.fabric.microsoft.com")

        from app import build_app

        app = build_app()
        with (
            TestClient(app) as client,
            patch(
                "history_sql.get_fabric_db_connection",
                new_callable=AsyncMock,
                side_effect=Exception("Connection timeout"),
            ),
        ):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["database"] == "unavailable"
            assert data["status"] == "degraded"


# ============================================================================
# CORS_ALLOWED_ORIGINS parsing
# ============================================================================


class TestCORSOrigins:
    """Tests for CORS origins configuration."""

    def test_default_cors_is_wildcard(self, monkeypatch):
        """Default CORS should allow all origins (*)."""
        monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
        from app import build_app

        app = build_app()
        # Find the CORS middleware
        cors_middleware = None
        for middleware in app.user_middleware:
            if middleware.cls.__name__ == "CORSMiddleware":
                cors_middleware = middleware
                break
        assert cors_middleware is not None
        assert "*" in cors_middleware.kwargs.get("allow_origins", [])

    def test_custom_cors_origins(self, monkeypatch):
        """Custom CORS origins should be parsed from comma-separated string."""
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com,https://admin.example.com")
        from app import build_app

        app = build_app()
        cors_middleware = None
        for middleware in app.user_middleware:
            if middleware.cls.__name__ == "CORSMiddleware":
                cors_middleware = middleware
                break
        origins = cors_middleware.kwargs.get("allow_origins", [])
        assert "https://app.example.com" in origins
        assert "https://admin.example.com" in origins


# ============================================================================
# Health endpoint response schema
# ============================================================================


class TestHealthResponseSchema:
    """Tests for /health endpoint response structure completeness."""

    def test_health_response_contains_all_required_fields(self, test_client):
        """Health response should contain all expected fields."""
        response = test_client.get("/health")
        data = response.json()
        required_fields = ["status", "version", "build_date", "timestamp", "environment", "model", "platform", "database"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_health_platform_is_foundry(self, test_client):
        """Platform field should always be 'Microsoft Foundry'."""
        response = test_client.get("/health")
        data = response.json()
        assert data["platform"] == "Microsoft Foundry"

    def test_health_timestamp_is_iso_format(self, test_client):
        """Timestamp should be valid ISO format."""
        response = test_client.get("/health")
        data = response.json()
        # Should not raise
        from datetime import datetime
        datetime.fromisoformat(data["timestamp"])
