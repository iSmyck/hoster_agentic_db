"""FastAPI routes for the Git Orchestrator adapter."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..adapters.gitlab import GitLabAdapter, GitLabAdapterError
from ..core.config import settings
from ..models.ops import ProposalRecord
from ..repositories.db import get_db
from ..schemas.ops import (
    DecisionRecordRequest,
    DecisionResponse,
    DocumentReadRequest,
    DocumentReadResponse,
    HealthResponse,
    MergeResponse,
    MergeRulesResponse,
    PrepareBranchRequest,
    PrepareBranchResponse,
    ProposalResponse,
    ProposalSubmitRequest,
    TreeRequest,
    TreeResponse,
)
from ..services import git_orchestrator
from ..services.git_orchestrator import GitOrchestratorError
from .auth import (
    AuthenticatedIdentity,
    get_current_identity,
    require_approver,
    require_space_access,
    validate_markdown_path,
    validate_target_branch,
)

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
        "MERGE_UNKNOWN_OUTCOME": status.HTTP_502_BAD_GATEWAY,
        "MERGE_PARENT_MISMATCH": status.HTTP_502_BAD_GATEWAY,
        "DECISION_ANCHOR_FAILED": status.HTTP_502_BAD_GATEWAY,
        "RECOVERY_REQUIRED": status.HTTP_409_CONFLICT,
        "DIRECT_PUSH_BLOCKED": status.HTTP_403_FORBIDDEN,
        "SOURCE_BRANCH_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "MR_CREATE_FAILED": status.HTTP_502_BAD_GATEWAY,
        "ACTOR_MISMATCH": status.HTTP_403_FORBIDDEN,
        "APPROVER_MISMATCH": status.HTTP_403_FORBIDDEN,
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


@router.get("/api/kb/v1/identity/me")
def identity_me(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
) -> dict[str, str]:
    return {"stable_id": identity.stable_id, "role": identity.role}


def _bind_author(
    request: ProposalSubmitRequest, identity: AuthenticatedIdentity
) -> ProposalSubmitRequest:
    proposal_data = dict(request.proposal_data)
    for key in ("author_stable_id", "requester_stable_id", "version_author_stable_id"):
        supplied = proposal_data.get(key)
        if supplied is not None and supplied != identity.stable_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ACTOR_MISMATCH",
                    "message": f"{key} does not match session identity",
                },
            )
    proposal_data["author_stable_id"] = identity.stable_id
    proposal_data["requester_stable_id"] = identity.stable_id
    if "version_author_stable_id" in proposal_data:
        proposal_data["version_author_stable_id"] = identity.stable_id
    return request.model_copy(update={"proposal_data": proposal_data})


def _bind_decision(
    request: DecisionRecordRequest, identity: AuthenticatedIdentity
) -> DecisionRecordRequest:
    if request.actor_id != identity.stable_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACTOR_MISMATCH",
                "message": "actor_id does not match session identity",
            },
        )
    decision_data = {
        **request.decision_data,
        "policy_bundle_id": settings.POLICY_BUNDLE_ID,
        "access_policy_revision": settings.ACCESS_POLICY_REVISION,
        "approval_policy_revision": settings.APPROVAL_POLICY_REVISION,
    }
    return request.model_copy(
        update={"actor_id": identity.stable_id, "decision_data": decision_data}
    )


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
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
) -> Any:
    require_space_access(identity, request.space_id)
    try:
        record = git_orchestrator.submit_proposal(db, adapter, _bind_author(request, identity))
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
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
) -> Any:
    require_approver(identity)
    try:
        record = git_orchestrator.record_decision(db, adapter, _bind_decision(request, identity))
    except GitOrchestratorError as exc:
        raise _handle_domain_error(exc) from exc
    return record


@router.get("/api/kb/v1/proposals/{proposal_id}", response_model=ProposalResponse)
def get_proposal(
    proposal_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
) -> ProposalRecord:
    record = db.get(ProposalRecord, proposal_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "proposal not found"},
        )
    require_space_access(identity, record.space_id)
    return record


@router.post(
    "/api/kb/v1/proposals/{proposal_id}/merge",
    response_model=MergeResponse,
)
def execute_merge(
    proposal_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    adapter: Annotated[GitLabAdapter, Depends(get_gitlab_adapter)],
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
) -> dict[str, Any]:
    require_approver(identity)
    try:
        return git_orchestrator.execute_merge(db, adapter, proposal_id, identity.stable_id)
    except GitOrchestratorError as exc:
        raise _handle_domain_error(exc) from exc


@router.post(
    "/api/kb/v1/proposals/{proposal_id}/reconcile",
    response_model=MergeResponse,
)
def reconcile_merge(
    proposal_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    adapter: Annotated[GitLabAdapter, Depends(get_gitlab_adapter)],
) -> dict[str, Any]:
    try:
        return git_orchestrator.reconcile_merge(db, adapter, proposal_id)
    except GitOrchestratorError as exc:
        raise _handle_domain_error(exc) from exc


@router.get(
    "/api/kb/v1/spaces/{space_id:path}/merge-rules",
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


@router.get("/api/kb/v1/spaces/{space_id:path}/branches/{branch}")
def get_branch(
    space_id: str,
    branch: str,
    db: Annotated[Session, Depends(get_db)],
    adapter: Annotated[GitLabAdapter, Depends(get_gitlab_adapter)],
) -> dict[str, Any]:
    try:
        return adapter.get_branch(space_id, branch)
    except (GitLabAdapterError, httpx.HTTPError) as exc:
        raise _handle_adapter_error(exc) from exc


def _gitlab_project_url(adapter: GitLabAdapter, space_id: str) -> str:
    """Return the GitLab project REST URL for a Space (Http adapter only)."""
    from urllib.parse import quote

    base = getattr(adapter, "base_url", "")
    prefix = getattr(adapter, "project_path_prefix", "")
    path = f"{prefix}{space_id}"
    return f"{base}/api/v4/projects/{quote(path, safe='')}"


@router.post("/api/g1-editor/prepare-branch", response_model=PrepareBranchResponse)
def prepare_branch(
    request: PrepareBranchRequest,
    adapter: Annotated[GitLabAdapter, Depends(get_gitlab_adapter)],
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
) -> dict[str, Any]:
    """Create or replay an authorized, idempotent proposal branch/commit."""
    require_space_access(identity, request.space_id)
    validate_target_branch(request.branch)
    validate_markdown_path(request.file_path)

    run_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"kb-prepare:{request.space_id}:{request.idempotency_key}",
    ).hex[:12]
    temp_branch = f"kb-prepare/{run_id}"
    base_url = _gitlab_project_url(adapter, request.space_id)
    branch_url = f"{base_url}/repository/branches"
    headers = getattr(adapter, "_headers", dict)()
    commit_message = (
        f"G1 browser editor proposal {run_id}\n\n"
        f"Prepare-Key: {request.idempotency_key}\n"
        f"Prepare-Path: {request.file_path}\n"
        f"Prepare-Branch: {request.branch}"
    )

    try:
        proposal_sha = ""
        base_sha = ""
        try:
            existing = adapter.get_branch(request.space_id, temp_branch)
            proposal_sha = str(existing.get("commit", {}).get("id") or "")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise

        if proposal_sha:
            existing_commit = adapter.get_commit(request.space_id, proposal_sha)
            if existing_commit.get("message") != commit_message:
                raise GitOrchestratorError(
                    "IDEMPOTENCY_KEY_REUSED",
                    "idempotency_key already used with different prepare payload",
                )
            parents = existing_commit.get("parent_ids", [])
            if len(parents) != 1:
                raise GitOrchestratorError(
                    "INVALID_STATE",
                    "prepared proposal commit has unexpected parentage",
                )
            base_sha = str(parents[0])
        else:
            base = adapter.get_branch(request.space_id, request.branch)
            base_sha = str(base.get("commit", {}).get("id") or "")
            if not base_sha:
                raise GitOrchestratorError("NOT_FOUND", "target branch HEAD not found")

            with httpx.Client(timeout=30) as client:
                client.post(
                    branch_url,
                    headers=headers,
                    json={"branch": temp_branch, "ref": base_sha},
                ).raise_for_status()
                commit_resp = client.post(
                    f"{base_url}/repository/commits",
                    headers=headers,
                    json={
                        "branch": temp_branch,
                        "commit_message": commit_message,
                        "actions": [
                            {
                                "action": "create",
                                "file_path": request.file_path,
                                "content": request.content,
                            }
                        ],
                    },
                )
                commit_resp.raise_for_status()
                proposal_sha = str(commit_resp.json()["id"])

        proposal_branch = f"proposal/{proposal_sha[:8]}"
        if not adapter.branch_exists(request.space_id, proposal_branch):
            httpx.post(
                branch_url,
                headers=headers,
                json={"branch": proposal_branch, "ref": proposal_sha},
                timeout=30,
            ).raise_for_status()
    except GitOrchestratorError as exc:
        raise _handle_domain_error(exc) from exc
    except (GitLabAdapterError, httpx.HTTPError) as exc:
        raise _handle_adapter_error(exc) from exc

    return {
        "space_id": request.space_id,
        "proposal_sha": proposal_sha,
        "base_sha": base_sha,
        "proposal_branch": proposal_branch,
        "file_path": request.file_path,
    }
