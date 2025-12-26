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

# PAC-BENSON-P74: Add repo root and tools paths for pac_linter tests
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # ChainBridge-local-repo
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools"))

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
# GOLD STANDARD CHECKLIST NEGATIVE TESTS — PAC-BENSON-P74
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoldStandardChecklistNegativePaths:
    """
    Test Gold Standard Checklist enforcement negative paths.
    PAC-BENSON-P74: All PACs must have PASS (13/13) checklist.
    """

    @pytest.fixture
    def pac_linter_imports(self):
        """Import pac_linter module for tests."""
        import sys

        # Set up paths for pac_linter imports
        # pac_linter.py is in ChainBridge-local-repo/tools/
        # It imports from core.governance.agent_roster which is in ChainBridge-local-repo/core/
        # NOTE: ChainBridge/core also exists but doesn't have governance, so we must
        # ensure ChainBridge-local-repo is at the FRONT of sys.path to avoid shadowing.
        repo_root = Path(__file__).resolve().parent.parent.parent.parent  # ChainBridge-local-repo
        chainbridge_dir = repo_root / "ChainBridge"  # The nested dir that might shadow

        tools_path = str(repo_root / "tools")
        root_path = str(repo_root)

        # Remove paths that would shadow core.governance
        # ChainBridge/core exists but doesn't have governance
        new_path = []
        for p in sys.path:
            if p == str(chainbridge_dir):
                continue  # Skip ChainBridge dir to avoid core shadowing
            new_path.append(p)
        sys.path[:] = new_path

        # Insert monorepo paths at the front
        if root_path not in sys.path:
            sys.path.insert(0, root_path)  # First, so core.governance resolves
        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)  # Second, so pac_linter resolves

        # Remove any cached versions
        for mod in list(sys.modules.keys()):
            if mod == "pac_linter" or mod.startswith("pac_linter."):
                del sys.modules[mod]
            if mod == "core" or mod.startswith("core."):
                del sys.modules[mod]

        from pac_linter import (
            lint_gold_standard_checklist_present,
            lint_gold_standard_checklist_status,
            lint_gold_standard_checklist_items,
            GOLD_STANDARD_CHECKLIST_ITEMS,
            GOLD_STANDARD_CHECKLIST_COUNT,
            ViolationSeverity,
        )
        return {
            "lint_present": lint_gold_standard_checklist_present,
            "lint_status": lint_gold_standard_checklist_status,
            "lint_items": lint_gold_standard_checklist_items,
            "items": GOLD_STANDARD_CHECKLIST_ITEMS,
            "count": GOLD_STANDARD_CHECKLIST_COUNT,
            "severity": ViolationSeverity,
        }

    def test_pac_without_checklist_fails(self, pac_linter_imports, tmp_path):
        """PAC without Gold Standard Checklist must fail validation."""
        lint_present = pac_linter_imports["lint_present"]

        # Create a PAC file without checklist
        pac_content = """
# PAC-TEST-P99-MISSING-CHECKLIST-01

## EXECUTING AGENT
ATLAS (GID-11)

## TASKS
- T1: Do something

## POSITIVE_CLOSURE
Ready for closure.

## END — ATLAS (GID-11) — 🔵 BLUE
"""
        pac_file = tmp_path / "PAC-TEST-P99.md"
        pac_file.write_text(pac_content)

        violations = lint_present(pac_content, pac_file)

        assert len(violations) == 1
        assert violations[0].rule == "pac-gold-standard-checklist-present"
        assert violations[0].severity == pac_linter_imports["severity"].ERROR

    def test_checklist_without_status_fails(self, pac_linter_imports, tmp_path):
        """Checklist without CHECKLIST_STATUS must fail."""
        lint_status = pac_linter_imports["lint_status"]

        pac_content = """
# PAC-TEST-P99-MISSING-STATUS-01

## GOLD_STANDARD_CHECKLIST
[✓] Canonical PAC template used
[✓] All gateways (G0–G7) executed in order

## POSITIVE_CLOSURE
"""
        pac_file = tmp_path / "PAC-TEST-P99.md"
        pac_file.write_text(pac_content)

        violations = lint_status(pac_content, pac_file)

        assert len(violations) == 1
        assert violations[0].rule == "pac-gold-standard-checklist-status"
        assert "CHECKLIST_STATUS" in violations[0].message

    def test_checklist_partial_pass_fails(self, pac_linter_imports, tmp_path):
        """Checklist with 12/13 must fail - no partial compliance."""
        lint_status = pac_linter_imports["lint_status"]

        pac_content = """
# PAC-TEST-P99-PARTIAL-PASS-01

## GOLD_STANDARD_CHECKLIST
[✓] Canonical PAC template used

CHECKLIST_STATUS: PASS (12/13)

## POSITIVE_CLOSURE
"""
        pac_file = tmp_path / "PAC-TEST-P99.md"
        pac_file.write_text(pac_content)

        violations = lint_status(pac_content, pac_file)

        assert len(violations) >= 1
        assert any("12/13" in v.message or "13/13" in v.message for v in violations)

    def test_checklist_wrong_total_fails(self, pac_linter_imports, tmp_path):
        """Checklist with wrong total count must fail."""
        lint_status = pac_linter_imports["lint_status"]

        pac_content = """
# PAC-TEST-P99-WRONG-TOTAL-01

## GOLD_STANDARD_CHECKLIST

CHECKLIST_STATUS: PASS (10/10)

## POSITIVE_CLOSURE
"""
        pac_file = tmp_path / "PAC-TEST-P99.md"
        pac_file.write_text(pac_content)

        violations = lint_status(pac_content, pac_file)

        assert len(violations) >= 1
        assert any("10" in v.message and "13" in v.message for v in violations)

    def test_checklist_missing_canonical_items_fails(self, pac_linter_imports, tmp_path):
        """Checklist missing canonical items must fail."""
        lint_items = pac_linter_imports["lint_items"]

        # Only include 3 items instead of 13
        pac_content = """
# PAC-TEST-P99-MISSING-ITEMS-01

## GOLD_STANDARD_CHECKLIST
[✓] Canonical PAC template used
[✓] Execution lane explicitly declared
[✓] WRAP requirement declared

CHECKLIST_STATUS: PASS (13/13)

## POSITIVE_CLOSURE
"""
        pac_file = tmp_path / "PAC-TEST-P99.md"
        pac_file.write_text(pac_content)

        violations = lint_items(pac_content, pac_file)

        # Should have violations for missing items
        # 13 canonical items - 3 present = at least 9-10 missing (depends on fuzzy matching)
        assert len(violations) >= 9  # Missing at least 9 canonical items
        assert all(v.rule == "pac-gold-standard-checklist-items" for v in violations)

    def test_checklist_unchecked_items_fails(self, pac_linter_imports, tmp_path):
        """Checklist with unchecked items must fail."""
        lint_items = pac_linter_imports["lint_items"]

        # Include unchecked items
        pac_content = """
# PAC-TEST-P99-UNCHECKED-01

## GOLD_STANDARD_CHECKLIST
[✓] Canonical PAC template used
[ ] All gateways (G0–G7) executed in order
[✓] Execution lane explicitly declared
[ ] Agent activation acknowledged (PAG-01)

CHECKLIST_STATUS: PASS (13/13)
"""
        pac_file = tmp_path / "PAC-TEST-P99.md"
        pac_file.write_text(pac_content)

        violations = lint_items(pac_content, pac_file)

        # Unchecked items won't be counted as checked
        assert len(violations) >= 2

    def test_valid_checklist_passes(self, pac_linter_imports, tmp_path):
        """Valid Gold Standard Checklist with all 13 items must pass."""
        lint_present = pac_linter_imports["lint_present"]
        lint_status = pac_linter_imports["lint_status"]
        lint_items = pac_linter_imports["lint_items"]

        pac_content = """
# PAC-TEST-P99-VALID-CHECKLIST-01

## EXECUTING AGENT
ATLAS (GID-11)

## GOLD_STANDARD_CHECKLIST
[✓] Canonical PAC template used
[✓] All gateways (G0–G7) executed in order
[✓] Execution lane explicitly declared
[✓] Agent activation acknowledged (PAG-01)
[✓] Runtime activation acknowledged
[✓] Constraints & guardrails declared
[✓] Tasks scoped and non-expansive
[✓] File scope explicitly bounded
[✓] Fail-closed posture enforced
[✓] WRAP requirement declared
[✓] BER requirement declared (if applicable)
[✓] Human review gate declared (if applicable)
[✓] Ledger mutation explicitly attested

CHECKLIST_STATUS: PASS (13/13)

## POSITIVE_CLOSURE
"""
        pac_file = tmp_path / "PAC-TEST-P99.md"
        pac_file.write_text(pac_content)

        # All lint checks should pass
        violations_present = lint_present(pac_content, pac_file)
        violations_status = lint_status(pac_content, pac_file)
        violations_items = lint_items(pac_content, pac_file)

        assert len(violations_present) == 0, f"Present violations: {violations_present}"
        assert len(violations_status) == 0, f"Status violations: {violations_status}"
        assert len(violations_items) == 0, f"Items violations: {violations_items}"


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
