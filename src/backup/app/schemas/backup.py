"""Request/response schemas for the Backup adapter API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    code: str
    detail: str


class BackupCreateResponse(BaseModel):
    space_id: str
    backup_id: str
    status: str
    package_path: str


class BackupLatestResponse(BaseModel):
    space_id: str
    backup_id: str
    status: str
    package_path: str
    manifest: dict[str, Any] | None = None


class ObjectUploadResponse(BaseModel):
    object_id: str
    version: str
    version_id: str | None = None
    sha256: str
    size: int


class RestoreResponse(BaseModel):
    space_id: str
    target_space_id: str
    backup_id: str
    status: str
    package_path: str
    restored_steps: list[str]
    restored_at: str | None = None
    integrity_report: dict[str, Any] | None = None
    closure_report: dict[str, Any] | None = None
    error: str | None = None


class IntegrityResponse(BaseModel):
    space_id: str
    backup_id: str
    package_path: str
    verified: bool
    checked_files: int
    checked_at: str | None = None
    mismatches: list[dict[str, Any]]
    missing_files: list[str]
