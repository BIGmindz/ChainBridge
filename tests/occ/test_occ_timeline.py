# ═══════════════════════════════════════════════════════════════════════════════
# OCC Timeline API Tests — PAC-BENSON-P22-C
#
# Tests for timeline visualization endpoints.
# READ-ONLY verification and invariant compliance.
#
# Authors:
# - CODY (GID-01) — Backend Lead
# - DAN (GID-07) — CI/Testing Lead
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /occ/timeline/{pac_id} - Full PAC Timeline
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetPACTimeline:
    """Test PAC timeline retrieval."""

    def test_get_pac_timeline_success(self):
        """GET /occ/timeline/{pac_id} returns timeline data."""
        response = client.get("/occ/timeline/PAC-BENSON-P22-C")
        assert response.status_code == 200
        data = response.json()
        
        assert data["pac_id"] == "PAC-BENSON-P22-C"
        assert "lifecycle_state" in data
        assert "events" in data
        assert "agent_acks" in data
        assert "wrap_milestones" in data
        assert "ber_records" in data

    def test_timeline_has_evidence_hashes(self):
        """Timeline events must have evidence hashes (INV-OCC-005)."""
        response = client.get("/occ/timeline/PAC-TEST-001")
        assert response.status_code == 200
        data = response.json()
        
        # Verify events have evidence hashes where applicable
        for event in data["events"]:
            # Evidence hashes should be present (may be None for some events)
            assert "evidence_hash" in event

    def test_timeline_shows_all_transitions(self):
        """Timeline shows all state transitions (INV-OCC-006)."""
        response = client.get("/occ/timeline/PAC-TEST-001")
        assert response.status_code == 200
        data = response.json()
        
        # Verify lifecycle state is visible
        assert data["lifecycle_state"] in [
            "ADMISSION",
            "RUNTIME_ACTIVATION",
            "AGENT_ACTIVATION",
            "EXECUTING",
            "WRAP_COLLECTION",
            "REVIEW_GATE",
            "BER_ISSUED",
            "SETTLED",
            "FAILED",
            "CANCELLED",
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# GET /occ/timeline/{pac_id}/events - Paginated Events
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetTimelineEvents:
    """Test timeline events retrieval."""

    def test_get_events_success(self):
        """GET /occ/timeline/{pac_id}/events returns events."""
        response = client.get("/occ/timeline/PAC-TEST-001/events")
        assert response.status_code == 200
        data = response.json()
        
        assert "events" in data
        assert "total" in data
        assert "has_more" in data

    def test_events_pagination(self):
        """Events support pagination parameters."""
        response = client.get("/occ/timeline/PAC-TEST-001/events?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["events"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["has_more"], bool)

    def test_events_filter_by_category(self):
        """Events can be filtered by category."""
        response = client.get("/occ/timeline/PAC-TEST-001/events?category=agent_activation")
        assert response.status_code == 200
        data = response.json()
        
        for event in data["events"]:
            assert event["category"] == "agent_activation"

    def test_events_filter_by_agent(self):
        """Events can be filtered by agent."""
        response = client.get("/occ/timeline/PAC-TEST-001/events?agent_id=GID-00")
        assert response.status_code == 200
        # Should succeed even if filtered results are empty


# ═══════════════════════════════════════════════════════════════════════════════
# GET /occ/timeline/{pac_id}/wraps - WRAP Milestones
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetWRAPMilestones:
    """Test WRAP milestones retrieval."""

    def test_get_wraps_success(self):
        """GET /occ/timeline/{pac_id}/wraps returns WRAP milestones."""
        response = client.get("/occ/timeline/PAC-TEST-001/wraps")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /occ/timeline/{pac_id}/ber - BER Records
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetBERRecords:
    """Test BER records retrieval."""

    def test_get_ber_records_success(self):
        """GET /occ/timeline/{pac_id}/ber returns BER records."""
        response = client.get("/occ/timeline/PAC-TEST-001/ber")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)


# ═══════════════════════════════════════════════════════════════════════════════
# READ-ONLY VERIFICATION (INV-OCC-005)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTimelineReadOnly:
    """Verify timeline endpoints are read-only."""

    def test_post_rejected(self):
        """POST mutations are rejected."""
        response = client.post("/occ/timeline/PAC-TEST-001", json={})
        assert response.status_code == 405
        assert "READ-ONLY" in response.json()["detail"]

    def test_put_rejected(self):
        """PUT mutations are rejected."""
        response = client.put("/occ/timeline/PAC-TEST-001", json={})
        assert response.status_code == 405
        assert "READ-ONLY" in response.json()["detail"]

    def test_patch_rejected(self):
        """PATCH mutations are rejected."""
        response = client.patch("/occ/timeline/PAC-TEST-001", json={})
        assert response.status_code == 405
        assert "READ-ONLY" in response.json()["detail"]

    def test_delete_rejected(self):
        """DELETE mutations are rejected."""
        response = client.delete("/occ/timeline/PAC-TEST-001")
        assert response.status_code == 405
        assert "READ-ONLY" in response.json()["detail"]

    def test_inv_occ_005_in_rejection(self):
        """Mutation rejections cite INV-OCC-005."""
        response = client.post("/occ/timeline/PAC-TEST-001", json={})
        assert "INV-OCC-005" in response.json()["detail"]
