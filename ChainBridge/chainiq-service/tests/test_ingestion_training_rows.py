"""
Unit tests for ChainIQ ML training row factory.

Tests cover:
- extract_features_from_events
- build_training_rows_from_events
- backfill_training_data (integration test)
"""

import json
from datetime import datetime


from app.ml.event_parsing import EventType, ParsedEvent
from app.ml.ingestion import backfill_training_data, build_training_rows_from_events, extract_features_from_events


def test_extract_features_from_events_basic():
    """Test feature extraction from basic event stream."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1, 0, 0), {"eta": "2024-01-03T00:00:00Z"}),
        ParsedEvent("e2", "shp1", EventType.SHIPMENT_PICKED_UP, datetime(2024, 1, 1, 6, 0), {}),
        ParsedEvent("e3", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 4, 6, 0), {}),
    ]

    features = extract_features_from_events("shp1", events)

    assert features["shipment_id"] == "shp1"
    assert features["planned_transit_hours"] == 48.0
    assert features["actual_transit_hours"] == 72.0
    assert features["eta_deviation_hours"] == 30.0
    assert features["num_route_deviations"] == 0
    assert features["handoff_count"] == 0


def test_extract_features_with_route_deviations():
    """Test feature extraction with route deviations."""
    events = [
        ParsedEvent("e1", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 2), {"deviation_km": 15.5}),
        ParsedEvent("e2", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 3), {"deviation_km": 25.0}),
    ]

    features = extract_features_from_events("shp1", events)

    assert features["num_route_deviations"] == 2
    assert features["max_route_deviation_km"] == 25.0


def test_extract_features_with_dwell_times():
    """Test feature extraction with dwell times."""
    events = [
        ParsedEvent("e1", "shp1", EventType.DWELL_START, datetime(2024, 1, 2, 10, 0), {}),
        ParsedEvent("e2", "shp1", EventType.DWELL_END, datetime(2024, 1, 2, 14, 0), {}),
        ParsedEvent("e3", "shp1", EventType.DWELL_START, datetime(2024, 1, 3, 8, 0), {}),
        ParsedEvent("e4", "shp1", EventType.DWELL_END, datetime(2024, 1, 3, 10, 0), {}),
    ]

    features = extract_features_from_events("shp1", events)

    # First dwell: 4 hours, second dwell: 2 hours
    assert features["total_dwell_hours"] == 6.0
    assert features["max_single_dwell_hours"] == 4.0


def test_extract_features_with_sensor_readings():
    """Test feature extraction with sensor readings."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SENSOR_READING, datetime(2024, 1, 1), {"temperature": 20.0}),
        ParsedEvent("e2", "shp1", EventType.SENSOR_READING, datetime(2024, 1, 2), {"temperature": 22.0}),
        ParsedEvent("e3", "shp1", EventType.SENSOR_READING, datetime(2024, 1, 3), {"temperature": 24.0}),
    ]

    features = extract_features_from_events("shp1", events)

    # Mean: (20 + 22 + 24) / 3 = 22.0
    assert features["temp_mean"] == 22.0
    # Std: should be > 0
    assert features["temp_std"] > 0


def test_extract_features_with_missing_docs():
    """Test feature extraction with missing documentation flag."""
    events = [
        ParsedEvent("e1", "shp1", EventType.MISSING_DOCUMENTATION, datetime(2024, 1, 2), {}),
    ]

    features = extract_features_from_events("shp1", events)

    assert features["missing_required_docs"] is True


def test_extract_features_with_delay_flag():
    """Test feature extraction with delay flag."""
    events = [
        ParsedEvent("e1", "shp1", EventType.DELAY_DETECTED, datetime(2024, 1, 2), {}),
    ]

    features = extract_features_from_events("shp1", events)

    assert features["delay_flag"] is True


def test_build_training_rows_from_events_single_shipment():
    """Test building training rows from single shipment."""
    event_records = [
        {
            "event_id": "e1",
            "shipment_id": "shp1",
            "event_type": "SHIPMENT_CREATED",
            "timestamp": "2024-01-01T00:00:00Z",
            "payload": {"eta": "2024-01-03T00:00:00Z"},
        },
        {
            "event_id": "e2",
            "shipment_id": "shp1",
            "event_type": "SHIPMENT_DELIVERED",
            "timestamp": "2024-01-05T06:00:00Z",  # 54 hours late (>48h threshold)
            "payload": {},
        },
        {
            "event_id": "e3",
            "shipment_id": "shp1",
            "event_type": "CLAIM_FILED",
            "timestamp": "2024-01-06T00:00:00Z",
            "payload": {"claim_amount": 500.0},
        },
    ]

    rows = build_training_rows_from_events(event_records)

    assert len(rows) == 1
    assert rows[0].shipment_id == "shp1"
    assert rows[0].had_claim is True
    assert rows[0].severe_delay is True  # >48 hours late (54h)
    assert rows[0].bad_outcome is True  # Has claim + severe delay


