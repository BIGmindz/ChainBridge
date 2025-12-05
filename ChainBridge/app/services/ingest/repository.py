"""Persistence helpers for ingestion archival/history."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from api.database import SessionLocal
from app.models.ingest import NormalizedShipmentRecord
from app.schemas.normalized_logistics import StandardShipment


def persist_standard_shipment(shipment: StandardShipment, raw_payload: Any, session: Optional[Session] = None) -> NormalizedShipmentRecord:
    db = session or SessionLocal()
    managed = session is None
    try:
        record = NormalizedShipmentRecord(
            source_system=shipment.source_system,
            external_id=shipment.external_id,
            shipment_id=shipment.shipment_id,
            raw_data_hash=shipment.raw_data_hash,
            expected_arrival=shipment.expected_arrival,
            payload=shipment.model_dump(mode="json"),
            raw_payload=raw_payload if isinstance(raw_payload, (dict, list)) else {"raw": str(raw_payload)},
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        if managed:
            db.close()


def load_latest_shipment(shipment_id: str, session: Optional[Session] = None) -> Optional[StandardShipment]:
    db = session or SessionLocal()
    managed = session is None
    try:
        record = (
            db.query(NormalizedShipmentRecord)
            .filter(NormalizedShipmentRecord.shipment_id == shipment_id)
            .order_by(desc(NormalizedShipmentRecord.id))
            .first()
        )
        if not record:
            return None
        return StandardShipment(**record.payload)
    finally:
        if managed:
            db.close()
