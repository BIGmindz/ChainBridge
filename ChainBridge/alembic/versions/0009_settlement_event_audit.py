"""Add settlement event audit table."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0009_settlement_event_audit"
down_revision = "0008_inventory_stakes_extension"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "settlement_event_audit",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("payment_intent_id", sa.String(), nullable=True),
        sa.Column("shipment_id", sa.String(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("payload_summary", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_settlement_event_audit_payment_intent",
        "settlement_event_audit",
        ["payment_intent_id"],
    )
    op.create_index(
        "ix_settlement_event_audit_shipment",
        "settlement_event_audit",
        ["shipment_id"],
    )
    op.create_index(
        "ix_settlement_event_audit_occurred_at_desc",
        "settlement_event_audit",
        [sa.text("occurred_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_settlement_event_audit_occurred_at_desc",
        table_name="settlement_event_audit",
    )
    op.drop_index("ix_settlement_event_audit_shipment", table_name="settlement_event_audit")
    op.drop_index("ix_settlement_event_audit_payment_intent", table_name="settlement_event_audit")
    op.drop_table("settlement_event_audit")