def test_build_training_rows_from_events_multiple_shipments():
    """Test building training rows from multiple shipments."""
    event_records = [
        # Shipment 1
        {
            "event_id": "e1",
            "shipment_id": "shp1",
            "event_type": "SHIPMENT_CREATED",
            "timestamp": "2024-01-01T00:00:00Z",
            "payload": {"eta": "2024-01-03T00:00:00Z"},
        },
        {"event_id": "e2", "shipment_id": "shp1", "event_type": "SHIPMENT_DELIVERED", "timestamp": "2024-01-03T00:00:00Z", "payload": {}},
        # Shipment 2
        {
            "event_id": "e3",
            "shipment_id": "shp2",
            "event_type": "SHIPMENT_CREATED",
            "timestamp": "2024-01-02T00:00:00Z",
            "payload": {"eta": "2024-01-04T00:00:00Z"},
        },
        {"event_id": "e4", "shipment_id": "shp2", "event_type": "SHIPMENT_DELIVERED", "timestamp": "2024-01-07T00:00:00Z", "payload": {}},
        {"event_id": "e5", "shipment_id": "shp2", "event_type": "CLAIM_FILED", "timestamp": "2024-01-08T00:00:00Z", "payload": {}},
    ]

    rows = build_training_rows_from_events(event_records)

    assert len(rows) == 2

    # Shipment 1: on-time, no claim
    shp1 = next(r for r in rows if r.shipment_id == "shp1")
    assert shp1.had_claim is False
    assert shp1.severe_delay is False
    assert shp1.bad_outcome is False

    # Shipment 2: late, with claim
    shp2 = next(r for r in rows if r.shipment_id == "shp2")
    assert shp2.had_claim is True
    assert shp2.severe_delay is True
    assert shp2.bad_outcome is True


def test_build_training_rows_filter_incomplete():
    """Test filtering incomplete shipments (no delivery)."""
    event_records = [
        # Complete shipment
        {"event_id": "e1", "shipment_id": "shp1", "event_type": "SHIPMENT_CREATED", "timestamp": "2024-01-01T00:00:00Z", "payload": {}},
        {"event_id": "e2", "shipment_id": "shp1", "event_type": "SHIPMENT_DELIVERED", "timestamp": "2024-01-03T00:00:00Z", "payload": {}},
        # Incomplete shipment (no delivery)
        {"event_id": "e3", "shipment_id": "shp2", "event_type": "SHIPMENT_CREATED", "timestamp": "2024-01-02T00:00:00Z", "payload": {}},
    ]

    rows = build_training_rows_from_events(event_records, filter_incomplete=True)

    # Should only have shp1 (complete)
    assert len(rows) == 1
    assert rows[0].shipment_id == "shp1"


def test_build_training_rows_include_incomplete():
    """Test including incomplete shipments when filter_incomplete=False."""
    event_records = [
        # Complete shipment
        {"event_id": "e1", "shipment_id": "shp1", "event_type": "SHIPMENT_CREATED", "timestamp": "2024-01-01T00:00:00Z", "payload": {}},
        {"event_id": "e2", "shipment_id": "shp1", "event_type": "SHIPMENT_DELIVERED", "timestamp": "2024-01-03T00:00:00Z", "payload": {}},
        # Incomplete shipment (no delivery)
        {"event_id": "e3", "shipment_id": "shp2", "event_type": "SHIPMENT_CREATED", "timestamp": "2024-01-02T00:00:00Z", "payload": {}},
    ]

    rows = build_training_rows_from_events(event_records, filter_incomplete=False)

    # Should have both shipments
    assert len(rows) == 2


