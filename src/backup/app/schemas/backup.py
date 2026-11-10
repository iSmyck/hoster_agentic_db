"""Request/response schemas for the Backup adapter API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    code: str
    message: str


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
