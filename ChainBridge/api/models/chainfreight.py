"""SQLAlchemy models for ChainFreight ingestion storage."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from api.database import Base


class IngestionBatch(Base):
    """Tracks batches of ingested EDI/external data."""

    __tablename__ = "ingestion_batches"

    id = Column(String, primary_key=True, default=lambda: f"BATCH-{uuid4()}")
    source_system = Column(String, nullable=False, index=True)  # "SEEBURGER", "PROJECT44", etc.
    batch_type = Column(String, nullable=False, index=True)  # "EDI_214", "EDI_210", "TELEMATICS"
    total_records = Column(Integer, nullable=False, default=0)
    processed_records = Column(Integer, nullable=False, default=0)
    failed_records = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="PROCESSING", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_summary = Column(Text, nullable=True)

    records = relationship("IngestionRecord", back_populates="batch", cascade="all, delete-orphan")


class IngestionRecord(Base):
    """Individual records within an ingestion batch."""

    __tablename__ = "ingestion_records"

    id = Column(String, primary_key=True, default=lambda: f"REC-{uuid4()}")
    batch_id = Column(
        String,
        ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_id = Column(String, nullable=True, index=True)  # External system's ID
    record_type = Column(String, nullable=False, index=True)  # "SHIPMENT_UPDATE", "MILESTONE_EVENT"
    shipment_reference = Column(String, nullable=True, index=True)  # BOL, PRO, etc.
    raw_payload = Column(JSON, nullable=False)  # Original EDI/API payload
    normalized_data = Column(JSON, nullable=True)  # Processed/standardized format
    processing_status = Column(String, nullable=False, default="PENDING", index=True)
    error_message = Column(Text, nullable=True)
    reconciliation_status = Column(String, nullable=True, index=True)  # "MATCHED", "UNMATCHED"
    matched_shipment_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    batch = relationship("IngestionBatch", back_populates="records")


class ShipmentEvent(Base):
    event_id = Column(String, nullable=True, comment="Unique event identifier")
    """Canonical shipment lifecycle events from various sources."""

    __tablename__ = "shipment_events"

    id = Column(String, primary_key=True, default=lambda: f"EVT-{uuid4()}")
    shipment_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)  # "PICKUP", "DELIVERY", "IN_TRANSIT"
    event_code = Column(String, nullable=True)  # EDI codes like "AF" (Arrived at Facility)
    event_timestamp = Column(DateTime, nullable=True, index=True)
    occurred_at = Column(DateTime, nullable=True, comment="When the event actually occurred (set by client)")
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="When the event was recorded in the system")
    actor = Column(String, nullable=True, comment="Who triggered the event")
    payload = Column(JSON, nullable=True, comment="Additional event payload")
    location_code = Column(String, nullable=True)
    location_name = Column(String, nullable=True)
    carrier_code = Column(String, nullable=True)
    equipment_id = Column(String, nullable=True)
    source_system = Column(String, nullable=True)  # Where this event came from
    source_service = Column(String, nullable=True, comment="Service that triggered the event (e.g., CHAINIQ)")
    source_record_id = Column(String, nullable=True)  # Link back to ingestion record
    confidence_score = Column(Float, nullable=True)  # Quality/reliability score
    payload_metadata = Column("metadata", JSON, nullable=True)  # Additional context
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
