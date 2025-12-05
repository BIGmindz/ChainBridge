"""Add tenant_id and console_id to preset_profile_weights

Revision ID: 20251130_01_add_tenant_console_to_profile_weights
Revises:
Create Date: 2025-11-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251130_01_add_tenant_console_to_profile_weights"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("preset_profile_weights") as batch_op:
        batch_op.add_column(sa.Column("tenant_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("console_id", sa.String(), nullable=True))
        batch_op.create_index("ix_preset_profile_weights_tenant_id", ["tenant_id"], unique=False)
        batch_op.create_index("ix_preset_profile_weights_console_id", ["console_id"], unique=False)
        batch_op.create_unique_constraint(
            "uq_profile_tenant_console",
            ["profile", "tenant_id", "console_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("preset_profile_weights") as batch_op:
        batch_op.drop_constraint("uq_profile_tenant_console", type_="unique")
        batch_op.drop_index("ix_preset_profile_weights_tenant_id")
        batch_op.drop_index("ix_preset_profile_weights_console_id")
        batch_op.drop_column("tenant_id")
        batch_op.drop_column("console_id")
