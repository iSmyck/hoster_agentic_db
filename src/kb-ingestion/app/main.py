"""FastAPI application factory for kb-ingestion."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .adapters.go_client import GOClient, StubGOClient
from .adapters.object_store import InMemoryObjectStore, ObjectStore
from .api.router import router
from .core.config import settings
from .services.agent_structurer import AgentStructurer
from .services.converted_corpus import ConvertedCorpus
from .services.converter import ConversionService
from .services.staging import StagingService
from .services.structure_proposals import StructureProposalStore, StructureReviewService


def create_app(
    object_store: ObjectStore | None = None,
    corpus: ConvertedCorpus | None = None,
    go_client: GOClient | None = None,
) -> FastAPI:
    """Create the kb-ingestion app; ``object_store`` is a test override."""
    app = FastAPI(
        title="corp-ai-db kb-ingestion",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    store = object_store or InMemoryObjectStore()
    converted_corpus = corpus or ConvertedCorpus()
    app.state.object_store = store
    app.state.converted_corpus = converted_corpus
    staging = StagingService(
        store,
        max_upload_size_bytes=settings.INGEST_MAX_UPLOAD_SIZE_BYTES,
    )
    app.state.staging_service = staging
    app.state.conversion_service = ConversionService(store, converted_corpus)
    structurer = AgentStructurer(converted_corpus)
    app.state.agent_structurer = structurer
    proposal_store = StructureProposalStore()
    app.state.structure_proposals = proposal_store
    resolved_go = go_client or StubGOClient()
    app.state.go_client = resolved_go
    app.state.structure_review = StructureReviewService(structurer, proposal_store, resolved_go)
    app.include_router(router)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        message = str(errors[0].get("msg", "invalid request")) if errors else "invalid request"
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": {"code": "VALIDATION_ERROR", "message": message}},
        )

    return app


app = create_app()