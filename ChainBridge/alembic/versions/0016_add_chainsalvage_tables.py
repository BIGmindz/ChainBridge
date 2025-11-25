"""add chainsalvage marketplace tables"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0016_add_chainsalvage_tables"
down_revision = "0015_add_financial_primitives"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketplace_listings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("shipment_id", sa.String(), sa.ForeignKey("shipments.id"), nullable=False, index=True),
        sa.Column("token_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("start_price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("buy_now_price", sa.Float(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_marketplace_listings_status", "marketplace_listings", ["status"])
    op.create_index("ix_marketplace_listings_expires", "marketplace_listings", ["expires_at"])

    op.create_table(
        "marketplace_bids",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("listing_id", sa.String(), sa.ForeignKey("marketplace_listings.id"), nullable=False, index=True),
        sa.Column("bidder_wallet", sa.String(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("marketplace_bids")
    op.drop_index("ix_marketplace_listings_expires", table_name="marketplace_listings")
    op.drop_index("ix_marketplace_listings_status", table_name="marketplace_listings")
    op.drop_table("marketplace_listings")
