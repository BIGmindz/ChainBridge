"""
Tests for ChainBoard API - Projection Layer over OCC.

Validates that ChainBoard endpoints correctly project OCC artifacts
and audit events for the dashboard UI.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from core.occ.schemas.artifact import ArtifactCreate, ArtifactStatus, ArtifactType, ArtifactUpdate


@pytest.fixture(autouse=True)
def reset_store_singleton(monkeypatch):
    """Reset the singleton store before each test."""
    fd, path = tempfile.mkstemp(suffix=".json", prefix="test_chainboard_")
    os.close(fd)
    os.unlink(path)

    monkeypatch.setenv("CHAINBRIDGE_ARTIFACT_STORE_PATH", path)

    import core.occ.store.artifact_store as store_module

    store_module._store_instance = None

    yield path

    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def client():
    """Create a test client for the API."""
    from api.server import app

    with TestClient(app) as c:
        yield c


# =============================================================================
# GET /api/chainboard/alerts Tests
# =============================================================================


class TestAlertsEndpoint:
    """Tests for the alerts projection endpoint."""

    def test_alerts_returns_200(self, client):
        """Alerts endpoint returns 200 OK."""
        response = client.get("/api/chainboard/alerts")
        assert response.status_code == 200

    def test_alerts_returns_expected_keys(self, client):
        """Alerts response contains required keys."""
        response = client.get("/api/chainboard/alerts")
        data = response.json()

        assert "items" in data
        assert "count" in data
        assert "total" in data
        assert "status" in data
        assert "limit" in data

    def test_alerts_empty_when_no_artifacts(self, client):
        """Alerts returns empty when no OCC artifacts exist."""
        response = client.get("/api/chainboard/alerts")
        data = response.json()

        assert data["items"] == []
        assert data["count"] == 0
        assert data["total"] == 0

    def test_alerts_default_params(self, client):
        """Alerts uses default params when not specified."""
        response = client.get("/api/chainboard/alerts")
        data = response.json()

        assert data["status"] == "open"
        assert data["limit"] == 50

    def test_alerts_projects_decision_artifact(self, client):
        """Decision artifacts appear as alerts."""
        # Create a Decision artifact via OCC API
        client.post(
            "/occ/artifacts",
            json={
                "name": "Urgent Decision Required",
                "artifact_type": "Decision",
                "description": "Needs review",
                "status": "Draft",
            },
        )

        response = client.get("/api/chainboard/alerts?status=open")
        data = response.json()

        assert data["count"] == 1
        assert data["items"][0]["title"] == "Urgent Decision Required"
        assert data["items"][0]["status"] == "open"
        assert data["items"][0]["severity"] == "medium"

    def test_alerts_projects_compliance_record(self, client):
        """ComplianceRecord artifacts appear as high-severity alerts."""
        client.post(
            "/occ/artifacts",
            json={
                "name": "Compliance Violation",
                "artifact_type": "ComplianceRecord",
                "status": "Pending",
            },
        )

        response = client.get("/api/chainboard/alerts?status=open")
        data = response.json()

        assert data["count"] == 1
        assert data["items"][0]["severity"] == "high"

    def test_alerts_filters_by_status_open(self, client):
        """Status=open returns Draft and Pending artifacts."""
        # Create Draft artifact
        client.post(
            "/occ/artifacts",
            json={"name": "Draft Alert", "artifact_type": "Decision", "status": "Draft"},
        )
        # Create Approved artifact (should not appear in open)
        resp = client.post(
            "/occ/artifacts",
            json={"name": "Approved Alert", "artifact_type": "Decision"},
        )
        artifact_id = resp.json()["id"]
        client.patch(f"/occ/artifacts/{artifact_id}", json={"status": "Approved"})

        response = client.get("/api/chainboard/alerts?status=open")
        data = response.json()

        assert data["count"] == 1
        assert data["items"][0]["title"] == "Draft Alert"

    def test_alerts_filters_by_status_blocked(self, client):
        """Status=blocked returns Rejected artifacts."""
        resp = client.post(
            "/occ/artifacts",
            json={"name": "Blocked Alert", "artifact_type": "Decision"},
        )
        artifact_id = resp.json()["id"]
        client.patch(f"/occ/artifacts/{artifact_id}", json={"status": "Rejected"})

        response = client.get("/api/chainboard/alerts?status=blocked")
        data = response.json()

        assert data["count"] == 1
        assert data["items"][0]["status"] == "blocked"

    def test_alerts_filters_by_status_resolved(self, client):
        """Status=resolved returns Approved and Locked artifacts."""
        resp = client.post(
            "/occ/artifacts",
            json={"name": "Resolved Alert", "artifact_type": "ComplianceRecord"},
        )
        artifact_id = resp.json()["id"]
        client.patch(f"/occ/artifacts/{artifact_id}", json={"status": "Approved"})

        response = client.get("/api/chainboard/alerts?status=resolved")
        data = response.json()

        assert data["count"] == 1
        assert data["items"][0]["status"] == "resolved"

    def test_alerts_status_all_returns_everything(self, client):
        """Status=all returns all alert-eligible artifacts."""
        client.post(
            "/occ/artifacts",
            json={"name": "Alert 1", "artifact_type": "Decision"},
        )
        resp = client.post(
            "/occ/artifacts",
            json={"name": "Alert 2", "artifact_type": "ComplianceRecord"},
        )
        artifact_id = resp.json()["id"]
        client.patch(f"/occ/artifacts/{artifact_id}", json={"status": "Approved"})

        response = client.get("/api/chainboard/alerts?status=all")
        data = response.json()

        assert data["count"] == 2

    def test_alerts_excludes_non_alert_types(self, client):
        """Plan and Report artifacts do not appear as alerts."""
        client.post(
            "/occ/artifacts",
            json={"name": "My Plan", "artifact_type": "Plan"},
        )
        client.post(
            "/occ/artifacts",
            json={"name": "My Report", "artifact_type": "Report"},
        )

        response = client.get("/api/chainboard/alerts?status=all")
        data = response.json()

        assert data["count"] == 0

    def test_alerts_respects_limit(self, client):
        """Alerts respects limit parameter."""
        for i in range(5):
            client.post(
                "/occ/artifacts",
                json={"name": f"Alert {i}", "artifact_type": "Decision"},
            )

        response = client.get("/api/chainboard/alerts?status=open&limit=3")
        data = response.json()

        assert data["count"] == 3
        assert data["total"] == 5

    def test_alerts_limit_bounds(self, client):
        """Alerts validates limit bounds (1-500)."""
        response = client.get("/api/chainboard/alerts?limit=0")
        assert response.status_code == 422

        response = client.get("/api/chainboard/alerts?limit=501")
        assert response.status_code == 422


# =============================================================================
# GET /api/chainboard/events/stream Tests
# =============================================================================


class TestEventsStreamEndpoint:
    """Tests for the SSE events stream endpoint."""

    def test_events_stream_returns_200(self, client):
        """Events stream endpoint returns 200 OK."""
        with client.stream("GET", "/api/chainboard/events/stream?max_events=1") as response:
            assert response.status_code == 200

    def test_events_stream_content_type(self, client):
        """Events stream returns text/event-stream content type."""
        with client.stream("GET", "/api/chainboard/events/stream?max_events=1") as response:
            content_type = response.headers.get("content-type", "")
            assert "text/event-stream" in content_type

    def test_events_stream_cache_control(self, client):
        """Events stream sets no-cache header."""
        with client.stream("GET", "/api/chainboard/events/stream?max_events=1") as response:
            cache_control = response.headers.get("cache-control", "")
            assert "no-cache" in cache_control

    def test_events_stream_sends_connected_event(self, client):
        """Events stream sends initial connected event."""
        with client.stream("GET", "/api/chainboard/events/stream?max_events=1") as response:
            first_chunk = next(response.iter_lines())
            assert "connected" in first_chunk


# =============================================================================
# Integration Tests - No 404s
# =============================================================================


class TestEndpointsExist:
    """Verify endpoints are reachable (no 404s)."""

    def test_alerts_not_404(self, client):
        """Alerts endpoint must not return 404."""
        response = client.get("/api/chainboard/alerts?status=open&limit=50")
        assert response.status_code != 404

    def test_events_stream_not_404(self, client):
        """Events stream endpoint must not return 404."""
        with client.stream("GET", "/api/chainboard/events/stream?max_events=1") as response:
            assert response.status_code != 404
