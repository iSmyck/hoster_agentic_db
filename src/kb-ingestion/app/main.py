"""FastAPI application factory for kb-ingestion."""

from __future__ import annotations

from fastapi import FastAPI

from .adapters.object_store import InMemoryObjectStore, ObjectStore
from .api.router import router
from .core.config import settings
from .services.staging import StagingService


def create_app(
    object_store: ObjectStore | None = None,
) -> FastAPI:
    """Create the kb-ingestion app; ``object_store`` is a test override."""
    app = FastAPI(
        title="corp-ai-db kb-ingestion",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    store = object_store or InMemoryObjectStore()
    app.state.object_store = store
    app.state.staging_service = StagingService(
        store,
        max_upload_size_bytes=settings.INGEST_MAX_UPLOAD_SIZE_BYTES,
    )
    app.include_router(router)
    return app


app = create_app()