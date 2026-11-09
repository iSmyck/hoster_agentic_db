"""SQLAlchemy ORM models for the kb_ops ingestion tables."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from ingestion.app.core.config import settings


class Base(DeclarativeBase):
    """Shared declarative base."""

    type_annotation_map: ClassVar[dict[type, Any]] = {dict: JSON, list: JSON}


_SCHEMA = settings.KB_OPS_SCHEMA


def _schema_args() -> dict[str, Any]:
    """Return table args with optional schema qualification."""
    if _SCHEMA:
        return {"schema": _SCHEMA}
    return {}


class SourceRegistry(Base):
    """Registered external source binding for a Space."""

    __tablename__ = "source_registries"
    __table_args__ = (
        Index("ix_source_registries_space_id", "space_id"),
        UniqueConstraint("space_id", "source_id"),
        _schema_args(),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    space_id: Mapped[str] = mapped_column(String(63), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB if _SCHEMA else JSON,
        default=dict,
        comment="Connector-specific configuration (path, credentials, filters).",
    )
    ownership_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="curated",
        comment="migrated | source_managed | curated | live_operational",
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    cursor: Mapped[SourceCursor | None] = relationship(
        "SourceCursor",
        back_populates="source",
        uselist=False,
        cascade="all, delete-orphan",
    )


class SourceCursor(Base):
    """Durable cursor for a registered source binding."""

    __tablename__ = "source_cursors"
    __table_args__ = (
        Index("ix_source_cursors_registry_id", "source_registry_id"),
        _schema_args(),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_registry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}source_registries.id"),
        nullable=False,
        unique=True,
    )
    cursor_value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cursor_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    last_merged_cursor: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Cursor value at the time of the last successful import.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    source: Mapped[SourceRegistry] = relationship("SourceRegistry", back_populates="cursor")


class DryRunManifest(Base):
    """Result of an import dry-run: manifest + blockers, no canonical writes."""

    __tablename__ = "dry_run_manifests"
    __table_args__ = (
        Index("ix_dry_run_manifests_space_source", "space_id", "source_id"),
        UniqueConstraint("idempotency_key"),
        _schema_args(),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    space_id: Mapped[str] = mapped_column(String(63), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        comment="pending | blocked | ready",
    )
    blockers: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB if _SCHEMA else JSON,
        default=list,
        comment="Admission blockers detected during dry-run.",
    )
    manifest_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB if _SCHEMA else JSON,
        default=dict,
        comment="Scanned source entries, provenance, path->ID mapping.",
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    import_packages: Mapped[list[ImportPackage]] = relationship(
        "ImportPackage",
        back_populates="dry_run",
        cascade="all, delete-orphan",
    )


class ImportPackage(Base):
    """Authorized import package derived from a dry-run manifest."""

    __tablename__ = "import_packages"
    __table_args__ = (
        Index("ix_import_packages_dry_run_id", "dry_run_id"),
        _schema_args(),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dry_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}dry_run_manifests.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        comment="pending | authorized | submitted | rejected",
    )
    authorized_by: Mapped[str | None] = mapped_column(String(512), nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    submitted_proposal_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="GO proposal id produced after submission.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    dry_run: Mapped[DryRunManifest] = relationship(
        "DryRunManifest",
        back_populates="import_packages",
    )
