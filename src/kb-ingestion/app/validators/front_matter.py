"""Front-matter-v2 draft generator (KBI-107)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from ..schemas.convert import AttachmentManifestEntry

_CONTRACTS = Path(__file__).resolve().parents[4] / "specs" / "corporate-kb" / "contracts"

_OWNERSHIP_MODES = frozenset({"migrated", "source_managed", "curated"})
_FORBIDDEN_KEYS = frozenset({"access", "owner", "status"})


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


def attachment_to_front_matter_ref(entry: AttachmentManifestEntry) -> dict[str, Any]:
    ref: dict[str, Any] = {
        "object_id": entry.object_id,
        "version": entry.version,
        "sha256": entry.sha256,
        "size": entry.size,
        "media_type": entry.media_type,
        "source_ref": entry.source_ref,
        "media_class": entry.media_class,
        "verification_status": entry.verification_status,
    }
    if entry.alt_text:
        ref["description"] = {"automatic": entry.automatic, "text": entry.alt_text}
    return ref


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
    attachment_refs = [attachment_to_front_matter_ref(item) for item in attachments]
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
    _validate_against_schema(draft)
    return draft


@lru_cache(maxsize=1)
def _front_matter_validator() -> Draft202012Validator:
    fm_schema = json.loads((_CONTRACTS / "front-matter.schema.json").read_text())
    origin_schema = json.loads((_CONTRACTS / "source-origin.schema.json").read_text())
    registry = Registry().with_resources(
        [
            (
                "front-matter.schema.json",
                Resource.from_contents(fm_schema, default_specification=DRAFT202012),
            ),
            (
                "source-origin.schema.json",
                Resource.from_contents(origin_schema, default_specification=DRAFT202012),
            ),
            (
                "./source-origin.schema.json",
                Resource.from_contents(origin_schema, default_specification=DRAFT202012),
            ),
        ]
    )
    return Draft202012Validator(
        fm_schema,
        registry=registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def validate_front_matter_draft(draft: dict[str, Any]) -> None:
    """Validate a front-matter mapping against document-front-matter-v2."""
    enforce_front_matter(draft)


def enforce_front_matter(draft: dict[str, Any]) -> None:
    """Reject forbidden keys, archive invariant breaks, and schema-invalid drafts."""
    if not isinstance(draft, dict):
        raise FrontMatterError("FRONT_MATTER_INVALID", "front matter must be an object")
    forbidden = sorted(_FORBIDDEN_KEYS.intersection(draft))
    if forbidden:
        raise FrontMatterError(
            "FRONT_MATTER_INVALID",
            f"forbidden front-matter keys: {', '.join(forbidden)}",
        )
    archived = bool(draft.get("archived"))
    has_archive = draft.get("archive") is not None
    if archived != has_archive:
        raise FrontMatterError(
            "ARCHIVE_INVARIANT_VIOLATION",
            "archived=true if and only if archive is present",
        )
    if draft.get("ownership_mode") == "source_managed" and not draft.get("origin"):
        raise FrontMatterError("ORIGIN_REQUIRED", "origin is required for source_managed")
    _validate_against_schema(draft)


def _validate_against_schema(draft: dict[str, Any]) -> None:
    try:
        _front_matter_validator().validate(draft)
    except ValidationError as exc:
        raise FrontMatterError("FRONT_MATTER_INVALID", exc.message) from exc


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