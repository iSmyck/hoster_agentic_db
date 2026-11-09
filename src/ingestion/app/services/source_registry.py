"""Source registry CRUD and cursor management."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ingestion.app.adapters.source_connector import SOURCE_CONNECTOR_REGISTRY
from ingestion.app.models.ingestion import SourceCursor, SourceRegistry


class SourceRegistryError(Exception):
    """Domain error raised by source registry operations."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def create_source(
    db: Session,
    space_id: str,
    source_id: str,
    source_type: str,
    config: dict[str, Any],
    ownership_mode: str = "curated",
    enabled: bool = True,
) -> SourceRegistry:
    """Register a new source binding."""
    if source_type not in SOURCE_CONNECTOR_REGISTRY:
        raise SourceRegistryError(
            "INVALID_SOURCE_TYPE",
            f"unknown source_type: {source_type}",
        )
    existing = db.query(SourceRegistry).filter_by(space_id=space_id, source_id=source_id).first()
    if existing is not None:
        raise SourceRegistryError(
            "ALREADY_EXISTS",
            f"source {source_id} already exists in space {space_id}",
        )
    source = SourceRegistry(
        space_id=space_id,
        source_id=source_id,
        source_type=source_type,
        config=config,
        ownership_mode=ownership_mode,
        enabled=enabled,
    )
    db.add(source)
    db.flush()
    return source


def get_source(db: Session, space_id: str, source_id: str) -> SourceRegistry:
    """Return a source binding by natural key."""
    source = db.query(SourceRegistry).filter_by(space_id=space_id, source_id=source_id).first()
    if source is None:
        raise SourceRegistryError("NOT_FOUND", "source binding not found")
    return source


def update_source(
    db: Session,
    space_id: str,
    source_id: str,
    config: dict[str, Any] | None = None,
    ownership_mode: str | None = None,
    enabled: bool | None = None,
) -> SourceRegistry:
    """Update mutable fields of a source binding."""
    source = get_source(db, space_id, source_id)
    if config is not None:
        source.config = config
    if ownership_mode is not None:
        source.ownership_mode = ownership_mode
    if enabled is not None:
        source.enabled = enabled
    db.flush()
    return source


def delete_source(db: Session, space_id: str, source_id: str) -> None:
    """Remove a source binding and its dependent cursor/manifests."""
    source = get_source(db, space_id, source_id)
    db.delete(source)


def get_or_create_cursor(db: Session, source: SourceRegistry) -> SourceCursor:
    """Return the source cursor, creating an empty one if absent."""
    cursor = db.query(SourceCursor).filter_by(source_registry_id=source.id).first()
    if cursor is not None:
        return cursor
    cursor = SourceCursor(
        source_registry_id=source.id,
        cursor_value="",
        cursor_hash="",
    )
    db.add(cursor)
    db.flush()
    return cursor


def update_cursor(
    db: Session,
    source: SourceRegistry,
    cursor_value: str,
    cursor_hash: str,
) -> SourceCursor:
    """Persist a new cursor for the source binding."""
    cursor = get_or_create_cursor(db, source)
    cursor.cursor_value = cursor_value
    cursor.cursor_hash = cursor_hash
    db.flush()
    return cursor
