"""Extend inventory_stakes with finance fields."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0008_inventory_stakes_extension"
down_revision = "0007_ricardian_supremacy_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inventory_stakes",
        sa.Column("principal_amount", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "inventory_stakes",
        sa.Column("max_advance_rate", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "inventory_stakes",
        sa.Column("applied_advance_rate", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "inventory_stakes",
        sa.Column("base_apr", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "inventory_stakes",
        sa.Column("risk_adjusted_apr", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "inventory_stakes",
        sa.Column("notional_value", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column("inventory_stakes", sa.Column("lender_name", sa.String(), nullable=True))
    op.add_column("inventory_stakes", sa.Column("borrower_name", sa.String(), nullable=True))
    op.add_column("inventory_stakes", sa.Column("activated_at", sa.DateTime(), nullable=True))
    op.add_column("inventory_stakes", sa.Column("repaid_at", sa.DateTime(), nullable=True))
    op.add_column("inventory_stakes", sa.Column("liquidated_at", sa.DateTime(), nullable=True))
    # existing columns "amount", "advance_pct", "apr_percent" may exist from earlier revision; keep for backward compatibility.


def downgrade() -> None:
    op.drop_column("inventory_stakes", "liquidated_at")
    op.drop_column("inventory_stakes", "repaid_at")
    op.drop_column("inventory_stakes", "activated_at")
    op.drop_column("inventory_stakes", "borrower_name")
    op.drop_column("inventory_stakes", "lender_name")
    op.drop_column("inventory_stakes", "notional_value")
    op.drop_column("inventory_stakes", "risk_adjusted_apr")
    op.drop_column("inventory_stakes", "base_apr")
    op.drop_column("inventory_stakes", "applied_advance_rate")
    op.drop_column("inventory_stakes", "max_advance_rate")
    op.drop_column("inventory_stakes", "principal_amount")
