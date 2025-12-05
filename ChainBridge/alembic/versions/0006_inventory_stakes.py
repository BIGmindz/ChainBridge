"""Create inventory_stakes table."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_inventory_stakes"
down_revision = "0005_ricardian_instruments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_stakes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("physical_reference", sa.String(), nullable=False, index=True),
        sa.Column("ricardian_instrument_id", sa.String(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="USD"),
        sa.Column("advance_pct", sa.Float(), nullable=False),
        sa.Column("apr_percent", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("reason_code", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_inventory_stakes_physical", "inventory_stakes", ["physical_reference"])
    op.create_index("ix_inventory_stakes_status", "inventory_stakes", ["status"])


def downgrade() -> None:
    op.drop_index("ix_inventory_stakes_status", table_name="inventory_stakes")
    op.drop_index("ix_inventory_stakes_physical", table_name="inventory_stakes")
    op.drop_table("inventory_stakes")
