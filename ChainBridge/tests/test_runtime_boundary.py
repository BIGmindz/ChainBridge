"""Runtime Boundary Guard Test Suite.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Cody (GID-01) — Senior Backend Engineer             ║
║ EXECUTING COLOR: 🟢 BLUE                                             ║
║ PAC: PAC-CODY-A6-ARCHITECTURE-ENFORCEMENT-WIRING-01                  ║
╚══════════════════════════════════════════════════════════════════════╝

Tests A6 Architecture Lock enforcement for runtime boundaries:
- Runtime cannot claim GIDs
- Runtime cannot sign PDOs
- Runtime cannot create proofs with agent binding
- Runtime cannot emit decisions

DOCTRINE:
- Runtime claiming GID → FAIL
- Runtime signing PDO → FAIL
- Runtime creating proof → FAIL
- All violations are FAIL-CLOSED

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import hashlib
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.services.runtime_guards import (
    RuntimeBoundaryGuard,
    RuntimeViolationType,
    RuntimeViolation,
    RuntimeGuardResult,
    AGENT_GID_PATTERN,
    KNOWN_RUNTIME_IDENTIFIERS,
    check_runtime_boundary_pdo,
    check_runtime_boundary_proof,
    check_runtime_boundary_decision,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def guard() -> RuntimeBoundaryGuard:
    """Provide RuntimeBoundaryGuard instance."""
    return RuntimeBoundaryGuard()


@pytest.fixture
def valid_pdo() -> dict:
    """Provide valid PDO with agent signer."""
    inputs_hash = hashlib.sha256(b"test-inputs").hexdigest()
    policy_version = "test-policy@v1.0"
    outcome = "APPROVED"
    binding_data = f"{inputs_hash}|{policy_version}|{outcome}"
    decision_hash = hashlib.sha256(binding_data.encode("utf-8")).hexdigest()
    
    return {
        "pdo_id": "PDO-RUNTIME12345678",
        "inputs_hash": inputs_hash,
        "policy_version": policy_version,
        "decision_hash": decision_hash,
        "outcome": outcome,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signer": "agent::cody-01",  # Valid agent signer
        "agent_id": "GID-01",
    }


@pytest.fixture
def valid_proof() -> dict:
    """Provide valid proof data."""
    return {
        "proof_id": str(uuid4()),
        "event_id": str(uuid4()),
        "event_hash": hashlib.sha256(b"event").hexdigest(),
        "event_type": "PRICE_SIGNAL",
        "decision_id": str(uuid4()),
        "decision_hash": hashlib.sha256(b"decision").hexdigest(),
        "decision_outcome": "APPROVED",
        "action_id": str(uuid4()),
        "action_type": "TRADE_EXECUTE",
        "action_status": "COMPLETED",
        "proof_timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_id": "GID-01",  # Valid agent binding
    }


# ---------------------------------------------------------------------------
# Runtime Identity Detection Tests
# ---------------------------------------------------------------------------


class TestRuntimeIdentityDetection:
    """Tests for runtime identity detection."""
    
    def test_known_runtime_identifiers_detected(self, guard: RuntimeBoundaryGuard):
        """Known runtime identifiers should be detected."""
        for runtime_id in KNOWN_RUNTIME_IDENTIFIERS:
            assert guard._is_runtime_identity(runtime_id) is True
    
    def test_runtime_keyword_detected(self, guard: RuntimeBoundaryGuard):
        """Identity containing 'runtime' should be detected."""
        runtime_like_ids = [
            "my_runtime",
            "RUNTIME_SYSTEM",
            "execution_runtime_v2",
            "Runtime-Handler",
        ]
        for runtime_id in runtime_like_ids:
            assert guard._is_runtime_identity(runtime_id) is True
    
    def test_system_signer_detected_as_runtime(self, guard: RuntimeBoundaryGuard):
        """System signers should be detected as runtime context."""
        system_signers = [
            "system::scheduler",
            "system::webhook-handler",
            "system::background-worker",
        ]
        for signer in system_signers:
            assert guard._is_runtime_identity(signer) is True
    
    def test_agent_identity_not_detected_as_runtime(self, guard: RuntimeBoundaryGuard):
        """Valid agent identities should NOT be detected as runtime."""
        agent_ids = [
            "agent::cody-01",
            "GID-01",
            "agent::ruby-12",
            "operator::admin",
        ]
        for agent_id in agent_ids:
            assert guard._is_runtime_identity(agent_id) is False
    
    def test_empty_identity_not_runtime(self, guard: RuntimeBoundaryGuard):
        """Empty identity should not be detected as runtime."""
        assert guard._is_runtime_identity("") is False
        assert guard._is_runtime_identity(None) is False


# ---------------------------------------------------------------------------
# PDO Creation Boundary Tests
# ---------------------------------------------------------------------------


class TestPDOCreationBoundary:
    """Tests for runtime boundary at PDO creation."""
    
    def test_agent_can_sign_pdo(self, guard: RuntimeBoundaryGuard, valid_pdo: dict):
        """Agent should be allowed to sign PDO."""
        result = guard.check_pdo_creation(valid_pdo, caller_identity="agent::cody")
        
        assert result.valid is True
        assert len(result.violations) == 0
    
    def test_runtime_cannot_sign_pdo(self, guard: RuntimeBoundaryGuard, valid_pdo: dict):
        """Runtime should be blocked from signing PDO."""
        valid_pdo["signer"] = "system::github_copilot"  # Runtime signer
        
        result = guard.check_pdo_creation(valid_pdo)
        
        assert result.valid is False
        assert any(v.violation_type == RuntimeViolationType.RUNTIME_SIGNS_PDO for v in result.violations)
    
    def test_runtime_cannot_claim_gid(self, guard: RuntimeBoundaryGuard, valid_pdo: dict):
        """Runtime caller cannot claim GID in agent_id field."""
        result = guard.check_pdo_creation(
            valid_pdo,
            caller_identity="github_copilot",  # Runtime caller
        )
        
        assert result.valid is False
        assert any(v.violation_type == RuntimeViolationType.RUNTIME_CLAIMS_GID for v in result.violations)
    
    def test_runtime_cannot_set_authority(self, guard: RuntimeBoundaryGuard, valid_pdo: dict):
        """Runtime caller cannot set authority fields."""
        valid_pdo["authority_gid"] = "GID-00"
        valid_pdo["authority_signature"] = "sig=="
        
        result = guard.check_pdo_creation(
            valid_pdo,
            caller_identity="runtime",  # Runtime caller
        )
        
        assert result.valid is False
        assert any(v.violation_type == RuntimeViolationType.RUNTIME_SETS_AUTHORITY for v in result.violations)
    
    def test_null_pdo_passes_check(self, guard: RuntimeBoundaryGuard):
        """Null PDO should pass check (nothing to violate)."""
        result = guard.check_pdo_creation(None)
        
        assert result.valid is True


# ---------------------------------------------------------------------------
# Proof Creation Boundary Tests
# ---------------------------------------------------------------------------


class TestProofCreationBoundary:
    """Tests for runtime boundary at proof creation."""
    
    def test_agent_can_create_proof(self, guard: RuntimeBoundaryGuard, valid_proof: dict):
        """Agent should be allowed to create proof."""
        result = guard.check_proof_creation(
            valid_proof,
            caller_identity="agent::cody",
        )
        
        assert result.valid is True
    
    def test_runtime_cannot_create_proof_with_agent_binding(self, guard: RuntimeBoundaryGuard, valid_proof: dict):
        """Runtime cannot create proof with agent_id binding."""
        result = guard.check_proof_creation(
            valid_proof,
            caller_identity="github_copilot",  # Runtime
        )
        
        assert result.valid is False
        assert any(v.violation_type == RuntimeViolationType.RUNTIME_CREATES_PROOF for v in result.violations)
    
    def test_runtime_can_create_proof_without_agent_binding(self, guard: RuntimeBoundaryGuard):
        """Runtime can create proof without agent binding (e.g., system events)."""
        system_proof = {
            "proof_id": str(uuid4()),
            "event_type": "SYSTEM_EVENT",
            # No agent_id or agent_gid
        }
        
        result = guard.check_proof_creation(
            system_proof,
            caller_identity="system::event-logger",
        )
        
        assert result.valid is True
    
    def test_null_proof_passes_check(self, guard: RuntimeBoundaryGuard):
        """Null proof should pass check."""
        result = guard.check_proof_creation(None)
        
        assert result.valid is True


# ---------------------------------------------------------------------------
# Decision Emission Boundary Tests
# ---------------------------------------------------------------------------


class TestDecisionEmissionBoundary:
    """Tests for runtime boundary at decision emission."""
    
    def test_agent_can_emit_decision(self, guard: RuntimeBoundaryGuard):
        """Agent should be allowed to emit decision."""
        decision = {"outcome": "APPROVED", "reason": "Policy satisfied"}
        
        result = guard.check_decision_emission(
            decision,
            caller_identity="agent::ruby-12",
        )
        
        assert result.valid is True
    
    def test_runtime_cannot_emit_decision(self, guard: RuntimeBoundaryGuard):
        """Runtime should be blocked from emitting decision."""
        decision = {"outcome": "APPROVED", "reason": "Policy satisfied"}
        
        result = guard.check_decision_emission(
            decision,
            caller_identity="github_copilot",
        )
        
        assert result.valid is False
        assert any(v.violation_type == RuntimeViolationType.RUNTIME_EMITS_DECISION for v in result.violations)
    
    def test_system_cannot_emit_decision(self, guard: RuntimeBoundaryGuard):
        """System signers cannot emit decisions."""
        decision = {"outcome": "APPROVED"}
        
        result = guard.check_decision_emission(
            decision,
            caller_identity="system::scheduler",
        )
        
        assert result.valid is False
    
    def test_null_decision_passes_check(self, guard: RuntimeBoundaryGuard):
        """Null decision should pass check."""
        result = guard.check_decision_emission(None)
        
        assert result.valid is True


# ---------------------------------------------------------------------------
# FAIL-CLOSED Behavior Tests
# ---------------------------------------------------------------------------


class TestFailClosedBehavior:
    """Tests ensuring FAIL-CLOSED behavior for runtime boundaries."""
    
    def test_all_known_runtimes_blocked_from_signing(self, guard: RuntimeBoundaryGuard, valid_pdo: dict):
        """All known runtime identifiers should be blocked from signing PDOs."""
        for runtime_id in KNOWN_RUNTIME_IDENTIFIERS:
            valid_pdo["signer"] = runtime_id
            result = guard.check_pdo_creation(valid_pdo)
            
            assert result.valid is False, f"Runtime '{runtime_id}' should be blocked"
    
    def test_runtime_in_signer_always_blocked(self, guard: RuntimeBoundaryGuard, valid_pdo: dict):
        """'runtime' keyword in signer should always be blocked."""
        runtime_signers = [
            "runtime::handler",
            "my_runtime_service",
            "RUNTIME",
        ]
        for signer in runtime_signers:
            valid_pdo["signer"] = signer
            result = guard.check_pdo_creation(valid_pdo)
            
            assert result.valid is False, f"Signer '{signer}' should be blocked"
    
    def test_multiple_violations_all_detected(self, guard: RuntimeBoundaryGuard, valid_pdo: dict):
        """Multiple violations should all be detected and reported."""
        valid_pdo["signer"] = "runtime"
        valid_pdo["authority_gid"] = "GID-00"
        valid_pdo["authority_signature"] = "sig=="
        
        result = guard.check_pdo_creation(
            valid_pdo,
            caller_identity="github_copilot",
        )
        
        assert result.valid is False
        # Should detect: RUNTIME_SIGNS_PDO, RUNTIME_CLAIMS_GID, RUNTIME_SETS_AUTHORITY
        assert len(result.violations) >= 2
    
    def test_validation_is_deterministic(self, guard: RuntimeBoundaryGuard, valid_pdo: dict):
        """Same input should produce same result."""
        valid_pdo["signer"] = "runtime"
        
        results = [guard.check_pdo_creation(valid_pdo) for _ in range(5)]
        
        for result in results:
            assert result.valid == results[0].valid
            assert len(result.violations) == len(results[0].violations)


# ---------------------------------------------------------------------------
# Module-Level Function Tests
# ---------------------------------------------------------------------------


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""
    
    def test_check_runtime_boundary_pdo(self, valid_pdo: dict):
        """Module-level PDO check should work."""
        result = check_runtime_boundary_pdo(valid_pdo, caller_identity="agent::test")
        
        assert result.valid is True
    
    def test_check_runtime_boundary_pdo_runtime_caller(self, valid_pdo: dict):
        """Module-level PDO check should detect runtime caller."""
        result = check_runtime_boundary_pdo(
            valid_pdo,
            caller_identity="github_copilot",
        )
        
        assert result.valid is False
    
    def test_check_runtime_boundary_proof(self, valid_proof: dict):
        """Module-level proof check should work."""
        result = check_runtime_boundary_proof(valid_proof, caller_identity="agent::test")
        
        assert result.valid is True
    
    def test_check_runtime_boundary_decision(self):
        """Module-level decision check should work."""
        decision = {"outcome": "APPROVED"}
        
        result = check_runtime_boundary_decision(decision, caller_identity="agent::test")
        
        assert result.valid is True


# ---------------------------------------------------------------------------
# Violation Record Tests
# ---------------------------------------------------------------------------


class TestViolationRecords:
    """Tests for violation record contents."""
    
    def test_violation_contains_type(self, guard: RuntimeBoundaryGuard, valid_pdo: dict):
        """Violation should contain violation type."""
        valid_pdo["signer"] = "runtime"
        
        result = guard.check_pdo_creation(valid_pdo)
        
        assert result.violations[0].violation_type is not None
    
    def test_violation_contains_field(self, guard: RuntimeBoundaryGuard, valid_pdo: dict):
        """Violation should contain field name."""
        valid_pdo["signer"] = "runtime"
        
        result = guard.check_pdo_creation(valid_pdo)
        
        assert result.violations[0].field is not None
    
    def test_violation_contains_message(self, guard: RuntimeBoundaryGuard, valid_pdo: dict):
        """Violation should contain informative message."""
        valid_pdo["signer"] = "runtime"
        
        result = guard.check_pdo_creation(valid_pdo)
        
        assert len(result.violations[0].message) > 0
        assert "runtime" in result.violations[0].message.lower()
    
    def test_result_contains_timestamp(self, guard: RuntimeBoundaryGuard, valid_pdo: dict):
        """Result should contain timestamp."""
        result = guard.check_pdo_creation(valid_pdo)
        
        assert result.checked_at is not None
        # Should be valid ISO timestamp
        datetime.fromisoformat(result.checked_at.replace("Z", "+00:00"))


# ═══════════════════════════════════════════════════════════════════════════
# END — Cody (GID-01) — 🔵
# ═══════════════════════════════════════════════════════════════════════════
