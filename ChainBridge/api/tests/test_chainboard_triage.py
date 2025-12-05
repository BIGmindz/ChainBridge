# api/tests/test_chainboard_triage.py
"""
ChainBoard Triage API Tests
============================

Tests for alert work queue and triage endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


# ============================================================================
# WORK QUEUE TESTS
# ============================================================================


def test_get_work_queue_no_filters():
    """Test GET /api/chainboard/alerts/work-queue returns all alerts"""
    response = client.get("/api/chainboard/alerts/work-queue")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert data["total"] > 0

    # Verify work item structure
    if data["items"]:
        item = data["items"][0]
        assert "alert" in item
        assert "owner" in item
        assert "notes" in item
        assert "actions" in item


def test_get_work_queue_with_limit():
    """Test work queue respects limit parameter"""
    response = client.get("/api/chainboard/alerts/work-queue?limit=3")
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) <= 3


def test_get_work_queue_filter_by_status():
    """Test work queue filters by status"""
    response = client.get("/api/chainboard/alerts/work-queue?status=open")
    assert response.status_code == 200

    data = response.json()
    for item in data["items"]:
        assert item["alert"]["status"] == "open"


def test_get_work_queue_filter_by_severity():
    """Test work queue filters by severity"""
    response = client.get("/api/chainboard/alerts/work-queue?severity=critical")
    assert response.status_code == 200

    data = response.json()
    for item in data["items"]:
        assert item["alert"]["severity"] == "critical"


def test_get_work_queue_filter_by_source():
    """Test work queue filters by source"""
    response = client.get("/api/chainboard/alerts/work-queue?source=iot")
    assert response.status_code == 200

    data = response.json()
    for item in data["items"]:
        assert item["alert"]["source"] == "iot"


# ============================================================================
# ASSIGNMENT TESTS
# ============================================================================


def test_assign_alert_to_owner():
    """Test POST /api/chainboard/alerts/{id}/assign assigns alert"""
    # Get first alert
    response = client.get("/api/chainboard/alerts/work-queue?limit=1")
    assert response.status_code == 200
    alert_id = response.json()["items"][0]["alert"]["id"]

    # Assign to owner
    assign_body = {
        "owner_id": "user-123",
        "owner_name": "Jane Operator",
        "owner_email": "jane@chainbridge.io",
        "owner_team": "Ops",
    }
    response = client.post(f"/api/chainboard/alerts/{alert_id}/assign", json=assign_body)
    assert response.status_code == 200

    work_item = response.json()
    assert work_item["owner"] is not None
    assert work_item["owner"]["id"] == "user-123"
    assert work_item["owner"]["name"] == "Jane Operator"

    # Verify action was recorded
    assert len(work_item["actions"]) > 0
    assert work_item["actions"][-1]["type"] == "assign"


def test_unassign_alert():
    """Test POST /api/chainboard/alerts/{id}/assign with null owner_id unassigns"""
    # Get first alert
    response = client.get("/api/chainboard/alerts/work-queue?limit=1")
    assert response.status_code == 200
    alert_id = response.json()["items"][0]["alert"]["id"]

    # Assign first
    assign_body = {
        "owner_id": "user-456",
        "owner_name": "John Operator",
    }
    client.post(f"/api/chainboard/alerts/{alert_id}/assign", json=assign_body)

    # Unassign
    unassign_body = {
        "owner_id": None,
        "owner_name": "System",
    }
    response = client.post(f"/api/chainboard/alerts/{alert_id}/assign", json=unassign_body)
    assert response.status_code == 200

    work_item = response.json()
    assert work_item["owner"] is None


def test_assign_alert_not_found():
    """Test assigning non-existent alert returns 404"""
    assign_body = {
        "owner_id": "user-123",
        "owner_name": "Jane Operator",
    }
    response = client.post("/api/chainboard/alerts/nonexistent-id/assign", json=assign_body)
    assert response.status_code == 404


def test_work_queue_filter_by_owner():
    """Test work queue filters by assigned owner"""
    # Get first alert
    response = client.get("/api/chainboard/alerts/work-queue?limit=1")
    assert response.status_code == 200
    alert_id = response.json()["items"][0]["alert"]["id"]

    # Assign to specific owner
    assign_body = {
        "owner_id": "owner-filter-test",
        "owner_name": "Filter Test User",
    }
    client.post(f"/api/chainboard/alerts/{alert_id}/assign", json=assign_body)

    # Query by owner
    response = client.get("/api/chainboard/alerts/work-queue?owner_id=owner-filter-test")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["owner"] is not None
        assert item["owner"]["id"] == "owner-filter-test"


# ============================================================================
# NOTE TESTS
# ============================================================================


def test_add_note_to_alert():
    """Test POST /api/chainboard/alerts/{id}/notes adds note"""
    # Get first alert
    response = client.get("/api/chainboard/alerts/work-queue?limit=1")
    assert response.status_code == 200
    alert_id = response.json()["items"][0]["alert"]["id"]

    # Add note
    note_body = {
        "message": "Investigating cold chain breach; checking IoT sensors.",
        "author_id": "user-789",
        "author_name": "Alice Analyst",
        "author_email": "alice@chainbridge.io",
    }
    response = client.post(f"/api/chainboard/alerts/{alert_id}/notes", json=note_body)
    assert response.status_code == 200

    work_item = response.json()
    assert len(work_item["notes"]) > 0

    # Find our note
    note = work_item["notes"][-1]
    assert note["message"] == "Investigating cold chain breach; checking IoT sensors."
    assert note["author"]["id"] == "user-789"
    assert note["author"]["name"] == "Alice Analyst"

    # Verify action was recorded
    assert len(work_item["actions"]) > 0
    comment_actions = [a for a in work_item["actions"] if a["type"] == "comment"]
    assert len(comment_actions) > 0


def test_add_note_alert_not_found():
    """Test adding note to non-existent alert returns 404"""
    note_body = {
        "message": "Test note",
        "author_id": "user-123",
        "author_name": "Test User",
    }
    response = client.post("/api/chainboard/alerts/nonexistent-id/notes", json=note_body)
    assert response.status_code == 404


# ============================================================================
# STATUS UPDATE TESTS
# ============================================================================


def test_update_alert_status_to_acknowledged():
    """Test POST /api/chainboard/alerts/{id}/status updates status"""
    # Get an open alert
    response = client.get("/api/chainboard/alerts/work-queue?status=open&limit=1")
    assert response.status_code == 200

    items = response.json()["items"]
    if not items:
        pytest.skip("No open alerts available for test")

    alert_id = items[0]["alert"]["id"]

    # Acknowledge
    status_body = {
        "status": "acknowledged",
        "actor_id": "user-999",
        "actor_name": "Bob Manager",
    }
    response = client.post(f"/api/chainboard/alerts/{alert_id}/status", json=status_body)
    assert response.status_code == 200

    work_item = response.json()
    assert work_item["alert"]["status"] == "acknowledged"

    # Verify action was recorded
    assert len(work_item["actions"]) > 0
    assert work_item["actions"][-1]["type"] == "acknowledge"


def test_update_alert_status_to_resolved():
    """Test resolving an alert"""
    # Get any alert
    response = client.get("/api/chainboard/alerts/work-queue?limit=1")
    assert response.status_code == 200
    alert_id = response.json()["items"][0]["alert"]["id"]

    # Resolve
    status_body = {
        "status": "resolved",
        "actor_id": "user-888",
        "actor_name": "Charlie Resolver",
    }
    response = client.post(f"/api/chainboard/alerts/{alert_id}/status", json=status_body)
    assert response.status_code == 200

    work_item = response.json()
    assert work_item["alert"]["status"] == "resolved"

    # Verify action was recorded
    assert len(work_item["actions"]) > 0
    assert work_item["actions"][-1]["type"] == "resolve"


def test_update_status_alert_not_found():
    """Test updating status of non-existent alert returns 404"""
    status_body = {
        "status": "acknowledged",
        "actor_id": "user-123",
        "actor_name": "Test User",
    }
    response = client.post("/api/chainboard/alerts/nonexistent-id/status", json=status_body)
    assert response.status_code == 404


def test_work_queue_filter_after_status_change():
    """Test work queue filters reflect status changes"""
    # Get an open alert
    response = client.get("/api/chainboard/alerts/work-queue?status=open&limit=1")
    assert response.status_code == 200

    items = response.json()["items"]
    if not items:
        pytest.skip("No open alerts available for test")

    alert_id = items[0]["alert"]["id"]

    # Resolve it
    status_body = {
        "status": "resolved",
        "actor_id": "user-777",
        "actor_name": "Test Resolver",
    }
    client.post(f"/api/chainboard/alerts/{alert_id}/status", json=status_body)

    # Verify it's in resolved queue
    response = client.get("/api/chainboard/alerts/work-queue?status=resolved")
    assert response.status_code == 200

    resolved_items = response.json()["items"]
    resolved_ids = [item["alert"]["id"] for item in resolved_items]
    assert alert_id in resolved_ids

    # Verify it's NOT in open queue
    response = client.get("/api/chainboard/alerts/work-queue?status=open")
    assert response.status_code == 200

    open_items = response.json()["items"]
    open_ids = [item["alert"]["id"] for item in open_items]
    assert alert_id not in open_ids
