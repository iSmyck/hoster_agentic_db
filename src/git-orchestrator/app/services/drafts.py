"""Draft service for durable browser editor state."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from ..models.ops import DraftRecord


class DraftServiceError(Exception):
    """Domain error raised by the draft service."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _make_idempotency_key(space_id: str, path: str, author_stable_id: str) -> str:
    """Return a deterministic idempotency key for a draft slot.

    The key is scoped to (space, path, author) so the same author always
    updates the same draft for a given page, while different authors or
    pages get independent drafts.
    """
    return f"draft:{space_id}:{path}:{author_stable_id}"


def save_draft(
    db: Session,
    space_id: str,
    path: str,
    author_stable_id: str,
    content: str,
    target_branch: str = "main",
    base_sha: str | None = None,
) -> DraftRecord:
    """Create or update the durable draft for the author's page slot."""
    idempotency_key = _make_idempotency_key(space_id, path, author_stable_id)
    existing = (
        db.query(DraftRecord)
        .filter_by(
            space_id=space_id,
            path=path,
            author_stable_id=author_stable_id,
        )
        .first()
    )
    now = datetime.now(UTC)
    if existing is not None:
        existing.content = content
        existing.target_branch = target_branch
        existing.base_sha = base_sha
        existing.updated_at = now
        db.flush()
        return existing

    record = DraftRecord(
        id=uuid.uuid5(uuid.NAMESPACE_URL, idempotency_key),
        space_id=space_id,
        path=path,
        author_stable_id=author_stable_id,
        content=content,
        target_branch=target_branch,
        base_sha=base_sha,
        idempotency_key=idempotency_key,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    db.flush()
    return record


def get_draft(
    db: Session,
    space_id: str,
    path: str,
    author_stable_id: str,
) -> DraftRecord | None:
    """Return the draft for the author's page slot, if any."""
    return (
        db.query(DraftRecord)
        .filter_by(
            space_id=space_id,
            path=path,
            author_stable_id=author_stable_id,
        )
        .first()
    )


def list_drafts(
    db: Session,
    space_id: str,
    author_stable_id: str,
    cursor: str | None = None,
    limit: int = 20,
) -> tuple[list[DraftRecord], str | None]:
    """Return drafts for the author in the Space, ordered by updated_at desc.

    The ``cursor`` is an ISO timestamp used for pagination. The returned
    next_cursor is None when no further pages are expected.
    """
    query = (
        db.query(DraftRecord)
        .filter_by(space_id=space_id, author_stable_id=author_stable_id)
        .order_by(DraftRecord.updated_at.desc())
    )
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            query = query.filter(DraftRecord.updated_at < cursor_dt)
        except ValueError as exc:
            raise DraftServiceError("INVALID_CURSOR", f"invalid cursor: {exc}") from exc
    records = query.limit(limit + 1).all()
    next_cursor = None
    if len(records) > limit:
        records = records[:limit]
        next_cursor = records[-1].updated_at.isoformat().replace("+00:00", "Z")
    return records, next_cursor


def discard_draft(
    db: Session,
    space_id: str,
    path: str,
    author_stable_id: str,
) -> bool:
    """Delete the draft for the author's page slot. Return True if deleted."""
    existing = (
        db.query(DraftRecord)
        .filter_by(
            space_id=space_id,
            path=path,
            author_stable_id=author_stable_id,
        )
        .first()
    )
    if existing is None:
        return False
    db.delete(existing)
    db.flush()
    return True


def draft_to_dict(record: DraftRecord) -> dict[str, Any]:
    """Serialize a DraftRecord to a JSON-friendly dict."""
    return {
        "id": str(record.id),
        "space_id": record.space_id,
        "path": record.path,
        "author_stable_id": record.author_stable_id,
        "content": record.content,
        "base_sha": record.base_sha,
        "target_branch": record.target_branch,
        "idempotency_key": record.idempotency_key,
        "created_at": record.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": record.updated_at.isoformat().replace("+00:00", "Z"),
    }
