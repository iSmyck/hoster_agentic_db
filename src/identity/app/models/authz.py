"""SQLAlchemy ORM models for the kb_authz schema."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from identity.app.core.config import settings


class Base(DeclarativeBase):
    """Shared declarative base."""

    type_annotation_map: ClassVar[dict[type, Any]] = {dict: JSON, list: JSON}


_SCHEMA = settings.KB_AUTHZ_SCHEMA


def _schema_args() -> dict[str, Any]:
    """Return table args with optional schema qualification."""
    if _SCHEMA:
        return {"schema": _SCHEMA}
    return {}


class Identity(Base):
    """Stable identity record with external provider references."""

    __tablename__ = "identities"
    __table_args__ = (
        Index(
            "ix_identities_external_refs_gin",
            "external_refs",
            postgresql_using="gin",
        ),
        _schema_args(),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    external_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB if _SCHEMA else JSON,
        default=list,
        comment="List of external provider references, e.g. [{issuer, sub}].",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class IdentityExternalRef(Base):
    """Normalized, unique external identity reference for indexed lookup."""

    __tablename__ = "identity_external_refs"
    __table_args__ = _schema_args()

    issuer: Mapped[str] = mapped_column(String(256), primary_key=True)
    sub: Mapped[str] = mapped_column(String(512), primary_key=True)
    identity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}identities.id"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class GroupSnapshot(Base):
    """Per-group membership snapshot for a Space."""

    __tablename__ = "group_snapshots"
    __table_args__ = _schema_args()

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    space_id: Mapped[str] = mapped_column(String(63), nullable=False, index=True)
    group_name: Mapped[str] = mapped_column(String(512), nullable=False)
    member_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB if _SCHEMA else JSON,
        default=list,
        comment="Member external refs belonging to this group.",
    )
    parent_groups: Mapped[list[str]] = mapped_column(
        JSONB if _SCHEMA else JSON,
        default=list,
        comment="Parent group names; used to resolve nested membership.",
    )
    epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Null while active; set when superseded.",
    )


class PolicyBundle(Base):
    """Activated access+approval policy bundle for a Space."""

    __tablename__ = "policy_bundles"
    __table_args__ = _schema_args()

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    space_id: Mapped[str] = mapped_column(String(63), nullable=False, index=True)
    policy_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB if _SCHEMA else JSON,
        default=dict,
        comment="Access and approval policy payload with revisions.",
    )
    activation_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Null while active; set when superseded.",
    )


class AuthzContext(Base):
    """Persisted server-issued AuthzContext envelope per Space."""

    __tablename__ = "authz_contexts"
    __table_args__ = _schema_args()

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    space_id: Mapped[str] = mapped_column(String(63), nullable=False, index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}identities.id"),
        nullable=False,
        index=True,
    )
    computed_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB if _SCHEMA else JSON,
        default=dict,
    )
    epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Revocation(Base):
    """Revocation epoch marker per Space."""

    __tablename__ = "revocations"
    __table_args__ = _schema_args()

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    space_id: Mapped[str] = mapped_column(String(63), nullable=False, index=True)
    revoked_at_epoch: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
