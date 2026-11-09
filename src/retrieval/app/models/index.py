"""SQLAlchemy ORM models for the kb_index schema."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from retrieval.app.core.config import settings


class Base(DeclarativeBase):
    """Shared declarative base."""

    type_annotation_map: ClassVar[dict[type, Any]] = {dict: JSON, list: JSON}


_SCHEMA = settings.KB_INDEX_SCHEMA


def _schema_args() -> dict[str, Any]:
    """Return table args with optional schema qualification."""
    if _SCHEMA:
        return {"schema": _SCHEMA}
    return {}


def _embedding_type(dimensions: int) -> Any:
    """Return pgvector Vector for PostgreSQL, JSON array fallback for SQLite."""
    if settings.DATABASE_URL.startswith("sqlite"):
        return JSON
    from pgvector.sqlalchemy import Vector

    return Vector(dimensions)


class IndexGeneration(Base):
    """A completed or in-progress index build for a Space/snapshot."""

    __tablename__ = "index_generations"
    __table_args__ = (
        Index(
            "ix_index_generations_space_id_snapshot_sha",
            "space_id",
            "snapshot_sha",
        ),
        _schema_args(),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    space_id: Mapped[str] = mapped_column(String(63), nullable=False, index=True)
    snapshot_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="building",
        comment="building | ready | active | failed | superseded",
    )
    ordering: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Monotonic generation sequence within a Space.",
    )
    equivalence_evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB if _SCHEMA else JSON,
        default=dict,
        comment="Closure, hash and validation evidence for this generation.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class IndexPointer(Base):
    """Active pointer selecting the serving generation for a Space/profile."""

    __tablename__ = "index_pointers"
    __table_args__ = (
        Index(
            "ix_index_pointers_space_profile_active",
            "space_id",
            "profile",
            "active",
            unique=True,
            postgresql_where="active",
        ),
        _schema_args(),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    space_id: Mapped[str] = mapped_column(String(63), nullable=False, index=True)
    profile: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    generation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}index_generations.id"),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fence_token: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Monotonic CAS token for pointer updates.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Chunk(Base):
    """A searchable chunk belonging to an index generation."""

    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunks_document_path", "document_path"),
        _schema_args(),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    generation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}index_generations.id"),
        nullable=False,
        index=True,
    )
    document_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any] = mapped_column(
        _embedding_type(settings.EMBEDDING_DIMENSIONS),
        nullable=True,
        comment="Embedding vector (pgvector on PostgreSQL, JSON array on SQLite).",
    )
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB if _SCHEMA else JSON,
        default=dict,
        comment="Citation metadata such as section heading and chunk index.",
    )


class SearchLog(Base):
    """Audit log of search queries and result counts."""

    __tablename__ = "search_logs"
    __table_args__ = _schema_args()

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    space_id: Mapped[str] = mapped_column(String(63), nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    profile: Mapped[str] = mapped_column(String(128), nullable=False)
    results_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actor_id: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
