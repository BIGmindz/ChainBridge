#!/usr/bin/env python3
"""
test_negative_paths.py — Negative-Path Test Coverage

PAC Reference: PAC-BENSON-P71R-ATLAS-CANONICAL-HARDENING-DRIFT-SEAL-01
Authority: BENSON (GID-00)
Executor: ATLAS (GID-11)

This module tests all negative/failure paths to ensure:
1. Silent failures are impossible
2. FAIL_CLOSED is enforced
3. Error codes are returned correctly
4. No operation succeeds when it should fail
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

# Add tools/governance to path
SCRIPT_DIR = Path(__file__).parent
TOOLS_DIR = SCRIPT_DIR.parent.parent / "tools" / "governance"
sys.path.insert(0, str(TOOLS_DIR))

from invariants import (
    InvariantRegistry,
    InvariantError,
    InvariantErrorCode,
    InvariantClass,
    get_invariant_registry,
    enforce_invariant,
)


# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURAL INVARIANT NEGATIVE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStructuralNegativePaths:
    """Test structural invariant violations."""
    
    def test_missing_runtime_activation_fails(self):
        """INV-001: Missing RUNTIME_ACTIVATION_ACK must fail."""
        ctx = {"content": "", "blocks": {}}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-001", ctx)
        assert exc.value.code == InvariantErrorCode.GS_501_MISSING_REQUIRED_FIELD
    
    def test_missing_agent_activation_fails(self):
        """INV-002: Missing AGENT_ACTIVATION_ACK must fail."""
        ctx = {"content": "RUNTIME_ACTIVATION_ACK: yes", "blocks": {}}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-002", ctx)
        assert exc.value.code == InvariantErrorCode.GS_501_MISSING_REQUIRED_FIELD
    
    def test_missing_gateway_sequence_fails(self):
        """INV-003: Missing CANONICAL_GATEWAY_SEQUENCE must fail."""
        ctx = {"content": "", "blocks": {}}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-003", ctx)
        assert exc.value.code == InvariantErrorCode.GS_501_MISSING_REQUIRED_FIELD
    
    def test_invalid_template_checksum_fails(self):
        """INV-004: Invalid template checksum must fail."""
        ctx = {"template_checksum": "invalid_checksum"}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-004", ctx)
        assert exc.value.code == InvariantErrorCode.GS_504_TEMPLATE_MISMATCH
    
    def test_missing_template_checksum_fails(self):
        """INV-004: Missing template checksum must fail."""
        ctx = {"template_checksum": ""}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-004", ctx)
        assert exc.value.code == InvariantErrorCode.GS_504_TEMPLATE_MISMATCH
    
    def test_incomplete_gold_standard_fails(self):
        """INV-005: Incomplete Gold Standard checklist must fail."""
        ctx = {"gold_standard_checklist": {"GS_01": "PASS"}}  # Only 1 of 13
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-005", ctx)
        assert exc.value.code == InvariantErrorCode.GS_500_STRUCTURAL_VIOLATION
    
    def test_gold_standard_item_failing(self):
        """INV-005: Failed Gold Standard item must fail."""
        ctx = {
            "gold_standard_checklist": {
                f"GS_{i:02d}": {"status": "PASS" if i != 7 else "FAIL"}
                for i in range(1, 14)
            }
        }
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-005", ctx)
        assert exc.value.code == InvariantErrorCode.GS_500_STRUCTURAL_VIOLATION


# ═══════════════════════════════════════════════════════════════════════════════
# BEHAVIORAL INVARIANT NEGATIVE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBehavioralNegativePaths:
    """Test behavioral invariant violations."""
    
    def test_non_fail_closed_mode_fails(self):
        """INV-011: Non-fail-closed mode must fail."""
        ctx = {"mode": "PERMISSIVE"}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-011", ctx)
        assert exc.value.code == InvariantErrorCode.GS_510_BEHAVIORAL_VIOLATION
    
    def test_empty_mode_fails(self):
        """INV-011: Empty mode must fail."""
        ctx = {"mode": ""}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-011", ctx)
        assert exc.value.code == InvariantErrorCode.GS_510_BEHAVIORAL_VIOLATION
    
    def test_non_deterministic_hash_fails(self):
        """INV-012: Non-deterministic hash must fail."""
        import hashlib
        test_data = {"key": "value"}
        wrong_hash = "wrong_hash_value"
        ctx = {"hash_test_data": test_data, "expected_hash": wrong_hash}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-012", ctx)
        assert exc.value.code == InvariantErrorCode.GS_512_NON_DETERMINISTIC
    
    def test_final_state_with_transitions_fails(self):
        """INV-013: FINAL state with outbound transitions must fail."""
        ctx = {
            "state": "FINAL",
            "valid_transitions": {"FINAL": ["DRAFT"]}  # Should be empty
        }
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-013", ctx)
        assert exc.value.code == InvariantErrorCode.GS_513_STATE_MUTATION_FORBIDDEN


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHORITY INVARIANT NEGATIVE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthorityNegativePaths:
    """Test authority invariant violations."""
    
    def test_orchestrator_with_business_logic_fails(self):
        """INV-020: Orchestrator with business logic must fail."""
        ctx = {"agent": "BENSON", "business_logic": "ALLOWED"}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-020", ctx)
        assert exc.value.code == InvariantErrorCode.GS_523_UNAUTHORIZED_ACTION
    
    def test_lane_boundary_violation_fails(self):
        """INV-021: Lane boundary violation must fail."""
        ctx = {"execution_lane": "BACKEND", "actual_lane": "FRONTEND"}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-021", ctx)
        assert exc.value.code == InvariantErrorCode.GS_521_LANE_BOUNDARY_CROSSED
    
    def test_wrap_by_non_benson_fails(self):
        """INV-022: WRAP by non-BENSON must fail."""
        ctx = {"artifact_type": "WRAP", "wrap_emitter": "CODY (GID-02)"}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-022", ctx)
        assert exc.value.code == InvariantErrorCode.GS_520_AUTHORITY_VIOLATION
    
    def test_agent_self_closure_fails(self):
        """INV-023: Agent self-closure must fail."""
        ctx = {"pac_agent": "CODY", "closer": "CODY"}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-023", ctx)
        assert exc.value.code == InvariantErrorCode.GS_524_SELF_CLOSURE_FORBIDDEN


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPORAL INVARIANT NEGATIVE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemporalNegativePaths:
    """Test temporal invariant violations."""
    
    def test_missing_human_review_gate_fails(self):
        """INV-031: Missing human review gate must fail."""
        ctx = {"human_review_required": False, "content": "No human review"}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-031", ctx)
        assert exc.value.code == InvariantErrorCode.GS_534_PREMATURE_EXECUTION
    
    def test_final_without_seal_fails(self):
        """INV-032: FINAL without prior SEAL must fail."""
        ctx = {"state": "FINAL", "sealed_at": None}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-032", ctx)
        assert exc.value.code == InvariantErrorCode.GS_530_TEMPORAL_VIOLATION


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRITY INVARIANT NEGATIVE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrityNegativePaths:
    """Test integrity invariant violations."""
    
    def test_broken_hash_chain_fails(self):
        """INV-040: Broken hash chain must fail."""
        ctx = {
            "ledger_entries": [
                {"entry_hash": "abc123"},
                {"prior_hash": "wrong_hash", "entry_hash": "def456"}
            ]
        }
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-040", ctx)
        assert exc.value.code == InvariantErrorCode.GS_541_HASH_CHAIN_BROKEN
    
    def test_incomplete_merkle_proof_fails(self):
        """INV-041: Incomplete merkle proof must fail."""
        ctx = {"composite_proof": {"merkle_root": "abc"}}  # Missing leaf_hashes
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-041", ctx)
        assert exc.value.code == InvariantErrorCode.GS_542_PROOF_INVALID
    
    def test_replay_attack_fails(self):
        """INV-042: Replay attack must fail."""
        ctx = {"nonce": "already_used", "used_nonces": {"already_used"}}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-042", ctx)
        assert exc.value.code == InvariantErrorCode.GS_544_REPLAY_DETECTED


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSITE INVARIANT NEGATIVE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompositeNegativePaths:
    """Test composite invariant violations."""
    
    def test_unvalidated_child_pdo_fails(self):
        """INV-050: Unvalidated child PDO must fail."""
        ctx = {
            "child_pdos": [
                {"pdo_id": "PDO-1", "status": "VALIDATED"},
                {"pdo_id": "PDO-2", "status": "PENDING"}
            ]
        }
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-050", ctx)
        assert exc.value.code == InvariantErrorCode.GS_551_DEPENDENCY_UNMET
    
    def test_cycle_in_dag_fails(self):
        """INV-051: Cycle in dependency DAG must fail."""
        ctx = {"cycle_detected": True}
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-051", ctx)
        assert exc.value.code == InvariantErrorCode.GS_550_COMPOSITE_VIOLATION


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY NEGATIVE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegistryNegativePaths:
    """Test registry-level negative paths."""
    
    def test_unknown_invariant_fails(self):
        """Unknown invariant ID must fail."""
        with pytest.raises(InvariantError) as exc:
            enforce_invariant("INV-UNKNOWN", {})
        assert exc.value.code == InvariantErrorCode.GS_500_STRUCTURAL_VIOLATION
    
    def test_duplicate_registration_fails(self):
        """Duplicate invariant registration must fail."""
        from invariants import Invariant, InvariantSeverity
        
        registry = InvariantRegistry()
        
        # Try to register same ID twice
        inv1 = Invariant(
            id="INV-DUP",
            name="TEST",
            description="Test",
            invariant_class=InvariantClass.STRUCTURAL,
            severity=InvariantSeverity.CRITICAL,
            error_code=InvariantErrorCode.GS_500_STRUCTURAL_VIOLATION,
            pac_source="TEST",
            enforce=lambda ctx: (True, "OK")
        )
        
        # First registration should succeed (INV-DUP is new)
        # But this will fail because _load_canonical_invariants already ran
        # So we need to check if it's already there
        existing = registry.get("INV-DUP")
        if existing is None:
            registry.register(inv1)
            # Second registration should fail
            with pytest.raises(InvariantError) as exc:
                registry.register(inv1)
            assert exc.value.code == InvariantErrorCode.GS_552_INVARIANT_CONFLICT


# ═══════════════════════════════════════════════════════════════════════════════
# O-PDO MODULE NEGATIVE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestOPDONegativePaths:
    """Test O-PDO module negative paths."""
    
    def test_empty_child_list_fails(self):
        """O-PDO with empty child list must fail."""
        from opdo import create_opdo, OPDOError, OPDOErrorCode
        
        with pytest.raises(OPDOError) as exc:
            create_opdo("PAC-TEST-001", [])
        assert exc.value.code == OPDOErrorCode.GS_400_EMPTY_CHILD_LIST
    
    def test_invalid_pac_ref_fails(self):
        """O-PDO with invalid PAC reference must fail."""
        from opdo import create_opdo, OPDOError, OPDOErrorCode, ChildPDO
        
        child = ChildPDO(
            pdo_id="PDO-TEST-001",
            agent_name="TEST",
            agent_gid="GID-99",
            sub_pac_id="Sub-PAC-TEST",
            ber_id="BER-TEST",
            status="VALIDATED",
            pdo_hash="abc",
            task_count=1,
            quality_score=1.0,
            created_at="2025-01-01T00:00:00Z"
        )
        
        with pytest.raises(OPDOError) as exc:
            create_opdo("INVALID", [child])
        assert exc.value.code == OPDOErrorCode.GS_441_INVALID_PAC_REF
    
    def test_unvalidated_child_fails(self):
        """O-PDO with unvalidated child must fail."""
        from opdo import create_opdo, OPDOError, OPDOErrorCode, ChildPDO
        
        child = ChildPDO(
            pdo_id="PDO-TEST-001",
            agent_name="TEST",
            agent_gid="GID-99",
            sub_pac_id="Sub-PAC-TEST",
            ber_id="BER-TEST",
            status="PENDING",  # Not VALIDATED
            pdo_hash="abc",
            task_count=1,
            quality_score=1.0,
            created_at="2025-01-01T00:00:00Z"
        )
        
        with pytest.raises(OPDOError) as exc:
            create_opdo("PAC-TEST-001", [child])
        assert exc.value.code == OPDOErrorCode.GS_402_CHILD_PDO_NOT_VALIDATED
    
    def test_finalize_without_seal_fails(self):
        """O-PDO finalization without seal must fail."""
        from opdo import (
            OrchestratedPDO, OPDOFinalityStateMachine, 
            OPDOError, OPDOErrorCode, OPDOState
        )
        
        opdo = OrchestratedPDO(
            opdo_id="OPDO-TEST",
            pac_orch_id="PAC-TEST",
            orchestrator_agent="BENSON",
            orchestrator_gid="GID-00",
            child_pdos=[]
        )
        opdo.state = OPDOState.DRAFT
        
        fsm = OPDOFinalityStateMachine(opdo)
        
        with pytest.raises(OPDOError) as exc:
            fsm.finalize("BER-TEST")
        assert exc.value.code == OPDOErrorCode.GS_433_SEAL_REQUIRED
    
    def test_transition_from_final_fails(self):
        """Transition from FINAL state must fail."""
        from opdo import (
            OrchestratedPDO, OPDOFinalityStateMachine,
            OPDOError, OPDOErrorCode, OPDOState, CompositeProof
        )
        
        opdo = OrchestratedPDO(
            opdo_id="OPDO-TEST",
            pac_orch_id="PAC-TEST",
            orchestrator_agent="BENSON",
            orchestrator_gid="GID-00",
            child_pdos=[],
            state=OPDOState.FINAL,
            final_hash="abc123"
        )
        
        fsm = OPDOFinalityStateMachine(opdo)
        
        with pytest.raises(OPDOError) as exc:
            fsm.transition(OPDOState.DRAFT, "test", "test")
        assert exc.value.code == OPDOErrorCode.GS_430_INVALID_STATE_TRANSITION


# ═══════════════════════════════════════════════════════════════════════════════
# BER CHALLENGE NEGATIVE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBERChallengeNegativePaths:
    """Test BER challenge-response negative paths."""
    
    def test_empty_ber_data_fails(self):
        """Challenge generation with empty BER data must fail."""
        from ber_challenge import generate_ber_challenge, BERChallengeError
        
        with pytest.raises(BERChallengeError) as exc:
            generate_ber_challenge({})
        assert "GS_301" in str(exc.value)
    
    def test_incorrect_response_fails(self):
        """Incorrect challenge response must fail."""
        from ber_challenge import (
            generate_ber_challenge, validate_challenge_response,
            BERChallengeError
        )
        
        ber_data = {
            "ber_id": "BER-TEST",
            "tasks_completed": 5,
            "files_created": ["a.py", "b.py"],
            "quality_score": 0.95,
            "agent_name": "TEST",
            "agent_gid": "GID-99"
        }
        
        challenge = generate_ber_challenge(ber_data)
        
        with pytest.raises(BERChallengeError) as exc:
            validate_challenge_response(
                challenge=challenge,
                response="WRONG_ANSWER",
                latency_ms=6000
            )
        assert "GS_310" in str(exc.value)
    
    def test_minimum_latency_not_met_fails(self):
        """Response below minimum latency must fail."""
        from ber_challenge import (
            generate_ber_challenge, validate_challenge_response,
            ChallengeType, BERChallengeError
        )
        
        ber_data = {
            "ber_id": "BER-TEST",
            "tasks_completed": 5,
            "files_created": ["a.py"],
            "quality_score": 0.95,
            "agent_name": "TEST",
            "agent_gid": "GID-99"
        }
        
        challenge = generate_ber_challenge(ber_data)
        
        with pytest.raises(BERChallengeError) as exc:
            validate_challenge_response(
                challenge=challenge,
                response=challenge.correct_answer,
                latency_ms=1000  # Below 5000ms minimum
            )
        assert "GS_315" in str(exc.value)


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
