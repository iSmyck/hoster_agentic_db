"""add_g1_merge_recovery_and_decision_anchor_columns

Revision ID: 83d4568073ac
Revises: 0001
Create Date: 2026-11-10 00:51:55.408255

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from git_orchestrator.app.core.config import settings

# revision identifiers, used by Alembic.
revision = "83d4568073ac"
down_revision = "0001"
branch_labels = None
depends_on = None

SCHEMA = settings.KB_OPS_SCHEMA


def upgrade() -> None:
    # G1 merge durability barrier and fencing.
    op.add_column(
        "proposals",
        sa.Column(
            "recovery_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Durable per-target merge barrier; blocks new merges until reconciled.",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "proposals",
        sa.Column(
            "merge_fence_token",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Monotonic fencing token for per-target merge serialization.",
        ),
        schema=SCHEMA,
    )

    # G1 canonical DecisionRecord anchors (note + protected tag).
    op.add_column(
        "decisions",
        sa.Column(
            "record_sha256",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("''"),
            comment="SHA-256 of the canonical JSON DecisionRecord.",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "decisions",
        sa.Column(
            "note_id",
            sa.Integer(),
            nullable=True,
            comment="GitLab MR note ID containing the canonical record.",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "decisions",
        sa.Column(
            "tag_name",
            sa.String(length=255),
            nullable=False,
            server_default=sa.text("''"),
            comment="Protected annotated tag name kb-decisions/<decision_id>.",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "decisions",
        sa.Column(
            "supersedes_decision_id",
            sa.Uuid(),
            nullable=True,
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "decisions",
        sa.Column(
            "state",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'quarantined'"),
            comment="recorded | merge_attempted | merged | failed | conflicted | invalid | quarantined",
        ),
        schema=SCHEMA,
    )
    op.create_foreign_key(
        "fk_decisions_supersedes_decision",
        "decisions",
        "decisions",
        ["supersedes_decision_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_decisions_supersedes_decision",
        "decisions",
        schema=SCHEMA,
        type_="foreignkey",
    )
    op.drop_column("decisions", "state", schema=SCHEMA)
    op.drop_column("decisions", "supersedes_decision_id", schema=SCHEMA)
    op.drop_column("decisions", "tag_name", schema=SCHEMA)
    op.drop_column("decisions", "note_id", schema=SCHEMA)
    op.drop_column("decisions", "record_sha256", schema=SCHEMA)
    op.drop_column("proposals", "merge_fence_token", schema=SCHEMA)
    op.drop_column("proposals", "recovery_required", schema=SCHEMA)
