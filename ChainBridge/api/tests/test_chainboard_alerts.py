# api/tests/test_chainboard_alerts.py
"""
ChainBoard Alerts & Triage Endpoint Tests
=========================================

Tests for the /api/chainboard/alerts endpoints, validating:
- Alert listing with filters
- Alert detail retrieval
- Response schema compliance
- Error handling

Author: ChainBridge Platform Team
Version: 1.0.0 (Production-Ready)
"""

from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)

BASE_URL = "/api/chainboard"


def test_list_alerts_basic():
    """Test basic alert listing returns valid response"""
    response = client.get(f"{BASE_URL}/alerts")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "alerts" in data
    assert "total" in data
    assert "generated_at" in data

    # Verify we have alerts
    assert isinstance(data["alerts"], list)
    assert data["total"] > 0
    assert len(data["alerts"]) > 0

    # Verify first alert has required fields
    alert = data["alerts"][0]
    assert "id" in alert
    assert "shipment_reference" in alert
    assert "title" in alert
    assert "description" in alert
    assert "source" in alert
    assert "severity" in alert
    assert "status" in alert
    assert "created_at" in alert
    assert "updated_at" in alert
    assert "tags" in alert


def test_list_alerts_sorted_desc():
    """Test alerts are sorted by created_at descending"""
    response = client.get(f"{BASE_URL}/alerts?limit=100")

    assert response.status_code == 200
    data = response.json()
    alerts = data["alerts"]

    # Verify descending order
    for i in range(len(alerts) - 1):
        current = alerts[i]["created_at"]
        next_alert = alerts[i + 1]["created_at"]
        assert current >= next_alert, f"Alerts not sorted: {current} < {next_alert}"


def test_list_alerts_filter_by_source():
    """Test filtering alerts by source"""
    response = client.get(f"{BASE_URL}/alerts?source=risk")

    assert response.status_code == 200
    data = response.json()
    alerts = data["alerts"]

    # Verify all alerts are from risk source
    for alert in alerts:
        assert alert["source"] == "risk"


def test_list_alerts_filter_by_severity():
    """Test filtering alerts by severity"""
    response = client.get(f"{BASE_URL}/alerts?severity=critical")

    assert response.status_code == 200
    data = response.json()
    alerts = data["alerts"]

    # Verify all alerts are critical
    for alert in alerts:
        assert alert["severity"] == "critical"


def test_list_alerts_filter_by_status():
    """Test filtering alerts by status"""
    response = client.get(f"{BASE_URL}/alerts?status=open")

    assert response.status_code == 200
    data = response.json()
    alerts = data["alerts"]

    # Verify all alerts are open
    for alert in alerts:
        assert alert["status"] == "open"


def test_list_alerts_limit_parameter():
    """Test limit parameter restricts results"""
    response = client.get(f"{BASE_URL}/alerts?limit=3")

    assert response.status_code == 200
    data = response.json()

    # Should have at most 3 alerts
    assert len(data["alerts"]) <= 3


def test_get_alert_detail():
    """Test retrieving a single alert by ID"""
    # First get list of alerts
    list_response = client.get(f"{BASE_URL}/alerts")
    assert list_response.status_code == 200
    alerts = list_response.json()["alerts"]
    assert len(alerts) > 0

    # Get first alert ID
    alert_id = alerts[0]["id"]

    # Retrieve alert detail
    response = client.get(f"{BASE_URL}/alerts/{alert_id}")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "alert" in data
    alert = data["alert"]

    # Verify it's the same alert
    assert alert["id"] == alert_id
    assert "shipment_reference" in alert
    assert "title" in alert
    assert "description" in alert


def test_get_alert_not_found():
    """Test 404 response for non-existent alert"""
    fake_id = "alert-00000000-0000-0000-0000-000000000000"

    response = client.get(f"{BASE_URL}/alerts/{fake_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_alert_has_valid_enums():
    """Test all alerts have valid enum values"""
    response = client.get(f"{BASE_URL}/alerts?limit=100")

    assert response.status_code == 200
    alerts = response.json()["alerts"]

    valid_sources = ["risk", "iot", "payment", "customs"]
    valid_severities = ["info", "warning", "critical"]
    valid_statuses = ["open", "acknowledged", "resolved"]

    for alert in alerts:
        assert alert["source"] in valid_sources
        assert alert["severity"] in valid_severities
        assert alert["status"] in valid_statuses


def test_alert_tags_are_list():
    """Test alert tags field is always a list"""
    response = client.get(f"{BASE_URL}/alerts")

    assert response.status_code == 200
    alerts = response.json()["alerts"]

    for alert in alerts:
        assert isinstance(alert["tags"], list)
