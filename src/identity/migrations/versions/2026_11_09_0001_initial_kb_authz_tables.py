"""Initial kb_authz tables.

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


SCHEMA = "kb_authz"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "identities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_identities_external_refs_gin",
        "identities",
        ["external_refs"],
        unique=False,
        postgresql_using="gin",
        schema=SCHEMA,
    )

    op.create_table(
        "identity_external_refs",
        sa.Column("issuer", sa.String(length=256), nullable=False),
        sa.Column("sub", sa.String(length=512), nullable=False),
        sa.Column("identity_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["identity_id"], [f"{SCHEMA}.identities.id"]),
        sa.PrimaryKeyConstraint("issuer", "sub"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_identity_external_refs_identity_id",
        "identity_external_refs",
        ["identity_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "group_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.String(length=63), nullable=False),
        sa.Column("group_name", sa.String(length=512), nullable=False),
        sa.Column("member_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("parent_groups", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_group_snapshots_space_id", "group_snapshots", ["space_id"], schema=SCHEMA)

    op.create_table(
        "policy_bundles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.String(length=63), nullable=False),
        sa.Column("policy_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("activation_epoch", sa.Integer(), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_policy_bundles_space_id", "policy_bundles", ["space_id"], schema=SCHEMA)

    op.create_table(
        "authz_contexts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.String(length=63), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("computed_context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], [f"{SCHEMA}.identities.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_authz_contexts_space_id", "authz_contexts", ["space_id"], schema=SCHEMA)
    op.create_index("ix_authz_contexts_actor_id", "authz_contexts", ["actor_id"], schema=SCHEMA)

    op.create_table(
        "revocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.String(length=63), nullable=False),
        sa.Column("revoked_at_epoch", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_revocations_space_id", "revocations", ["space_id"], schema=SCHEMA)


def downgrade() -> None:
    for table in (
        "revocations",
        "authz_contexts",
        "policy_bundles",
        "group_snapshots",
        "identity_external_refs",
        "identities",
    ):
        op.drop_table(table, schema=SCHEMA)

