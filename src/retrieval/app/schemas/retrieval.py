"""Pydantic request/response schemas for the Retrieval + Indexing API."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """GET /health"""

    status: str


class IndexBuildRequest(BaseModel):
    """POST /api/kb/v1/index/build"""

    space_id: str = Field(..., max_length=63)
    snapshot_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")


class IndexBuildResponse(BaseModel):
    """Result of starting an index build."""

    generation_id: uuid.UUID
    space_id: str
    snapshot_sha: str
    status: str
    chunks_indexed: int


class IndexActivateRequest(BaseModel):
    """POST /api/kb/v1/index/activate"""

    space_id: str = Field(..., max_length=63)
    profile: str = Field(..., max_length=128)
    generation_id: uuid.UUID
    fence_token: int


class IndexActivateResponse(BaseModel):
    """Result of activating a pointer."""

    pointer_id: uuid.UUID
    space_id: str
    profile: str
    generation_id: uuid.UUID
    fence_token: int
    active: bool


class IndexPointerResponse(BaseModel):
    """Active index pointer for a space/profile."""

    pointer_id: uuid.UUID
    space_id: str
    profile: str
    generation_id: uuid.UUID
    fence_token: int
    active: bool


class SearchRequest(BaseModel):
    """POST /api/kb/v1/search"""

    space_id: str = Field(..., max_length=63)
    query: str = Field(..., min_length=1)
    actor_id: uuid.UUID
    profile: str = Field(default="default", max_length=128)
    mode: Literal["semantic", "exact", "hybrid"] = "hybrid"
    top_k: int = Field(default=10, ge=1, le=100)


class SearchResultItem(BaseModel):
    """Single ranked search result."""

    chunk_id: uuid.UUID
    document_path: str
    content: str
    score: float
    mode: str
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    """Ranked search results with per-Space snapshot descriptor."""

    space_id: str
    query: str
    profile: str
    generation_id: uuid.UUID | None
    snapshot_sha: str | None
    results: list[SearchResultItem]
    authorization_filtered_count: int = 0


class ReconcileIndexRequest(BaseModel):
    """POST /api/kb/v1/index/reconcile"""

    space_id: str = Field(..., max_length=63)
    profile: str = Field(default="default", max_length=128)
    branch: str = Field(default="main", max_length=255)


class ReconcileIndexResponse(BaseModel):
    """Index-to-HEAD reconciliation report."""

    space_id: str
    profile: str
    branch: str
    status: str
    index_snapshot_sha: str | None
    head_sha: str | None
    stale: bool
