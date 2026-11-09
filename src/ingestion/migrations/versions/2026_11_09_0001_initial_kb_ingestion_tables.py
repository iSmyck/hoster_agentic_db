"""Initial kb_ops ingestion tables.

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
        "source_registries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.String(length=63), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("ownership_mode", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("space_id", "source_id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_source_registries_space_id",
        "source_registries",
        ["space_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "source_cursors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_registry_id", sa.Uuid(), nullable=False),
        sa.Column("cursor_value", sa.Text(), nullable=False),
        sa.Column("cursor_hash", sa.String(length=64), nullable=False),
        sa.Column("last_merged_cursor", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_registry_id"],
            [f"{SCHEMA}.source_registries.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_registry_id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_source_cursors_registry_id",
        "source_cursors",
        ["source_registry_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "dry_run_manifests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.String(length=63), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "blockers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "manifest_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dry_run_manifests_space_source",
        "dry_run_manifests",
        ["space_id", "source_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "import_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dry_run_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("authorized_by", sa.String(length=512), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_proposal_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dry_run_id"],
            [f"{SCHEMA}.dry_run_manifests.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_import_packages_dry_run_id",
        "import_packages",
        ["dry_run_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    for table in (
        "import_packages",
        "dry_run_manifests",
        "source_cursors",
        "source_registries",
    ):
        op.drop_table(table, schema=SCHEMA)

