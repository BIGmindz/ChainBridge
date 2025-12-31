"""
Test Suite — BER Loop Enforcement (PAC-020)
════════════════════════════════════════════════════════════════════════════════

Tests for BER_LOOP_ENFORCEMENT_LAW_v1.md compliance.

REQUIRED SCENARIOS:
- WRAP without BER → FAIL
- BER always emitted or session terminated
- Drafting surface cannot consume WRAP
- Agent cannot self-issue BER
- Session state machine enforcement

════════════════════════════════════════════════════════════════════════════════
"""

import io
import pytest

from core.governance.ber_loop_enforcer import (
    ALL_TERMINAL_STATES,
    BERLoopEnforcer,
    BERLoopTerminalRenderer,
    BERNotIssuedError,
    BERRequiredError,
    INVALID_TERMINAL_STATES,
    NON_TERMINAL_STATES,
    SessionInvalidError,
    SessionRecord,
    SessionState,
    VALID_TERMINAL_STATES,
    WRAPNotRoutedError,
    get_ber_loop_enforcer,
    is_invalid_terminal_state,
    is_terminal_state,
    is_valid_terminal_state,
    process_wrap_to_ber,
    reset_ber_loop_enforcer,
)
from core.governance.session_state import (
    VALID_TRANSITIONS,
    can_transition_to_terminal,
    is_valid_transition,
    require_valid_terminal,
    require_valid_transition,
    requires_ber,
    ber_was_issued,
    validate_terminal_state,
)
from core.governance.orchestration_engine import (
    DispatchResult,
    DispatchStatus,
    GovernanceOrchestrationEngine,
    LoopState,
    get_orchestration_engine,
    reset_orchestration_engine,
)
from core.governance.pac_schema import (
    BERStatus,
    PACBuilder,
    PACDiscipline,
    PACMode,
    PACSchema,
    WRAPStatus,
)
from core.governance.pac_schema_validator import PACSchemaValidator
from core.governance.system_identities import BERAuthorityError
from core.governance.terminal_gates import TerminalGateRenderer


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_state():
    """Reset singletons before each test."""
    reset_ber_loop_enforcer()
    reset_orchestration_engine()
    yield
    reset_ber_loop_enforcer()
    reset_orchestration_engine()


@pytest.fixture
def enforcer() -> BERLoopEnforcer:
    """Create BER loop enforcer with terminal output disabled."""
    return BERLoopEnforcer(emit_terminal=False)


@pytest.fixture
def buffer():
    """Create StringIO buffer for output capture."""
    return io.StringIO()


@pytest.fixture
def renderer(buffer):
    """Create terminal renderer with buffer."""
    return TerminalGateRenderer(output=buffer)


