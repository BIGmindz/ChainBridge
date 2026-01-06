"""
PAC-20260106-P10-SETTLEMENT-GUARD
Settlement Safeguards Tests — Verdict Guard Enforcement

Verifies:
- INV-CP-023: NO VERDICT = NO COMMIT
- Commit without verdict raises error
- Commit with verdict succeeds

Author: BENSON (GID-00-EXEC)
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.settlement_oc import router as settlement_router
from core.governance.settlement_engine import (
    SettlementLifecycle,
    SettlementPhase,
    SettlementEngine,
    get_settlement_engine,
    reset_settlement_engine,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def app():
    """FastAPI app with settlement router."""
    app = FastAPI()
    app.include_router(settlement_router)
    return app


@pytest.fixture
def client(app):
    """Test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_engine():
    """Reset settlement engine before each test."""
    reset_settlement_engine()
    yield
    reset_settlement_engine()


# =============================================================================
# INV-CP-023 TESTS — NO VERDICT = NO COMMIT
# =============================================================================


class TestCommitWithoutVerdictRaisesError:
    """Test that commit without verdict raises SettlementError."""
    
    def test_commit_without_verdict_raises_error(self, client):
        """
        Attempt to commit without readiness verdict MUST FAIL.
        
        INV-CP-023: NO VERDICT = NO COMMIT
        """
        # Setup: Activate engine and create lifecycle
        engine = get_settlement_engine()
        engine.activate()
        
        # Create lifecycle without readiness evaluation
        lifecycle = engine.create_lifecycle("PAC-TEST-001")
        assert lifecycle.readiness_verdict_hash is None, "Precondition: No verdict"
        
        # Attempt ledger commit
        response = client.post(
            "/oc/settlement/ledger/commit",
            json={
                "settlement_id": lifecycle.settlement_id,
                "ber_hash": "test-ber-hash",
            },
        )
        
        # MUST FAIL with 400 and specific error
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        error_detail = response.json().get("detail", "")
        assert "INV-CP-023" in error_detail, f"Error must cite INV-CP-023: {error_detail}"
        assert "Readiness Verdict" in error_detail, f"Error must mention verdict: {error_detail}"
    
    def test_commit_without_verdict_does_not_mutate_lifecycle(self, client):
        """
        Failed commit attempt must not mutate lifecycle state.
        """
        engine = get_settlement_engine()
        engine.activate()
        
        lifecycle = engine.create_lifecycle("PAC-TEST-002")
        original_phase = lifecycle.current_phase
        
        # Attempt commit (should fail)
        response = client.post(
            "/oc/settlement/ledger/commit",
            json={
                "settlement_id": lifecycle.settlement_id,
                "ber_hash": "test-ber-hash",
            },
        )
        
        assert response.status_code == 400
        
        # Verify lifecycle unchanged
        lifecycle_after = engine.get_lifecycle(lifecycle.settlement_id)
        assert lifecycle_after.current_phase == original_phase
        assert lifecycle_after.ledger_commit is None


