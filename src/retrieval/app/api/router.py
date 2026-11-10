"""FastAPI routes for the Retrieval + Indexing adapter."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from retrieval.app.adapters.embeddings import EmbeddingAdapter
from retrieval.app.adapters.go_client import GOClient
from retrieval.app.adapters.identity_client import IdentityClient
from retrieval.app.repositories.db import get_db
from retrieval.app.schemas.retrieval import (
    HealthResponse,
    IndexActivateRequest,
    IndexActivateResponse,
    IndexBuildRequest,
    IndexBuildResponse,
    IndexPointerResponse,
    ReconcileIndexRequest,
    ReconcileIndexResponse,
    SearchRequest,
    SearchResponse,
)
from retrieval.app.services import indexing, search
from retrieval.app.services.retrieval_error import RetrievalServiceError

router = APIRouter()


def get_identity_client(request: Request) -> IdentityClient:
    """Return the identity client stored on the application instance."""
    return request.app.state.identity_client


def get_go_client(request: Request) -> GOClient:
    """Return the Git Orchestrator client stored on the application instance."""
    return request.app.state.go_client


def get_embedding_adapter(request: Request) -> EmbeddingAdapter:
    """Return the embedding adapter stored on the application instance."""
    return request.app.state.embedding_adapter


def _handle_domain_error(exc: RetrievalServiceError) -> HTTPException:
    code_map = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "FORBIDDEN": status.HTTP_403_FORBIDDEN,
        "INDEX_NOT_READY": status.HTTP_503_SERVICE_UNAVAILABLE,
        "INDEX_GENERATION_CONFLICT": status.HTTP_409_CONFLICT,
        "INVALID_STATE": status.HTTP_409_CONFLICT,
        "STALE_SNAPSHOT": status.HTTP_409_CONFLICT,
        "UPSTREAM_UNAVAILABLE": status.HTTP_502_BAD_GATEWAY,
    }
    return HTTPException(
        status_code=code_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/kb/v1/index/build", response_model=IndexBuildResponse)
def build_index(
    request: IndexBuildRequest,
    db: Annotated[Session, Depends(get_db)],
    go_client: Annotated[GOClient, Depends(get_go_client)],
    embedding_adapter: Annotated[EmbeddingAdapter, Depends(get_embedding_adapter)],
) -> dict[str, Any]:
    try:
        generation = indexing.build_index(
            db,
            go_client,
            embedding_adapter,
            request.space_id,
            request.snapshot_sha,
        )
    except RetrievalServiceError as exc:
        raise _handle_domain_error(exc) from exc

    chunk_count = (
        db.query(indexing.Chunk)
        .filter(indexing.Chunk.generation_id == generation.id)
        .count()
    )
    return {
        "generation_id": generation.id,
        "space_id": request.space_id,
        "snapshot_sha": request.snapshot_sha,
        "status": generation.status,
        "chunks_indexed": chunk_count,
    }


@router.post("/api/kb/v1/index/activate", response_model=IndexActivateResponse)
def activate_index(
    request: IndexActivateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    try:
        pointer = indexing.activate_pointer(
            db,
            request.space_id,
            request.profile,
            request.generation_id,
            request.fence_token,
        )
    except RetrievalServiceError as exc:
        raise _handle_domain_error(exc) from exc
    return {
        "pointer_id": pointer.id,
        "space_id": pointer.space_id,
        "profile": pointer.profile,
        "generation_id": pointer.generation_id,
        "fence_token": pointer.fence_token,
        "active": pointer.active,
    }


@router.get(
    "/api/kb/v1/index/pointer",
    response_model=IndexPointerResponse,
)
def get_active_pointer(
    space_id: str,
    db: Annotated[Session, Depends(get_db)],
    profile: str = "default",
) -> dict[str, Any]:
    pointer = indexing.get_active_pointer(db, space_id, profile)
    if pointer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "no active pointer for space/profile"},
        )
    return {
        "pointer_id": pointer.id,
        "space_id": pointer.space_id,
        "profile": pointer.profile,
        "generation_id": pointer.generation_id,
        "fence_token": pointer.fence_token,
        "active": pointer.active,
    }


@router.post("/api/kb/v1/search", response_model=SearchResponse)
def search_index(
    request: SearchRequest,
    db: Annotated[Session, Depends(get_db)],
    identity_client: Annotated[IdentityClient, Depends(get_identity_client)],
    embedding_adapter: Annotated[EmbeddingAdapter, Depends(get_embedding_adapter)],
) -> dict[str, Any]:
    try:
        return search.search(
            db,
            identity_client,
            embedding_adapter,
            request.space_id,
            request.query,
            request.actor_id,
            profile=request.profile,
            mode=request.mode,
            top_k=request.top_k,
            cursor=request.cursor,
        )
    except RetrievalServiceError as exc:
        raise _handle_domain_error(exc) from exc


@router.post("/api/kb/v1/index/reconcile", response_model=ReconcileIndexResponse)
def reconcile_index(
    request: ReconcileIndexRequest,
    db: Annotated[Session, Depends(get_db)],
    go_client: Annotated[GOClient, Depends(get_go_client)],
) -> dict[str, Any]:
    try:
        return indexing.reconcile_index_with_head(
            db,
            go_client,
            request.space_id,
            request.profile,
            request.branch,
        )
    except RetrievalServiceError as exc:
        raise _handle_domain_error(exc) from exc
