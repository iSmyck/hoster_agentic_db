"""add_kb_drafts_table

Revision ID: 183bf70ff169
Revises: 83d4568073ac
Create Date: 2026-11-10 19:20:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from git_orchestrator.app.core.config import settings

# revision identifiers, used by Alembic.
revision = "183bf70ff169"
down_revision = "83d4568073ac"
branch_labels = None
depends_on = None

SCHEMA = settings.KB_OPS_SCHEMA


def upgrade() -> None:
    op.create_table(
        "drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.String(length=63), nullable=False),
        sa.Column("path", sa.String(length=2048), nullable=False),
        sa.Column("author_stable_id", sa.String(length=512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("base_sha", sa.String(length=64), nullable=True),
        sa.Column("target_branch", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_drafts_space_path_author",
        "drafts",
        ["space_id", "path", "author_stable_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_drafts_space_path_author", table_name="drafts", schema=SCHEMA)
    op.drop_table("drafts", schema=SCHEMA)
