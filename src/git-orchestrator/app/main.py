"""FastAPI application factory for the Git Orchestrator adapter."""

from __future__ import annotations

from fastapi import FastAPI

from .adapters.gitlab import GitLabAdapter, HttpGitLabAdapter
from .api.router import router as go_router
from .core.config import settings


def create_app(adapter: GitLabAdapter | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="corp-ai-db Git Orchestrator",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    if adapter is None:
        adapter = HttpGitLabAdapter(
            settings.GITLAB_URL,
            settings.GITLAB_TOKEN,
            settings.GITLAB_PROJECT_PATH_PREFIX,
        )
    app.state.gitlab_adapter = adapter
    app.include_router(go_router)
    return app


app = create_app()
