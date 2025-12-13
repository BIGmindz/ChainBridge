"""
Unit tests for ChainIQ ML event parsing module.

Tests cover:
- Event parsing from raw dicts
- Event grouping by shipment
- Timestamp extraction
- Transit time computation
- Event counting
- Sensor reading extraction
"""

from datetime import datetime

import pytest

from app.ml.event_parsing import (
    EventType,
    ParsedEvent,
    compute_transit_times,
    count_event_types,
    extract_event_timestamps,
    extract_sensor_readings,
    group_events_by_shipment,
    parse_event_log,
)


def test_parse_event_log_basic():
    """Test parsing a basic valid event."""
    raw_event = {
        "event_id": "evt_123",
        "shipment_id": "shp_456",
        "event_type": "DELAY_DETECTED",
        "timestamp": "2024-12-11T10:00:00Z",
        "payload": {"delay_hours": 2.5},
        "source": "system",
    }

    event = parse_event_log(raw_event)

    assert event.event_id == "evt_123"
    assert event.shipment_id == "shp_456"
    assert event.event_type == EventType.DELAY_DETECTED
    assert event.timestamp.year == 2024
    assert event.timestamp.month == 12
    assert event.timestamp.day == 11
    assert event.payload["delay_hours"] == 2.5
    assert event.source == "system"


def test_parse_event_log_missing_required_field():
    """Test that parsing fails if required field is missing."""
    raw_event = {
        "event_id": "evt_123",
        "event_type": "DELAY_DETECTED",
        "timestamp": "2024-12-11T10:00:00Z",
        # Missing shipment_id
    }

    with pytest.raises(ValueError, match="Missing required field"):
        parse_event_log(raw_event)


def test_parse_event_log_invalid_event_type():
    """Test that parsing fails for invalid event type."""
    raw_event = {
        "event_id": "evt_123",
        "shipment_id": "shp_456",
        "event_type": "INVALID_EVENT_TYPE",
        "timestamp": "2024-12-11T10:00:00Z",
    }

    with pytest.raises(ValueError):
        parse_event_log(raw_event)


def test_group_events_by_shipment():
    """Test grouping events by shipment_id."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1), {}),
        ParsedEvent("e2", "shp2", EventType.SHIPMENT_CREATED, datetime(2024, 1, 2), {}),
        ParsedEvent("e3", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 3), {}),
        ParsedEvent("e4", "shp1", EventType.DELAY_DETECTED, datetime(2024, 1, 2), {}),
    ]

    grouped = group_events_by_shipment(events)

    assert len(grouped) == 2
    assert len(grouped["shp1"]) == 3
    assert len(grouped["shp2"]) == 1

    # Check chronological sorting
    shp1_events = grouped["shp1"]
    assert shp1_events[0].event_type == EventType.SHIPMENT_CREATED
    assert shp1_events[1].event_type == EventType.DELAY_DETECTED
    assert shp1_events[2].event_type == EventType.SHIPMENT_DELIVERED


def test_extract_event_timestamps_complete_lifecycle():
    """Test timestamp extraction for complete shipment lifecycle."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1, 0, 0), {"eta": "2024-01-03T00:00:00Z"}),
        ParsedEvent("e2", "shp1", EventType.SHIPMENT_PICKED_UP, datetime(2024, 1, 1, 6, 0), {}),
        ParsedEvent("e3", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 4, 6, 0), {}),
        ParsedEvent("e4", "shp1", EventType.DELAY_DETECTED, datetime(2024, 1, 2, 0, 0), {}),
        ParsedEvent("e5", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 5, 0, 0), {}),
    ]

    timestamps = extract_event_timestamps(events)

    assert timestamps["created_at"].day == 1
    assert timestamps["picked_up_at"].day == 1
    assert timestamps["delivered_at"].day == 4
    assert timestamps["eta"].day == 3
    assert timestamps["first_delay_at"].day == 2
    assert timestamps["first_claim_at"].day == 5


