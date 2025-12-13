"""shadow pilot runs and shipments tables."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0018_shadow_pilot_tables"
down_revision = "0017_add_dutch_auction_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shadow_pilot_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("prospect_name", sa.String(length=255), nullable=False),
        sa.Column("period_months", sa.Integer(), nullable=False),
        sa.Column("total_gmv_usd", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("financeable_gmv_usd", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("financed_gmv_usd", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("protocol_revenue_usd", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("working_capital_saved_usd", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("losses_avoided_usd", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("salvage_revenue_usd", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("average_days_pulled_forward", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("shipments_evaluated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shipments_financeable", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_filename", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "shadow_pilot_shipments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=128), sa.ForeignKey("shadow_pilot_runs.run_id"), nullable=False),
        sa.Column("shipment_id", sa.String(length=255), nullable=False),
        sa.Column("corridor", sa.String(length=255), nullable=True),
        sa.Column("mode", sa.String(length=64), nullable=True),
        sa.Column("customer_segment", sa.String(length=128), nullable=True),
        sa.Column("cargo_value_usd", sa.Numeric(20, 2), nullable=False),
        sa.Column("event_truth_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("eligible_for_finance", sa.Boolean(), nullable=False),
        sa.Column("financed_amount_usd", sa.Numeric(20, 2), nullable=False),
        sa.Column("days_pulled_forward", sa.Integer(), nullable=False),
        sa.Column("wc_saved_usd", sa.Numeric(20, 2), nullable=False),
        sa.Column("protocol_revenue_usd", sa.Numeric(20, 2), nullable=False),
        sa.Column("avoided_loss_usd", sa.Numeric(20, 2), nullable=False),
        sa.Column("salvage_revenue_usd", sa.Numeric(20, 2), nullable=False),
        sa.Column("exception_flag", sa.Boolean(), nullable=False),
        sa.Column("loss_flag", sa.Boolean(), nullable=False),
    )
    op.create_index("idx_shadow_pilot_shipments_run_id", "shadow_pilot_shipments", ["run_id"])
    op.create_index("idx_shadow_pilot_shipments_corridor", "shadow_pilot_shipments", ["corridor"])
    op.create_index("idx_shadow_pilot_shipments_customer_segment", "shadow_pilot_shipments", ["customer_segment"])
    op.create_index("idx_shadow_pilot_shipments_shipment_id", "shadow_pilot_shipments", ["shipment_id"])


def downgrade() -> None:
    op.drop_index("idx_shadow_pilot_shipments_customer_segment", table_name="shadow_pilot_shipments")
    op.drop_index("idx_shadow_pilot_shipments_corridor", table_name="shadow_pilot_shipments")
    op.drop_index("idx_shadow_pilot_shipments_run_id", table_name="shadow_pilot_shipments")
    op.drop_index("idx_shadow_pilot_shipments_shipment_id", table_name="shadow_pilot_shipments")
    op.drop_table("shadow_pilot_shipments")
    op.drop_table("shadow_pilot_runs")
