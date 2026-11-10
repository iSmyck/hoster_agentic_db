"""Pydantic request/response schemas for the Git Orchestrator API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """GET /health"""

    status: str


class DocumentReadRequest(BaseModel):
    """POST /api/kb/v1/documents/read"""

    space_id: str = Field(..., max_length=63)
    path: str = Field(..., max_length=2048)
    sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")


class DocumentReadResponse(BaseModel):
    """Exact-SHA document read result."""

    space_id: str
    path: str
    sha: str
    content: str


class TreeRequest(BaseModel):
    """POST /api/kb/v1/documents/tree"""

    space_id: str = Field(..., max_length=63)
    sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")


class TreeEntry(BaseModel):
    """Single tree entry."""

    path: str
    type: str
    sha: str
    mode: str | None = None


class TreeResponse(BaseModel):
    """Tree listing result."""

    space_id: str
    sha: str
    entries: list[TreeEntry]


class ProposalSubmitRequest(BaseModel):
    """POST /api/kb/v1/proposals"""

    space_id: str = Field(..., max_length=63)
    proposal_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    base_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    target_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    target_branch: str = Field(default="main", max_length=255)
    idempotency_key: str = Field(..., max_length=255)
    proposal_data: dict[str, Any] = Field(default_factory=dict)


class ProposalResponse(BaseModel):
    """Stored ProposalRecord projection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    space_id: str
    proposal_sha: str
    base_sha: str
    target_sha: str | None
    status: str
    idempotency_key: str
    proposal_data: dict[str, Any]
    created_at: datetime


class DecisionRecordRequest(BaseModel):
    """POST /api/kb/v1/decisions"""

    proposal_id: uuid.UUID
    action: Literal["accepted", "rejected", "cancelled"]
    actor_id: str = Field(..., max_length=512)
    idempotency_key: str = Field(..., max_length=255)
    decision_data: dict[str, Any] = Field(default_factory=dict)


class DecisionResponse(BaseModel):
    """Stored DecisionRecord projection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    proposal_id: uuid.UUID
    outcome: str
    actor_id: str
    idempotency_key: str
    record_sha256: str
    note_id: int | None
    tag_name: str
    state: str
    supersedes_decision_id: uuid.UUID | None
    created_at: datetime


class MergeResponse(BaseModel):
    """Result of executing a proposal merge."""

    proposal_id: uuid.UUID
    status: str
    merge_sha: str | None
    detail: str
    fence_token: int | None = None
    recovery_required: bool | None = None


class MergeRulesResponse(BaseModel):
    """Protected-branch / merge-only rules for a Space."""

    space_id: str
    protected: bool
    merge_only: bool
    rules: dict[str, Any]


class PrepareBranchRequest(BaseModel):
    """POST /api/g1-editor/prepare-branch"""

    space_id: str = Field(..., max_length=63)
    branch: str = Field(..., max_length=255)
    file_path: str = Field(..., max_length=2048)
    content: str
    idempotency_key: str = Field(..., max_length=255)


class PrepareBranchResponse(BaseModel):
    """Branch/commit preparation result for the browser editor."""

    space_id: str
    proposal_sha: str
    base_sha: str
    proposal_branch: str
    file_path: str
