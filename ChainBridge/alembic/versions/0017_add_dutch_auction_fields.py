"""add dutch auction fields to marketplace listings"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0017_add_dutch_auction_fields"
down_revision = "0016_add_chainsalvage_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("marketplace_listings") as batch:
        batch.add_column(sa.Column("reserve_price", sa.Float(), nullable=True))
        batch.add_column(sa.Column("decay_rate_per_minute", sa.Float(), nullable=True))
        batch.add_column(sa.Column("start_time", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("marketplace_listings") as batch:
        batch.drop_column("start_time")
        batch.drop_column("decay_rate_per_minute")
        batch.drop_column("reserve_price")
