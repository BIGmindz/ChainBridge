"""Add final payout and adjustment reason to payment_intents."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0013_payment_intent_final_payout_fields"
down_revision = "0012_chaindocs_hashing_and_proof"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payment_intents", sa.Column("final_payout_amount", sa.Float(), nullable=True))
    op.add_column("payment_intents", sa.Column("adjustment_reason", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("payment_intents", "adjustment_reason")
    op.drop_column("payment_intents", "final_payout_amount")
