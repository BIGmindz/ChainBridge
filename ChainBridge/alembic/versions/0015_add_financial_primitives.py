"""add financial primitives to shipments"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0015_add_financial_primitives"
down_revision = "0014_stake_positions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("shipments") as batch:
        batch.add_column(sa.Column("staking_status", sa.String(), nullable=True))
        batch.add_column(sa.Column("collateral_value", sa.Float(), nullable=True))
        batch.add_column(sa.Column("loan_amount", sa.Float(), nullable=True))
        batch.add_column(sa.Column("current_audit_score", sa.Float(), nullable=True))
        batch.add_column(sa.Column("ricardian_hash", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("shipments") as batch:
        batch.drop_column("ricardian_hash")
        batch.drop_column("current_audit_score")
        batch.drop_column("loan_amount")
        batch.drop_column("collateral_value")
        batch.drop_column("staking_status")
