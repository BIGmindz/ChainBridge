"""SQLAlchemy models for ChainIQ telemetry storage."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String

from api.database import Base


class DocumentHealthSnapshot(Base):
    """Stores historical document health metrics per shipment."""

    __tablename__ = "document_health_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(String, index=True, nullable=False)
    corridor_code = Column(String, nullable=True)
    mode = Column(String, nullable=True)
    incoterm = Column(String, nullable=True)
    template_name = Column(String, nullable=True)

    present_count = Column(Integer, nullable=False)
    missing_count = Column(Integer, nullable=False)
    required_total = Column(Integer, nullable=False)
    optional_total = Column(Integer, nullable=False)
    blocking_gap_count = Column(Integer, nullable=False)
    completeness_pct = Column(Integer, nullable=False)

    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String, nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SnapshotExportEvent(Base):
    """Outbox entries for downstream BIS/SxT/ML exports."""

    __tablename__ = "snapshot_export_events"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("document_health_snapshots.id"), index=True, nullable=False)
    target_system = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PENDING")
    retry_count = Column(Integer, nullable=False, default=0)
    claimed_by = Column(String, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    last_error = Column(String, nullable=True)


class RiskDecision(Base):
    """Persisted outputs of ChainIQ risk scoring runs."""

    __tablename__ = "risk_decisions"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(String, index=True, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    features = Column(JSON, nullable=True)
    decided_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ShipmentEvent(Base):
    """Append-only log of shipment events across services."""

    __tablename__ = "shipment_events"
    __table_args__ = (
        Index("ix_shipment_events_shipment_occurred", "shipment_id", "occurred_at"),
    )

    event_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    shipment_id = Column(String, index=True, nullable=False)
    shipment_leg_id = Column(String, nullable=True)
    actor = Column(String, nullable=True)
    source_service = Column(String, nullable=True)
    event_type = Column(String, nullable=False)
    occurred_at = Column(DateTime, nullable=False)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    payload = Column(JSON, nullable=True)
