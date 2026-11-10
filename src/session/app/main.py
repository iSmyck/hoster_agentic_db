"""FastAPI application factory for the Session service."""

from __future__ import annotations

from fastapi import FastAPI

from session.app.api.router import router as session_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="corp-ai-db Session Service",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(session_router)
    return app


app = create_app()
