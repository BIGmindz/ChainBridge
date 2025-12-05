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


"""ChainIQ persistence models.

The canonical `shipment_events` table is defined by the
`ShipmentEvent` ORM model in `api.models.chainfreight`. To avoid
defining the same table twice on the SQLAlchemy `MetaData` (which
triggers an `InvalidRequestError`), ChainIQ models must not declare a
second `ShipmentEvent` mapped class here. ChainIQ code that needs
access to shipment events should import `ShipmentEvent` from
`api.models.chainfreight` instead of re-declaring it.
"""
