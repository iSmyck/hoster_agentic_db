"""Pydantic schemas aligned with the authz-context-v2 contract."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ExternalRef(BaseModel):
    """External identity reference, e.g. OIDC sub or LDAP objectGUID."""

    issuer: str
    sub: str


class ResolveIdentityRequest(BaseModel):
    """POST /api/kb/v1/identity/resolve"""

    external_ref: ExternalRef | dict[str, Any]


class ResolveTokenRequest(BaseModel):
    """POST /api/kb/v1/identity/resolve-token"""

    access_token: str


class IdentityResponse(BaseModel):
    """Stable identity response."""

    id: uuid.UUID
    external_refs: list[dict[str, Any]]
    created_at: datetime


class GroupRow(BaseModel):
    """Single group membership row inside a snapshot."""

    group_name: str = Field(..., max_length=512)
    member_refs: list[ExternalRef | dict[str, Any]] = Field(default_factory=list)
    parent_groups: list[str] = Field(default_factory=list)


class GroupSnapshotRequest(BaseModel):
    """POST /api/kb/v1/groups/snapshot"""

    space_id: str = Field(..., max_length=63)
    snapshot_id: uuid.UUID | None = None
    captured_at: datetime | None = None
    groups: list[GroupRow]


class PolicyBundleRequest(BaseModel):
    """POST /api/kb/v1/policies/activate"""

    space_id: str = Field(..., max_length=63)
    bundle_id: str = Field(..., max_length=256)
    repository_id: str = Field(..., max_length=128)
    access_policy_revision: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    approval_policy_revision: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    group_capabilities: dict[str, list[str]] = Field(default_factory=dict)
    path_approvers: dict[str, list[str]] = Field(default_factory=dict)


ActorType = Literal["human", "agent", "connector", "internal_ci"]


class AuthzContextRequest(BaseModel):
    """POST /api/kb/v1/authz/context"""

    space_id: str = Field(..., max_length=63)
    actor_id: uuid.UUID
    actor_type: ActorType = "human"


class PathCheckRequest(BaseModel):
    """POST /api/kb/v1/authz/check"""

    space_id: str = Field(..., max_length=63)
    actor_id: uuid.UUID
    path: str = Field(..., max_length=513)


class AuthzContextResponse(BaseModel):
    """Server-issued AuthzContext aligned with authz-context-v2."""

    schema_version: str = "authz-context-v2"
    context_id: uuid.UUID
    issuer: str
    stable_id: str
    actor_type: str
    space_scopes: list[dict[str, Any]]
    path_scopes: list[dict[str, Any]]
    evaluated_at: datetime
    expires_at: datetime
    revocation_epoch: int


class PathCheckResponse(BaseModel):
    """Path approval check response."""

    approved: bool
    space_id: str
    actor_id: uuid.UUID
    path: str
    matched_prefix: str | None = None
    reason: str


class HealthResponse(BaseModel):
    """GET /health"""

    status: str
