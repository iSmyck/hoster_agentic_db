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
    data_profile: Literal["strict", "pii_permitted"] = "strict"
    legal_basis: str | None = None
    inference_provider: str = "internal"


class AttachmentManifestEntry(BaseModel):
    object_id: str
    version: str
    sha256: str
    size: int
    media_type: str
    source_ref: str
    media_class: str
    verification_status: Literal["not_required", "pending", "verified", "rejected"]
    alt_text: str
    automatic: bool = False
    diagram_candidate: bool = False
    mermaid_source: str | None = None
    mermaid_status: Literal["none", "skipped", "generated", "validated", "invalid"] = "none"


class CorrectionTaskDraft(BaseModel):
    schema_version: Literal["docops-correction-task-v1"] = "docops-correction-task-v1"
    state: Literal["proposed_draft"] = "proposed_draft"
    blocker_code: str
    document_path: str
    document_id: str
    reason: str


class DryRunReport(BaseModel):
    path_map: dict[str, str]
    markdown_object_id: str
    markdown: str
    attachments: list[AttachmentManifestEntry]
    blockers: list[dict[str, str]]
    losses: list[dict[str, str]]
    errors: list[dict[str, str]]
    front_matter_draft: dict[str, Any]
    correction_tasks: list[CorrectionTaskDraft]
    status: Literal["ready", "blocked"]