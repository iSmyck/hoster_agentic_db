"""Controlled import: authorization gate and GO proposal submission."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from ingestion.app.adapters.go_client import GOClient
from ingestion.app.models.ingestion import DryRunManifest, ImportPackage
from ingestion.app.services import source_registry as registry_service


class ImporterError(Exception):
    """Domain error raised by import operations."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def create_import_package(
    db: Session,
    dry_run_id: uuid.UUID,
    authorized_by: str,
) -> ImportPackage:
    """Authorize a dry-run manifest for import.

    Requires a separate authorization step before any GO proposal is created.
    """
    dry_run = db.get(DryRunManifest, dry_run_id)
    if dry_run is None:
        raise ImporterError("NOT_FOUND", "dry-run manifest not found")
    if dry_run.status != "ready":
        raise ImporterError(
            "NOT_AUTHORIZED",
            f"dry-run is {dry_run.status}; cannot authorize",
        )

    pending = db.query(ImportPackage).filter_by(dry_run_id=dry_run_id, status="pending").first()
    if pending is not None:
        if pending.authorized_by != authorized_by:
            raise ImporterError(
                "AUTHORIZATION_CONFLICT",
                "pending import package already exists with a different authorized_by",
            )
        return pending

    package = ImportPackage(
        dry_run_id=dry_run_id,
        status="authorized",
        authorized_by=authorized_by,
        authorized_at=datetime.now(UTC),
    )
    db.add(package)
    db.flush()
    return package


def submit_source_proposal(
    db: Session,
    go_client: GOClient,
    space_id: str,
    import_package_id: uuid.UUID,
) -> ImportPackage:
    """Submit an authorized import package as a GO proposal.

    The import package must be authorized first. The resulting proposal goes
    through the normal GO/MR lifecycle; ingestion never merges directly.
    """
    package = db.get(ImportPackage, import_package_id)
    if package is None:
        raise ImporterError("NOT_FOUND", "import package not found")
    if package.status != "authorized":
        raise ImporterError(
            "INVALID_STATE",
            f"import package is {package.status}; must be authorized first",
        )

    dry_run = package.dry_run
    source = registry_service.get_source(db, space_id, dry_run.source_id)

    entries = dry_run.manifest_data.get("entries", [])
    if not entries:
        raise ImporterError("EMPTY_MANIFEST", "no entries to import")

    proposal_content = _build_proposal_content(entries)
    proposal_sha = _hash_hex(proposal_content)
    base_sha = go_client.get_current_head(space_id) or "0" * 40
    target_branch = source.config.get("target_branch", "main")

    idempotency_key = f"import:{space_id}:{source.source_id}:{import_package_id}"

    proposal_payload = {
        "space_id": space_id,
        "proposal_sha": proposal_sha,
        "base_sha": base_sha,
        "target_branch": target_branch,
        "idempotency_key": idempotency_key,
        "proposal_data": {
            "origin": "ingestion",
            "source_id": source.source_id,
            "source_type": source.source_type,
            "import_package_id": str(import_package_id),
            "dry_run_id": str(dry_run.id),
            "entries": entries,
            "ownership_mode": source.ownership_mode,
        },
    }

    try:
        proposal = go_client.submit_proposal(proposal_payload)
    except Exception as exc:
        raise ImporterError(
            "PROPOSAL_SUBMISSION_FAILED",
            f"failed to submit GO proposal: {exc}",
        ) from exc

    package.status = "submitted"
    package.submitted_proposal_id = str(proposal.get("id", ""))

    cursor_record = registry_service.get_or_create_cursor(db, source)
    cursor_record.last_merged_cursor = cursor_record.cursor_value

    db.flush()
    return package


def _build_proposal_content(entries: list[dict[str, Any]]) -> str:
    """Serialize manifest entries into a deterministic proposal payload string."""
    payload = {
        "schema_version": "ingestion-import-v1",
        "entries": [
            {
                "path": e["path"],
                "media_type": e["media_type"],
                "size": e["size"],
                "metadata": e.get("metadata", {}),
            }
            for e in entries
        ],
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _hash_hex(value: str) -> str:
    """Return a 40-character hex SHA-1 for compatibility with Git object IDs."""
    return hashlib.sha1(value.encode("utf-8")).hexdigest()
