"""Initial kb_ops tables for the Git Orchestrator.

Revision ID: 0001
Revises:
Create Date: 2026-11-09 00:00:00.000000

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

SCHEMA = "kb_ops"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.String(length=63), nullable=False),
        sa.Column("proposal_sha", sa.String(length=64), nullable=False),
        sa.Column("base_sha", sa.String(length=64), nullable=False),
        sa.Column("target_sha", sa.String(length=64), nullable=True),
        sa.Column(
            "proposal_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_proposals_space_id",
        "proposals",
        ["space_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column(
            "decision_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("actor_id", sa.String(length=512), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["proposal_id"], [f"{SCHEMA}.proposals.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_decisions_proposal_id",
        "decisions",
        ["proposal_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "source_sync_cursors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.String(length=63), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("cursor_value", sa.Text(), nullable=False),
        sa.Column("cursor_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_cursors_space_source",
        "source_sync_cursors",
        ["space_id", "source_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "cutovers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.String(length=63), nullable=False),
        sa.Column("cutover_sha", sa.String(length=64), nullable=False),
        sa.Column("signed_by", sa.String(length=512), nullable=False),
        sa.Column(
            "signed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_cutovers_space_id",
        "cutovers",
        ["space_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    for table in (
        "cutovers",
        "source_sync_cursors",
        "decisions",
        "proposals",
    ):
        op.drop_table(table, schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA}")
