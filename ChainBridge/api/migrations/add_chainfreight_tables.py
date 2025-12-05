"""Add ChainFreight ingestion and event tables.

Revision ID: add_chainfreight_tables
Revises:
Create Date: 2025-11-26 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_chainfreight_tables"
down_revision = None  # Update this to the latest revision
branch_labels = None
depends_on = None


def upgrade():
    """Add ChainFreight tables."""
    # Create ingestion_batches table
    op.create_table(
        "ingestion_batches",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=False),
        sa.Column("batch_type", sa.String(), nullable=False),
        sa.Column("total_records", sa.Integer(), nullable=False, default=0),
        sa.Column("processed_records", sa.Integer(), nullable=False, default=0),
        sa.Column("failed_records", sa.Integer(), nullable=False, default=0),
        sa.Column("status", sa.String(), nullable=False, default="PROCESSING"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for ingestion_batches
    op.create_index("ix_ingestion_batches_source_system", "ingestion_batches", ["source_system"])
    op.create_index("ix_ingestion_batches_batch_type", "ingestion_batches", ["batch_type"])
    op.create_index("ix_ingestion_batches_status", "ingestion_batches", ["status"])

    # Create ingestion_records table
    op.create_table(
        "ingestion_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("batch_id", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("record_type", sa.String(), nullable=False),
        sa.Column("shipment_reference", sa.String(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("normalized_data", sa.JSON(), nullable=True),
        sa.Column("processing_status", sa.String(), nullable=False, default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("reconciliation_status", sa.String(), nullable=True),
        sa.Column("matched_shipment_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for ingestion_records
    op.create_index("ix_ingestion_records_batch_id", "ingestion_records", ["batch_id"])
    op.create_index("ix_ingestion_records_external_id", "ingestion_records", ["external_id"])
    op.create_index("ix_ingestion_records_record_type", "ingestion_records", ["record_type"])
    op.create_index("ix_ingestion_records_shipment_reference", "ingestion_records", ["shipment_reference"])
    op.create_index("ix_ingestion_records_processing_status", "ingestion_records", ["processing_status"])
    op.create_index("ix_ingestion_records_reconciliation_status", "ingestion_records", ["reconciliation_status"])
    op.create_index("ix_ingestion_records_matched_shipment_id", "ingestion_records", ["matched_shipment_id"])

    # Create shipment_events table
    op.create_table(
        "shipment_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("shipment_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("event_code", sa.String(), nullable=True),
        sa.Column("event_timestamp", sa.DateTime(), nullable=False),
        sa.Column("location_code", sa.String(), nullable=True),
        sa.Column("location_name", sa.String(), nullable=True),
        sa.Column("carrier_code", sa.String(), nullable=True),
        sa.Column("equipment_id", sa.String(), nullable=True),
        sa.Column("source_system", sa.String(), nullable=False),
        sa.Column("source_record_id", sa.String(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for shipment_events
    op.create_index("ix_shipment_events_shipment_id", "shipment_events", ["shipment_id"])
    op.create_index("ix_shipment_events_event_type", "shipment_events", ["event_type"])
    op.create_index("ix_shipment_events_event_timestamp", "shipment_events", ["event_timestamp"])


def downgrade():
    """Remove ChainFreight tables."""
    # Drop tables in reverse order
    op.drop_table("shipment_events")
    op.drop_table("ingestion_records")
    op.drop_table("ingestion_batches")
