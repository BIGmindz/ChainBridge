"""
Tests for ChainBoard IoT endpoints and ChainSense IoT provider.

This test suite verifies:
- IoT health summary endpoint
- Per-shipment IoT snapshot endpoints
- IoT provider façade functionality
- Edge cases (missing IoT data, shipments without sensors)
"""

from fastapi.testclient import TestClient

from api.chainsense.client import MockIoTDataProvider
from api.server import app

client = TestClient(app)


# ============================================================================
# GLOBAL IOT HEALTH TESTS
# ============================================================================


def test_get_iot_health_snapshot():
    """Test GET /api/chainboard/iot/health returns valid health summary."""
    response = client.get("/api/chainboard/iot/health")
    assert response.status_code == 200

    payload = response.json()
    assert "iot_health" in payload
    assert "generated_at" in payload

    iot_health = payload["iot_health"]
    for field in [
        "shipments_with_iot",
        "active_sensors",
        "alerts_last_24h",
        "critical_alerts_last_24h",
        "coverage_percent",
    ]:
        assert field in iot_health
        assert isinstance(iot_health[field], (int, float))


def test_iot_health_coverage_within_range():
    """Test that coverage percent is between 0 and 100."""
    response = client.get("/api/chainboard/iot/health")
    payload = response.json()
    coverage = payload["iot_health"]["coverage_percent"]
    assert 0 <= coverage <= 100


def test_iot_health_via_chainboard_metrics():
    """Test GET /api/chainboard/metrics/iot/summary also works."""
    response = client.get("/api/chainboard/metrics/iot/summary")
    assert response.status_code == 200

    payload = response.json()
    assert "iot_health" in payload
    assert payload["iot_health"]["shipments_with_iot"] > 0


# ============================================================================
# PER-SHIPMENT IOT SNAPSHOT TESTS
# ============================================================================


def test_get_shipment_iot_snapshot_exists():
    """Test retrieving IoT snapshot for a shipment with sensors."""
    # SHP-1001 is known to have IoT sensors
    response = client.get("/api/chainboard/metrics/iot/shipments/SHP-1001")
    assert response.status_code == 200

    payload = response.json()
    assert "snapshot" in payload
    assert "retrieved_at" in payload

    snapshot = payload["snapshot"]
    assert snapshot["shipment_id"] == "SHP-1001"
    assert "latest_readings" in snapshot
    assert isinstance(snapshot["latest_readings"], list)
    assert "alert_count_24h" in snapshot
    assert "critical_alerts_24h" in snapshot


def test_get_shipment_iot_snapshot_not_found():
    """Test 404 for shipment without IoT sensors."""
    # NONEXISTENT-999 does not have IoT data
    response = client.get("/api/chainboard/metrics/iot/shipments/NONEXISTENT-999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_shipment_iot_snapshot_has_sensor_readings():
    """Test that snapshots contain valid sensor readings."""
    response = client.get("/api/chainboard/metrics/iot/shipments/SHP-1001")
    payload = response.json()

    readings = payload["snapshot"]["latest_readings"]
    assert len(readings) > 0

    # Check first reading has required fields
    first_reading = readings[0]
    assert "sensor_type" in first_reading
    assert "value" in first_reading
    assert "timestamp" in first_reading
    assert "status" in first_reading


def test_shipment_iot_snapshot_critical_alerts():
    """Test shipment with critical IoT alerts."""
    # SHP-1004 has a door open alert (critical)
    response = client.get("/api/chainboard/metrics/iot/shipments/SHP-1004")
    payload = response.json()

    snapshot = payload["snapshot"]
    assert snapshot["critical_alerts_24h"] > 0


# ============================================================================
# IOT PROVIDER FAÇADE TESTS
# ============================================================================


def test_mock_iot_provider_global_health():
    """Test MockIoTDataProvider.get_global_health() directly."""
    provider = MockIoTDataProvider()
    health = provider.get_global_health()

    assert health.shipments_with_iot > 0
    assert health.active_sensors > 0
    assert 0 <= health.coverage_percent <= 100


def test_mock_iot_provider_shipment_snapshot():
    """Test MockIoTDataProvider.get_shipment_snapshot() directly."""
    provider = MockIoTDataProvider()

    # Test existing shipment
    snapshot = provider.get_shipment_snapshot("SHP-1001")
    assert snapshot is not None
    assert snapshot.shipment_id == "SHP-1001"
    assert len(snapshot.latest_readings) > 0

    # Test non-existent shipment
    snapshot = provider.get_shipment_snapshot("DOES-NOT-EXIST")
    assert snapshot is None


def test_mock_iot_provider_shipment_events():
    """Test MockIoTDataProvider.get_shipment_events() returns IoT events only."""
    provider = MockIoTDataProvider()

    # SHP-1001 should have IoT_ALERT events
    events = provider.get_shipment_events("SHP-1001", limit=10)

    # Should return list (may be empty if no IoT events generated)
    assert isinstance(events, list)

    # If there are events, they should all be IoT_ALERT type
    for event in events:
        assert event.event_type.value == "iot_alert"


def test_mock_iot_provider_events_sorted_by_recent():
    """Test that IoT events are sorted most recent first."""
    provider = MockIoTDataProvider()
    events = provider.get_shipment_events("SHP-1001", limit=50)

    if len(events) > 1:
        # Verify descending order by occurred_at
        for i in range(len(events) - 1):
            assert events[i].occurred_at >= events[i + 1].occurred_at


# ============================================================================
# LIST IOT SNAPSHOTS TESTS
# ============================================================================


def test_list_shipment_iot_snapshots():
    """Test listing IoT snapshots with limit."""
    response = client.get("/api/chainboard/metrics/iot/shipments?limit=5")
    assert response.status_code == 200

    payload = response.json()
    assert "snapshots" in payload
    assert "total" in payload
    assert len(payload["snapshots"]) <= 5


def test_list_iot_snapshots_filter_by_alerts():
    """Test filtering snapshots by alert presence."""
    response = client.get("/api/chainboard/metrics/iot/shipments?has_alerts=true")
    assert response.status_code == 200

    payload = response.json()
    snapshots = payload["snapshots"]

    # All returned snapshots should have alerts
    for snapshot in snapshots:
        assert snapshot["alert_count_24h"] > 0 or snapshot["critical_alerts_24h"] > 0
