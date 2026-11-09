"""FastAPI application factory for the Identity + AuthZ adapter."""

from __future__ import annotations

from fastapi import FastAPI

from identity.app.api.router import router as identity_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="corp-ai-db Identity + AuthZ Adapter",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(identity_router)
    return app


app = create_app()
