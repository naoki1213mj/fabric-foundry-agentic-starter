"""
FastAPI application entry point for the Agentic Applications for Unified Data Foundation Solution Accelerator.

This module sets up the FastAPI app, configures middleware, loads environment variables,
registers API routers, and manages application lifespan events such as agent initialization
and cleanup.
"""

import logging
import os
import time
from datetime import UTC, datetime

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from chat import router as chat_router
from history import router as history_router
from history_sql import router as history_sql_router

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Application Insights setup (must be done early, before other imports that use logging)
try:
    from azure.monitor.opentelemetry import configure_azure_monitor

    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if connection_string:
        configure_azure_monitor(connection_string=connection_string)
        logger.info("Application Insights configured successfully")
    else:
        logger.warning("APPLICATIONINSIGHTS_CONNECTION_STRING not set, telemetry disabled")
except ImportError:
    logger.warning("azure-monitor-opentelemetry not installed, telemetry disabled")

# Application version - updated for CI/CD pipeline validation
APP_VERSION = "2.11.0"
BUILD_DATE = "2026-02-04"
BUILD_INFO = "Application Insights logging integration"


def build_app() -> FastAPI:
    """
    Creates and configures the FastAPI application instance.
    """
    fastapi_app = FastAPI(
        title="Agentic Applications for Unified Data Foundation Solution Accelerator",
        version=APP_VERSION,
    )

    # CORS configuration - restrict origins in production
    allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware
    @fastapi_app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all incoming requests with timing information."""
        start_time = time.time()
        request_id = request.headers.get("x-request-id", "unknown")

        # Log request start
        logger.info(
            f"Request started: {request.method} {request.url.path} [request_id={request_id}]"
        )

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log request completion
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"status={response.status_code} duration={duration:.3f}s "
                f"[request_id={request_id}]"
            )
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"error={str(e)} duration={duration:.3f}s "
                f"[request_id={request_id}]"
            )
            raise

    # Include routers
    fastapi_app.include_router(chat_router, prefix="/api", tags=["chat"])
    fastapi_app.include_router(history_router, prefix="/history", tags=["history"])
    fastapi_app.include_router(history_sql_router, prefix="/historyfab", tags=["historyfab"])

    @fastapi_app.get("/health")
    async def health_check():
        """
        Health check endpoint with extended diagnostics.
        Returns application status, version, and environment info.
        Checks DB connectivity when FABRIC_SQL_SERVER is configured.
        """
        health_status = "healthy"
        db_status = "not_configured"

        fabric_server = os.getenv("FABRIC_SQL_SERVER")
        if fabric_server:
            try:
                from history_sql import get_fabric_db_connection

                conn = await get_fabric_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                    conn.close()
                    db_status = "connected"
                else:
                    db_status = "unavailable"
                    health_status = "degraded"
            except Exception as e:
                logger.warning(f"Health check DB probe failed: {e}")
                db_status = "unavailable"
                health_status = "degraded"

        return {
            "status": health_status,
            "version": APP_VERSION,
            "build_date": BUILD_DATE,
            "timestamp": datetime.now(UTC).isoformat(),
            "environment": os.getenv("AZURE_ENV_NAME", "development"),
            "model": os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME", "unknown"),
            "platform": "Microsoft Foundry",
            "database": db_status,
        }

    @fastapi_app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "Agentic AI API",
            "version": APP_VERSION,
            "docs": "/docs",
            "health": "/health",
        }

    return fastapi_app


app = build_app()


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
