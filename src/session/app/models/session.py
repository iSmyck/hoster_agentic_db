"""SQLAlchemy ORM models for the kb_sessions schema."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from session.app.core.config import settings


class Base(DeclarativeBase):
    """Shared declarative base."""

    type_annotation_map: ClassVar[dict[type, Any]] = {dict: JSON, list: JSON}


_SCHEMA = settings.KB_SESSIONS_SCHEMA


def _schema_args() -> dict[str, Any]:
    """Return table args with optional schema qualification."""
    if _SCHEMA:
        return {"schema": _SCHEMA}
    return {}


class SessionRecord(Base):
    """Identity-bound session with token metadata and policy revisions."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_stable_id", "stable_id"),
        Index("ix_sessions_revoked_at", "revoked_at"),
        _schema_args(),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    stable_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    refresh_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    access_policy_revision: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="0" * 40,
    )
    approval_policy_revision: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="0" * 40,
    )
    extra_claims: Mapped[dict[str, Any]] = mapped_column(
        JSONB if _SCHEMA else JSON,
        nullable=False,
        default=dict,
        comment="Optional provider-specific claims preserved at issuance.",
    )
