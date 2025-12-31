# ═══════════════════════════════════════════════════════════════════════════════
# Read-Only Enforcement Tests — PAC-BENSON-P23-C
#
# Tests for API read-only enforcement middleware.
# Validates mutation blocking on protected paths.
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
# OCC TIMELINE READ-ONLY ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestOCCTimelineReadOnly:
    """Test read-only enforcement on OCC timeline endpoints."""

    def test_get_allowed(self):
        """GET requests are allowed."""
        response = client.get("/occ/timeline/PAC-TEST-001")
        assert response.status_code == 200

    def test_post_blocked(self):
        """POST requests are blocked."""
        response = client.post("/occ/timeline/PAC-TEST-001", json={})
        assert response.status_code == 405
        assert "READ-ONLY" in response.json()["detail"]

    def test_put_blocked(self):
        """PUT requests are blocked."""
        response = client.put("/occ/timeline/PAC-TEST-001", json={})
        assert response.status_code == 405

    def test_patch_blocked(self):
        """PATCH requests are blocked."""
        response = client.patch("/occ/timeline/PAC-TEST-001", json={})
        assert response.status_code == 405

    def test_delete_blocked(self):
        """DELETE requests are blocked."""
        response = client.delete("/occ/timeline/PAC-TEST-001")
        assert response.status_code == 405

    def test_invariant_cited_in_error(self):
        """Error message cites INV-OCC-005."""
        response = client.post("/occ/timeline/PAC-TEST-001", json={})
        assert "INV-OCC-005" in response.json()["detail"]


# ═══════════════════════════════════════════════════════════════════════════════
# OCC AGENTS READ-ONLY ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestOCCAgentsReadOnly:
    """Test read-only enforcement on OCC agents endpoints."""

    def test_get_drilldown_allowed(self):
        """GET drilldown is allowed."""
        response = client.get("/occ/agents/GID-00/drilldown")
        assert response.status_code == 200

    def test_get_history_allowed(self):
        """GET history is allowed."""
        response = client.get("/occ/agents/GID-00/history")
        assert response.status_code == 200

    def test_post_blocked(self):
        """POST requests are blocked."""
        response = client.post("/occ/agents/GID-00", json={})
        assert response.status_code == 405

    def test_put_blocked(self):
        """PUT requests are blocked."""
        response = client.put("/occ/agents/GID-00", json={})
        assert response.status_code == 405


# ═══════════════════════════════════════════════════════════════════════════════
# OCC DIFF READ-ONLY ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestOCCDiffReadOnly:
    """Test read-only enforcement on OCC diff endpoints."""

    def test_get_diff_allowed(self):
        """GET diff is allowed."""
        response = client.get("/occ/diff/item-001/item-002")
        assert response.status_code == 200

    def test_get_ber_diff_allowed(self):
        """GET BER diff is allowed."""
        response = client.get("/occ/diff/ber/BER-001/BER-002")
        assert response.status_code == 200

    def test_get_pdo_diff_allowed(self):
        """GET PDO diff is allowed."""
        response = client.get("/occ/diff/pdo/PDO-001/PDO-002")
        assert response.status_code == 200

    def test_post_blocked(self):
        """POST requests are blocked."""
        response = client.post("/occ/diff/item-001/item-002", json={})
        assert response.status_code == 405


# ═══════════════════════════════════════════════════════════════════════════════
# OCC DASHBOARD READ-ONLY ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestOCCDashboardReadOnly:
    """Test read-only enforcement on OCC dashboard endpoints."""

    def test_get_state_allowed(self):
        """GET dashboard state is allowed."""
        response = client.get("/occ/dashboard/state")
        assert response.status_code == 200

    def test_get_agents_allowed(self):
        """GET agents dashboard is allowed."""
        response = client.get("/occ/dashboard/agents")
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE HASH PRESENCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvidenceHashPresence:
    """Test evidence hash presence in responses."""

    def test_timeline_has_evidence_hashes(self):
        """Timeline responses include evidence hashes."""
        response = client.get("/occ/timeline/PAC-TEST-001")
        data = response.json()
        
        # Check events have evidence_hash field
        for event in data.get("events", []):
            assert "evidence_hash" in event

    def test_agents_evidence_has_content_hash(self):
        """Agent evidence artifacts have content hashes."""
        response = client.get("/occ/agents/GID-02/evidence")
        data = response.json()
        
        for artifact in data.get("artifacts", []):
            assert "content_hash" in artifact

    def test_diff_has_evidence_hashes(self):
        """Diff responses include evidence hashes."""
        response = client.get("/occ/diff/item-001/item-002")
        data = response.json()
        
        assert "left_evidence_hash" in data
        assert "right_evidence_hash" in data
