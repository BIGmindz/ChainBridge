"""Add preset_analytics_snapshots table

Revision ID: 20251130_02_add_preset_analytics_snapshots
Revises: 20251130_01_add_tenant_console_to_profile_weights
Create Date: 2025-11-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251130_02_add_preset_analytics_snapshots"
down_revision = "20251130_01_add_tenant_console_to_profile_weights"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preset_analytics_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("profile", sa.String(), nullable=False),
        sa.Column("ctr", sa.Float(), nullable=False),
        sa.Column("hit_at_1", sa.Float(), nullable=False),
        sa.Column("hit_at_3", sa.Float(), nullable=False),
        sa.Column("avg_time_to_preset_ms", sa.Float(), nullable=True),
        sa.Column("interaction_count", sa.Integer(), nullable=True),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("console_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_preset_analytics_snapshots_profile",
        "preset_analytics_snapshots",
        ["profile"],
        unique=False,
    )
    op.create_index(
        "ix_preset_analytics_snapshots_tenant_id",
        "preset_analytics_snapshots",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_preset_analytics_snapshots_console_id",
        "preset_analytics_snapshots",
        ["console_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_preset_analytics_snapshots_profile", table_name="preset_analytics_snapshots")
    op.drop_index("ix_preset_analytics_snapshots_tenant_id", table_name="preset_analytics_snapshots")
    op.drop_index("ix_preset_analytics_snapshots_console_id", table_name="preset_analytics_snapshots")
    op.drop_table("preset_analytics_snapshots")
