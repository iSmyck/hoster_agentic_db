"""Front-matter-v2 draft generator (KBI-107)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..schemas.convert import AttachmentManifestEntry

_OWNERSHIP_MODES = frozenset({"migrated", "source_managed", "curated"})


class FrontMatterError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_source_path(source_path: str) -> None:
    if not source_path or source_path.startswith("/") or ".." in Path(source_path).parts:
        raise FrontMatterError("SECURITY_BLOCKER", "invalid source_path")
    if re.search(r'[<>:"|?*\x00]', source_path):
        raise FrontMatterError("SECURITY_BLOCKER", "invalid source_path characters")


def build_front_matter_draft(
    *,
    source_path: str,
    markdown_body: str,
    attachments: list[AttachmentManifestEntry],
    ownership_mode: str,
    origin: dict[str, Any] | None,
    staged_sha256: str,
    staged_object_id: str,
    staged_version_id: str,
) -> dict[str, Any]:
    if ownership_mode not in _OWNERSHIP_MODES:
        raise FrontMatterError("FRONT_MATTER_INVALID", "invalid ownership_mode")
    title = _title_from_path(source_path, markdown_body)
    doc_id = str(uuid.uuid4())
    attachment_refs = [
        {
            "object_id": item.object_id,
            "media_type": item.media_type,
            "media_class": item.media_class,
        }
        for item in attachments
    ]
    draft: dict[str, Any] = {
        "schema_version": "document-front-matter-v2",
        "id": doc_id,
        "title": title,
        "parent_id": None,
        "ownership_mode": ownership_mode,
        "links": [],
        "valid_until": None,
        "archived": False,
        "attachments": attachment_refs,
    }
    if ownership_mode == "source_managed":
        if not origin:
            raise FrontMatterError("ORIGIN_REQUIRED", "origin is required for source_managed")
        if origin.get("ownership_mode") != "source_managed":
            raise FrontMatterError("FRONT_MATTER_INVALID", "origin ownership_mode mismatch")
        draft["origin"] = origin
    elif ownership_mode == "migrated" and origin is None:
        draft["origin"] = _default_migrated_origin(
            source_path=source_path,
            staged_object_id=staged_object_id,
            staged_version_id=staged_version_id,
            staged_sha256=staged_sha256,
        )
    elif origin is not None:
        draft["origin"] = origin
    return draft


def _title_from_path(source_path: str, markdown_body: str) -> str:
    for line in markdown_body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()[:512]
    stem = Path(source_path).stem
    return stem or "untitled"


def _default_migrated_origin(
    *,
    source_path: str,
    staged_object_id: str,
    staged_version_id: str,
    staged_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "source-origin-v1",
        "source_id": "ingest-convert",
        "source_binding_id": "kb-ingestion",
        "source_object_id": staged_object_id,
        "source_version": staged_version_id,
        "source_content_sha256": staged_sha256,
        "source_ref": source_path,
        "observed_at": datetime.now(UTC).isoformat(),
        "ownership_mode": "migrated",
    }