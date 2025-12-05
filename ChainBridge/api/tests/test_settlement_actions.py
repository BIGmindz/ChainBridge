# api/tests/test_settlement_actions.py
"""
Tests for Settlement Operator Action Endpoints
===============================================

Validates settlement operator actions with audit logging.
"""

import pytest
from fastapi.testclient import TestClient

from api.server import app
from api.storage.settlement_actions import clear_actions, list_recent_actions

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_action_log():
    clear_actions()


def test_escalate_to_risk_success():
    """Test escalate to risk action endpoint."""
    milestone_id = "SHP-2025-001-M1"
    payload = {
        "reason": "High risk shipment detected",
        "requested_by": "operator@chainbridge.com",
    }

    response = client.post(
        f"/api/chainboard/settlements/{milestone_id}/actions/escalate",
        json=payload,
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["milestone_id"] == milestone_id
    assert data["action"] == "escalate_to_risk"
    assert data["note"] == "action logged"
    assert data["requested_by"] == "operator@chainbridge.com"
    assert "created_at" in data

    actions = list_recent_actions(5)
    assert len(actions) == 1
    assert actions[0].milestone_id == milestone_id
    assert actions[0].action == "escalate_to_risk"
    assert actions[0].reason == payload["reason"]


def test_escalate_to_risk_minimal_payload():
    """Test escalate action with minimal payload (no reason or requested_by)."""
    milestone_id = "SHP-2025-002-M2"
    payload = {}

    response = client.post(
        f"/api/chainboard/settlements/{milestone_id}/actions/escalate",
        json=payload,
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["milestone_id"] == milestone_id
    assert data["requested_by"] is None
    actions = list_recent_actions(5)
    assert len(actions) == 1
    assert actions[0].requested_by is None


def test_mark_manually_reviewed_success():
    """Test mark as manually reviewed action endpoint."""
    milestone_id = "SHP-2025-003-M3"
    payload = {
        "reason": "Operator verified all documents",
        "requested_by": "reviewer@chainbridge.com",
    }

    response = client.post(
        f"/api/chainboard/settlements/{milestone_id}/actions/mark-reviewed",
        json=payload,
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["milestone_id"] == milestone_id
    assert data["action"] == "mark_manually_reviewed"
    assert data["note"] == "action logged"
    assert data["requested_by"] == "reviewer@chainbridge.com"
    actions = list_recent_actions(5)
    assert len(actions) == 1
    assert actions[0].action == "mark_manually_reviewed"


def test_request_documentation_success():
    """Test request documentation action endpoint."""
    milestone_id = "SHP-2025-004-M4"
    payload = {
        "reason": "Missing POD confirmation",
        "requested_by": "compliance@chainbridge.com",
    }

    response = client.post(
        f"/api/chainboard/settlements/{milestone_id}/actions/request-docs",
        json=payload,
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["milestone_id"] == milestone_id
    assert data["action"] == "request_documentation"
    assert data["note"] == "action logged"
    assert data["requested_by"] == "compliance@chainbridge.com"
    actions = list_recent_actions(5)
    assert len(actions) == 1
    assert actions[0].action == "request_documentation"


def test_invalid_milestone_id_format():
    """Test action endpoint with invalid milestone_id format."""
    milestone_id = "X"  # Too short
    payload = {}

    response = client.post(
        f"/api/chainboard/settlements/{milestone_id}/actions/escalate",
        json=payload,
    )

    assert response.status_code == 400
    data = response.json()
    assert "Invalid milestone_id format" in data["detail"]


def test_empty_milestone_id():
    """Test action endpoint with empty milestone_id."""
    # FastAPI will handle this at the path level, but test for completeness
    milestone_id = ""
    payload = {}

    # Empty milestone_id in path will result in 404 (no route match)
    response = client.post(
        f"/api/chainboard/settlements/{milestone_id}/actions/escalate",
        json=payload,
    )

    # Should be 404 (not found) since the route pattern won't match
    assert response.status_code == 404


def test_all_action_types():
    """Test all three action types to ensure consistent behavior."""
    milestone_id = "SHP-2025-005-M5"
    payload = {"requested_by": "test-operator"}

    # Test escalate
    response1 = client.post(
        f"/api/chainboard/settlements/{milestone_id}/actions/escalate",
        json=payload,
    )
    assert response1.status_code == 202
    assert response1.json()["action"] == "escalate_to_risk"

    # Test mark-reviewed
    response2 = client.post(
        f"/api/chainboard/settlements/{milestone_id}/actions/mark-reviewed",
        json=payload,
    )
    assert response2.status_code == 202
    assert response2.json()["action"] == "mark_manually_reviewed"

    # Test request-docs
    response3 = client.post(
        f"/api/chainboard/settlements/{milestone_id}/actions/request-docs",
        json=payload,
    )
    assert response3.status_code == 202
    assert response3.json()["action"] == "request_documentation"


def test_recent_actions_endpoint():
    """Verify the recent actions endpoint returns ordered records."""
    payload = {"requested_by": "audit@chainbridge.com"}
    client.post("/api/chainboard/settlements/SHP-FOO-M1/actions/escalate", json=payload)
    client.post("/api/chainboard/settlements/SHP-FOO-M2/actions/mark-reviewed", json=payload)
    client.post("/api/chainboard/settlements/SHP-FOO-M3/actions/request-docs", json=payload)

    response = client.get("/api/chainboard/settlements/actions/recent?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Should be ordered by created_at desc, so last action first
    assert data[0]["milestone_id"] == "SHP-FOO-M3"
    assert data[0]["action"] == "request_documentation"
    assert data[1]["milestone_id"] == "SHP-FOO-M2"
    assert data[1]["action"] == "mark_manually_reviewed"


def test_recent_actions_limit_clamped():
    """Ensure limit is clamped to 100."""
    payload = {"requested_by": "audit@chainbridge.com"}
    for i in range(150):
        client.post(
            f"/api/chainboard/settlements/SHP-CLAMP-M{i}/actions/escalate",
            json=payload,
        )

    response = client.get("/api/chainboard/settlements/actions/recent?limit=500")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 100
