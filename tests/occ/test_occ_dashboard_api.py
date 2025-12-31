# ═══════════════════════════════════════════════════════════════════════════════
# OCC Dashboard API Tests
# PAC-BENSON-P21-C: OCC Intensive Multi-Agent Execution
#
# Tests for OCC Dashboard read-only endpoints:
# - /occ/dashboard/agents
# - /occ/dashboard/decisions
# - /occ/dashboard/governance
# - /occ/dashboard/kill-switch
# - /occ/dashboard/state
#
# INVARIANTS TESTED:
# - INV-OCC-001: No mutation routes - read-only state display
# - INV-OCC-002: Always reflects backend state
# - INV-OCC-003: UI reflects invariant failures with rule IDs
#
# Author: DAN (GID-07) — CI/Testing
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from fastapi.testclient import TestClient

from api.server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestOCCDashboardAgents:
    """Tests for /occ/dashboard/agents endpoint."""

    def test_get_agents_returns_list(self, client):
        """GET /occ/dashboard/agents returns agent tiles list."""
        response = client.get("/occ/dashboard/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "total" in data
        assert "timestamp" in data
        assert isinstance(data["agents"], list)
        assert data["total"] == len(data["agents"])

    def test_get_agents_contains_required_fields(self, client):
        """Each agent tile has required fields."""
        response = client.get("/occ/dashboard/agents")
        assert response.status_code == 200
        data = response.json()

        if data["agents"]:
            agent = data["agents"][0]
            required_fields = [
                "agent_id",
                "agent_name",
                "lane",
                "health",
                "execution_state",
                "tasks_completed",
                "tasks_pending",
                "last_heartbeat",
            ]
            for field in required_fields:
                assert field in agent, f"Missing field: {field}"

    def test_get_agents_filter_by_lane(self, client):
        """Filter agents by lane."""
        response = client.get("/occ/dashboard/agents", params={"lane": "frontend"})
        assert response.status_code == 200
        data = response.json()
        for agent in data["agents"]:
            assert agent["lane"] == "frontend"

    def test_get_agents_filter_by_health(self, client):
        """Filter agents by health state."""
        response = client.get("/occ/dashboard/agents", params={"health": "healthy"})
        assert response.status_code == 200
        data = response.json()
        for agent in data["agents"]:
            assert agent["health"] == "healthy"

    def test_get_agents_filter_by_execution_state(self, client):
        """Filter agents by execution state."""
        response = client.get("/occ/dashboard/agents", params={"execution_state": "idle"})
        assert response.status_code == 200
        data = response.json()
        for agent in data["agents"]:
            assert agent["execution_state"] == "idle"


class TestOCCDashboardDecisions:
    """Tests for /occ/dashboard/decisions endpoint."""

    def test_get_decisions_returns_stream(self, client):
        """GET /occ/dashboard/decisions returns decision stream."""
        response = client.get("/occ/dashboard/decisions")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "has_more" in data
        assert "timestamp" in data
        assert isinstance(data["items"], list)

    def test_get_decisions_with_pagination(self, client):
        """Pagination parameters work correctly."""
        response = client.get("/occ/dashboard/decisions", params={"limit": 10, "offset": 0})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 10

    def test_get_decisions_filter_by_pac_id(self, client):
        """Filter decisions by PAC ID."""
        response = client.get("/occ/dashboard/decisions", params={"pac_id": "PAC-BENSON-P21-C"})
        assert response.status_code == 200
        data = response.json()
        # All returned items should be for the specified PAC
        for item in data["items"]:
            if item["pdo_card"]:
                assert item["pdo_card"]["pac_id"] == "PAC-BENSON-P21-C"
            elif item["ber_card"]:
                assert item["ber_card"]["pac_id"] == "PAC-BENSON-P21-C"

    def test_get_decisions_filter_by_item_type(self, client):
        """Filter decisions by item type."""
        response = client.get("/occ/dashboard/decisions", params={"item_type": "pdo"})
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["item_type"] == "pdo"


class TestOCCDashboardGovernance:
    """Tests for /occ/dashboard/governance endpoint."""

    def test_get_governance_returns_state(self, client):
        """GET /occ/dashboard/governance returns governance state."""
        response = client.get("/occ/dashboard/governance")
        assert response.status_code == 200
        data = response.json()
        assert "invariants" in data
        assert "lint_v2_passing" in data
        assert "schema_registry_valid" in data
        assert "fail_closed_active" in data
        assert "last_refresh" in data

    def test_get_governance_invariants_have_rule_ids(self, client):
        """Each invariant has a rule ID (INV-OCC-003)."""
        response = client.get("/occ/dashboard/governance")
        assert response.status_code == 200
        data = response.json()

        for invariant in data["invariants"]:
            assert "invariant_id" in invariant
            assert "rule_id" in invariant
            assert invariant["rule_id"].startswith("RULE-")

    def test_get_governance_filter_by_class(self, client):
        """Filter invariants by class."""
        response = client.get("/occ/dashboard/governance", params={"invariant_class": "S-INV"})
        assert response.status_code == 200
        data = response.json()
        for invariant in data["invariants"]:
            assert invariant["class"] == "S-INV"

    def test_get_governance_filter_by_status(self, client):
        """Filter invariants by status."""
        response = client.get("/occ/dashboard/governance", params={"status": "passing"})
        assert response.status_code == 200
        data = response.json()
        for invariant in data["invariants"]:
            assert invariant["status"] == "passing"


class TestOCCDashboardKillSwitch:
    """Tests for /occ/dashboard/kill-switch endpoint."""

    def test_get_kill_switch_returns_status(self, client):
        """GET /occ/dashboard/kill-switch returns kill switch status."""
        response = client.get("/occ/dashboard/kill-switch")
        assert response.status_code == 200
        data = response.json()
        assert "state" in data
        assert "auth_level" in data
        assert data["state"] in ["DISARMED", "ARMED", "ENGAGED", "COOLDOWN"]
        assert data["auth_level"] in ["UNAUTHORIZED", "ARM_ONLY", "FULL_ACCESS"]


class TestOCCDashboardState:
    """Tests for /occ/dashboard/state endpoint."""

    def test_get_state_returns_aggregate(self, client):
        """GET /occ/dashboard/state returns full aggregate state."""
        response = client.get("/occ/dashboard/state")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "decision_stream" in data
        assert "governance_rail" in data
        assert "kill_switch" in data
        assert "timestamp" in data

    def test_get_state_has_active_pac(self, client):
        """Aggregate state includes active PAC detection."""
        response = client.get("/occ/dashboard/state")
        assert response.status_code == 200
        data = response.json()
        # active_pac_id may be None or a string
        assert "active_pac_id" in data


class TestOCCDashboardReadOnly:
    """Tests for read-only invariant (INV-OCC-001)."""

    def test_post_agents_returns_405(self, client):
        """POST /occ/dashboard/agents returns 405."""
        response = client.post("/occ/dashboard/agents", json={})
        assert response.status_code == 405

    def test_put_agents_returns_405(self, client):
        """PUT /occ/dashboard/agents returns 405."""
        response = client.put("/occ/dashboard/agents", json={})
        assert response.status_code == 405

    def test_patch_agents_returns_405(self, client):
        """PATCH /occ/dashboard/agents returns 405."""
        response = client.patch("/occ/dashboard/agents", json={})
        assert response.status_code == 405

    def test_delete_agents_returns_405(self, client):
        """DELETE /occ/dashboard/agents returns 405."""
        response = client.delete("/occ/dashboard/agents")
        assert response.status_code == 405

    def test_post_decisions_returns_405(self, client):
        """POST /occ/dashboard/decisions returns 405."""
        response = client.post("/occ/dashboard/decisions", json={})
        assert response.status_code == 405

    def test_post_governance_returns_405(self, client):
        """POST /occ/dashboard/governance returns 405."""
        response = client.post("/occ/dashboard/governance", json={})
        assert response.status_code == 405

    def test_post_kill_switch_returns_405(self, client):
        """POST /occ/dashboard/kill-switch returns 405."""
        response = client.post("/occ/dashboard/kill-switch", json={})
        assert response.status_code == 405

    def test_mutation_error_message_explains_governance(self, client):
        """Mutation error messages explain governance requirement."""
        response = client.post("/occ/dashboard/agents", json={})
        assert response.status_code == 405
        data = response.json()
        assert "READ-ONLY" in data["detail"]
