"""SQLAlchemy models for ingested Golden Record storage."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String

from api.database import Base

# Avoid table redefinition during repeated imports in test bootstrap
if "normalized_shipments" in Base.metadata.tables:
    Base.metadata.remove(Base.metadata.tables["normalized_shipments"])


class NormalizedShipmentRecord(Base):
    """Append-only archive of normalized shipments."""

    __tablename__ = "normalized_shipments"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    source_system = Column(String, nullable=False)
    external_id = Column(String, nullable=False, index=True)
    shipment_id = Column(String, nullable=False, index=True)
    raw_data_hash = Column(String, nullable=False, index=True)
    expected_arrival = Column(DateTime, nullable=True)
    payload = Column(JSON, nullable=False)
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
