"""Validation request/response models (KBI.4.1–4.2)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .convert import CorrectionTaskDraft


class FrontMatterValidateRequest(BaseModel):
    front_matter: dict[str, Any]


class FrontMatterValidateReport(BaseModel):
    valid: bool = True


class DataBarrierRequest(BaseModel):
    data_profile: Literal["strict", "pii_permitted"]
    text: str = ""
    legal_basis: str | None = None
    inference_provider: str = Field(default="internal", min_length=1)
    document_path: str = "unknown"
    document_id: str = "00000000-0000-0000-0000-000000000000"


class DataBarrierReport(BaseModel):
    valid: bool = True
    hits: list[dict[str, Any]] = Field(default_factory=list)
    correction_task: CorrectionTaskDraft | None = None
