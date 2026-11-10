"""Pydantic models for Backup packages, manifests and exports."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BackupStatus(str, Enum):
    """Lifecycle states of a backup package."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


class FileHash(BaseModel):
    """SHA-256 hash for a single file inside a backup package."""

    path: str
    sha256: str


class BackupManifest(BaseModel):
    """Immutable manifest describing a per-Space backup package."""

    space_id: str
    backup_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    head_sha: str = ""
    hour_bucket: str = ""
    files: list[FileHash] = Field(default_factory=list)


class BackupPackage(BaseModel):
    """Status wrapper for a created or in-progress backup package."""

    space_id: str
    backup_id: str
    status: BackupStatus
    package_path: str
    manifest: BackupManifest | None = None
    error: str | None = None


class NoteSummary(BaseModel):
    """Minimal read-only MR note metadata for backup."""

    id: int
    body: str
    author_id: int | None = None
    created_at: str | None = None


class MetadataExport(BaseModel):
    """GitLab metadata exported for a Space."""

    space_id: str
    merge_requests: list[dict[str, Any]] = Field(default_factory=list)
    notes: dict[str, list[NoteSummary]] = Field(default_factory=dict)
    tags: list[dict[str, Any]] = Field(default_factory=list)


class KbOpsExport(BaseModel):
    """Read-only operational records exported from kb_ops for a Space."""

    space_id: str
    proposals: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
