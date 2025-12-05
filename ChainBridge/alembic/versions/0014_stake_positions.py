"""Create stake_positions table for analytics."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0014_stake_positions"
down_revision = "0013_payment_intent_final_payout_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stake_positions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("shipment_id", sa.String(), nullable=False, index=True),
        sa.Column("payment_intent_id", sa.String(), nullable=True, index=True),
        sa.Column("pool_id", sa.String(), nullable=False),
        sa.Column("corridor", sa.String(), nullable=True),
        sa.Column("notional_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("staked_at", sa.DateTime(), nullable=False),
        sa.Column("expected_maturity_at", sa.DateTime(), nullable=True),
        sa.Column("realized_apy", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="QUEUED"),
        sa.Column("risk_level", sa.String(), nullable=True),
        sa.Column("payout_confidence", sa.Float(), nullable=True),
        sa.Column("final_payout_amount", sa.Float(), nullable=True),
    )
    op.create_index("ix_stake_positions_pool", "stake_positions", ["pool_id"])
    op.create_index("ix_stake_positions_status", "stake_positions", ["status"])
    op.create_index("ix_stake_positions_corridor", "stake_positions", ["corridor"])
    op.create_index("ix_stake_positions_staked_at", "stake_positions", ["staked_at"])


def downgrade() -> None:
    op.drop_index("ix_stake_positions_staked_at", table_name="stake_positions")
    op.drop_index("ix_stake_positions_corridor", table_name="stake_positions")
    op.drop_index("ix_stake_positions_status", table_name="stake_positions")
    op.drop_index("ix_stake_positions_pool", table_name="stake_positions")
    op.drop_table("stake_positions")
