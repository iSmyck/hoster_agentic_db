"""SQLAlchemy ORM models for the kb_ops schema (Git Orchestrator projections)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from ..core.config import settings


class Base(DeclarativeBase):
    """Shared declarative base."""

    type_annotation_map: ClassVar[dict[type, Any]] = {dict: JSON, list: JSON}


_SCHEMA = settings.KB_OPS_SCHEMA


def _schema_args() -> dict[str, Any]:
    """Return table args with optional schema qualification."""
    if _SCHEMA:
        return {"schema": _SCHEMA}
    return {}


class ProposalRecord(Base):
    """Operational projection of a canonical ProposalVersion/MR pair."""

    __tablename__ = "proposals"
    __table_args__ = (
        Index("ix_proposals_space_id", "space_id"),
        _schema_args(),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    space_id: Mapped[str] = mapped_column(String(63), nullable=False)
    proposal_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    base_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    target_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    proposal_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB if _SCHEMA else JSON,
        default=dict,
        comment="Canonical ProposalRecord payload plus operational metadata (e.g. mr_iid).",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="in_review",
        comment="in_review | rejected | cancelled | merged | superseded | conflicted | quarantined",
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    recovery_required: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        comment="Durable per-target merge barrier; blocks new merges until reconciled.",
    )
    merge_fence_token: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Monotonic fencing token for per-target merge serialization.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class DecisionRecord(Base):
    """Operational projection of a canonical DecisionRecord (note/tag)."""

    __tablename__ = "decisions"
    __table_args__ = (
        Index("ix_decisions_proposal_id", "proposal_id"),
        _schema_args(),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}proposals.id"),
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="accepted | rejected | cancelled",
    )
    decision_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB if _SCHEMA else JSON,
        default=dict,
        comment="Canonical DecisionRecord payload.",
    )
    actor_id: Mapped[str] = mapped_column(String(512), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    record_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        comment="SHA-256 of the canonical JSON DecisionRecord.",
    )
    note_id: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="GitLab MR note ID containing the canonical record.",
    )
    tag_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        comment="Protected annotated tag name kb-decisions/<decision_id>.",
    )
    supersedes_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}decisions.id"),
        nullable=True,
    )
    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="recorded",
        comment="recorded | merge_attempted | merged | failed | conflicted | invalid | quarantined",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class SourceSyncCursor(Base):
    """Durable cursor for a (Space, source binding, source object)."""

    __tablename__ = "source_sync_cursors"
    __table_args__ = (
        Index("ix_cursors_space_source", "space_id", "source_id"),
        _schema_args(),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    space_id: Mapped[str] = mapped_column(String(63), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    cursor_value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cursor_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CutoverRecord(Base):
    """Operational projection of a Space cutover state machine."""

    __tablename__ = "cutovers"
    __table_args__ = (
        Index("ix_cutovers_space_id", "space_id"),
        _schema_args(),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    space_id: Mapped[str] = mapped_column(String(63), nullable=False)
    cutover_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    signed_by: Mapped[str] = mapped_column(String(512), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="freeze_pending",
        comment="freeze_pending | frozen | protected | preflight | activating | activated | failed",
    )
