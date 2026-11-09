"""Dry-run business logic: scan, manifest, blockers, conflict detection."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from sqlalchemy.orm import Session

from ingestion.app.adapters.go_client import GOClient
from ingestion.app.adapters.source_connector import SourceConnector
from ingestion.app.models.ingestion import DryRunManifest
from ingestion.app.services import source_registry as registry_service


class DryRunError(Exception):
    """Domain error raised by dry-run operations."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


_MEDIA_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".mp4",
    ".mov",
    ".avi",
    ".mp3",
    ".wav",
    ".ogg",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
}

_SECURITY_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".sh",
    ".bash",
    ".bin",
    ".com",
    ".dll",
    ".so",
    ".dylib",
    ".msi",
    ".app",
    ".apk",
    ".jar",
}

_SUPPORTED_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".html",
    ".htm",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
}

_PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}


def run_dry_run(
    db: Session,
    connector: SourceConnector,
    space_id: str,
    source_id: str,
    idempotency_key: str,
) -> DryRunManifest:
    """Scan a source, build a manifest, detect blockers, and store the result.

    This function never performs canonical writes or emits queue events.
    """
    source = registry_service.get_source(db, space_id, source_id)
    cursor_record = registry_service.get_or_create_cursor(db, source)

    result = connector.scan(cursor_record.cursor_value or None)

    entries_data = []
    blockers: list[dict[str, Any]] = []
    for entry in result.entries:
        entry_blockers = _detect_blockers(entry)
        blockers.extend(entry_blockers)
        entries_data.append(
            {
                "path": entry.path,
                "media_type": entry.media_type,
                "size": entry.size,
                "metadata": entry.metadata,
                "blockers": [b["type"] for b in entry_blockers],
            }
        )

    status = "blocked" if blockers else "ready"
    manifest_data = {
        "scanned_count": len(result.entries),
        "cursor_value": result.cursor_value,
        "cursor_hash": result.cursor_hash,
        "entries": entries_data,
        "ownership_mode": source.ownership_mode,
    }

    existing = db.query(DryRunManifest).filter_by(idempotency_key=idempotency_key).first()
    if existing is not None:
        if existing.status != status or existing.manifest_data != manifest_data:
            raise DryRunError(
                "IDEMPOTENCY_KEY_REUSED",
                "idempotency_key already used with a different dry-run",
            )
        return existing

    manifest = DryRunManifest(
        space_id=space_id,
        source_id=source_id,
        status=status,
        blockers=blockers,
        manifest_data=manifest_data,
        idempotency_key=idempotency_key,
    )
    db.add(manifest)
    db.flush()
    return manifest


def detect_three_way_conflict(
    db: Session,
    go_client: GOClient,
    space_id: str,
    source_id: str,
    proposed_state: dict[str, Any],
) -> dict[str, Any]:
    """Compare source cursor, last merged state, and current GO state.

    Returns a conflict report. A conflict means the proposed import is stale
    relative to at least one of the three reference points.
    """
    source = registry_service.get_source(db, space_id, source_id)
    cursor_record = registry_service.get_or_create_cursor(db, source)

    current_source_cursor = cursor_record.cursor_value
    last_merged_cursor = cursor_record.last_merged_cursor
    current_go_head = go_client.get_current_head(space_id)

    mismatches: list[str] = []
    if proposed_state.get("source_cursor") != current_source_cursor:
        mismatches.append("source_cursor")
    if (
        last_merged_cursor is not None
        and proposed_state.get("last_merged_cursor") != last_merged_cursor
    ):
        mismatches.append("last_merged_cursor")
    if proposed_state.get("go_head") != current_go_head:
        mismatches.append("go_head")

    return {
        "space_id": space_id,
        "source_id": source_id,
        "conflict": bool(mismatches),
        "mismatches": mismatches,
        "current_source_cursor": current_source_cursor,
        "last_merged_cursor": last_merged_cursor,
        "current_go_head": current_go_head,
    }


def _detect_blockers(entry: Any) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    path_lower = entry.path.lower()
    ext = PathExtension(path_lower).suffix

    if ext in _SECURITY_EXTENSIONS:
        blockers.append(
            {
                "type": "security",
                "path": entry.path,
                "detail": f"executable/security-risk extension {ext}",
            }
        )

    if ext in _MEDIA_EXTENSIONS:
        blockers.append(
            {
                "type": "media",
                "path": entry.path,
                "detail": f"media/attachment extension {ext} requires explicit handling",
            }
        )

    if ext not in _SUPPORTED_EXTENSIONS:
        blockers.append(
            {
                "type": "unsupported_format",
                "path": entry.path,
                "detail": f"unsupported extension {ext}",
            }
        )

    text = _entry_text(entry)
    if text:
        for pii_type, pattern in _PII_PATTERNS.items():
            if pattern.search(text):
                blockers.append(
                    {
                        "type": "pii",
                        "path": entry.path,
                        "detail": f"potential {pii_type} detected",
                    }
                )
                break

    return blockers


def _entry_text(entry: Any) -> str | None:
    try:
        return entry.content.decode("utf-8")
    except (AttributeError, UnicodeDecodeError):
        return None


class PathExtension:
    """Tiny helper to extract the last suffix from a lower-case path."""

    def __init__(self, path: str) -> None:
        self.path = path

    @property
    def suffix(self) -> str:
        if "." not in self.path:
            return ""
        return self.path[self.path.rfind(".") :]


def build_idempotency_key(
    space_id: str,
    source_id: str,
    cursor_value: str = "",
    cursor_hash: str = "",
    prefix: str = "dry-run",
) -> str:
    """Build a deterministic idempotency key for dry-run operations.

    The key is stable for identical space/source/cursor inputs so that repeated
    dry-runs without an explicit client key return the cached manifest.
    """
    payload = f"{prefix}:{space_id}:{source_id}:{cursor_value}:{cursor_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
