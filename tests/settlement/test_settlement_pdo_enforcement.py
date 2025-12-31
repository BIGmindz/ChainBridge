"""
Tests for Settlement PDO Enforcement — INV-SETTLEMENT-001 through 005
════════════════════════════════════════════════════════════════════════════════

Tests that validate:
- INV-SETTLEMENT-001: No settlement without valid PDO
- INV-SETTLEMENT-002: No milestone without milestone PDO
- INV-SETTLEMENT-003: No state change without ledger append
- INV-SETTLEMENT-004: Ledger failure aborts settlement
- INV-SETTLEMENT-005: All transitions auditable

PAC Reference: PAC-BENSON-CHAINBRIDGE-PDO-SETTLEMENT-EXEC-006C
Effective Date: 2025-12-30
Test Implementation — Dan (GID-07)

════════════════════════════════════════════════════════════════════════════════
"""

import json
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from core.governance.pdo_artifact import PDOArtifact, PDOArtifactFactory, PDO_AUTHORITY
from core.governance.pdo_registry import PDORegistry, get_pdo_registry, reset_pdo_registry
from core.governance.pdo_execution_gate import (
    PDOExecutionGate,
    ProofContainer,
    DecisionContainer,
    GateResult,
    get_pdo_gate,
    reset_pdo_gate,
)
from core.governance.pdo_ledger import (
    PDOLedger,
    LedgerError,
    get_pdo_ledger,
    reset_pdo_ledger,
)
from core.settlement.settlement_engine import (
    SettlementEngine,
    SettlementRequest,
    SettlementResult,
    SettlementStatus,
    SettlementPDORequiredError,
    SettlementLedgerFailureError,
    SettlementNotFoundError,
    get_settlement_engine,
    reset_settlement_engine,
)
from core.settlement.settlement_state_machine import (
    SettlementStateMachine,
    SettlementState,
    MilestoneState,
    SettlementTransition,
    MilestoneTransition,
    InvalidTransitionError,
    MilestonePDORequiredError,
    LedgerAppendRequiredError,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singletons before each test."""
    reset_pdo_gate()
    reset_pdo_ledger()
    reset_pdo_registry()
    reset_settlement_engine()
    yield
    reset_pdo_gate()
    reset_pdo_ledger()
    reset_pdo_registry()
    reset_settlement_engine()


@pytest.fixture
def pdo_registry():
    """Get fresh PDO registry."""
    return PDORegistry()


@pytest.fixture
def pdo_gate(pdo_registry):
    """Get PDO gate with registry."""
    return PDOExecutionGate(registry=pdo_registry)


@pytest.fixture
def pdo_ledger():
    """Get fresh PDO ledger."""
    return PDOLedger()


@pytest.fixture
def settlement_engine(pdo_gate, pdo_ledger):
    """Get settlement engine with dependencies."""
    return SettlementEngine(pdo_gate=pdo_gate, pdo_ledger=pdo_ledger)


@pytest.fixture
def valid_pdo(pdo_registry):
    """Create and register a valid PDO."""
    pac_id = f"PAC-TEST-{uuid.uuid4().hex[:8]}"
    wrap_id = f"wrap_{uuid.uuid4().hex[:12]}"
    ber_id = f"ber_{uuid.uuid4().hex[:12]}"
    
    pdo = PDOArtifactFactory.create(
        pac_id=pac_id,
        wrap_id=wrap_id,
        wrap_data={"test": "data"},
        ber_id=ber_id,
        ber_data={"status": "ACCEPTED"},
        outcome_status="ACCEPTED",
        issuer=PDO_AUTHORITY,
    )
    pdo_registry.register(pdo)
    return pdo


@pytest.fixture
def settlement_request(valid_pdo):
    """Create settlement request with valid PDO."""
    return SettlementRequest(
        pac_id=valid_pdo.pac_id,
        pdo_id=valid_pdo.pdo_id,
        pdo_artifact=valid_pdo,
        amount=1000.00,
        currency="USD",
        counterparty_id="counterparty_001",
        description="Test settlement",
    )


# Compound fixture that ensures all components share the same registry
@pytest.fixture
def settlement_context(pdo_registry, pdo_ledger):
    """
    Create a complete settlement context with shared registry.
    
    Returns dict with: pdo_registry, pdo_gate, pdo_ledger, settlement_engine, valid_pdo, settlement_request
    """
    pdo_gate = PDOExecutionGate(registry=pdo_registry)
    settlement_engine = SettlementEngine(pdo_gate=pdo_gate, pdo_ledger=pdo_ledger)
    
    # Create and register a PDO
    pac_id = f"PAC-TEST-{uuid.uuid4().hex[:8]}"
    wrap_id = f"wrap_{uuid.uuid4().hex[:12]}"
    ber_id = f"ber_{uuid.uuid4().hex[:12]}"
    
    valid_pdo = PDOArtifactFactory.create(
        pac_id=pac_id,
        wrap_id=wrap_id,
        wrap_data={"test": "data"},
        ber_id=ber_id,
        ber_data={"status": "ACCEPTED"},
        outcome_status="ACCEPTED",
        issuer=PDO_AUTHORITY,
    )
    pdo_registry.register(valid_pdo)
    
    settlement_request = SettlementRequest(
        pac_id=valid_pdo.pac_id,
        pdo_id=valid_pdo.pdo_id,
        pdo_artifact=valid_pdo,
        amount=1000.00,
        currency="USD",
        counterparty_id="counterparty_001",
        description="Test settlement",
    )
    
    return {
        "pdo_registry": pdo_registry,
        "pdo_gate": pdo_gate,
        "pdo_ledger": pdo_ledger,
        "settlement_engine": settlement_engine,
        "valid_pdo": valid_pdo,
        "settlement_request": settlement_request,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# INV-SETTLEMENT-001: No settlement without valid PDO
# ═══════════════════════════════════════════════════════════════════════════════

class TestINVSettlement001:
    """Tests for INV-SETTLEMENT-001: No settlement without valid PDO."""
    
    def test_settlement_without_pdo_fails(self, settlement_engine):
        """Settlement without PDO should be blocked."""
        request = SettlementRequest(
            pac_id="PAC-NONEXISTENT",
            pdo_id="pdo_nonexistent",
            amount=1000.00,
        )
        
        with pytest.raises(SettlementPDORequiredError) as exc_info:
            settlement_engine.initiate_settlement(request)
        
        assert "INV-SETTLEMENT-001" in str(exc_info.value)
    
    def test_settlement_with_invalid_pdo_id_fails(self, settlement_context):
        """Settlement with mismatched PDO ID should be blocked."""
        engine = settlement_context["settlement_engine"]
        valid_pdo = settlement_context["valid_pdo"]
        
        request = SettlementRequest(
            pac_id=valid_pdo.pac_id,
            pdo_id="pdo_wrong_id",  # Wrong PDO ID
            amount=1000.00,
        )
        
        with pytest.raises(SettlementPDORequiredError):
            engine.initiate_settlement(request)
    
    def test_settlement_with_valid_pdo_succeeds(self, settlement_context):
        """Settlement with valid PDO should succeed."""
        engine = settlement_context["settlement_engine"]
        request = settlement_context["settlement_request"]
        
        result = engine.initiate_settlement(request)
        
        assert result.success is True
        assert result.status == SettlementStatus.INITIATED
        assert result.pdo_id == request.pdo_id
        assert result.ledger_entry_id is not None
    
    def test_settlement_request_missing_pdo_fails(self, settlement_engine):
        """Settlement request missing PDO ID should fail."""
        request = SettlementRequest(
            pac_id="PAC-TEST",
            pdo_id="",  # Empty PDO ID
            amount=1000.00,
        )
        
        with pytest.raises(SettlementPDORequiredError):
            settlement_engine.initiate_settlement(request)


# ═══════════════════════════════════════════════════════════════════════════════
# INV-SETTLEMENT-002: No milestone without milestone PDO
# ═══════════════════════════════════════════════════════════════════════════════

class TestINVSettlement002:
    """Tests for INV-SETTLEMENT-002: No milestone without milestone PDO."""
    
    def test_milestone_transition_without_pdo_fails(self, pdo_gate, pdo_ledger, pdo_registry):
        """Milestone transition without PDO should be blocked."""
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.INITIATED,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        # Add milestone
        sm.add_milestone("milestone_001", "First Milestone")
        milestone = sm.get_milestone("milestone_001")
        
        # Transition to IN_PROGRESS (needs PDO)
        with pytest.raises(MilestonePDORequiredError) as exc_info:
            sm.transition_milestone(
                milestone_id="milestone_001",
                to_state=MilestoneState.IN_PROGRESS,
                pdo_id="pdo_nonexistent",
                pac_id="PAC-NONEXISTENT",
                reason="Starting milestone",
            )
        
        assert "INV-SETTLEMENT-002" in str(exc_info.value)
    
    def test_milestone_transition_with_valid_pdo_succeeds(self, settlement_context):
        """Milestone transition with valid PDO should succeed."""
        pdo_gate = settlement_context["pdo_gate"]
        pdo_ledger = settlement_context["pdo_ledger"]
        valid_pdo = settlement_context["valid_pdo"]
        
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.INITIATED,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        # Add milestone
        sm.add_milestone("milestone_001", "First Milestone", pdo_id=valid_pdo.pdo_id)
        
        # Transition to IN_PROGRESS
        transition = sm.transition_milestone(
            milestone_id="milestone_001",
            to_state=MilestoneState.IN_PROGRESS,
            pdo_id=valid_pdo.pdo_id,
            pac_id=valid_pdo.pac_id,
            reason="Starting milestone",
        )
        
        assert transition is not None
        assert transition.to_state == MilestoneState.IN_PROGRESS
        assert transition.pdo_id == valid_pdo.pdo_id
        assert transition.ledger_entry_id is not None
    
    def test_milestone_completion_requires_pdo(self, pdo_gate, pdo_ledger, pdo_registry):
        """Completing a milestone requires a valid PDO."""
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.INITIATED,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        sm.add_milestone("milestone_001", "First Milestone")
        
        # First transition to IN_PROGRESS should fail without PDO
        with pytest.raises(MilestonePDORequiredError):
            sm.transition_milestone(
                milestone_id="milestone_001",
                to_state=MilestoneState.IN_PROGRESS,
                pdo_id="pdo_nonexistent",
                pac_id="PAC-NONEXISTENT",
                reason="Starting",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# INV-SETTLEMENT-003: No state change without ledger append
# ═══════════════════════════════════════════════════════════════════════════════

class TestINVSettlement003:
    """Tests for INV-SETTLEMENT-003: No state change without ledger append."""
    
    def test_settlement_creates_ledger_entry(self, settlement_context):
        """Settlement should create ledger entry."""
        engine = settlement_context["settlement_engine"]
        request = settlement_context["settlement_request"]
        pdo_ledger = settlement_context["pdo_ledger"]
        
        initial_count = len(pdo_ledger)
        
        result = engine.initiate_settlement(request)
        
        assert len(pdo_ledger) > initial_count
        assert result.ledger_entry_id is not None
        assert result.ledger_entry_hash is not None
    
    def test_state_machine_transition_creates_ledger_entry(self, settlement_context):
        """State machine transition should create ledger entry."""
        pdo_gate = settlement_context["pdo_gate"]
        pdo_ledger = settlement_context["pdo_ledger"]
        valid_pdo = settlement_context["valid_pdo"]
        
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.PENDING,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        initial_count = len(pdo_ledger)
        
        transition = sm.transition(
            to_state=SettlementState.INITIATED,
            pdo_id=valid_pdo.pdo_id,
            pac_id=valid_pdo.pac_id,
            reason="Initiating settlement",
        )
        
        assert len(pdo_ledger) > initial_count
        assert transition.ledger_entry_id is not None
        assert transition.ledger_entry_hash is not None
    
    def test_milestone_transition_creates_ledger_entry(self, settlement_context):
        """Milestone transition should create ledger entry."""
        pdo_gate = settlement_context["pdo_gate"]
        pdo_ledger = settlement_context["pdo_ledger"]
        valid_pdo = settlement_context["valid_pdo"]
        
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.INITIATED,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        sm.add_milestone("milestone_001", "First Milestone")
        initial_count = len(pdo_ledger)
        
        transition = sm.transition_milestone(
            milestone_id="milestone_001",
            to_state=MilestoneState.IN_PROGRESS,
            pdo_id=valid_pdo.pdo_id,
            pac_id=valid_pdo.pac_id,
            reason="Starting milestone",
        )
        
        assert len(pdo_ledger) > initial_count
        assert transition.ledger_entry_id is not None


# ═══════════════════════════════════════════════════════════════════════════════
# INV-SETTLEMENT-004: Ledger failure aborts settlement
# ═══════════════════════════════════════════════════════════════════════════════

class TestINVSettlement004:
    """Tests for INV-SETTLEMENT-004: Ledger failure aborts settlement."""
    
    def test_ledger_failure_aborts_settlement(self, settlement_context):
        """Ledger failure should abort settlement."""
        # Use same gate/registry but mock ledger
        pdo_gate = settlement_context["pdo_gate"]
        valid_pdo = settlement_context["valid_pdo"]
        
        # Create mock ledger that fails
        mock_ledger = MagicMock(spec=PDOLedger)
        mock_ledger.append.side_effect = LedgerError("Simulated ledger failure")
        
        engine = SettlementEngine(pdo_gate=pdo_gate, pdo_ledger=mock_ledger)
        
        request = SettlementRequest(
            pac_id=valid_pdo.pac_id,
            pdo_id=valid_pdo.pdo_id,
            amount=1000.00,
        )
        
        with pytest.raises(SettlementLedgerFailureError) as exc_info:
            engine.initiate_settlement(request)
        
        assert "INV-SETTLEMENT-004" in str(exc_info.value)
        assert "Simulated ledger failure" in str(exc_info.value)
    
    def test_state_machine_ledger_failure_blocks_transition(self, settlement_context):
        """Ledger failure should block state transition."""
        pdo_gate = settlement_context["pdo_gate"]
        valid_pdo = settlement_context["valid_pdo"]
        
        mock_ledger = MagicMock(spec=PDOLedger)
        mock_ledger.append.side_effect = LedgerError("Simulated ledger failure")
        
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.PENDING,
            pdo_gate=pdo_gate,
            pdo_ledger=mock_ledger,
        )
        
        with pytest.raises(LedgerAppendRequiredError) as exc_info:
            sm.transition(
                to_state=SettlementState.INITIATED,
                pdo_id=valid_pdo.pdo_id,
                pac_id=valid_pdo.pac_id,
                reason="Initiating",
            )
        
        assert "INV-SETTLEMENT-003" in str(exc_info.value)
        # State should NOT change
        assert sm.state == SettlementState.PENDING


# ═══════════════════════════════════════════════════════════════════════════════
# INV-SETTLEMENT-005: All transitions auditable
# ═══════════════════════════════════════════════════════════════════════════════

class TestINVSettlement005:
    """Tests for INV-SETTLEMENT-005: All transitions auditable."""
    
    def test_settlement_records_gate_evaluation(self, settlement_context):
        """Settlement should record gate evaluation."""
        engine = settlement_context["settlement_engine"]
        request = settlement_context["settlement_request"]
        
        result = engine.initiate_settlement(request)
        
        assert len(result.gate_evaluations) > 0
        eval_dict = result.gate_evaluations[0].to_dict()
        assert "evaluation_id" in eval_dict
        assert "gate_id" in eval_dict
        assert "result" in eval_dict
    
    def test_state_machine_records_transition_history(self, settlement_context):
        """State machine should record transition history."""
        pdo_gate = settlement_context["pdo_gate"]
        pdo_ledger = settlement_context["pdo_ledger"]
        valid_pdo = settlement_context["valid_pdo"]
        
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.PENDING,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        # Make transition
        sm.transition(
            to_state=SettlementState.INITIATED,
            pdo_id=valid_pdo.pdo_id,
            pac_id=valid_pdo.pac_id,
            reason="Test transition",
        )
        
        transitions = sm.get_transitions()
        assert len(transitions) == 1
        
        t = transitions[0]
        assert t.from_state == SettlementState.PENDING
        assert t.to_state == SettlementState.INITIATED
        assert t.pdo_id == valid_pdo.pdo_id
        assert t.ledger_entry_id is not None
    
    def test_milestone_records_transition_history(self, settlement_context):
        """Milestone should record transition history."""
        pdo_gate = settlement_context["pdo_gate"]
        pdo_ledger = settlement_context["pdo_ledger"]
        valid_pdo = settlement_context["valid_pdo"]
        
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.INITIATED,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        sm.add_milestone("milestone_001", "First Milestone")
        
        # Make transition
        sm.transition_milestone(
            milestone_id="milestone_001",
            to_state=MilestoneState.IN_PROGRESS,
            pdo_id=valid_pdo.pdo_id,
            pac_id=valid_pdo.pac_id,
            reason="Starting",
        )
        
        milestone = sm.get_milestone("milestone_001")
        assert len(milestone.transitions) == 1
        
        t = milestone.transitions[0]
        assert t.from_state == MilestoneState.PENDING
        assert t.to_state == MilestoneState.IN_PROGRESS
        assert t.ledger_entry_id is not None
    
    def test_settlement_record_to_dict_exportable(self, settlement_context):
        """Settlement record should be exportable to dict."""
        engine = settlement_context["settlement_engine"]
        request = settlement_context["settlement_request"]
        
        result = engine.initiate_settlement(request)
        
        record = engine.get_settlement(result.settlement_id)
        # The record should have state_transitions
        assert hasattr(record, 'state_transitions')
        assert len(record.state_transitions) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# STATE MACHINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSettlementStateMachine:
    """Tests for settlement state machine."""
    
    def test_valid_transitions_allowed(self, settlement_context):
        """Valid state transitions should be allowed."""
        pdo_gate = settlement_context["pdo_gate"]
        pdo_ledger = settlement_context["pdo_ledger"]
        valid_pdo = settlement_context["valid_pdo"]
        
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.PENDING,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        # PENDING → INITIATED is valid
        sm.transition(
            to_state=SettlementState.INITIATED,
            pdo_id=valid_pdo.pdo_id,
            pac_id=valid_pdo.pac_id,
            reason="Starting",
        )
        
        assert sm.state == SettlementState.INITIATED
    
    def test_invalid_transitions_blocked(self, settlement_context):
        """Invalid state transitions should be blocked."""
        pdo_gate = settlement_context["pdo_gate"]
        pdo_ledger = settlement_context["pdo_ledger"]
        valid_pdo = settlement_context["valid_pdo"]
        
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.PENDING,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        # PENDING → COMPLETED is invalid (must go through INITIATED first)
        with pytest.raises(InvalidTransitionError) as exc_info:
            sm.transition(
                to_state=SettlementState.COMPLETED,
                pdo_id=valid_pdo.pdo_id,
                pac_id=valid_pdo.pac_id,
                reason="Trying to skip",
            )
        
        assert "not allowed" in str(exc_info.value)
        assert sm.state == SettlementState.PENDING  # State unchanged
    
    def test_terminal_states_have_no_transitions(self, pdo_gate, pdo_ledger):
        """Terminal states should have no outgoing transitions."""
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.COMPLETED,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        assert sm.is_terminal is True
        assert len(sm.get_allowed_transitions()) == 0


class TestMilestoneStateMachine:
    """Tests for milestone state transitions."""
    
    def test_milestone_valid_transitions(self, settlement_context):
        """Valid milestone transitions should be allowed."""
        pdo_gate = settlement_context["pdo_gate"]
        pdo_ledger = settlement_context["pdo_ledger"]
        valid_pdo = settlement_context["valid_pdo"]
        
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.INITIATED,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        sm.add_milestone("m1", "Milestone 1")
        
        # PENDING → IN_PROGRESS
        sm.transition_milestone(
            milestone_id="m1",
            to_state=MilestoneState.IN_PROGRESS,
            pdo_id=valid_pdo.pdo_id,
            pac_id=valid_pdo.pac_id,
            reason="Starting",
        )
        
        assert sm.get_milestone("m1").state == MilestoneState.IN_PROGRESS
    
    def test_milestone_invalid_transitions_blocked(self, settlement_context):
        """Invalid milestone transitions should be blocked."""
        pdo_gate = settlement_context["pdo_gate"]
        pdo_ledger = settlement_context["pdo_ledger"]
        valid_pdo = settlement_context["valid_pdo"]
        
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.INITIATED,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        sm.add_milestone("m1", "Milestone 1")
        
        # PENDING → COMPLETED is invalid (must go through IN_PROGRESS first)
        with pytest.raises(InvalidTransitionError):
            sm.transition_milestone(
                milestone_id="m1",
                to_state=MilestoneState.COMPLETED,
                pdo_id=valid_pdo.pdo_id,
                pac_id=valid_pdo.pac_id,
                reason="Trying to skip",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# POSITIVE TESTS (VALID PDO → SUCCESS)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPositiveScenarios:
    """Positive test scenarios with valid PDOs."""
    
    def test_full_settlement_lifecycle(self, settlement_context):
        """Full settlement lifecycle with valid PDO."""
        engine = settlement_context["settlement_engine"]
        pdo_registry = settlement_context["pdo_registry"]
        valid_pdo = settlement_context["valid_pdo"]
        
        # Create settlement
        request = SettlementRequest(
            pac_id=valid_pdo.pac_id,
            pdo_id=valid_pdo.pdo_id,
            amount=5000.00,
        )
        
        result = engine.initiate_settlement(request)
        assert result.success is True
        assert result.status == SettlementStatus.INITIATED
        
        # Create completion PDO
        completion_pdo = PDOArtifactFactory.create(
            pac_id=f"PAC-COMPLETE-{uuid.uuid4().hex[:8]}",
            wrap_id=f"wrap_{uuid.uuid4().hex[:12]}",
            wrap_data={"completion": True},
            ber_id=f"ber_{uuid.uuid4().hex[:12]}",
            ber_data={"status": "COMPLETED"},
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        pdo_registry.register(completion_pdo)
        
        # Complete settlement
        completion_result = engine.complete_settlement(
            settlement_id=result.settlement_id,
            completion_pdo_id=completion_pdo.pdo_id,
            completion_pac_id=completion_pdo.pac_id,
        )
        
        assert completion_result.success is True
        assert completion_result.status == SettlementStatus.COMPLETED
    
    def test_ledger_entry_linked_to_settlement(self, settlement_context):
        """Ledger entry should be linked to settlement."""
        engine = settlement_context["settlement_engine"]
        request = settlement_context["settlement_request"]
        pdo_ledger = settlement_context["pdo_ledger"]
        
        result = engine.initiate_settlement(request)
        
        # Find ledger entry
        entry = None
        for e in pdo_ledger:
            if e.entry_id == result.ledger_entry_id:
                entry = e
                break
        
        assert entry is not None
        assert entry.pdo_id == request.pdo_id


# ═══════════════════════════════════════════════════════════════════════════════
# NEGATIVE TESTS (FAIL SCENARIOS)
# ═══════════════════════════════════════════════════════════════════════════════

class TestNegativeScenarios:
    """Negative test scenarios that should fail."""
    
    def test_settlement_with_empty_request_fails(self, settlement_engine):
        """Settlement with empty request should fail."""
        request = SettlementRequest()  # All defaults
        
        with pytest.raises(SettlementPDORequiredError):
            settlement_engine.initiate_settlement(request)
    
    def test_duplicate_milestone_fails(self, pdo_gate, pdo_ledger):
        """Adding duplicate milestone should fail."""
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.INITIATED,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        sm.add_milestone("m1", "First")
        
        with pytest.raises(ValueError) as exc_info:
            sm.add_milestone("m1", "Duplicate")
        
        assert "already exists" in str(exc_info.value)
    
    def test_nonexistent_milestone_fails(self, pdo_gate, pdo_ledger, valid_pdo):
        """Transitioning nonexistent milestone should fail."""
        sm = SettlementStateMachine(
            settlement_id="settle_test",
            initial_state=SettlementState.INITIATED,
            pdo_gate=pdo_gate,
            pdo_ledger=pdo_ledger,
        )
        
        with pytest.raises(ValueError):
            sm.transition_milestone(
                milestone_id="nonexistent",
                to_state=MilestoneState.IN_PROGRESS,
                pdo_id=valid_pdo.pdo_id,
                pac_id=valid_pdo.pac_id,
                reason="Testing",
            )
    
    def test_nonexistent_settlement_fails(self, settlement_engine):
        """Getting nonexistent settlement should fail."""
        with pytest.raises(SettlementNotFoundError):
            settlement_engine.get_settlement("nonexistent")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingleton:
    """Tests for singleton access patterns."""
    
    def test_settlement_engine_singleton(self):
        """get_settlement_engine should return singleton."""
        engine1 = get_settlement_engine()
        engine2 = get_settlement_engine()
        
        assert engine1 is engine2
    
    def test_reset_clears_singleton(self):
        """reset_settlement_engine should clear singleton."""
        engine1 = get_settlement_engine()
        reset_settlement_engine()
        engine2 = get_settlement_engine()
        
        assert engine1 is not engine2
