"""API-level tests for ChainSense ingestion."""

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from chainbridge.chainsense.consistency import ConsistencyEngine
from chainbridge.chainsense.geofence import GeofenceDefinition, GeofenceEngine, GeofenceKind
from chainbridge.chainsense.iot_api import (
    ChainIQPublisher,
    ChainSenseIngestionService,
    DeviceProfile,
    DeviceRegistry,
    TelemetryIngestRequest,
    _sign_payload,
    get_service,
    router,
)
from chainbridge.chainsense.mt01_builder import MT01Builder
from chainbridge.events import IoTEventRouter


def _build_service() -> ChainSenseIngestionService:
    registry = DeviceRegistry()
    registry.register(DeviceProfile(device_id="DEV-TEST", secret="top-secret", owner="QA"))
    geofence_engine = GeofenceEngine(
        definitions=[
            GeofenceDefinition(
                geofence_id="SHIPPER",
                name="Origin",
                kind=GeofenceKind.SHIPPER_PICKUP,
                polygons=[[(33.0, -96.0), (33.0, -96.01), (33.01, -96.01), (33.01, -96.0)]],
            ),
            GeofenceDefinition(
                geofence_id="CONSIGNEE",
                name="Dest",
                kind=GeofenceKind.CONSIGNEE,
                polygons=[[(34.0, -96.0), (34.0, -96.01), (34.01, -96.01), (34.01, -96.0)]],
            ),
        ]
    )
    return ChainSenseIngestionService(
        device_registry=registry,
        geofence_engine=geofence_engine,
        consistency_engine=ConsistencyEngine(),
        event_router=IoTEventRouter(mt01_builder=MT01Builder()),
        chainiq_publisher=ChainIQPublisher(),
    )


def _signing_payload(base: dict, secret: str) -> dict:
    provisional = TelemetryIngestRequest(**{**base, "signature": "x" * 64})
    signature = _sign_payload(secret, provisional)
    base["signature"] = signature
    return base


def test_ingestion_generates_receipts():
    service = _build_service()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    event_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    base = {
        "device_id": "DEV-TEST",
        "shipment_id": "SHP-9",
        "event_time": event_time.isoformat(),
        "latitude": 33.005,
        "longitude": -96.005,
        "speed_mph": 0.0,
        "heading": 0,
        "engine_state": "ON",
        "idle_time_seconds": 0,
        "ignition": True,
        "battery_voltage": 12.6,
        "raw_metadata": {},
        "nonce": 1,
    }
    payload = _signing_payload(base.copy(), "top-secret")
    resp = client.post("/chainsense/iot/telemetry", json=payload)
    assert resp.status_code == 202
    assert resp.json()["milestones_generated"] == 0

    exit_payload = base.copy()
    exit_payload.update(
        {
            "latitude": 34.1,
            "longitude": -95.5,
            "speed_mph": 10.0,
            "event_time": (event_time + timedelta(minutes=5)).isoformat(),
            "nonce": 2,
        }
    )
    exit_payload = _signing_payload(exit_payload, "top-secret")
    resp = client.post("/chainsense/iot/telemetry", json=exit_payload)
    assert resp.status_code == 202
    data = resp.json()
    assert data["milestones_generated"] >= 0
    assert data["accepted"] is True

    status_resp = client.get("/chainsense/iot/device/DEV-TEST/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["device_id"] == "DEV-TEST"
