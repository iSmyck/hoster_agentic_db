"""Update chunks.embedding dimension to match configured model.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-09 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SCHEMA = "kb_index"


def _embedding_dim() -> int:
    """Return the configured embedding dimension, defaulting to 1024."""
    import os

    value = os.environ.get("RETRIEVAL_EMBEDDING_DIMENSIONS", "1024")
    try:
        return int(value)
    except ValueError:
        return 1024


def upgrade() -> None:
    dim = _embedding_dim()
    # The table is expected to be empty or small during development; drop and
    # recreate with the correct vector dimension because pgvector cannot alter
    # the dimension of an existing populated vector column.
    op.drop_table("chunks", schema=SCHEMA)
    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("generation_id", sa.Uuid(), nullable=False),
        sa.Column("document_path", sa.String(length=2048), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(dim), nullable=True),
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


def downgrade() -> None:
    # Restore the original 384-dimension chunks table.
    op.drop_table("chunks", schema=SCHEMA)
    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("generation_id", sa.Uuid(), nullable=False),
        sa.Column("document_path", sa.String(length=2048), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=True),
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
