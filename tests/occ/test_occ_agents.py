# ═══════════════════════════════════════════════════════════════════════════════
# OCC Agents API Tests — PAC-BENSON-P22-C
#
# Tests for agent drilldown endpoints.
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
# GET /occ/agents/{agent_id}/drilldown - Full Agent Drilldown
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetAgentDrilldown:
    """Test agent drilldown retrieval."""

    def test_get_drilldown_success(self):
        """GET /occ/agents/{agent_id}/drilldown returns drilldown data."""
        response = client.get("/occ/agents/GID-00/drilldown")
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == "GID-00"
        assert data["agent_name"] == "BENSON"
        assert "executions" in data
        assert "failures" in data
        assert "evidence" in data
        assert "metrics" in data

    def test_drilldown_unknown_agent(self):
        """GET returns 404 for unknown agent."""
        response = client.get("/occ/agents/GID-999/drilldown")
        assert response.status_code == 404

    def test_drilldown_all_known_agents(self):
        """Drilldown works for all known agents."""
        known_agents = ["GID-00", "GID-01", "GID-02", "GID-03", "GID-04", "GID-05", "GID-06", "GID-07", "GID-11"]
        for agent_id in known_agents:
            response = client.get(f"/occ/agents/{agent_id}/drilldown")
            assert response.status_code == 200, f"Failed for {agent_id}"


# ═══════════════════════════════════════════════════════════════════════════════
# GET /occ/agents/{agent_id}/history - Execution History
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetAgentHistory:
    """Test agent history retrieval."""

    def test_get_history_success(self):
        """GET /occ/agents/{agent_id}/history returns history."""
        response = client.get("/occ/agents/GID-02/history")
        assert response.status_code == 200
        data = response.json()
        
        assert "executions" in data
        assert "total" in data
        assert "has_more" in data

    def test_history_pagination(self):
        """History supports pagination."""
        response = client.get("/occ/agents/GID-02/history?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["executions"], list)

    def test_history_filter_by_pac(self):
        """History can be filtered by PAC ID."""
        response = client.get("/occ/agents/GID-02/history?pac_id=PAC-BENSON-P22-C")
        assert response.status_code == 200

    def test_history_filter_by_status(self):
        """History can be filtered by status."""
        response = client.get("/occ/agents/GID-02/history?status=completed")
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# GET /occ/agents/{agent_id}/failures - Failure Records
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetAgentFailures:
    """Test agent failures retrieval."""

    def test_get_failures_success(self):
        """GET /occ/agents/{agent_id}/failures returns failures."""
        response = client.get("/occ/agents/GID-01/failures")
        assert response.status_code == 200
        data = response.json()
        
        assert "failures" in data
        assert "total" in data
        assert "unresolved_count" in data

    def test_failures_filter_by_severity(self):
        """Failures can be filtered by severity."""
        response = client.get("/occ/agents/GID-01/failures?severity=critical")
        assert response.status_code == 200

    def test_failures_filter_by_resolved(self):
        """Failures can be filtered by resolved status."""
        response = client.get("/occ/agents/GID-01/failures?resolved=false")
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# GET /occ/agents/{agent_id}/evidence - Evidence Artifacts
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetAgentEvidence:
    """Test agent evidence retrieval."""

    def test_get_evidence_success(self):
        """GET /occ/agents/{agent_id}/evidence returns evidence."""
        response = client.get("/occ/agents/GID-02/evidence")
        assert response.status_code == 200
        data = response.json()
        
        assert "artifacts" in data
        assert "total" in data
        assert "total_size_bytes" in data

    def test_evidence_has_content_hash(self):
        """Evidence artifacts have content hashes (INV-OCC-005)."""
        response = client.get("/occ/agents/GID-02/evidence")
        assert response.status_code == 200
        data = response.json()
        
        for artifact in data["artifacts"]:
            assert "content_hash" in artifact

    def test_evidence_filter_by_type(self):
        """Evidence can be filtered by type."""
        response = client.get("/occ/agents/GID-02/evidence?artifact_type=evidence")
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# GET /occ/agents/{agent_id}/metrics - Performance Metrics
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetAgentMetrics:
    """Test agent metrics retrieval."""

    def test_get_metrics_success(self):
        """GET /occ/agents/{agent_id}/metrics returns metrics."""
        response = client.get("/occ/agents/GID-00/metrics")
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == "GID-00"
        assert "total_executions" in data
        assert "success_rate" in data
        assert "avg_duration_ms" in data


# ═══════════════════════════════════════════════════════════════════════════════
# READ-ONLY VERIFICATION (INV-OCC-005)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentsReadOnly:
    """Verify agent endpoints are read-only."""

    def test_post_rejected(self):
        """POST mutations are rejected."""
        response = client.post("/occ/agents/GID-00", json={})
        assert response.status_code == 405
        assert "READ-ONLY" in response.json()["detail"]

    def test_put_rejected(self):
        """PUT mutations are rejected."""
        response = client.put("/occ/agents/GID-00", json={})
        assert response.status_code == 405

    def test_patch_rejected(self):
        """PATCH mutations are rejected."""
        response = client.patch("/occ/agents/GID-00", json={})
        assert response.status_code == 405

    def test_delete_rejected(self):
        """DELETE mutations are rejected."""
        response = client.delete("/occ/agents/GID-00")
        assert response.status_code == 405

    def test_inv_occ_005_in_rejection(self):
        """Mutation rejections cite INV-OCC-005."""
        response = client.post("/occ/agents/GID-00", json={})
        assert "INV-OCC-005" in response.json()["detail"]
