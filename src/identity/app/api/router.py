"""FastAPI routes for the Identity + AuthZ adapter."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from identity.app.repositories.db import get_db
from identity.app.schemas.authz import (
    AuthzContextRequest,
    AuthzContextResponse,
    GroupSnapshotRequest,
    HealthResponse,
    IdentityResponse,
    PathCheckRequest,
    PathCheckResponse,
    PolicyBundleRequest,
    RecheckGroupsRequest,
    RecheckGroupsResponse,
    ResolveIdentityRequest,
    ResolveTokenRequest,
)
from identity.app.services import identity_service
from identity.app.services.identity_service import IdentityServiceError

router = APIRouter()


def _extract_bearer(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Bearer token required"},
        )
    token = authorization[len("Bearer "):].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Bearer token required"},
        )
    return token


def _require_authz_context(request: Request, space_id: str) -> None:
    """Require an authenticated principal with manage_grants capability.

    The Open WebUI upstream session middleware sets ``request.state.actor_id``
    and ``request.state.authz_context`` after resolving the bearer token.
    Endpoints that mutate authorization state must verify the caller has the
    ``manage_grants`` capability for the target Space.
    """
    actor_id = getattr(request.state, "actor_id", None)
    if actor_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHENTICATED", "message": "authentication required"},
        )
    context = getattr(request.state, "authz_context", None)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "authorization context missing"},
        )
    space_scopes = context.get("space_scopes", [])
    for scope in space_scopes:
        if scope.get("space_id") == space_id and "manage_grants" in scope.get("capabilities", []):
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "FORBIDDEN", "message": "manage_grants required for this space"},
    )


def _handle_domain_error(exc: IdentityServiceError) -> HTTPException:
    code_map = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "FORBIDDEN": status.HTTP_403_FORBIDDEN,
        "GROUP_SNAPSHOT_STALE": status.HTTP_409_CONFLICT,
        "POLICY_REVISION_MISMATCH": status.HTTP_409_CONFLICT,
        "INVALID_POLICY": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "INVALID_SNAPSHOT": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "INVALID_PATH": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "INVALID_ACTOR_TYPE": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "INVALID_IDENTITY_REF": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "IDENTITY_ADAPTER_NOT_AVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
        "IDENTITY_ADAPTER_ERROR:TOKEN_INVALID": status.HTTP_401_UNAUTHORIZED,
        "UNKNOWN_IDENTITY_ADAPTER": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    return HTTPException(
        status_code=code_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


@router.post("/api/kb/v1/identity/resolve", response_model=IdentityResponse)
def resolve_identity(
    request: ResolveIdentityRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    try:
        identity = identity_service.resolve_identity(db, request.external_ref)
    except IdentityServiceError as exc:
        raise _handle_domain_error(exc) from exc
    return identity


@router.post("/api/kb/v1/identity/resolve-token", response_model=IdentityResponse)
def resolve_identity_token(
    request: ResolveTokenRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    try:
        identity = identity_service.resolve_identity_from_token(db, request.access_token)
    except IdentityServiceError as exc:
        raise _handle_domain_error(exc) from exc
    return identity


@router.get("/api/kb/v1/identity/groups")
def identity_groups(
    http_request: Request,
) -> dict[str, list[str]]:
    """Return the upstream group memberships for the bearer access token."""
    token = _extract_bearer(http_request)
    try:
        groups = identity_service.fetch_upstream_groups(token)
    except IdentityServiceError as exc:
        raise _handle_domain_error(exc) from exc
    return {"groups": groups}


@router.post("/api/kb/v1/authz/context", response_model=AuthzContextResponse)
def authz_context(
    request: AuthzContextRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    try:
        context = identity_service.compute_authz_context(
            db,
            request.space_id,
            request.actor_id,
            request.actor_type,
        )
    except IdentityServiceError as exc:
        raise _handle_domain_error(exc) from exc
    return context.computed_context


@router.post("/api/kb/v1/authz/check", response_model=PathCheckResponse)
def authz_check(
    request: PathCheckRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    try:
        return identity_service.check_path_approval(
            db,
            request.space_id,
            request.actor_id,
            request.path,
        )
    except IdentityServiceError as exc:
        raise _handle_domain_error(exc) from exc


@router.post("/api/kb/v1/groups/snapshot", status_code=status.HTTP_201_CREATED)
def groups_snapshot(
    request: GroupSnapshotRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    try:
        rows = identity_service.ingest_group_snapshot(
            db,
            request.space_id,
            request,
        )
    except IdentityServiceError as exc:
        raise _handle_domain_error(exc) from exc
    return {
        "space_id": request.space_id,
        "snapshot_id": str(request.snapshot_id) if request.snapshot_id else None,
        "epoch": rows[0].epoch if rows else 0,
        "groups_ingested": len(rows),
    }


@router.post("/api/kb/v1/policies/activate", status_code=status.HTTP_201_CREATED)
def policies_activate(
    request: PolicyBundleRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    try:
        bundle = identity_service.activate_policy_bundle(db, request.space_id, request)
    except IdentityServiceError as exc:
        raise _handle_domain_error(exc) from exc
    return {
        "space_id": request.space_id,
        "bundle_id": request.bundle_id,
        "activation_epoch": bundle.activation_epoch,
    }


@router.post("/api/kb/v1/groups/recheck", response_model=RecheckGroupsResponse)
def groups_recheck(
    request: RecheckGroupsRequest,
    http_request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    """Recheck upstream group membership before a sensitive operation."""
    _require_authz_context(http_request, request.space_id)
    try:
        return identity_service.recheck_group_membership(
            db,
            request.space_id,
            request.access_token,
        )
    except IdentityServiceError as exc:
        raise _handle_domain_error(exc) from exc


@router.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok"}
