"""Initial kb_sessions tables.

Revision ID: 0001
Revises:
Create Date: 2026-11-10 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


SCHEMA = "kb_sessions"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    op.create_table(
        "sessions",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("stable_id", sa.String(length=1024), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_policy_revision", sa.String(length=40), nullable=False),
        sa.Column("approval_policy_revision", sa.String(length=40), nullable=False),
        sa.Column("extra_claims", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("session_id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_sessions_stable_id",
        "sessions",
        ["stable_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_sessions_revoked_at",
        "sessions",
        ["revoked_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("sessions", schema=SCHEMA)
