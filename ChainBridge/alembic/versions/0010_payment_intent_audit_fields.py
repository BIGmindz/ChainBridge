"""Add reconciliation fields to payment_intents."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0010_payment_intent_audit_fields"
down_revision = "0009_settlement_event_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payment_intents", sa.Column("payout_confidence", sa.Float(), nullable=True))
    op.add_column("payment_intents", sa.Column("auto_adjusted_amount", sa.Float(), nullable=True))
    op.add_column(
        "payment_intents",
        sa.Column("reconciliation_explanation", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payment_intents", "reconciliation_explanation")
    op.drop_column("payment_intents", "auto_adjusted_amount")
    op.drop_column("payment_intents", "payout_confidence")