def test_build_training_rows_handles_invalid_events():
    """Test that invalid events are skipped gracefully."""
    event_records = [
        # Valid event
        {"event_id": "e1", "shipment_id": "shp1", "event_type": "SHIPMENT_CREATED", "timestamp": "2024-01-01T00:00:00Z", "payload": {}},
        # Invalid event (missing required field)
        {
            "event_id": "e2",
            # Missing shipment_id
            "event_type": "SHIPMENT_DELIVERED",
            "timestamp": "2024-01-03T00:00:00Z",
        },
        # Another valid event
        {"event_id": "e3", "shipment_id": "shp1", "event_type": "SHIPMENT_DELIVERED", "timestamp": "2024-01-03T00:00:00Z", "payload": {}},
    ]

    rows = build_training_rows_from_events(event_records)

    # Should successfully build row for shp1 (invalid event skipped)
    assert len(rows) == 1
    assert rows[0].shipment_id == "shp1"


def test_backfill_training_data_integration(tmp_path):
    """Integration test for full backfill pipeline."""
    # Create temporary input file
    input_file = tmp_path / "events.jsonl"
    output_file = tmp_path / "training_rows.jsonl"

    # Write test events
    events = [
        {
            "event_id": "e1",
            "shipment_id": "shp1",
            "event_type": "SHIPMENT_CREATED",
            "timestamp": "2024-01-01T00:00:00Z",
            "payload": {"eta": "2024-01-03T00:00:00Z"},
        },
        {
            "event_id": "e2",
            "shipment_id": "shp1",
            "event_type": "SHIPMENT_DELIVERED",
            "timestamp": "2024-01-05T06:00:00Z",  # 54 hours late (>48h threshold)
            "payload": {},
        },
        {
            "event_id": "e3",
            "shipment_id": "shp1",
            "event_type": "CLAIM_FILED",
            "timestamp": "2024-01-06T00:00:00Z",
            "payload": {"claim_amount": 750.0},
        },
    ]

    with open(input_file, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    # Run backfill
    count = backfill_training_data(str(input_file), str(output_file))

    assert count == 1
    assert output_file.exists()

    # Read and verify output
    with open(output_file, "r") as f:
        lines = f.readlines()

    assert len(lines) == 1

    row_dict = json.loads(lines[0])
    assert row_dict["shipment_id"] == "shp1"
    assert row_dict["had_claim"] is True
    assert row_dict["severe_delay"] is True


def test_backfill_training_data_empty_input(tmp_path):
    """Test backfill with empty input file."""
    input_file = tmp_path / "empty_events.jsonl"
    output_file = tmp_path / "training_rows.jsonl"

    # Create empty file
    input_file.touch()

    count = backfill_training_data(str(input_file), str(output_file))

    assert count == 0
    assert output_file.exists()

    # Output should be empty
    with open(output_file, "r") as f:
        lines = f.readlines()
    assert len(lines) == 0


def test_extract_features_defaults_for_missing_data():
    """Test that feature extraction provides sensible defaults for missing data."""
    from datetime import timezone

    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1, tzinfo=timezone.utc), {}),
        # No other events
    ]

    features = extract_features_from_events("shp1", events)

    # Should have defaults (transit times will be None without ETA/delivery)
    assert features["planned_transit_hours"] == 48.0  # Default
    assert features["actual_transit_hours"] == 48.0  # Default
    assert features["eta_deviation_hours"] == 0.0
    assert features["temp_mean"] == 20.0  # Default
    assert features["temp_std"] == 0.0  # No variance with default
    assert features["carrier_on_time_pct_90d"] == 85.0  # Simulated
    assert features["lane_sentiment_score"] == 0.7  # Simulated


def test_training_row_determinism():
    """Test that the same events produce the same training row."""
    event_records = [
        {
            "event_id": "e1",
            "shipment_id": "shp1",
            "event_type": "SHIPMENT_CREATED",
            "timestamp": "2024-01-01T00:00:00Z",
            "payload": {"eta": "2024-01-03T00:00:00Z"},
        },
        {"event_id": "e2", "shipment_id": "shp1", "event_type": "SHIPMENT_DELIVERED", "timestamp": "2024-01-03T00:00:00Z", "payload": {}},
    ]

    # Build rows twice
    rows1 = build_training_rows_from_events(event_records)
    rows2 = build_training_rows_from_events(event_records)

    # Should be identical
    assert len(rows1) == len(rows2)
    assert rows1[0].shipment_id == rows2[0].shipment_id
    assert rows1[0].had_claim == rows2[0].had_claim
    assert rows1[0].severe_delay == rows2[0].severe_delay
    assert rows1[0].planned_transit_hours == rows2[0].planned_transit_hours
