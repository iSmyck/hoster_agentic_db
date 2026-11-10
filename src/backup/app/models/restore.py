"""Pydantic models for restore, closure verification and integrity reports."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RestoreStatus(str, Enum):
    """Lifecycle states of a restore operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


class RestoreRequest(BaseModel):
    """Request body for a restore operation."""

    backup_id: str | None = Field(
        default=None,
        description="Backup package identifier; defaults to the latest complete package.",
    )
    target_space_id: str | None = Field(
        default=None,
        description="Optional target Space identifier; defaults to the source space_id.",
    )
    force: bool = Field(
        default=False,
        description="Allow restore into an existing target Space.",
    )


class IntegrityReport(BaseModel):
    """Result of verifying every file hash in a backup package against manifest.json."""

    space_id: str
    backup_id: str
    package_path: str
    verified: bool
    checked_files: int
    mismatches: list[dict[str, Any]] = Field(default_factory=list)
    missing_files: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ClosureMismatch(BaseModel):
    """Single closure mismatch detail."""

    scope: str
    key: str
    expected: Any
    actual: Any


class ClosureReport(BaseModel):
    """Result of comparing pre-restore and post-restore closure state."""

    space_id: str
    target_space_id: str
    backup_id: str
    consistent: bool
    mismatches: list[ClosureMismatch] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RestoreStep(str, Enum):
    """Named restore steps for progress reporting."""

    INTEGRITY_CHECK = "integrity_check"
    GIT_MIRROR = "git_mirror"
    POSTGRES = "postgres"
    OBJECT_STORE = "object_store"
    CLOSURE_VERIFY = "closure_verify"


class RestoreResult(BaseModel):
    """Result of a full restore operation."""

    space_id: str
    target_space_id: str
    backup_id: str
    status: RestoreStatus
    package_path: str
    restored_steps: list[RestoreStep] = Field(default_factory=list)
    integrity_report: IntegrityReport | None = None
    closure_report: ClosureReport | None = None
    error: str | None = None
    restored_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
