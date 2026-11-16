"""Strict / pii_permitted data barrier (KBI.4.2)."""

from __future__ import annotations

import re
from typing import Any

from ..schemas.convert import CorrectionTaskDraft

_INTERNAL_PROVIDERS = frozenset({"internal", "hoster.ai"})
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"\+7[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}")
_CANARY = "SYNTHETIC_PII"


class DataBarrierError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        hits: list[dict[str, Any]] | None = None,
        correction_task: CorrectionTaskDraft | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.hits = hits or []
        self.correction_task = correction_task


def scan_pii(text: str) -> list[dict[str, Any]]:
    """Return synthetic PII hits as kind+offset only (no raw excerpts)."""
    hits: list[dict[str, Any]] = []
    if _CANARY in text:
        hits.append({"kind": "canary", "offset": text.index(_CANARY)})
    for match in _EMAIL.finditer(text):
        hits.append({"kind": "email", "offset": match.start()})
    for match in _PHONE.finditer(text):
        hits.append({"kind": "phone", "offset": match.start()})
    return hits


def enforce_data_barrier(
    *,
    data_profile: str,
    text: str,
    legal_basis: str | None = None,
    inference_provider: str = "internal",
    document_path: str = "unknown",
    document_id: str = "00000000-0000-0000-0000-000000000000",
) -> list[dict[str, Any]]:
    if data_profile == "pii_permitted":
        if not (legal_basis and legal_basis.strip()):
            raise DataBarrierError(
                "LEGAL_BASIS_REQUIRED",
                "legal_basis is required for pii_permitted",
            )
        if inference_provider not in _INTERNAL_PROVIDERS:
            raise DataBarrierError(
                "EGRESS_FORBIDDEN",
                "pii_permitted content cannot use an external inference provider",
            )
        return []
    if data_profile != "strict":
        raise DataBarrierError("INVALID_DATA_PROFILE", "invalid data_profile")
    hits = scan_pii(text)
    if not hits:
        return []
    task = CorrectionTaskDraft(
        blocker_code="PII_REVIEW_REQUIRED",
        document_path=document_path,
        document_id=document_id,
        reason="synthetic PII hit under strict profile",
    )
    raise DataBarrierError(
        "PII_BLOCKED",
        "strict profile rejected synthetic PII",
        hits=hits,
        correction_task=task,
    )
