"""Initial kb_index tables for the Retrieval + Indexing adapter.

Revision ID: 0001
Revises:
Create Date: 2026-11-09 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def _schema() -> str:
    """Return the target schema from the environment, defaulting to kb_index."""
    import os

    return (
        os.environ.get("RETRIEVAL_KB_INDEX_SCHEMA")
        or os.environ.get("KB_INDEX_SCHEMA")
        or "kb_index"
    )


SCHEMA = _schema()
EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "index_generations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.String(length=63), nullable=False),
        sa.Column("snapshot_sha", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("ordering", sa.Integer(), nullable=False),
        sa.Column(
            "equivalence_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
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
        "ix_index_generations_space_id_snapshot_sha",
        "index_generations",
        ["space_id", "snapshot_sha"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_index_generations_space_id",
        "index_generations",
        ["space_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "index_pointers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.String(length=63), nullable=False),
        sa.Column("profile", sa.String(length=128), nullable=False),
        sa.Column("generation_id", sa.Uuid(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("fence_token", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["generation_id"],
            [f"{SCHEMA}.index_generations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_index_pointers_space_profile_active",
        "index_pointers",
        ["space_id", "profile", "active"],
        unique=True,
        postgresql_where="active",
        schema=SCHEMA,
    )
    op.create_index(
        "ix_index_pointers_space_id",
        "index_pointers",
        ["space_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("generation_id", sa.Uuid(), nullable=False),
        sa.Column("document_path", sa.String(length=2048), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["generation_id"],
            [f"{SCHEMA}.index_generations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_chunks_generation_id", "chunks", ["generation_id"], schema=SCHEMA)
    op.create_index("ix_chunks_document_path", "chunks", ["document_path"], schema=SCHEMA)

    op.create_table(
        "search_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.String(length=63), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("profile", sa.String(length=128), nullable=False),
        sa.Column("results_count", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.String(length=512), nullable=False),
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
        "ix_search_logs_space_id",
        "search_logs",
        ["space_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    for table in ("search_logs", "chunks", "index_pointers", "index_generations"):
        op.drop_table(table, schema=SCHEMA)

