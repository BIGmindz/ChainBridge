"""Geofence detection tests."""

from datetime import datetime, timezone

from chainbridge.chainsense.geofence import (
    GeofenceDefinition,
    GeofenceEngine,
    GeofenceEventType,
    GeofenceKind,
)
from chainbridge.chainsense.normalizer import DeviceState, RawTelemetry, normalize_telemetry


def _record(lat: float, lon: float, speed: float = 0.0, ignition: bool = True):
    raw = RawTelemetry(
        device_id="DEV-1",
        shipment_id="SHP-1",
        event_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        latitude=lat,
        longitude=lon,
        speed_mph=speed,
        heading=0,
        engine_state="ON" if ignition else "OFF",
        idle_time_seconds=300,
        ignition=ignition,
        battery_voltage=12.5,
    )
    return normalize_telemetry(raw, device_state=None)


def test_geofence_enter_and_exit():
    engine = GeofenceEngine(
        definitions=[
            GeofenceDefinition(
                geofence_id="SHIPPER",
                name="Origin",
                kind=GeofenceKind.SHIPPER_PICKUP,
                polygons=[[(33.0, -96.0), (33.0, -96.01), (33.01, -96.01), (33.01, -96.0)]],
            )
        ]
    )

    inside = _record(33.005, -96.005)
    events_inside = engine.evaluate(inside)
    assert any(event.event_type == GeofenceEventType.ENTER for event in events_inside)

    outside = _record(34.0, -95.0, speed=10)
    events_outside = engine.evaluate(outside)
    assert any(event.event_type == GeofenceEventType.EXIT for event in events_outside)


def test_geofence_docked_event():
    engine = GeofenceEngine(
        definitions=[
            GeofenceDefinition(
                geofence_id="CONSIGNEE",
                name="Destination",
                kind=GeofenceKind.CONSIGNEE,
                polygons=[[(35.0, -100.0), (35.0, -100.01), (35.01, -100.01), (35.01, -100.0)]],
            )
        ]
    )

    record = _record(35.005, -100.005, speed=0.0, ignition=False)
    events = engine.evaluate(record)
    assert any(event.event_type == GeofenceEventType.DOCKED for event in events)
