"""FastAPI application factory for the Retrieval + Indexing adapter."""

from __future__ import annotations

from fastapi import FastAPI

from retrieval.app.adapters.embeddings import EmbeddingAdapter, build_embedding_adapter
from retrieval.app.adapters.go_client import GOClient, HttpGOClient, build_synthetic_stub_go_client
from retrieval.app.adapters.identity_client import HttpIdentityClient, IdentityClient
from retrieval.app.api.router import router as retrieval_router
from retrieval.app.core.config import settings


def create_app(
    identity_client: IdentityClient | None = None,
    go_client: GOClient | None = None,
    embedding_adapter: EmbeddingAdapter | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="corp-ai-db Retrieval + Indexing Adapter",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    if identity_client is None:
        identity_client = HttpIdentityClient(settings.IDENTITY_SERVICE_URL)
    if go_client is None:
        if settings.GO_CLIENT_MODE.lower() == "stub":
            go_client = build_synthetic_stub_go_client()
        else:
            go_client = HttpGOClient(settings.GO_SERVICE_URL)
    if embedding_adapter is None:
        embedding_adapter = build_embedding_adapter(settings)

    app.state.identity_client = identity_client
    app.state.go_client = go_client
    app.state.embedding_adapter = embedding_adapter

    app.include_router(retrieval_router)
    return app


app = create_app()
