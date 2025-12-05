"""Add stake_jobs table."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0011_stake_jobs"
down_revision = "0010_payment_intent_audit_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stake_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("shipment_id", sa.String(), nullable=False, index=True),
        sa.Column("payment_intent_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, default="PENDING"),
        sa.Column("requested_amount", sa.Float(), nullable=False),
        sa.Column("settled_amount", sa.Float(), nullable=True),
        sa.Column("failure_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_stake_jobs_shipment", "stake_jobs", ["shipment_id"])
    op.create_index("ix_stake_jobs_status", "stake_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_stake_jobs_status", table_name="stake_jobs")
    op.drop_index("ix_stake_jobs_shipment", table_name="stake_jobs")
    op.drop_table("stake_jobs")
