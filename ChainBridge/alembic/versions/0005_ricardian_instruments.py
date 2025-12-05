"""Create ricardian_instruments table."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_ricardian_instruments"
down_revision = "0004_payment_intent_recon_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ricardian_instruments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("instrument_type", sa.String(), nullable=False),
        sa.Column("physical_reference", sa.String(), nullable=False),
        sa.Column("pdf_uri", sa.String(), nullable=False),
        sa.Column("pdf_ipfs_uri", sa.String(), nullable=True),
        sa.Column("pdf_hash", sa.String(), nullable=False),
        sa.Column(
            "ricardian_version",
            sa.String(),
            nullable=False,
            server_default="Ricardian_v1",
        ),
        sa.Column("governing_law", sa.String(), nullable=False),
        sa.Column("smart_contract_chain", sa.String(), nullable=True),
        sa.Column("smart_contract_address", sa.String(), nullable=True),
        sa.Column("last_signed_tx_hash", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("freeze_reason", sa.String(), nullable=True),
        sa.Column("ricardian_metadata", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_ricardian_instrument_type", "ricardian_instruments", ["instrument_type"])
    op.create_index(
        "ix_ricardian_physical_reference",
        "ricardian_instruments",
        ["physical_reference"],
    )
    op.create_index(
        "ix_ricardian_chain_address",
        "ricardian_instruments",
        ["smart_contract_chain", "smart_contract_address"],
    )
    op.create_index("ix_ricardian_status", "ricardian_instruments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ricardian_status", table_name="ricardian_instruments")
    op.drop_index("ix_ricardian_chain_address", table_name="ricardian_instruments")
    op.drop_index("ix_ricardian_physical_reference", table_name="ricardian_instruments")
    op.drop_index("ix_ricardian_instrument_type", table_name="ricardian_instruments")
    op.drop_table("ricardian_instruments")
