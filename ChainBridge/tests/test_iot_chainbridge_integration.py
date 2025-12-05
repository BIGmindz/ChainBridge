"""End-to-end test from ingestion to MT-01 token creation."""

from datetime import datetime, timedelta, timezone

from chainbridge.chainsense.consistency import ConsistencyEngine
from chainbridge.chainsense.geofence import GeofenceDefinition, GeofenceEngine, GeofenceKind
from chainbridge.chainsense.iot_api import (
    ChainIQPublisher,
    ChainSenseIngestionService,
    DeviceProfile,
    DeviceRegistry,
    TelemetryIngestRequest,
    _sign_payload,
)
from chainbridge.chainsense.mt01_builder import MT01Builder
from chainbridge.events import IoTEventRouter


def _service():
    registry = DeviceRegistry()
    registry.register(DeviceProfile(device_id="DEV-END2END", secret="secret", owner="QA"))
    geofence_engine = GeofenceEngine(
        definitions=[
            GeofenceDefinition(
                geofence_id="SHIPPER",
                name="Origin",
                kind=GeofenceKind.SHIPPER_PICKUP,
                polygons=[[(10.0, 10.0), (10.0, 10.01), (10.01, 10.01), (10.01, 10.0)]],
            ),
            GeofenceDefinition(
                geofence_id="CONSIGNEE",
                name="Destination",
                kind=GeofenceKind.CONSIGNEE,
                polygons=[[(11.0, 11.0), (11.0, 11.01), (11.01, 11.01), (11.01, 11.0)]],
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


def _payload(device_id: str, shipment_id: str, nonce: int, lat: float, lon: float, speed: float, event_time: datetime):
    base = {
        "device_id": device_id,
        "shipment_id": shipment_id,
        "event_time": event_time,
        "latitude": lat,
        "longitude": lon,
        "speed_mph": speed,
        "heading": 0,
        "engine_state": "ON" if speed > 0 else "OFF",
        "idle_time_seconds": 600,
        "ignition": speed > 0,
        "battery_voltage": 12.4,
        "raw_metadata": {},
        "nonce": nonce,
    }
    provisional = TelemetryIngestRequest(**{**base, "signature": "x" * 64})
    signature = _sign_payload("secret", provisional)
    base["signature"] = signature
    return TelemetryIngestRequest(**base)


def test_end_to_end_generates_oc_payload():
    service = _service()
    first = _payload(
        "DEV-END2END",
        "SHP-END",
        1,
        10.005,
        10.005,
        0,
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    receipt1 = asyncio_run(service.ingest(first))
    assert receipt1.accepted

    second = _payload(
        "DEV-END2END",
        "SHP-END",
        2,
        11.005,
        11.005,
        0,
        datetime(2025, 1, 1, 0, 10, tzinfo=timezone.utc),
    )
    receipt2 = asyncio_run(service.ingest(second))
    assert "location" in receipt2.oc_payload


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)
