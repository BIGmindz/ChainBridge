"""Consistency engine tests."""

from datetime import datetime, timedelta, timezone

from chainbridge.chainsense.consistency import ConsistencyEngine
from chainbridge.chainsense.normalizer import RawTelemetry, normalize_telemetry


def _record(event_time: datetime, lat: float, lon: float, speed: float) -> tuple:
    raw = RawTelemetry(
        device_id="DEV-20",
        shipment_id="SHP-100",
        event_time=event_time,
        latitude=lat,
        longitude=lon,
        speed_mph=speed,
        heading=0,
        engine_state="ON",
        idle_time_seconds=0,
        ignition=True,
        battery_voltage=12.2,
    )
    return normalize_telemetry(raw, device_state=None)


def test_consistency_flags_impossible_speed():
    engine = ConsistencyEngine()
    first = _record(datetime(2025, 1, 1, tzinfo=timezone.utc), 30.0, -90.0, 10)
    engine.evaluate(first)
    second = _record(
        datetime(2025, 1, 1, minute=5, tzinfo=timezone.utc),
        40.0,
        -80.0,
        10,
    )
    flags = engine.evaluate(second)
    assert any(flag.code == "IMPOSSIBLE_SPEED" for flag in flags)


def test_consistency_detects_duplicate_timestamp():
    engine = ConsistencyEngine()
    timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
    first = _record(timestamp, 30.0, -90.0, 5)
    engine.evaluate(first)
    second = _record(timestamp, 30.1, -90.1, 5)
    flags = engine.evaluate(second)
    assert any(flag.code == "TIMESTAMP_DUPLICATE" for flag in flags)
