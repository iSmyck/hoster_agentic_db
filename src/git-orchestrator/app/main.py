"""FastAPI application factory for the Git Orchestrator adapter."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .adapters.gitlab import GitLabAdapter, HttpGitLabAdapter, StubGitLabAdapter
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip() for origin in settings.CORS_ALLOW_ORIGINS.split(",") if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if adapter is None:
        if settings.GITLAB_ADAPTER == "stub":
            adapter = StubGitLabAdapter()
        else:
            adapter = HttpGitLabAdapter(
                settings.GITLAB_URL,
                settings.GITLAB_TOKEN,
                settings.GITLAB_PROJECT_PATH_PREFIX,
            )
    app.state.gitlab_adapter = adapter
    app.include_router(go_router)

    return app


app = create_app()
