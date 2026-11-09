"""FastAPI application factory for the Ingestion adapter."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from ingestion.app.adapters.go_client import GOClient, HttpGOClient, StubGOClient
from ingestion.app.adapters.source_connector import SourceConnector, build_source_connector
from ingestion.app.api.router import router as ingestion_router
from ingestion.app.core.config import settings


def create_app(
    go_client: GOClient | None = None,
    connector_factory: Any | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    ``go_client`` and ``connector_factory`` are override points for tests.
    """
    app = FastAPI(
        title="corp-ai-db Ingestion + Source Connectors",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(ingestion_router)

    app.state.go_client = go_client or _default_go_client()
    app.state.connector_factory = connector_factory or _default_connector_factory
    return app


def _default_go_client() -> GOClient:
    if settings.GO_SERVICE_URL:
        return HttpGOClient(settings.GO_SERVICE_URL)
    return StubGOClient()


def _default_connector_factory(source_type: str, config: dict) -> SourceConnector:
    return build_source_connector(source_type, config)


app = create_app()
