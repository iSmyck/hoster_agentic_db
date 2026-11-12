"""Pydantic schemas for the Session service."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExternalRef(BaseModel):
    """External identity reference used to derive a stable_id."""

    issuer: str
    sub: str


class CreateSessionRequest(BaseModel):
    """POST /api/kb/v1/session/create"""

    external_ref: dict[str, Any] | None = None
    stable_id: str | None = None
    access_policy_revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    approval_policy_revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    extra_claims: dict[str, Any] = Field(default_factory=dict)


class TokenPairResponse(BaseModel):
    """Issued token pair."""

    access_token: str
    refresh_token: str
    session_id: uuid.UUID
    stable_id: str
    access_expires_at: datetime
    refresh_expires_at: datetime


class RefreshRequest(BaseModel):
    """POST /api/kb/v1/session/refresh"""

    refresh_token: str = Field(..., min_length=1, max_length=8192)


class LogoutRequest(BaseModel):
    """POST /api/kb/v1/session/logout"""

    access_token: str = Field(..., min_length=1, max_length=8192)


class ValidationResponse(BaseModel):
    """GET /api/kb/v1/session/validate"""

    session_id: uuid.UUID
    stable_id: str
    access_policy_revision: str
    approval_policy_revision: str
    role: str = "user"
    groups: list[str] = Field(default_factory=list)


class RevokeAllRequest(BaseModel):
    """POST /api/kb/v1/session/revoke-all"""

    stable_id: str = Field(..., min_length=1, max_length=1024)


class HealthResponse(BaseModel):
    """GET /health"""

    status: str
