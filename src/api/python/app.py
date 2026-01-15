"""
FastAPI application entry point for the Agentic Applications for Unified Data Foundation Solution Accelerator.

This module sets up the FastAPI app, configures middleware, loads environment variables,
registers API routers, and manages application lifespan events such as agent initialization
and cleanup.
"""

import os
from datetime import datetime, timezone

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Application version - updated for CI/CD pipeline validation
APP_VERSION = "2.1.0"
BUILD_DATE = "2026-01-16"

from chat import router as chat_router
from history import router as history_router
from history_sql import router as history_sql_router

load_dotenv()


def build_app() -> FastAPI:
    """
    Creates and configures the FastAPI application instance.
    """
    fastapi_app = FastAPI(
        title="Agentic Applications for Unified Data Foundation Solution Accelerator",
        version="1.0.0",
    )

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    fastapi_app.include_router(chat_router, prefix="/api", tags=["chat"])
    fastapi_app.include_router(history_router, prefix="/history", tags=["history"])
    fastapi_app.include_router(
        history_sql_router, prefix="/historyfab", tags=["historyfab"]
    )

    @fastapi_app.get("/health")
    async def health_check():
        """
        Health check endpoint with extended diagnostics.
        Returns application status, version, and environment info.
        """
        return {
            "status": "healthy",
            "version": APP_VERSION,
            "build_date": BUILD_DATE,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": os.getenv("AZURE_ENV_NAME", "development"),
            "model": os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME", "unknown"),
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
