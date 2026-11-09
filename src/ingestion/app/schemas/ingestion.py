"""Pydantic request/response schemas for the Ingestion API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """GET /health"""

    status: str


class SourceCreateRequest(BaseModel):
    """POST /api/kb/v1/sources"""

    space_id: str = Field(..., max_length=63)
    source_id: str = Field(..., max_length=128)
    source_type: str = Field(..., max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)
    ownership_mode: Literal["migrated", "source_managed", "curated", "live_operational"] = "curated"
    enabled: bool = True


class SourceResponse(BaseModel):
    """SourceRegistry projection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    space_id: str
    source_id: str
    source_type: str
    config: dict[str, Any]
    ownership_mode: str
    enabled: bool
    created_at: datetime


class SourceUpdateRequest(BaseModel):
    """PATCH /api/kb/v1/sources/{source_id}"""

    config: dict[str, Any] | None = None
    ownership_mode: Literal["migrated", "source_managed", "curated", "live_operational"] | None = (
        None
    )
    enabled: bool | None = None


class CursorUpdateRequest(BaseModel):
    """POST /api/kb/v1/sources/{source_id}/cursor"""

    cursor_value: str
    cursor_hash: str


class CursorResponse(BaseModel):
    """SourceCursor projection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_registry_id: uuid.UUID
    cursor_value: str
    cursor_hash: str
    last_merged_cursor: str | None
    updated_at: datetime


class DryRunRequest(BaseModel):
    """POST /api/kb/v1/sources/{source_id}/dry-run"""

    idempotency_key: str | None = Field(default=None, max_length=255)


class DryRunResponse(BaseModel):
    """DryRunManifest projection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    space_id: str
    source_id: str
    status: str
    blockers: list[dict[str, Any]]
    manifest_data: dict[str, Any]
    idempotency_key: str
    created_at: datetime


class AuthorizeRequest(BaseModel):
    """POST /api/kb/v1/dry-runs/{dry_run_id}/authorize"""

    authorized_by: str = Field(..., max_length=512)


class ImportPackageResponse(BaseModel):
    """ImportPackage projection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dry_run_id: uuid.UUID
    status: str
    authorized_by: str | None
    authorized_at: datetime | None
    submitted_proposal_id: str | None
    created_at: datetime


class ConflictCheckRequest(BaseModel):
    """Request body for three-way conflict detection."""

    source_cursor: str | None = None
    last_merged_cursor: str | None = None
    go_head: str | None = None


class ConflictCheckResponse(BaseModel):
    """Three-way conflict detection result."""

    space_id: str
    source_id: str
    conflict: bool
    mismatches: list[str]
    current_source_cursor: str
    last_merged_cursor: str | None
    current_go_head: str
