from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import SessionLocal, init_db
from api.events.bus import EventType, event_bus
from app.api.endpoints import ingest as ingest_endpoint
from app.models.ingest import NormalizedShipmentRecord

pytestmark = pytest.mark.phase4


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(ingest_endpoint.router)
    return app


def test_edi_856_is_normalized_and_archived() -> None:
    init_db()
    event_bus.clear_subscribers()
    ingested_event: dict = {}
    event_bus.subscribe(EventType.SHIPMENT_INGESTED, lambda payload: ingested_event.update(payload))

    app = create_app()
    client = TestClient(app)

    external_id = f"856-{uuid.uuid4().hex[:6]}"
    shipment_id = f"SHP-{uuid.uuid4().hex[:6]}"
    payload = {
        "control_number": external_id,
        "shipment_id": shipment_id,
        "expected_arrival": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "carrier": "MAERSK",
        "line_items": [
            {"sku": "ABC-123", "description": "Widgets", "quantity": 10, "unit": "EA"},
            {"sku": "XYZ-999", "description": "Gadgets", "quantity": 5, "unit": "CTN"},
        ],
        "tolerances": {"max_temp": 4.5},
    }

    resp = client.post("/ingest/seeburger", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["external_id"] == external_id
    assert data["shipment_id"] == shipment_id
    assert data["raw_data_hash"]
    assert data["metadata"]["raw_summary"]["line_item_count"] == 2

    session = SessionLocal()
    try:
        record = (
            session.query(NormalizedShipmentRecord)
            .filter(NormalizedShipmentRecord.external_id == external_id)
            .order_by(NormalizedShipmentRecord.id.desc())
            .first()
        )
        assert record is not None, "Normalized record should be archived"
        assert record.payload["shipment_id"] == shipment_id
        assert record.payload["raw_data_hash"] == data["raw_data_hash"]
    finally:
        session.close()

    assert ingested_event.get("archive_status") is not None
    hydrated = ingested_event.get("shipment")
    assert hydrated is not None
    assert hydrated["external_id"] == external_id
    assert len(hydrated["assets"]) == 2