class TestCommitWithVerdictSucceeds:
    """Test that commit with valid verdict succeeds."""
    
    def test_commit_with_verdict_succeeds(self, client):
        """
        Commit with readiness verdict MUST SUCCEED.
        """
        engine = get_settlement_engine()
        engine.activate()
        
        # Create lifecycle and advance through readiness
        lifecycle = engine.create_lifecycle("PAC-TEST-003")
        
        # Create and process PDO (required before readiness)
        from core.governance.settlement_engine import create_settlement_pdo
        pdo = create_settlement_pdo(
            pac_id="PAC-TEST-003",
            amount=100.0,
            currency="USD",
            source_account="SRC-001",
            destination_account="DST-001",
            approved=True,
        )
        engine.process_pdo(lifecycle, pdo)
        
        # Evaluate readiness (sets verdict hash)
        engine.evaluate_readiness(
            lifecycle,
            readiness_verdict_hash="verdict-hash-123",
            is_eligible=True,
        )
        
        # Verify verdict is set
        assert lifecycle.readiness_verdict_hash is not None, "Verdict must be set"
        
        # Now commit should succeed
        response = client.post(
            "/oc/settlement/ledger/commit",
            json={
                "settlement_id": lifecycle.settlement_id,
                "ber_hash": "ber-hash-123",
            },
        )
        
        # MUST SUCCEED
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
        
        data = response.json()
        assert data["status"] == "COMMITTED"
        assert "commit_hash" in data
    
    def test_commit_transitions_lifecycle_to_committed(self, client):
        """
        Successful commit must transition lifecycle to LEDGER_COMMITTED.
        """
        engine = get_settlement_engine()
        engine.activate()
        
        lifecycle = engine.create_lifecycle("PAC-TEST-004")
        
        # Setup: PDO + Readiness
        from core.governance.settlement_engine import create_settlement_pdo
        pdo = create_settlement_pdo(
            pac_id="PAC-TEST-004",
            amount=500.0,
            currency="USD",
            source_account="SRC-004",
            destination_account="DST-004",
            approved=True,
        )
        engine.process_pdo(lifecycle, pdo)
        engine.evaluate_readiness(
            lifecycle,
            readiness_verdict_hash="verdict-hash-004",
            is_eligible=True,
        )
        
        # Commit
        response = client.post(
            "/oc/settlement/ledger/commit",
            json={
                "settlement_id": lifecycle.settlement_id,
                "ber_hash": "ber-hash-004",
            },
        )
        
        assert response.status_code == 200
        
        # Verify phase transition
        lifecycle_after = engine.get_lifecycle(lifecycle.settlement_id)
        assert lifecycle_after.current_phase == SettlementPhase.LEDGER_COMMITTED


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestSettlementGuardEdgeCases:
    """Edge case tests for settlement guard."""
    
    def test_commit_nonexistent_lifecycle_returns_404(self, client):
        """Commit for non-existent lifecycle returns 404."""
        engine = get_settlement_engine()
        engine.activate()
        
        response = client.post(
            "/oc/settlement/ledger/commit",
            json={
                "settlement_id": "NONEXISTENT-ID",
                "ber_hash": "test-ber-hash",
            },
        )
        
        assert response.status_code == 404
    
    def test_commit_without_engine_activation_returns_400(self, client):
        """Commit without engine activation returns 400."""
        # Engine not activated
        response = client.post(
            "/oc/settlement/ledger/commit",
            json={
                "settlement_id": "ANY-ID",
                "ber_hash": "test-ber-hash",
            },
        )
        
        assert response.status_code == 400
        assert "not activated" in response.json().get("detail", "").lower()
    
    def test_empty_verdict_hash_fails_guard(self, client):
        """Empty string verdict hash should fail the guard."""
        engine = get_settlement_engine()
        engine.activate()
        
        lifecycle = engine.create_lifecycle("PAC-TEST-EMPTY")
        # Manually set empty string (should be treated as falsy)
        lifecycle.readiness_verdict_hash = ""
        
        response = client.post(
            "/oc/settlement/ledger/commit",
            json={
                "settlement_id": lifecycle.settlement_id,
                "ber_hash": "test-ber-hash",
            },
        )
        
        # Empty string is falsy, should fail guard
        assert response.status_code == 400
        assert "INV-CP-023" in response.json().get("detail", "")


# =============================================================================
# INVARIANT ASSERTION TESTS
# =============================================================================


class TestInvariantINVCP023:
    """Direct invariant tests for INV-CP-023."""
    
    def test_invariant_message_is_explicit(self, client):
        """Error message must explicitly state the invariant violation."""
        engine = get_settlement_engine()
        engine.activate()
        
        lifecycle = engine.create_lifecycle("PAC-INV-TEST")
        
        response = client.post(
            "/oc/settlement/ledger/commit",
            json={
                "settlement_id": lifecycle.settlement_id,
                "ber_hash": "test-ber-hash",
            },
        )
        
        assert response.status_code == 400
        error = response.json().get("detail", "")
        
        # Must be explicit, not generic
        assert "SettlementError" in error or "Violation" in error
        assert "INV-CP-023" in error
        assert "Readiness" in error
    
    def test_guard_runs_before_engine_commit(self, client):
        """Guard must run BEFORE attempting engine commit."""
        engine = get_settlement_engine()
        engine.activate()
        
        lifecycle = engine.create_lifecycle("PAC-ORDER-TEST")
        
        # If guard runs after engine, we'd see a phase transition error instead
        response = client.post(
            "/oc/settlement/ledger/commit",
            json={
                "settlement_id": lifecycle.settlement_id,
                "ber_hash": "test-ber-hash",
            },
        )
        
        # Error should be about verdict, not about phase transition
        error = response.json().get("detail", "")
        assert "INV-CP-023" in error
        assert "phase" not in error.lower()