def test_extract_event_timestamps_incomplete():
    """Test timestamp extraction when some events are missing."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1), {}),
        # No pickup, no delivery
    ]

    timestamps = extract_event_timestamps(events)

    assert timestamps["created_at"] is not None
    assert timestamps["picked_up_at"] is None
    assert timestamps["delivered_at"] is None


def test_compute_transit_times_complete():
    """Test transit time computation for complete shipment."""
    from datetime import timezone

    events = [
        ParsedEvent(
            "e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc), {"eta": "2024-01-03T00:00:00+00:00"}
        ),
        ParsedEvent("e2", "shp1", EventType.SHIPMENT_PICKED_UP, datetime(2024, 1, 1, 6, 0, tzinfo=timezone.utc), {}),
        ParsedEvent("e3", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 4, 6, 0, tzinfo=timezone.utc), {}),
    ]

    times = compute_transit_times(events)

    # Planned: Jan 1 00:00 to Jan 3 00:00 = 48 hours
    assert times["planned_transit_hours"] == 48.0

    # Actual: Jan 1 06:00 to Jan 4 06:00 = 72 hours
    assert times["actual_transit_hours"] == 72.0

    # ETA deviation: Jan 4 06:00 - Jan 3 00:00 = 30 hours
    assert times["eta_deviation_hours"] == 30.0

    # Delay: 72 - 48 = 24 hours
    assert times["delay_hours"] == 24.0


def test_compute_transit_times_incomplete():
    """Test transit time computation when data is incomplete."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1), {}),
        # No pickup, no delivery, no ETA
    ]

    times = compute_transit_times(events)

    assert times["planned_transit_hours"] is None
    assert times["actual_transit_hours"] is None
    assert times["eta_deviation_hours"] is None
    assert times["delay_hours"] is None


def test_count_event_types():
    """Test counting event type occurrences."""
    events = [
        ParsedEvent("e1", "shp1", EventType.DELAY_DETECTED, datetime(2024, 1, 1), {}),
        ParsedEvent("e2", "shp1", EventType.DELAY_DETECTED, datetime(2024, 1, 2), {}),
        ParsedEvent("e3", "shp1", EventType.DELAY_DETECTED, datetime(2024, 1, 3), {}),
        ParsedEvent("e4", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 4), {}),
        ParsedEvent("e5", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 5), {}),
    ]

    counts = count_event_types(events)

    assert counts[EventType.DELAY_DETECTED] == 3
    assert counts[EventType.CLAIM_FILED] == 1
    assert counts[EventType.ROUTE_DEVIATION] == 1
    assert counts.get(EventType.DISPUTE_OPENED, 0) == 0


def test_extract_sensor_readings():
    """Test extracting sensor readings from events."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SENSOR_READING, datetime(2024, 1, 1), {"temperature": 20.5, "humidity": 65.0}),
        ParsedEvent("e2", "shp1", EventType.SENSOR_READING, datetime(2024, 1, 2), {"temperature": 22.0, "humidity": 60.0}),
        ParsedEvent("e3", "shp1", EventType.SENSOR_READING, datetime(2024, 1, 3), {"temperature": 21.5, "battery_level": 85.0}),
        ParsedEvent("e4", "shp1", EventType.DELAY_DETECTED, datetime(2024, 1, 4), {}),
    ]

    readings = extract_sensor_readings(events)

    assert readings["temperatures"] == [20.5, 22.0, 21.5]
    assert readings["humidities"] == [65.0, 60.0]
    assert readings["battery_levels"] == [85.0]


def test_extract_sensor_readings_empty():
    """Test sensor reading extraction when no sensor events."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1), {}),
    ]

    readings = extract_sensor_readings(events)

    assert readings["temperatures"] == []
    assert readings["humidities"] == []
    assert readings["battery_levels"] == []


def test_parsed_event_timestamp_string_conversion():
    """Test that ParsedEvent converts string timestamps to datetime."""
    event = ParsedEvent("e1", "shp1", "SHIPMENT_CREATED", "2024-12-11T10:00:00Z", {})

    assert isinstance(event.timestamp, datetime)
    assert event.timestamp.year == 2024


def test_parsed_event_enum_conversion():
    """Test that ParsedEvent converts string event_type to enum."""
    event = ParsedEvent("e1", "shp1", "DELAY_DETECTED", datetime(2024, 1, 1), {})

    assert isinstance(event.event_type, EventType)
    assert event.event_type == EventType.DELAY_DETECTED


def test_parse_event_log_default_source():
    """Test that source defaults to 'system' if not provided."""
    raw_event = {
        "event_id": "evt_123",
        "shipment_id": "shp_456",
        "event_type": "DELAY_DETECTED",
        "timestamp": "2024-12-11T10:00:00Z",
        # No source field
    }

    event = parse_event_log(raw_event)

    assert event.source == "system"


def test_parse_event_log_empty_payload():
    """Test parsing event with empty payload."""
    raw_event = {
        "event_id": "evt_123",
        "shipment_id": "shp_456",
        "event_type": "SHIPMENT_CREATED",
        "timestamp": "2024-12-11T10:00:00Z",
        # No payload field
    }

    event = parse_event_log(raw_event)

    assert event.payload == {}
