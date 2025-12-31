"""
Tests for PDO Execution Gate — Core Enforcement Pipeline
════════════════════════════════════════════════════════════════════════════════

Tests that validate:
- INV-PDO-GATE-001: No execution without valid Proof
- INV-PDO-GATE-002: No settlement without valid Decision
- INV-PDO-GATE-003: No outcome without persisted PDO
- INV-PDO-GATE-004: All gates are fail-closed
- INV-PDO-GATE-005: Gate violations produce audit records

PAC Reference: PAC-JEFFREY-CHAINBRIDGE-PDO-CORE-EXEC-005
Effective Date: 2025-12-30
"""

import pytest
import uuid
from datetime import datetime, timezone

from core.governance.pdo_execution_gate import (
    PDOExecutionGate,
    ProofContainer,
    DecisionContainer,
    GateEvaluation,
    GateResult,
    GateBlockReason,
    PDOGateError,
    ProofGateError,
    DecisionGateError,
    OutcomeGateError,
    get_pdo_gate,
    reset_pdo_gate,
    GATE_PROOF,
    GATE_DECISION,
    GATE_OUTCOME,
)
from core.governance.pdo_registry import (
    get_pdo_registry,
    reset_pdo_registry,
)
from core.governance.pdo_artifact import PDO_AUTHORITY


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before each test."""
    reset_pdo_gate()
    reset_pdo_registry()
    yield
    reset_pdo_gate()
    reset_pdo_registry()


@pytest.fixture
def gate():
    """Get fresh PDO execution gate."""
    return PDOExecutionGate()


@pytest.fixture
def valid_proof():
    """Create valid proof container."""
    return ProofContainer(
        pac_id="PAC-TEST-001",
        wrap_id=f"wrap_{uuid.uuid4().hex[:12]}",
        wrap_data={
            "status": "COMPLETE",
            "from_gid": "GID-01",
            "artifacts": ["file1.py", "file2.py"],
        },
    )


@pytest.fixture
def valid_decision(valid_proof):
    """Create valid decision container linked to proof."""
    return DecisionContainer(
        pac_id="PAC-TEST-001",
        ber_id=f"ber_{uuid.uuid4().hex[:12]}",
        ber_data={
            "status": "APPROVE",
            "issuer": "GID-00",
            "decision": "ACCEPTED",
        },
        proof_hash=valid_proof.wrap_hash,
        decision_status="APPROVE",
        issuer=PDO_AUTHORITY,
        rationale="All gates passed",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GATE 1: PROOF GATE TESTS (INV-PDO-GATE-001)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProofGate:
    """Tests for INV-PDO-GATE-001: No execution without valid Proof."""
    
    def test_require_proof_passes_with_valid_proof(self, gate, valid_proof):
        """Valid proof should pass the gate."""
        evaluation = gate.require_proof(valid_proof)
        
        assert evaluation.result == GateResult.PASS
        assert evaluation.gate_id == GATE_PROOF
        assert evaluation.pac_id == valid_proof.pac_id
        assert evaluation.proof_hash == valid_proof.wrap_hash
        assert evaluation.reason is None
    
    def test_require_proof_blocks_when_none(self, gate):
        """No proof should block execution."""
        with pytest.raises(ProofGateError) as exc_info:
            gate.require_proof(None)
        
        assert exc_info.value.reason == GateBlockReason.NO_PROOF
        assert "No proof provided" in str(exc_info.value)
    
    def test_require_proof_blocks_invalid_proof(self, gate):
        """Invalid proof should block execution."""
        invalid_proof = ProofContainer(
            pac_id="",  # Missing PAC ID
            wrap_id="",
            wrap_data={},
        )
        
        with pytest.raises(ProofGateError) as exc_info:
            gate.require_proof(invalid_proof)
        
        assert exc_info.value.reason == GateBlockReason.INVALID_PROOF
    
    def test_proof_gate_records_evaluation(self, gate, valid_proof):
        """Gate should record evaluation in audit trail."""
        gate.require_proof(valid_proof)
        
        evaluations = gate.get_evaluations(gate_id=GATE_PROOF)
        assert len(evaluations) == 1
        assert evaluations[0].result == GateResult.PASS
    
    def test_proof_gate_records_blocked_evaluation(self, gate):
        """Blocked gate should record evaluation."""
        try:
            gate.require_proof(None)
        except ProofGateError:
            pass
        
        blocked = gate.get_blocked_evaluations()
        assert len(blocked) == 1
        assert blocked[0].reason == GateBlockReason.NO_PROOF


# ═══════════════════════════════════════════════════════════════════════════════
# GATE 2: DECISION GATE TESTS (INV-PDO-GATE-002)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecisionGate:
    """Tests for INV-PDO-GATE-002: No settlement without valid Decision."""
    
    def test_require_decision_passes_with_valid_decision(
        self, gate, valid_proof, valid_decision
    ):
        """Valid decision should pass the gate."""
        evaluation = gate.require_decision(valid_decision, valid_proof.wrap_hash)
        
        assert evaluation.result == GateResult.PASS
        assert evaluation.gate_id == GATE_DECISION
        assert evaluation.pac_id == valid_decision.pac_id
        assert evaluation.decision_hash == valid_decision.decision_hash
    
    def test_require_decision_blocks_when_none(self, gate, valid_proof):
        """No decision should block settlement."""
        with pytest.raises(DecisionGateError) as exc_info:
            gate.require_decision(None, valid_proof.wrap_hash)
        
        assert exc_info.value.reason == GateBlockReason.NO_DECISION
    
    def test_require_decision_blocks_invalid_decision(self, gate, valid_proof):
        """Invalid decision should block settlement."""
        invalid_decision = DecisionContainer(
            pac_id="",
            ber_id="",
            ber_data={},
            proof_hash=valid_proof.wrap_hash,
            decision_status="",
        )
        
        with pytest.raises(DecisionGateError) as exc_info:
            gate.require_decision(invalid_decision, valid_proof.wrap_hash)
        
        assert exc_info.value.reason == GateBlockReason.INVALID_DECISION
    
    def test_require_decision_blocks_proof_hash_mismatch(self, gate, valid_proof):
        """Mismatched proof hash should block settlement."""
        decision = DecisionContainer(
            pac_id="PAC-TEST-001",
            ber_id="ber_test",
            ber_data={"status": "APPROVE"},
            proof_hash="wrong_hash_" + "0" * 54,  # Wrong hash
            decision_status="APPROVE",
        )
        
        with pytest.raises(DecisionGateError) as exc_info:
            gate.require_decision(decision, valid_proof.wrap_hash)
        
        assert exc_info.value.reason == GateBlockReason.PROOF_HASH_MISMATCH
    
    def test_require_decision_blocks_non_approved(self, gate, valid_proof):
        """Non-approved decision should block settlement."""
        rejected_decision = DecisionContainer(
            pac_id="PAC-TEST-001",
            ber_id="ber_test",
            ber_data={"status": "REJECT"},
            proof_hash=valid_proof.wrap_hash,
            decision_status="REJECT",  # Not approved
        )
        
        with pytest.raises(DecisionGateError) as exc_info:
            gate.require_decision(rejected_decision, valid_proof.wrap_hash)
        
        assert exc_info.value.reason == GateBlockReason.DECISION_NOT_APPROVED


# ═══════════════════════════════════════════════════════════════════════════════
# GATE 3: OUTCOME GATE TESTS (INV-PDO-GATE-003)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutcomeGate:
    """Tests for INV-PDO-GATE-003: No outcome without persisted PDO."""
    
    def test_require_pdo_blocks_when_not_found(self, gate):
        """Missing PDO should block outcome."""
        with pytest.raises(OutcomeGateError) as exc_info:
            gate.require_pdo("PAC-NONEXISTENT")
        
        assert exc_info.value.reason == GateBlockReason.NO_PDO
    
    def test_require_pdo_passes_when_exists(self, gate, valid_proof, valid_decision):
        """Existing PDO should pass the gate."""
        # First create a PDO through the full pipeline
        pdo = gate.execute_with_pdo(valid_proof, valid_decision, persist=True)
        
        # Now require it
        evaluation, retrieved_pdo = gate.require_pdo(valid_proof.pac_id)
        
        assert evaluation.result == GateResult.PASS
        assert evaluation.gate_id == GATE_OUTCOME
        assert retrieved_pdo.pdo_id == pdo.pdo_id


# ═══════════════════════════════════════════════════════════════════════════════
# FULL PIPELINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullPipeline:
    """Tests for full PDO pipeline execution."""
    
    def test_execute_with_pdo_creates_artifact(self, gate, valid_proof, valid_decision):
        """Full pipeline should create PDO artifact."""
        pdo = gate.execute_with_pdo(valid_proof, valid_decision)
        
        assert pdo is not None
        assert pdo.pac_id == valid_proof.pac_id
        assert pdo.issuer == PDO_AUTHORITY
        assert pdo.outcome_status == "ACCEPTED"
    
    def test_execute_with_pdo_registers_in_registry(
        self, gate, valid_proof, valid_decision
    ):
        """PDO should be registered in registry."""
        pdo = gate.execute_with_pdo(valid_proof, valid_decision, persist=True)
        
        registry = get_pdo_registry()
        retrieved = registry.get_by_pac_id(valid_proof.pac_id)
        
        assert retrieved is not None
        assert retrieved.pdo_id == pdo.pdo_id
    
    def test_execute_with_pdo_no_persist(self, gate, valid_proof, valid_decision):
        """PDO with persist=False should not be registered."""
        pdo = gate.execute_with_pdo(valid_proof, valid_decision, persist=False)
        
        registry = get_pdo_registry()
        retrieved = registry.get_by_pac_id(valid_proof.pac_id)
        
        assert pdo is not None
        assert retrieved is None
    
    def test_execute_with_pdo_fails_on_proof_error(self, gate, valid_decision):
        """Pipeline should fail if proof gate fails."""
        invalid_proof = ProofContainer(
            pac_id="",
            wrap_id="",
            wrap_data={},
        )
        
        with pytest.raises(ProofGateError):
            gate.execute_with_pdo(invalid_proof, valid_decision)
    
    def test_execute_with_pdo_fails_on_decision_error(self, gate, valid_proof):
        """Pipeline should fail if decision gate fails."""
        invalid_decision = DecisionContainer(
            pac_id="PAC-TEST-001",
            ber_id="ber_test",
            ber_data={},
            proof_hash="wrong_hash",
            decision_status="APPROVE",
        )
        
        with pytest.raises(DecisionGateError):
            gate.execute_with_pdo(valid_proof, invalid_decision)


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT TRAIL TESTS (INV-PDO-GATE-005)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditTrail:
    """Tests for gate evaluation audit trail."""
    
    def test_export_audit_trail(self, gate, valid_proof, valid_decision):
        """Audit trail should be exportable."""
        gate.execute_with_pdo(valid_proof, valid_decision)
        
        trail = gate.export_audit_trail()
        
        assert isinstance(trail, list)
        assert len(trail) >= 2  # At least proof + decision gates
    
    def test_audit_contains_all_gates(self, gate, valid_proof, valid_decision):
        """Audit should contain all gate evaluations."""
        gate.execute_with_pdo(valid_proof, valid_decision)
        
        proof_evals = gate.get_evaluations(gate_id=GATE_PROOF)
        decision_evals = gate.get_evaluations(gate_id=GATE_DECISION)
        
        assert len(proof_evals) == 1
        assert len(decision_evals) == 1
    
    def test_blocked_evaluations_tracked(self, gate):
        """All blocked evaluations should be tracked."""
        # Generate some blocked evaluations
        try:
            gate.require_proof(None)
        except ProofGateError:
            pass
        
        try:
            gate.require_pdo("NONEXISTENT")
        except OutcomeGateError:
            pass
        
        blocked = gate.get_blocked_evaluations()
        assert len(blocked) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingleton:
    """Tests for singleton gate access."""
    
    def test_get_pdo_gate_returns_same_instance(self):
        """get_pdo_gate should return singleton."""
        gate1 = get_pdo_gate()
        gate2 = get_pdo_gate()
        
        assert gate1 is gate2
    
    def test_reset_pdo_gate_clears_instance(self):
        """reset_pdo_gate should create new instance."""
        gate1 = get_pdo_gate()
        reset_pdo_gate()
        gate2 = get_pdo_gate()
        
        assert gate1 is not gate2
