"""FastAPI routes for the Session service."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from session.app.repositories.db import get_db
from session.app.schemas.session import (
    CreateSessionRequest,
    HealthResponse,
    LogoutRequest,
    RefreshRequest,
    RevokeAllRequest,
    TokenPairResponse,
    ValidationResponse,
)
from session.app.services import session_service
from session.app.services.session_service import SessionServiceError

router = APIRouter()


def _derive_stable_id(external_ref: dict[str, Any] | None, provided_stable_id: str | None) -> str:
    """Derive canonical stable_id from external_ref or a provided stable_id."""
    if provided_stable_id:
        return provided_stable_id
    if external_ref:
        issuer = external_ref.get("issuer")
        sub = external_ref.get("sub")
        if issuer and sub:
            return f"{issuer}:{sub}"
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "INVALID_REF", "message": "external_ref or stable_id required"},
    )


def _handle_domain_error(exc: SessionServiceError) -> HTTPException:
    code_map = {
        "TOKEN_EXPIRED": status.HTTP_401_UNAUTHORIZED,
        "TOKEN_INVALID": status.HTTP_401_UNAUTHORIZED,
        "TOKEN_REVOKED": status.HTTP_401_UNAUTHORIZED,
        "INVALID_IDENTITY": status.HTTP_401_UNAUTHORIZED,
    }
    return HTTPException(
        status_code=code_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


def _extract_bearer(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Bearer token required"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Bearer token required"},
        )
    return token


@router.post("/api/kb/v1/session/create", response_model=TokenPairResponse)
def create_session(
    request: CreateSessionRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    """Create a session and return access + refresh tokens.

    Accepts either an ``external_ref`` (issuer + sub) or a pre-computed
    ``stable_id``. This lets tests and clients issue tokens without calling
    the upstream IdP.
    """
    ref = (
        request.external_ref.model_dump()
        if hasattr(request.external_ref, "model_dump")
        else (request.external_ref or {})
    )
    stable_id = _derive_stable_id(ref, request.stable_id)

    try:
        pair = session_service.create_session(
            db,
            stable_id=stable_id,
            access_policy_revision=request.access_policy_revision,
            approval_policy_revision=request.approval_policy_revision,
            extra_claims=request.extra_claims,
        )
    except SessionServiceError as exc:
        raise _handle_domain_error(exc) from exc

    return {
        "access_token": pair.access_token,
        "refresh_token": pair.refresh_token,
        "session_id": pair.session_id,
        "stable_id": pair.stable_id,
        "access_expires_at": pair.access_expires_at,
        "refresh_expires_at": pair.refresh_expires_at,
    }


@router.get("/api/kb/v1/session/validate", response_model=ValidationResponse)
def validate_session(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    """Validate a Bearer access token and return identity + policy revisions."""
    token = _extract_bearer(request)
    try:
        result = session_service.validate_access_token(db, token)
    except SessionServiceError as exc:
        raise _handle_domain_error(exc) from exc

    return {
        "session_id": result.session_id,
        "stable_id": result.stable_id,
        "access_policy_revision": result.access_policy_revision,
        "approval_policy_revision": result.approval_policy_revision,
    }


@router.post("/api/kb/v1/session/refresh", response_model=TokenPairResponse)
def refresh_session(
    request: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    """Refresh an access token using a refresh token."""
    try:
        pair = session_service.refresh_access_token(db, request.refresh_token)
    except SessionServiceError as exc:
        raise _handle_domain_error(exc) from exc

    return {
        "access_token": pair.access_token,
        "refresh_token": pair.refresh_token,
        "session_id": pair.session_id,
        "stable_id": pair.stable_id,
        "access_expires_at": pair.access_expires_at,
        "refresh_expires_at": pair.refresh_expires_at,
    }


@router.post("/api/kb/v1/session/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: LogoutRequest,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Revoke the session associated with the provided access token."""
    try:
        session_service.logout(db, request.access_token)
    except SessionServiceError as exc:
        raise _handle_domain_error(exc) from exc


@router.post("/api/kb/v1/session/revoke-all", status_code=status.HTTP_200_OK)
def revoke_all(
    request: RevokeAllRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Revoke all active sessions for a stable identity."""
    try:
        revoked_count = session_service.revoke_all_for_user(db, request.stable_id)
    except SessionServiceError as exc:
        raise _handle_domain_error(exc) from exc

    return {"stable_id": request.stable_id, "revoked_count": revoked_count}


@router.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok"}
