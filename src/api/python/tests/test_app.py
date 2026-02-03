"""
Unit tests for app.py - FastAPI application setup and health endpoints.
"""


class TestAppConfiguration:
    """Tests for application configuration and setup."""

    def test_app_version_exists(self):
        """Verify that app version is defined."""
        from app import APP_VERSION

        assert APP_VERSION is not None
        assert isinstance(APP_VERSION, str)
        assert len(APP_VERSION) > 0

    def test_build_app_creates_fastapi_instance(self):
        """Verify that build_app creates a valid FastAPI instance."""
        from fastapi import FastAPI

        from app import build_app

        app = build_app()

        assert isinstance(app, FastAPI)
        assert app.title == "Agentic Applications for Unified Data Foundation Solution Accelerator"

    def test_cors_middleware_configured(self):
        """Verify that CORS middleware is properly configured."""
        from app import build_app

        app = build_app()

        # Check that middleware is added
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_endpoint_returns_ok(self, test_client):
        """Health endpoint should return 200 OK."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint_returns_welcome(self, test_client):
        """Root endpoint should return API information."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        # API returns name and version info
        assert "name" in data or "version" in data or "status" in data


class TestAPIRouterRegistration:
    """Tests for API router registration."""

    def test_chat_router_registered(self):
        """Verify chat router is registered under /api prefix."""
        from app import build_app

        app = build_app()
        routes = [r.path for r in app.routes]

        # Check for chat-related routes
        assert any("/api" in route for route in routes)

    def test_history_router_registered(self):
        """Verify history router is registered under /history prefix."""
        from app import build_app

        app = build_app()
        routes = [r.path for r in app.routes]

        # Check for history-related routes
        assert any("/history" in route for route in routes)

    def test_historyfab_router_registered(self):
        """Verify Fabric SQL history router is registered under /historyfab prefix."""
        from app import build_app

        app = build_app()
        routes = [r.path for r in app.routes]

        # Check for historyfab-related routes
        assert any("/historyfab" in route for route in routes)
