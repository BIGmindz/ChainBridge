"""MT-01 builder tests."""

from datetime import datetime, timezone

from chainbridge.chainsense.geofence import GeofenceEvent, GeofenceEventType, GeofenceKind
from chainbridge.chainsense.mt01_builder import MT01Builder, MT01Context, MilestoneType
from chainbridge.chainsense.normalizer import RawTelemetry, normalize_telemetry


def _record(speed: float = 5.0, ignition: bool = True):
    raw = RawTelemetry(
        device_id="DEV-5",
        shipment_id="SHP-9",
        event_time=datetime(2025, 1, 2, 12, tzinfo=timezone.utc),
        latitude=30.1,
        longitude=-97.1,
        speed_mph=speed,
        heading=90,
        engine_state="ON" if ignition else "OFF",
        idle_time_seconds=600,
        ignition=ignition,
        battery_voltage=12.4,
    )
    return normalize_telemetry(raw, device_state=None)


def test_builder_creates_in_transit_token():
    builder = MT01Builder()
    record = _record(speed=8.0)
    events = [
        GeofenceEvent(
            geofence_id="SHIPPER",
            kind=GeofenceKind.SHIPPER_PICKUP,
            event_type=GeofenceEventType.EXIT,
            timestamp=record.event_time,
        )
    ]
    tokens = builder.build(MT01Context(st01_id="SHP-9"), record, events)
    assert tokens
    assert tokens[0].metadata["milestone_type"] == MilestoneType.IN_TRANSIT.value


def test_builder_detects_delivery():
    builder = MT01Builder()
    record = _record(speed=0.0, ignition=False)
    events = [
        GeofenceEvent(
            geofence_id="CONSIGNEE",
            kind=GeofenceKind.CONSIGNEE,
            event_type=GeofenceEventType.ENTER,
            timestamp=record.event_time,
        )
    ]
    tokens = builder.build(MT01Context(st01_id="SHP-9"), record, events)
    assert tokens
    assert tokens[0].metadata["milestone_type"] == MilestoneType.DELIVERED.value
