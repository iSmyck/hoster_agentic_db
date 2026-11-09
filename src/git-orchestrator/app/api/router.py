"""FastAPI routes for the Git Orchestrator adapter."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..adapters.gitlab import GitLabAdapter, GitLabAdapterError
from ..repositories.db import get_db
from ..schemas.ops import (
    DecisionRecordRequest,
    DecisionResponse,
    DocumentReadRequest,
    DocumentReadResponse,
    HealthResponse,
    MergeResponse,
    MergeRulesResponse,
    ProposalResponse,
    ProposalSubmitRequest,
    TreeRequest,
    TreeResponse,
)
from ..services import git_orchestrator
from ..services.git_orchestrator import GitOrchestratorError

router = APIRouter()


def get_gitlab_adapter(request: Request) -> GitLabAdapter:
    """Return the GitLab adapter stored on the application instance."""
    return request.app.state.gitlab_adapter


def _handle_domain_error(exc: GitOrchestratorError) -> HTTPException:
    code_map = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "IDEMPOTENCY_KEY_REUSED": status.HTTP_409_CONFLICT,
        "INVALID_STATE": status.HTTP_409_CONFLICT,
        "SELF_APPROVAL": status.HTTP_403_FORBIDDEN,
        "BASE_MISMATCH": status.HTTP_409_CONFLICT,
        "MERGE_FAILED": status.HTTP_502_BAD_GATEWAY,
        "DIRECT_PUSH_BLOCKED": status.HTTP_403_FORBIDDEN,
        "SOURCE_BRANCH_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "MR_CREATE_FAILED": status.HTTP_502_BAD_GATEWAY,
    }
    return HTTPException(
        status_code=code_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


def _handle_adapter_error(exc: Exception) -> HTTPException:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code == 404:
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "resource not found"},
            )
        if status_code >= 500:
            return HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"code": "ADAPTER_ERROR", "message": str(exc)},
            )
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ADAPTER_ERROR", "message": str(exc)},
        )
    if isinstance(exc, GitLabAdapterError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(exc)},
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"code": "INTERNAL_ERROR", "message": str(exc)},
    )


@router.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/kb/v1/documents/read", response_model=DocumentReadResponse)
def read_document(
    request: DocumentReadRequest,
    db: Annotated[Session, Depends(get_db)],
    adapter: Annotated[GitLabAdapter, Depends(get_gitlab_adapter)],
) -> dict[str, Any]:
    try:
        content = git_orchestrator.read_document(
            db,
            adapter,
            request.space_id,
            request.path,
            request.sha,
        )
    except (GitLabAdapterError, httpx.HTTPError) as exc:
        raise _handle_adapter_error(exc) from exc
    return {
        "space_id": request.space_id,
        "path": request.path,
        "sha": request.sha,
        "content": content,
    }


@router.post("/api/kb/v1/documents/tree", response_model=TreeResponse)
def get_tree(
    request: TreeRequest,
    db: Annotated[Session, Depends(get_db)],
    adapter: Annotated[GitLabAdapter, Depends(get_gitlab_adapter)],
) -> dict[str, Any]:
    try:
        entries = git_orchestrator.get_tree(db, adapter, request.space_id, request.sha)
    except (GitLabAdapterError, httpx.HTTPError) as exc:
        raise _handle_adapter_error(exc) from exc
    # GitLab returns object hashes in the ``id`` field; expose them as ``sha``
    # to match the internal contract.
    normalized = [
        {
            "path": entry.get("path", ""),
            "type": entry.get("type", ""),
            "sha": entry.get("sha") or entry.get("id", ""),
            "mode": entry.get("mode"),
        }
        for entry in entries
    ]
    return {
        "space_id": request.space_id,
        "sha": request.sha,
        "entries": normalized,
    }


@router.post(
    "/api/kb/v1/proposals",
    status_code=status.HTTP_201_CREATED,
    response_model=ProposalResponse,
)
def submit_proposal(
    request: ProposalSubmitRequest,
    db: Annotated[Session, Depends(get_db)],
    adapter: Annotated[GitLabAdapter, Depends(get_gitlab_adapter)],
) -> Any:
    try:
        record = git_orchestrator.submit_proposal(db, adapter, request)
    except GitOrchestratorError as exc:
        raise _handle_domain_error(exc) from exc
    return record


@router.post(
    "/api/kb/v1/decisions",
    status_code=status.HTTP_201_CREATED,
    response_model=DecisionResponse,
)
def record_decision(
    request: DecisionRecordRequest,
    db: Annotated[Session, Depends(get_db)],
    adapter: Annotated[GitLabAdapter, Depends(get_gitlab_adapter)],
) -> Any:
    try:
        record = git_orchestrator.record_decision(db, adapter, request)
    except GitOrchestratorError as exc:
        raise _handle_domain_error(exc) from exc
    return record


@router.post(
    "/api/kb/v1/proposals/{proposal_id}/merge",
    response_model=MergeResponse,
)
def execute_merge(
    proposal_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    adapter: Annotated[GitLabAdapter, Depends(get_gitlab_adapter)],
) -> dict[str, Any]:
    try:
        return git_orchestrator.execute_merge(db, adapter, proposal_id)
    except GitOrchestratorError as exc:
        raise _handle_domain_error(exc) from exc


@router.get(
    "/api/kb/v1/spaces/{space_id}/merge-rules",
    response_model=MergeRulesResponse,
)
def merge_rules(
    space_id: str,
    db: Annotated[Session, Depends(get_db)],
    adapter: Annotated[GitLabAdapter, Depends(get_gitlab_adapter)],
) -> dict[str, Any]:
    try:
        return git_orchestrator.direct_push_guard(db, adapter, space_id)
    except GitOrchestratorError as exc:
        raise _handle_domain_error(exc) from exc
