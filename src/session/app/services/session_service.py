"""Session service business logic.

Issues, validates, refreshes and revokes identity-bound access/refresh tokens.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from sqlalchemy.orm import Session

from session.app.core.config import settings
from session.app.models.session import SessionRecord

ALGORITHM = "HS256"
ACCESS_TYPE = "access"
REFRESH_TYPE = "refresh"


class SessionServiceError(Exception):
    """Domain error raised by session services."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class TokenPair:
    """Issued token pair and metadata."""

    access_token: str
    refresh_token: str
    session_id: uuid.UUID
    stable_id: str
    access_expires_at: datetime
    refresh_expires_at: datetime


@dataclass(frozen=True)
class ValidationResult:
    """Result of access-token validation."""

    session_id: uuid.UUID
    stable_id: str
    access_policy_revision: str
    approval_policy_revision: str


def _now() -> datetime:
    """Return current UTC time."""
    return datetime.now(UTC)


def _to_naive_utc(value: datetime) -> datetime:
    """Normalize a DB datetime to a naive UTC datetime for comparisons."""
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _encode(
    session_id: uuid.UUID,
    stable_id: str,
    token_type: str,
    expires_at: datetime,
    jti: uuid.UUID | None = None,
) -> str:
    payload = {
        "session_id": str(session_id),
        "stable_id": stable_id,
        "type": token_type,
        "iss": settings.ISSUER,
        "iat": _now(),
        "exp": expires_at,
    }
    if jti is not None:
        payload["jti"] = str(jti)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def _decode(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=settings.ISSUER,
            options={"require": ["exp", "iat", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise SessionServiceError("TOKEN_EXPIRED", "token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise SessionServiceError("TOKEN_INVALID", f"invalid token: {exc}") from exc


def _default_policy_revisions() -> tuple[str, str]:
    """Return sensible default policy revisions for synthetic/test sessions."""
    return (
        settings.ACCESS_POLICY_REVISION
        if hasattr(settings, "ACCESS_POLICY_REVISION")
        else "0" * 40,
        settings.APPROVAL_POLICY_REVISION
        if hasattr(settings, "APPROVAL_POLICY_REVISION")
        else "0" * 40,
    )


def create_session(
    db: Session,
    stable_id: str,
    access_policy_revision: str | None = None,
    approval_policy_revision: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> TokenPair:
    """Create a new session and return access + refresh tokens.

    ``stable_id`` is the canonical identity string returned by the identity
    adapter (e.g. ``issuer:sub``). Policy revisions are snapshotted at session
    creation time.
    """
    if not stable_id:
        raise SessionServiceError("INVALID_IDENTITY", "stable_id is required")

    now = _now()
    access_expires_at = now + timedelta(seconds=settings.ACCESS_TTL_SECONDS)
    refresh_expires_at = now + timedelta(seconds=settings.REFRESH_TTL_SECONDS)

    access_rev = access_policy_revision or _default_policy_revisions()[0]
    approval_rev = approval_policy_revision or _default_policy_revisions()[1]

    access_jti = uuid.uuid4()
    merged_extra = dict(extra_claims or {})
    merged_extra["access_jti"] = str(access_jti)

    record = SessionRecord(
        stable_id=stable_id,
        issued_at=now,
        expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
        access_policy_revision=access_rev,
        approval_policy_revision=approval_rev,
        extra_claims=merged_extra,
    )
    db.add(record)
    db.flush()

    access_token = _encode(
        record.session_id, stable_id, ACCESS_TYPE, access_expires_at, jti=access_jti
    )
    refresh_token = _encode(record.session_id, stable_id, REFRESH_TYPE, refresh_expires_at)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        session_id=record.session_id,
        stable_id=stable_id,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
    )


def validate_access_token(db: Session, token: str) -> ValidationResult:
    """Validate a Bearer access token.

    Checks signature, expiry, issuer, token type, and DB revocation state.
    """
    claims = _decode(token)
    if claims.get("type") != ACCESS_TYPE:
        raise SessionServiceError("TOKEN_INVALID", "token type mismatch")

    session_id_str = claims.get("session_id")
    stable_id = claims.get("stable_id")
    if not session_id_str or not stable_id:
        raise SessionServiceError("TOKEN_INVALID", "malformed token claims")

    try:
        session_id = uuid.UUID(session_id_str)
    except ValueError as exc:
        raise SessionServiceError("TOKEN_INVALID", "invalid session_id") from exc

    record = db.get(SessionRecord, session_id)
    if record is None:
        raise SessionServiceError("TOKEN_INVALID", "session not found")
    if record.revoked_at is not None:
        raise SessionServiceError("TOKEN_REVOKED", "session has been revoked")
    if record.stable_id != stable_id:
        raise SessionServiceError("TOKEN_INVALID", "stable_id mismatch")
    expected_jti = record.extra_claims.get("access_jti")
    if expected_jti is not None and claims.get("jti") != expected_jti:
        raise SessionServiceError("TOKEN_REVOKED", "access token superseded")
    if _to_naive_utc(_now()) > _to_naive_utc(record.expires_at):
        raise SessionServiceError("TOKEN_EXPIRED", "session expired")

    return ValidationResult(
        session_id=record.session_id,
        stable_id=record.stable_id,
        access_policy_revision=record.access_policy_revision,
        approval_policy_revision=record.approval_policy_revision,
    )


def refresh_access_token(db: Session, refresh_token: str) -> TokenPair:
    """Issue a new access token from a valid refresh token.

    Invalidates the old access token by rotating the session expiry while
    preserving the session identity and policy revisions.
    """
    claims = _decode(refresh_token)
    if claims.get("type") != REFRESH_TYPE:
        raise SessionServiceError("TOKEN_INVALID", "token type mismatch")

    session_id_str = claims.get("session_id")
    stable_id = claims.get("stable_id")
    if not session_id_str or not stable_id:
        raise SessionServiceError("TOKEN_INVALID", "malformed token claims")

    try:
        session_id = uuid.UUID(session_id_str)
    except ValueError as exc:
        raise SessionServiceError("TOKEN_INVALID", "invalid session_id") from exc

    record = db.get(SessionRecord, session_id)
    if record is None:
        raise SessionServiceError("TOKEN_INVALID", "session not found")
    if record.revoked_at is not None:
        raise SessionServiceError("TOKEN_REVOKED", "session has been revoked")
    if record.stable_id != stable_id:
        raise SessionServiceError("TOKEN_INVALID", "stable_id mismatch")
    if _to_naive_utc(_now()) > _to_naive_utc(record.refresh_expires_at):
        raise SessionServiceError("TOKEN_EXPIRED", "refresh token expired")

    now = _now()
    new_access_expires_at = now + timedelta(seconds=settings.ACCESS_TTL_SECONDS)
    new_access_jti = uuid.uuid4()
    record.expires_at = new_access_expires_at
    record.extra_claims = {**record.extra_claims, "access_jti": str(new_access_jti)}
    db.flush()

    access_token = _encode(
        record.session_id,
        record.stable_id,
        ACCESS_TYPE,
        new_access_expires_at,
        jti=new_access_jti,
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        session_id=record.session_id,
        stable_id=record.stable_id,
        access_expires_at=new_access_expires_at,
        refresh_expires_at=record.refresh_expires_at,
    )


def revoke_session(db: Session, token: str) -> None:
    """Revoke the session associated with the given access token."""
    claims = _decode(token)
    if claims.get("type") != ACCESS_TYPE:
        raise SessionServiceError("TOKEN_INVALID", "token type mismatch")

    session_id_str = claims.get("session_id")
    if not session_id_str:
        raise SessionServiceError("TOKEN_INVALID", "malformed token claims")

    try:
        session_id = uuid.UUID(session_id_str)
    except ValueError as exc:
        raise SessionServiceError("TOKEN_INVALID", "invalid session_id") from exc

    record = db.get(SessionRecord, session_id)
    if record is None:
        raise SessionServiceError("TOKEN_INVALID", "session not found")

    record.revoked_at = _now()
    db.flush()


def revoke_all_for_user(db: Session, stable_id: str) -> int:
    """Revoke all active sessions for a stable identity.

    Returns the number of sessions revoked.
    """
    if not stable_id:
        raise SessionServiceError("INVALID_IDENTITY", "stable_id is required")

    now = _now()
    rows = (
        db.query(SessionRecord)
        .filter(
            SessionRecord.stable_id == stable_id,
            SessionRecord.revoked_at.is_(None),
        )
        .all()
    )
    for record in rows:
        record.revoked_at = now
    db.flush()
    return len(rows)


def logout(db: Session, token: str) -> None:
    """Synonym for revoke_session using an access token."""
    revoke_session(db, token)