@pytest.fixture
def valid_pac() -> PACSchema:
    """Create a fully compliant PAC for testing."""
    return (
        PACBuilder()
        .with_id("PAC-TEST-EXEC-BER-LOOP-001")
        .with_issuer("Test")
        .with_target("Test Target")
        .with_mode(PACMode.EXECUTION)
        .with_discipline(PACDiscipline.FAIL_CLOSED)
        .with_objective("Test objective")
        .with_execution_plan("Test plan")
        .add_deliverable("Deliverable 1")
        .add_constraint("Constraint 1")
        .add_success_criterion("Criterion 1")
        .with_dispatch("GID-01", "Role", "LANE", PACMode.EXECUTION)
        .with_wrap_obligation()
        .with_ber_obligation()
        .with_final_state()
        .build()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE ENUM TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionStateEnum:
    """Test SessionState enum definitions."""
    
    def test_terminal_states_defined(self):
        """Terminal states should be defined (PAC-021: BER_EMITTED is terminal)."""
        # PAC-021: BER_ISSUED is no longer terminal (must emit)
        assert SessionState.BER_ISSUED in NON_TERMINAL_STATES
        assert SessionState.BER_EMITTED in VALID_TERMINAL_STATES
        assert SessionState.SESSION_COMPLETE in VALID_TERMINAL_STATES
        assert SessionState.SESSION_INVALID in INVALID_TERMINAL_STATES
    
    def test_non_terminal_states_defined(self):
        """Non-terminal states should be defined."""
        assert SessionState.PAC_RECEIVED in NON_TERMINAL_STATES
        assert SessionState.PAC_DISPATCHED in NON_TERMINAL_STATES
        assert SessionState.WRAP_RECEIVED in NON_TERMINAL_STATES
        assert SessionState.BER_REQUIRED in NON_TERMINAL_STATES
        # PAC-021: BER_ISSUED is non-terminal (must emit)
        assert SessionState.BER_ISSUED in NON_TERMINAL_STATES
    
    def test_ber_required_is_non_terminal(self):
        """BER_REQUIRED must be non-terminal."""
        assert SessionState.BER_REQUIRED in NON_TERMINAL_STATES
        assert SessionState.BER_REQUIRED not in ALL_TERMINAL_STATES
        assert not is_terminal_state(SessionState.BER_REQUIRED)


# ═══════════════════════════════════════════════════════════════════════════════
# STATE MACHINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStateMachine:
    """Test session state machine transitions."""
    
    def test_wrap_received_must_go_to_ber_required(self):
        """WRAP_RECEIVED can only go to BER_REQUIRED or SESSION_INVALID."""
        valid_next = VALID_TRANSITIONS[SessionState.WRAP_RECEIVED]
        assert SessionState.BER_REQUIRED in valid_next
        assert SessionState.SESSION_INVALID in valid_next
        # Cannot skip to BER_ISSUED or SESSION_COMPLETE
        assert SessionState.BER_ISSUED not in valid_next
        assert SessionState.SESSION_COMPLETE not in valid_next
    
    def test_ber_required_must_go_to_ber_issued_or_invalid(self):
        """BER_REQUIRED can only go to BER_ISSUED or SESSION_INVALID."""
        valid_next = VALID_TRANSITIONS[SessionState.BER_REQUIRED]
        assert SessionState.BER_ISSUED in valid_next
        assert SessionState.SESSION_INVALID in valid_next
        # Cannot go to SESSION_COMPLETE directly
        assert SessionState.SESSION_COMPLETE not in valid_next
    
    def test_valid_transition_enforcement(self):
        """is_valid_transition should enforce state machine."""
        # Valid transitions
        assert is_valid_transition(SessionState.WRAP_RECEIVED, SessionState.BER_REQUIRED)
        assert is_valid_transition(SessionState.BER_REQUIRED, SessionState.BER_ISSUED)
        
        # Invalid transitions (skipping BER_REQUIRED)
        assert not is_valid_transition(SessionState.WRAP_RECEIVED, SessionState.BER_ISSUED)
        assert not is_valid_transition(SessionState.WRAP_RECEIVED, SessionState.SESSION_COMPLETE)
    
    def test_require_valid_transition_raises(self):
        """require_valid_transition should raise on invalid."""
        with pytest.raises(ValueError):
            require_valid_transition(SessionState.WRAP_RECEIVED, SessionState.BER_ISSUED)


# ═══════════════════════════════════════════════════════════════════════════════
# BER LOOP ENFORCER — POSITIVE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBERLoopEnforcerPositive:
    """Test BER loop enforcer with valid flows."""
    
    def test_synchronous_wrap_to_ber(self, enforcer):
        """WRAP should synchronously result in BER emission (PAC-021)."""
        pac_id = "PAC-TEST-001"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        
        # Process WRAP synchronously - returns BERArtifact now
        artifact = enforcer.process_wrap_synchronously(
            pac_id, "COMPLETE", "GID-01"
        )
        
        # Get session to check state
        session = enforcer.get_session(pac_id)
        
        # BER should be issued AND emitted (PAC-021)
        assert session.state == SessionState.BER_EMITTED
        assert session.ber_status == "APPROVE"
        assert session.ber_issuer == "GID-00"
        assert artifact.decision == "APPROVE"
    
    def test_wrap_to_ber_required_to_ber_issued(self, enforcer):
        """State should transition: WRAP_RECEIVED → BER_REQUIRED → BER_ISSUED."""
        pac_id = "PAC-TEST-002"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        
        # Receive WRAP (auto-transitions to BER_REQUIRED)
        session = enforcer.receive_wrap(pac_id, "COMPLETE", "GID-01")
        
        # Should be in BER_REQUIRED (intermediate state)
        assert session.state == SessionState.BER_REQUIRED
        
        # Issue BER
        session = enforcer.issue_ber(pac_id, "APPROVE")
        
        # Should be in BER_ISSUED
        assert session.state == SessionState.BER_ISSUED
    
    def test_corrective_ber_for_partial_wrap(self, enforcer):
        """PARTIAL WRAP should result in CORRECTIVE BER."""
        pac_id = "PAC-TEST-003"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        
        artifact = enforcer.process_wrap_synchronously(
            pac_id, "PARTIAL", "GID-01"
        )
        
        # Get session to check state
        session = enforcer.get_session(pac_id)
        
        assert session.ber_status == "CORRECTIVE"
        assert artifact.decision == "CORRECTIVE"


# ═══════════════════════════════════════════════════════════════════════════════
# BER LOOP ENFORCER — NEGATIVE TESTS (WRAP WITHOUT BER)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWRAPWithoutBER:
    """Test that WRAP without BER fails."""
    
    def test_cannot_complete_in_ber_required(self, enforcer):
        """Session cannot complete in BER_REQUIRED state."""
        pac_id = "PAC-TEST-004"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        
        # Receive WRAP without issuing BER
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-01")
        
        # Should be in BER_REQUIRED
        session = enforcer.get_session(pac_id)
        assert session.state == SessionState.BER_REQUIRED
        
        # Attempting to complete should fail
        with pytest.raises(BERRequiredError):
            enforcer.complete_session(pac_id)
    
    def test_ber_required_sessions_detected(self, enforcer):
        """Enforcer should detect sessions awaiting BER."""
        pac_id = "PAC-TEST-005"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-01")
        
        # Should detect BER required
        ber_required = enforcer.get_ber_required_sessions()
        assert len(ber_required) == 1
        assert ber_required[0].pac_id == pac_id
        
        # Enforcement check should fail
        assert enforcer.has_ber_required()
        with pytest.raises(BERNotIssuedError):
            enforcer.enforce_no_ber_required()


# ═══════════════════════════════════════════════════════════════════════════════
# BER LOOP ENFORCER — AUTHORITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBERAuthority:
    """Test that only GID-00 can issue BER."""
    
    def test_agent_cannot_issue_ber(self, enforcer):
        """Agent (GID-01) cannot issue BER."""
        pac_id = "PAC-TEST-006"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-01")
        
        # Agent trying to issue BER should fail
        with pytest.raises(BERAuthorityError):
            enforcer.issue_ber(pac_id, "APPROVE", issuer_gid="GID-01")
    
    def test_only_gid00_can_issue_ber(self, enforcer):
        """Only GID-00 can issue BER."""
        pac_id = "PAC-TEST-007"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-01")
        
        # GID-00 should succeed
        session = enforcer.issue_ber(pac_id, "APPROVE", issuer_gid="GID-00")
        assert session.ber_issuer == "GID-00"


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION ENGINE INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrchestrationEngineIntegration:
    """Test orchestration engine with BER loop enforcement."""
    
    def test_receive_wrap_auto_issues_ber(self, valid_pac):
        """receive_wrap should automatically issue BER (PAC-020)."""
        engine = GovernanceOrchestrationEngine()
        engine._validator = PACSchemaValidator(emit_terminal=False)
        
        # Dispatch PAC
        result = engine.dispatch(valid_pac)
        assert result.success
        
        # Receive WRAP (should auto-issue BER)
        loop = engine.receive_wrap(
            valid_pac.pac_id,
            WRAPStatus.COMPLETE,
            from_gid="GID-01",
        )
        
        # PAC-021: receive_wrap now returns BERArtifact
        # Get loop state separately to check
        loop = engine.get_loop_state(valid_pac.pac_id)
        
        # Loop should be closed (BER auto-issued and emitted)
        assert loop.is_loop_closed
        assert loop.wrap_received
        assert loop.ber_issued
        assert loop.ber_emitted
    
    def test_complete_wrap_gets_approve_ber(self, valid_pac):
        """COMPLETE WRAP should result in APPROVE BER with ACCEPTED PDO."""
        engine = GovernanceOrchestrationEngine()
        engine._validator = PACSchemaValidator(emit_terminal=False)
        
        engine.dispatch(valid_pac)
        artifact = engine.receive_wrap(
            valid_pac.pac_id,
            WRAPStatus.COMPLETE,
            from_gid="GID-01",
        )
        
        # PAC-020: receive_wrap returns PDOArtifact
        assert artifact.outcome_status == "ACCEPTED"  # APPROVE maps to ACCEPTED
        
        # Also check loop state
        loop = engine.get_loop_state(valid_pac.pac_id)
        assert loop.ber_status == BERStatus.APPROVE
        # BERArtifact still available via loop
        assert loop.ber_artifact.decision == BERStatus.APPROVE.value
    
    def test_partial_wrap_gets_corrective_ber(self, valid_pac):
        """PARTIAL WRAP should result in CORRECTIVE BER with CORRECTIVE PDO."""
        engine = GovernanceOrchestrationEngine()
        engine._validator = PACSchemaValidator(emit_terminal=False)
        
        engine.dispatch(valid_pac)
        artifact = engine.receive_wrap(
            valid_pac.pac_id,
            WRAPStatus.PARTIAL,
            from_gid="GID-01",
        )
        
        # PAC-020: receive_wrap returns PDOArtifact
        assert artifact.outcome_status == "CORRECTIVE"
        
        # Also check loop state
        loop = engine.get_loop_state(valid_pac.pac_id)
        assert loop.ber_status == BERStatus.CORRECTIVE
        # BERArtifact still available via loop
        assert loop.ber_artifact.decision == BERStatus.CORRECTIVE.value


# ═══════════════════════════════════════════════════════════════════════════════
# TERMINAL VISIBILITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTerminalVisibility:
    """Test terminal emissions for BER loop enforcement."""
    
    def test_wrap_routing_emission(self, buffer, renderer):
        """WRAP receipt should emit routing notification."""
        ber_renderer = BERLoopTerminalRenderer(renderer)
        enforcer = BERLoopEnforcer(renderer=ber_renderer, emit_terminal=True)
        
        pac_id = "PAC-TEST-008"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-01")
        
        output = buffer.getvalue()
        assert "WRAP RECEIVED" in output
        assert "ORCHESTRATION ENGINE" in output
    
    def test_ber_required_emission(self, buffer, renderer):
        """BER_REQUIRED state should emit notification."""
        ber_renderer = BERLoopTerminalRenderer(renderer)
        enforcer = BERLoopEnforcer(renderer=ber_renderer, emit_terminal=True)
        
        pac_id = "PAC-TEST-009"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-01")
        
        output = buffer.getvalue()
        assert "BER_REQUIRED" in output
    
    def test_ber_issued_loop_closed_emission(self, buffer, renderer):
        """BER issuance and emission should emit visibility notifications (PAC-021)."""
        ber_renderer = BERLoopTerminalRenderer(renderer)
        enforcer = BERLoopEnforcer(renderer=ber_renderer, emit_terminal=True)
        
        pac_id = "PAC-TEST-010"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        enforcer.process_wrap_synchronously(pac_id, "COMPLETE", "GID-01")
        
        output = buffer.getvalue()
        assert "BER ISSUED" in output
        # PAC-021: Now also emits BER EMITTED
        assert "BER EMITTED" in output or "BER_EMITTED" in output
    
    def test_session_invalid_emission(self, buffer, renderer):
        """Session invalidation should emit notification."""
        ber_renderer = BERLoopTerminalRenderer(renderer)
        enforcer = BERLoopEnforcer(renderer=ber_renderer, emit_terminal=True)
        
        pac_id = "PAC-TEST-011"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        enforcer.invalidate_session(pac_id, "Test invalidation")
        
        output = buffer.getvalue()
        assert "SESSION TERMINATED" in output or "SESSION_INVALID" in output


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvariants:
    """Test BER loop enforcement invariants."""
    
    def test_inv_ber_001_wrap_triggers_ber_required(self, enforcer):
        """INV-BER-001: WRAP_RECEIVED → BER_REQUIRED."""
        pac_id = "PAC-TEST-INV-001"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        
        session = enforcer.receive_wrap(pac_id, "COMPLETE", "GID-01")
        
        # After WRAP, must be in BER_REQUIRED
        assert session.state == SessionState.BER_REQUIRED
    
    def test_inv_ber_002_no_awaiting_ber_terminal(self, enforcer):
        """INV-BER-002: No terminal state can be AWAITING_BER."""
        # BER_REQUIRED is not a valid terminal state
        assert not is_terminal_state(SessionState.BER_REQUIRED)
        assert SessionState.BER_REQUIRED not in ALL_TERMINAL_STATES
    
    def test_inv_ber_003_ber_required_non_terminal(self, enforcer):
        """INV-BER-003: BER_REQUIRED is non-terminal."""
        with pytest.raises(ValueError):
            validate_terminal_state(SessionState.BER_REQUIRED)
    
    def test_inv_ber_004_valid_terminal_states_only(self, enforcer):
        """INV-BER-004: Only valid terminal states allowed for completion."""
        pac_id = "PAC-TEST-INV-004"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        enforcer.process_wrap_synchronously(pac_id, "COMPLETE", "GID-01")
        
        session = enforcer.get_session(pac_id)
        
        # Should be in valid terminal state
        assert is_valid_terminal_state(session.state)
    
    def test_inv_ber_005_ber_authority_restricted(self, enforcer):
        """INV-BER-005: Only GID-00 can issue BER."""
        pac_id = "PAC-TEST-INV-005"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-01")
        
        # Non-GID-00 should fail
        for gid in ["GID-01", "GID-02", "DRAFTING_SURFACE"]:
            with pytest.raises(BERAuthorityError):
                enforcer.issue_ber(pac_id, "APPROVE", issuer_gid=gid)
    
    def test_inv_ber_006_loop_closure_mechanical(self, enforcer):
        """INV-BER-006: Loop closure is mechanical (WRAP → BER guaranteed)."""
        pac_id = "PAC-TEST-INV-006"
        enforcer.create_session(pac_id)
        enforcer.dispatch(pac_id)
        
        # Synchronous processing guarantees BER emission (PAC-021)
        artifact = enforcer.process_wrap_synchronously(
            pac_id, "COMPLETE", "GID-01"
        )
        
        # Get session to check state
        session = enforcer.get_session(pac_id)
        
        # PAC-021: BER_EMITTED or SESSION_INVALID — never BER_REQUIRED or BER_ISSUED
        assert session.state in {SessionState.BER_EMITTED, SessionState.SESSION_INVALID}


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    """Test exception behaviors."""
    
    def test_ber_not_issued_error_message(self):
        """BERNotIssuedError should have clear message."""
        error = BERNotIssuedError("TEST-PAC", "Test reason")
        assert "BER_NOT_ISSUED" in str(error)
        assert "TEST-PAC" in str(error)
    
    def test_ber_required_error_message(self):
        """BERRequiredError should have clear message."""
        error = BERRequiredError("TEST-PAC")
        assert "BER_REQUIRED" in str(error)
        assert "TEST-PAC" in str(error)
    
    def test_session_invalid_error_message(self):
        """SessionInvalidError should have clear message."""
        error = SessionInvalidError("TEST-PAC", "Test reason")
        assert "SESSION_INVALID" in str(error)
        assert "TEST-PAC" in str(error)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE HELPER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionStateHelpers:
    """Test session state helper functions."""
    
    def test_requires_ber(self):
        """requires_ber should identify states needing BER."""
        assert requires_ber(SessionState.WRAP_RECEIVED)
        assert requires_ber(SessionState.BER_REQUIRED)
        assert not requires_ber(SessionState.BER_ISSUED)
        assert not requires_ber(SessionState.SESSION_COMPLETE)
    
    def test_ber_was_issued(self):
        """ber_was_issued should identify post-BER states."""
        assert ber_was_issued(SessionState.BER_ISSUED)
        assert ber_was_issued(SessionState.SESSION_COMPLETE)
        assert not ber_was_issued(SessionState.BER_REQUIRED)
        assert not ber_was_issued(SessionState.WRAP_RECEIVED)
    
    def test_can_transition_to_terminal(self):
        """can_transition_to_terminal should be accurate."""
        assert can_transition_to_terminal(SessionState.BER_ISSUED)
        assert can_transition_to_terminal(SessionState.BER_REQUIRED)  # To SESSION_INVALID
        assert not can_transition_to_terminal(SessionState.PAC_RECEIVED)
