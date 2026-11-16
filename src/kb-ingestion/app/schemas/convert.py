"""Request/response models for convert pipeline."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ConvertRunRequest(BaseModel):
    space_id: str
    client_id: str
    object_id: str
    source_path: str = Field(min_length=1, max_length=1024)
    ownership_mode: Literal["migrated", "source_managed", "curated"] = "migrated"
    origin: dict[str, Any] | None = None


class AttachmentManifestEntry(BaseModel):
    object_id: str
    media_type: str
    media_class: str
    alt_text: str
    automatic: bool = False
    verification_status: Literal["pending"] | None = None


class DryRunReport(BaseModel):
    path_map: dict[str, str]
    markdown: str
    attachments: list[AttachmentManifestEntry]
    blockers: list[dict[str, str]]
    losses: list[dict[str, str]]
    errors: list[dict[str, str]]
    front_matter_draft: dict[str, Any]
    status: Literal["ready", "blocked"]