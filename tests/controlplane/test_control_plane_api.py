# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Control Plane API Tests
# PAC-JEFFREY-P01: Benson Execution Control Plane UI — Multi-Agent Build
# CORRECTIVE REISSUANCE · GOLD STANDARD
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for Control Plane OC API endpoints.

Validates:
- GET-only enforcement (405 on mutations)
- Correct response schemas
- FAIL_CLOSED governance
- Multi-agent WRAP aggregation (PAC-JEFFREY-P01 Section 7)
- RG-01 Review Gate (PAC-JEFFREY-P01 Section 8)
- BSRG-01 Self-Review Gate (PAC-JEFFREY-P01 Section 9)
- ACK latency settlement binding (PAC-JEFFREY-P01 Section 6)
- Ledger commit attestation (PAC-JEFFREY-P01 Section 11)

Author: Benson Execution Orchestrator (GID-00)
Backend Lane: CODY (GID-01)
"""

import pytest
from fastapi.testclient import TestClient

from api.server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: READ-ONLY ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadOnlyEnforcement:
    """Test that Control Plane OC is read-only."""

    def test_post_rejected_with_405(self, client):
        """POST requests must return 405."""
        response = client.post("/oc/controlplane/state/PAC-TEST", json={})
        assert response.status_code == 405

    def test_put_rejected_with_405(self, client):
        """PUT requests must return 405."""
        response = client.put("/oc/controlplane/state/PAC-TEST", json={})
        assert response.status_code == 405

    def test_delete_rejected_with_405(self, client):
        """DELETE requests must return 405."""
        response = client.delete("/oc/controlplane/state/PAC-TEST")
        assert response.status_code == 405

    def test_patch_rejected_with_405(self, client):
        """PATCH requests must return 405."""
        response = client.patch("/oc/controlplane/state/PAC-TEST", json={})
        assert response.status_code == 405


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: STATE ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

class TestStateEndpoint:
    """Test Control Plane state endpoint."""

    def test_get_state_returns_demo_state(self, client):
        """GET /oc/controlplane/state/{pac_id} returns demo state."""
        response = client.get("/oc/controlplane/state/PAC-CP-UI-EXEC-001")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pac_id"] == "PAC-CP-UI-EXEC-001"
        assert data["runtime_id"] == "PAC-CP-UI-EXEC-001"
        assert "lifecycle_state" in data
        assert "agent_acks" in data
        assert "ack_summary" in data

    def test_get_state_not_found(self, client):
        """GET for unknown PAC returns 404."""
        response = client.get("/oc/controlplane/state/UNKNOWN-PAC")
        assert response.status_code == 404

    def test_state_includes_ack_summary(self, client):
        """State response must include ACK summary."""
        response = client.get("/oc/controlplane/state/PAC-CP-UI-EXEC-001")
        data = response.json()
        
        summary = data["ack_summary"]
        assert "total" in summary
        assert "acknowledged" in summary
        assert "pending" in summary
        assert "rejected" in summary
        assert "timeout" in summary
        assert "latency" in summary


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: LIST ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

class TestListEndpoint:
    """Test Control Plane list endpoint."""

    def test_list_returns_items(self, client):
        """GET /oc/controlplane/list returns list of states."""
        response = client.get("/oc/controlplane/list")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_list_pagination(self, client):
        """List endpoint respects pagination parameters."""
        response = client.get("/oc/controlplane/list?limit=5&offset=0")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) <= 5


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ACK ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

class TestACKEndpoint:
    """Test ACK visibility endpoints."""

    def test_get_acks_returns_list(self, client):
        """GET /oc/controlplane/state/{pac_id}/acks returns ACK list."""
        response = client.get("/oc/controlplane/state/PAC-CP-UI-EXEC-001/acks")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pac_id"] == "PAC-CP-UI-EXEC-001"
        assert "acks" in data
        assert "summary" in data

    def test_get_ack_by_agent(self, client):
        """GET /oc/controlplane/state/{pac_id}/acks/{agent_gid} returns single ACK."""
        response = client.get("/oc/controlplane/state/PAC-CP-UI-EXEC-001/acks/GID-00")
        assert response.status_code == 200
        
        data = response.json()
        assert data["agent_gid"] == "GID-00"
        assert "state" in data
        assert "ack_hash" in data

    def test_get_ack_not_found(self, client):
        """GET for unknown agent returns 404."""
        response = client.get("/oc/controlplane/state/PAC-CP-UI-EXEC-001/acks/GID-UNKNOWN")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SETTLEMENT ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

class TestSettlementEndpoint:
    """Test settlement eligibility endpoint."""

    def test_get_settlement_eligibility(self, client):
        """GET /oc/controlplane/state/{pac_id}/settlement returns eligibility."""
        response = client.get("/oc/controlplane/state/PAC-CP-UI-EXEC-001/settlement")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pac_id"] == "PAC-CP-UI-EXEC-001"
        assert "eligibility" in data
        assert "is_eligible" in data
        assert "blocking_reasons" in data


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: AUDIT ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditEndpoint:
    """Test audit trail endpoint."""

    def test_get_audit_trail(self, client):
        """GET /oc/controlplane/state/{pac_id}/audit returns audit trail."""
        response = client.get("/oc/controlplane/state/PAC-CP-UI-EXEC-001/audit")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pac_id"] == "PAC-CP-UI-EXEC-001"
        assert "transitions" in data
        assert "total_transitions" in data
        assert "current_state" in data


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: HEALTH ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_returns_ok(self, client):
        """GET /oc/controlplane/health returns healthy status."""
        response = client.get("/oc/controlplane/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "control-plane-oc"
        assert data["governance"] == "FAIL_CLOSED"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: MULTI-AGENT WRAP AGGREGATION (PAC-JEFFREY-P01 SECTION 7)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiAgentWRAPEndpoint:
    """Test multi-agent WRAP aggregation endpoint."""

    def test_get_wraps_returns_aggregation_status(self, client):
        """GET /oc/controlplane/state/{pac_id}/wraps returns WRAP set status."""
        response = client.get("/oc/controlplane/state/PAC-JEFFREY-P01/wraps")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pac_id"] == "PAC-JEFFREY-P01"
        assert "expected_agents" in data
        assert "is_complete" in data
        assert "missing_agents" in data
        assert "collected_wraps" in data
        assert "set_hash" in data
        assert data["schema_version"] == "CHAINBRIDGE_CANONICAL_WRAP_SCHEMA v1.0.0"

    def test_wraps_includes_governance_invariant(self, client):
        """WRAP response must include governance invariant."""
        response = client.get("/oc/controlplane/state/PAC-JEFFREY-P01/wraps")
        data = response.json()
        
        assert "governance_invariant" in data
        assert "INV-CP-006" in data["governance_invariant"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: RG-01 REVIEW GATE (PAC-JEFFREY-P01 SECTION 8)
# ═══════════════════════════════════════════════════════════════════════════════

class TestReviewGateRG01Endpoint:
    """Test RG-01 Review Gate endpoint."""

    def test_get_review_gate_status(self, client):
        """GET /oc/controlplane/state/{pac_id}/review-gate returns RG-01 status."""
        response = client.get("/oc/controlplane/state/PAC-JEFFREY-P01/review-gate")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pac_id"] == "PAC-JEFFREY-P01"
        assert data["gate_type"] == "RG-01"
        assert data["reviewer"] == "BENSON"
        assert "pass_conditions" in data
        assert data["fail_action"] == "emit corrective PAC"

    def test_review_gate_includes_pass_conditions(self, client):
        """RG-01 response must include pass conditions."""
        response = client.get("/oc/controlplane/state/PAC-JEFFREY-P01/review-gate")
        data = response.json()
        
        conditions = data["pass_conditions"]
        condition_names = [c["condition"] for c in conditions]
        assert "wrap_schema_valid" in condition_names
        assert "all_mandatory_blocks" in condition_names
        assert "no_forbidden_actions" in condition_names


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BSRG-01 SELF-REVIEW GATE (PAC-JEFFREY-P01 SECTION 9)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBSRG01Endpoint:
    """Test BSRG-01 Benson Self-Review Gate endpoint."""

    def test_get_bsrg01_status(self, client):
        """GET /oc/controlplane/state/{pac_id}/bsrg-gate returns BSRG-01 status."""
        response = client.get("/oc/controlplane/state/PAC-JEFFREY-P01/bsrg-gate")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pac_id"] == "PAC-JEFFREY-P01"
        assert data["gate_type"] == "BSRG-01"
        assert "self_attestation" in data
        assert data["self_attestation_required"] is True
        assert data["training_signal_emission_required"] is True

    def test_bsrg01_violations_enum(self, client):
        """BSRG-01 violations must be NONE or LIST."""
        response = client.get("/oc/controlplane/state/PAC-JEFFREY-P01/bsrg-gate")
        data = response.json()
        
        # violations should be "NONE" (string) or a list
        violations = data["violations"]
        assert violations == "NONE" or isinstance(violations, list)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ACK LATENCY SETTLEMENT BINDING (PAC-JEFFREY-P01 SECTION 6)
# ═══════════════════════════════════════════════════════════════════════════════

class TestACKLatencyEndpoint:
    """Test ACK latency settlement binding endpoint."""

    def test_get_ack_latency_eligibility(self, client):
        """GET /oc/controlplane/state/{pac_id}/ack-latency returns latency status."""
        response = client.get("/oc/controlplane/state/PAC-CP-UI-EXEC-001/ack-latency")
        assert response.status_code == 200
        
        data = response.json()
        assert "latency_eligible" in data
        assert "threshold_ms" in data
        assert "max_latency_ms" in data
        assert "agent_latencies" in data
        assert "governance_invariant" in data
        assert "INV-CP-008" in data["governance_invariant"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: LEDGER COMMIT ATTESTATION (PAC-JEFFREY-P01 SECTION 11)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLedgerAttestationEndpoint:
    """Test ledger commit attestation endpoint."""

    def test_get_ledger_attestation_pending(self, client):
        """GET /oc/controlplane/state/{pac_id}/ledger-attestation returns status."""
        response = client.get("/oc/controlplane/state/PAC-JEFFREY-P01/ledger-attestation")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pac_id"] == "PAC-JEFFREY-P01"
        assert "attestation_status" in data
        assert "governance_invariant" in data
        assert "INV-CP-007" in data["governance_invariant"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: GOVERNANCE SUMMARY (PAC-JEFFREY-P01)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceSummaryEndpoint:
    """Test governance summary endpoint."""

    def test_get_governance_summary(self, client):
        """GET /oc/controlplane/state/{pac_id}/governance-summary returns complete summary."""
        response = client.get("/oc/controlplane/state/PAC-CP-UI-EXEC-001/governance-summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "governance_tier" in data
        assert data["fail_mode"] == "HARD_FAIL / FAIL-CLOSED"  # PAC-JEFFREY-P03 update
        assert data["execution_mode"] == "PARALLEL"
        assert data["execution_barrier"] == "AGENT_ACK_BARRIER"
        assert "barrier_release_condition" in data
        assert "gates" in data
        assert "positive_closure" in data
        assert "schema_references" in data

    def test_governance_summary_includes_all_gates(self, client):
        """Governance summary must include all governance gates."""
        response = client.get("/oc/controlplane/state/PAC-CP-UI-EXEC-001/governance-summary")
        data = response.json()
        
        gates = data["gates"]
        assert "ack_gate" in gates
        assert "wrap_gate" in gates
        assert "rg01_gate" in gates
        assert "bsrg01_gate" in gates
        assert "latency_gate" in gates
        assert "ledger_gate" in gates
        # PAC-JEFFREY-P02R additions
        assert "training_gate" in gates
        assert "closure_gate" in gates

    def test_governance_summary_schema_references(self, client):
        """Governance summary must include canonical schema references."""
        response = client.get("/oc/controlplane/state/PAC-CP-UI-EXEC-001/governance-summary")
        data = response.json()
        
        schemas = data["schema_references"]
        assert "pac" in schemas
        assert "wrap" in schemas
        assert "ber" in schemas
        assert "v1.0.0" in schemas["pac"]
        assert "v1.0.0" in schemas["wrap"]
        assert "v1.0.0" in schemas["ber"]
