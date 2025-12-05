# api/tests/test_chainboard_events.py
"""
Tests for Timeline Events Endpoints
===================================

Validates the /api/chainboard/events and /api/chainboard/shipments/{ref}/events endpoints.
"""

from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


def test_list_events():
    """Test that events endpoint returns valid structure."""
    response = client.get("/api/chainboard/events")

    assert response.status_code == 200
    data = response.json()

    # Validate envelope structure
    assert "events" in data
    assert "total" in data
    assert "generated_at" in data

    # Validate counts
    assert isinstance(data["events"], list)
    assert data["total"] == len(data["events"])
    assert data["total"] > 0  # Should have events from mock data


def test_event_has_required_fields():
    """Test that each event has all required fields with valid data."""
    response = client.get("/api/chainboard/events")
    assert response.status_code == 200

    events = response.json()["events"]
    assert len(events) > 0

    for event in events:
        # Required fields
        assert "shipment_id" in event
        assert "reference" in event
        assert "corridor" in event
        assert "event_type" in event
        assert "description" in event
        assert "occurred_at" in event
        assert "source" in event
        assert "severity" in event

        # Validate field types and formats
        assert isinstance(event["shipment_id"], str)
        assert isinstance(event["reference"], str)
        assert isinstance(event["corridor"], str)
        assert isinstance(event["event_type"], str)
        assert isinstance(event["description"], str)
        assert isinstance(event["occurred_at"], str)  # ISO datetime
        assert isinstance(event["source"], str)
        assert isinstance(event["severity"], str)

        # Validate enum values
        assert event["event_type"] in [
            "created",
            "booked",
            "picked_up",
            "departed_port",
            "arrived_port",
            "customs_hold",
            "customs_released",
            "delivered",
            "payment_release",
            "iot_alert",
        ]
        assert event["source"] in ["TMS", "IoT", "Finance"]
        assert event["severity"] in ["info", "warning", "critical"]


def test_events_sorted_by_time():
    """Test that events are sorted by occurred_at descending (most recent first)."""
    response = client.get("/api/chainboard/events")
    assert response.status_code == 200

    events = response.json()["events"]

    # Convert to timestamps and verify descending order
    timestamps = [event["occurred_at"] for event in events]
    assert timestamps == sorted(timestamps, reverse=True)


def test_events_limit_parameter():
    """Test that limit parameter correctly restricts result count."""
    # Get first 5 events
    response = client.get("/api/chainboard/events?limit=5")
    assert response.status_code == 200

    data = response.json()
    assert len(data["events"]) == 5
    assert data["total"] == 5

    # Get first 10 events
    response = client.get("/api/chainboard/events?limit=10")
    assert response.status_code == 200

    data = response.json()
    assert len(data["events"]) == 10
    assert data["total"] == 10


def test_get_shipment_events():
    """Test that shipment-specific events endpoint returns filtered results."""
    # First, get all events to find a valid reference
    response = client.get("/api/chainboard/events")
    assert response.status_code == 200

    all_events = response.json()["events"]
    assert len(all_events) > 0

    # Pick the first event's reference
    test_reference = all_events[0]["reference"]

    # Get events for this specific shipment
    response = client.get(f"/api/chainboard/shipments/{test_reference}/events")
    assert response.status_code == 200

    data = response.json()
    assert "events" in data
    assert len(data["events"]) > 0

    # Verify all events belong to the requested shipment
    for event in data["events"]:
        assert event["reference"] == test_reference


def test_get_shipment_events_not_found():
    """Test that non-existent shipment reference returns 404."""
    response = client.get("/api/chainboard/shipments/INVALID-REF-9999/events")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_shipment_events_limit_parameter():
    """Test that limit parameter works for shipment-specific events."""
    # Get a valid reference
    response = client.get("/api/chainboard/events")
    test_reference = response.json()["events"][0]["reference"]

    # Get events with limit
    response = client.get(f"/api/chainboard/shipments/{test_reference}/events?limit=3")
    assert response.status_code == 200

    data = response.json()
    assert len(data["events"]) <= 3
    assert data["total"] <= 3
