"""
PAC-021: BER Emission Enforcement Tests
════════════════════════════════════════════════════════════════════════════════

Tests verifying that BER is not only issued internally but EMITTED externally.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-BER-EMISSION-ENFORCEMENT-021
Effective Date: 2025-12-26

INVARIANTS TESTED:
- INV-BER-007: BER must be externally emitted (not just internally issued)
- INV-BER-008: Drafting surfaces prohibited from BER flow

FAILURE MODES ELIMINATED:
- BER issued but never emitted → User never sees BER
- Internal completion without external visibility
- Drafting surface attempting BER emission

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from core.governance.ber_loop_enforcer import (
    BERArtifact,
    BERLoopEnforcer,
    BERLoopTerminalRenderer,
    BERNotEmittedError,
    BERNotIssuedError,
    BERRequiredError,
    DraftingSurfaceInBERFlowError,
    SessionInvalidError,
    SessionRecord,
    SessionState,
    VALID_TERMINAL_STATES,
    NON_TERMINAL_STATES,
    get_ber_loop_enforcer,
    reset_ber_loop_enforcer,
    process_wrap_to_ber,
)
from core.governance.orchestration_engine import (
    BERStatus,
    GovernanceOrchestrationEngine,
    LoopState,
    WRAPStatus,
    get_orchestration_engine,
    reset_orchestration_engine,
)
from core.governance.pac_schema import (
    PACBuilder,
    PACDiscipline,
    PACMode,
)
from core.governance.system_identities import BERAuthorityError


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def enforcer():
    """Create fresh BER loop enforcer."""
    reset_ber_loop_enforcer()
    return BERLoopEnforcer(emit_terminal=False)


@pytest.fixture
def engine():
    """Create fresh orchestration engine."""
    reset_orchestration_engine()
    return GovernanceOrchestrationEngine()


@pytest.fixture
def sample_pac():
    """Create a valid PAC for testing."""
    return (
        PACBuilder()
        .with_id("PAC-TEST-021")
        .with_issuer("Jeffrey")
        .with_target("BENSON")
        .with_mode(PACMode.EXECUTION)
        .with_discipline(PACDiscipline.FAIL_CLOSED)
        .with_objective("Test BER emission enforcement")
        .with_execution_plan("Execute PAC-021 BER emission tests")
        .add_deliverable("Test emission")
        .add_deliverable("Verify artifact")
        .add_constraint("BER must be emitted externally")
        .add_success_criterion("All tests pass")
        .with_dispatch("GID-99", "TEST_AGENT", "testing", PACMode.EXECUTION)
        .with_wrap_obligation()
        .with_ber_obligation()
        .with_final_state()
        .build()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAC-021 CORE INVARIANTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBEREmissionState:
    """Test BER_EMITTED state exists and is required."""
    
    def test_ber_emitted_state_exists(self):
        """BER_EMITTED state must exist in SessionState enum."""
        assert hasattr(SessionState, "BER_EMITTED")
        assert SessionState.BER_EMITTED.value == "BER_EMITTED"
    
    def test_ber_emitted_is_terminal(self):
        """BER_EMITTED is a valid terminal state."""
        assert SessionState.BER_EMITTED in VALID_TERMINAL_STATES
    
    def test_ber_issued_is_not_terminal(self):
        """BER_ISSUED is NOT a terminal state (must emit)."""
        assert SessionState.BER_ISSUED in NON_TERMINAL_STATES
        assert SessionState.BER_ISSUED not in VALID_TERMINAL_STATES
    
    def test_session_cannot_complete_from_ber_issued(self, enforcer):
        """Session cannot skip BER_EMITTED state."""
        pac_id = "PAC-EMIT-001"
        
        # Setup session to BER_ISSUED
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        enforcer.issue_ber(pac_id, "APPROVE")
        
        session = enforcer.get_session(pac_id)
        assert session.state == SessionState.BER_ISSUED
        
        # Cannot complete from BER_ISSUED - must emit first
        with pytest.raises(BERNotEmittedError):
            enforcer.complete_session(pac_id)


class TestBERArtifact:
    """Test BERArtifact is created and returned."""
    
    def test_artifact_is_frozen(self):
        """BERArtifact must be immutable."""
        artifact = BERArtifact(
            pac_id="PAC-TEST",
            decision="APPROVE",
            issuer="GID-00",
            issued_at=datetime.now(timezone.utc).isoformat(),
            emitted_at=datetime.now(timezone.utc).isoformat(),
            wrap_status="COMPLETE",
            session_state="BER_EMITTED",
        )
        
        # Cannot modify frozen dataclass
        with pytest.raises(Exception):  # FrozenInstanceError
            artifact.pac_id = "CHANGED"
    
    def test_artifact_has_required_fields(self):
        """BERArtifact has all required fields."""
        now = datetime.now(timezone.utc).isoformat()
        artifact = BERArtifact(
            pac_id="PAC-TEST",
            decision="APPROVE",
            issuer="GID-00",
            issued_at=now,
            emitted_at=now,
            wrap_status="COMPLETE",
            session_state="BER_EMITTED",
        )
        
        assert artifact.pac_id == "PAC-TEST"
        assert artifact.decision == "APPROVE"
        assert artifact.issuer == "GID-00"
        assert artifact.issued_at == now
        assert artifact.emitted_at == now
        assert artifact.wrap_status == "COMPLETE"
        assert artifact.session_state == "BER_EMITTED"
    
    def test_artifact_is_approved(self):
        """BERArtifact.is_approved property works."""
        now = datetime.now(timezone.utc).isoformat()
        artifact = BERArtifact(
            pac_id="PAC-TEST",
            decision="APPROVE",
            issuer="GID-00",
            issued_at=now,
            emitted_at=now,
            wrap_status="COMPLETE",
            session_state="BER_EMITTED",
        )
        
        assert artifact.is_approved is True
    
    def test_artifact_is_emitted(self):
        """BERArtifact.is_emitted property works."""
        now = datetime.now(timezone.utc).isoformat()
        artifact = BERArtifact(
            pac_id="PAC-TEST",
            decision="APPROVE",
            issuer="GID-00",
            issued_at=now,
            emitted_at=now,
            wrap_status="COMPLETE",
            session_state="BER_EMITTED",
        )
        
        assert artifact.is_emitted is True


# ═══════════════════════════════════════════════════════════════════════════════
# INV-BER-007: BER MUST BE EXTERNALLY EMITTED
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvBer007:
    """Test INV-BER-007: BER must be externally emitted."""
    
    def test_emit_ber_returns_artifact(self, enforcer):
        """emit_ber() must return BERArtifact."""
        pac_id = "PAC-007-001"
        
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        enforcer.issue_ber(pac_id, "APPROVE")
        
        artifact = enforcer.emit_ber(pac_id)
        
        assert isinstance(artifact, BERArtifact)
        assert artifact.pac_id == pac_id
        assert artifact.decision == "APPROVE"
    
    def test_issue_and_emit_ber_returns_artifact(self, enforcer):
        """issue_and_emit_ber() must return BERArtifact."""
        pac_id = "PAC-007-002"
        
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        
        artifact = enforcer.issue_and_emit_ber(pac_id, "APPROVE")
        
        assert isinstance(artifact, BERArtifact)
        assert artifact.pac_id == pac_id
    
    def test_process_wrap_synchronously_returns_artifact(self, enforcer):
        """process_wrap_synchronously() must return BERArtifact."""
        pac_id = "PAC-007-003"
        
        enforcer.dispatch(pac_id)
        artifact = enforcer.process_wrap_synchronously(pac_id, "COMPLETE", "GID-99")
        
        assert isinstance(artifact, BERArtifact)
        assert artifact.pac_id == pac_id
    
    def test_convenience_function_returns_artifact(self):
        """process_wrap_to_ber() must return BERArtifact."""
        reset_ber_loop_enforcer()
        enforcer = get_ber_loop_enforcer()
        enforcer._emit_terminal = False
        
        pac_id = "PAC-007-004"
        enforcer.dispatch(pac_id)
        
        artifact = process_wrap_to_ber(pac_id, "COMPLETE", "GID-99")
        
        assert isinstance(artifact, BERArtifact)
    
    def test_session_records_emission(self, enforcer):
        """Session record must track BER emission."""
        pac_id = "PAC-007-005"
        
        enforcer.dispatch(pac_id)
        enforcer.process_wrap_synchronously(pac_id, "COMPLETE", "GID-99")
        
        session = enforcer.get_session(pac_id)
        
        assert session.ber_emitted is True
        assert session.ber_emitted_at is not None
        assert session.state == SessionState.BER_EMITTED
    
    def test_ber_issued_not_emitted_detected(self, enforcer):
        """Session can detect BER issued but not emitted."""
        pac_id = "PAC-007-006"
        
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        enforcer.issue_ber(pac_id, "APPROVE")
        
        session = enforcer.get_session(pac_id)
        
        assert session.is_ber_issued_not_emitted is True
        assert session.ber_emitted is False


# ═══════════════════════════════════════════════════════════════════════════════
# INV-BER-008: DRAFTING SURFACES PROHIBITED FROM BER FLOW
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvBer008:
    """Test INV-BER-008: Drafting surfaces prohibited from BER flow."""
    
    def test_drafting_surface_cannot_emit_ber(self, enforcer):
        """Drafting surface attempting BER emission raises error."""
        pac_id = "PAC-008-001"
        
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        enforcer.issue_ber(pac_id, "APPROVE", "GID-00")
        
        with pytest.raises(DraftingSurfaceInBERFlowError):
            enforcer.emit_ber(pac_id, issuer_gid="DRAFTING_SURFACE")
    
    def test_drafting_surface_error_contains_surface_id(self, enforcer):
        """DraftingSurfaceInBERFlowError contains surface ID."""
        pac_id = "PAC-008-002"
        
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        enforcer.issue_ber(pac_id, "APPROVE", "GID-00")
        
        try:
            enforcer.emit_ber(pac_id, issuer_gid="DRAFTING_UI")
            pytest.fail("Should have raised DraftingSurfaceInBERFlowError")
        except DraftingSurfaceInBERFlowError as e:
            assert "DRAFTING_UI" in str(e)
    
    def test_agent_cannot_emit_ber(self, enforcer):
        """Agent attempting BER emission raises BERAuthorityError."""
        pac_id = "PAC-008-003"
        
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        enforcer.issue_ber(pac_id, "APPROVE", "GID-00")
        
        with pytest.raises(BERAuthorityError):
            enforcer.emit_ber(pac_id, issuer_gid="GID-99")
    
    def test_only_gid_00_can_emit_ber(self, enforcer):
        """Only GID-00 (ORCHESTRATION_ENGINE) can emit BER."""
        pac_id = "PAC-008-004"
        
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        enforcer.issue_ber(pac_id, "APPROVE", "GID-00")
        
        # GID-00 should succeed
        artifact = enforcer.emit_ber(pac_id, issuer_gid="GID-00")
        
        assert artifact is not None
        assert artifact.issuer == "GID-00"


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION ENGINE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrchestrationEngineEmission:
    """Test orchestration engine returns PDOArtifact (PAC-020) with BER info."""
    
    def test_receive_wrap_returns_artifact(self, engine, sample_pac):
        """receive_wrap() must return PDOArtifact (PAC-020 upgrade)."""
        from core.governance.pdo_artifact import PDOArtifact
        
        result = engine.dispatch(sample_pac)
        assert result.success
        
        artifact = engine.receive_wrap(
            result.pac_id,
            WRAPStatus.COMPLETE,
            "GID-99",
        )
        
        # PAC-020: Now returns PDOArtifact instead of BERArtifact
        assert isinstance(artifact, PDOArtifact)
        assert artifact.pac_id == result.pac_id
        assert artifact.outcome_status == "ACCEPTED"  # APPROVE maps to ACCEPTED
        
        # BERArtifact still available via loop state
        loop = engine.get_loop_state(result.pac_id)
        assert loop.ber_artifact is not None
        assert loop.ber_artifact.decision == "APPROVE"
    
    def test_issue_and_emit_ber_returns_artifact(self, engine, sample_pac):
        """issue_and_emit_ber() must return PDOArtifact (PAC-020 upgrade)."""
        from core.governance.pdo_artifact import PDOArtifact
        
        result = engine.dispatch(sample_pac)
        assert result.success
        
        # Manually receive WRAP without auto-BER
        engine.receive_wrap_without_auto_ber(result.pac_id, WRAPStatus.COMPLETE)
        
        artifact = engine.issue_and_emit_ber(result.pac_id, BERStatus.APPROVE)
        
        # PAC-020: Now returns PDOArtifact instead of BERArtifact
        assert isinstance(artifact, PDOArtifact)
        assert artifact.pac_id == result.pac_id
        assert artifact.outcome_status == "ACCEPTED"
    
    def test_loop_state_tracks_emission(self, engine, sample_pac):
        """LoopState must track BER emission."""
        result = engine.dispatch(sample_pac)
        
        artifact = engine.receive_wrap(result.pac_id, WRAPStatus.COMPLETE)
        
        loop = engine.get_loop_state(result.pac_id)
        
        assert loop.ber_emitted is True
        assert loop.ber_emitted_at is not None
        assert loop.ber_artifact is not None
    
    def test_loop_requires_emission_to_close(self, engine, sample_pac):
        """Loop is not closed until BER is emitted."""
        result = engine.dispatch(sample_pac)
        
        # Receive WRAP without auto-BER
        engine.receive_wrap_without_auto_ber(result.pac_id, WRAPStatus.COMPLETE)
        
        # Issue but don't emit
        engine.issue_ber(result.pac_id, BERStatus.APPROVE)
        
        loop = engine.get_loop_state(result.pac_id)
        
        # Loop should NOT be closed (BER issued but not emitted)
        assert loop.awaiting_emission is True
        assert loop.is_loop_closed is False


# ═══════════════════════════════════════════════════════════════════════════════
# STATE TRANSITION ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestStateTransitions:
    """Test state transition enforcement for emission."""
    
    def test_cannot_emit_before_issue(self, enforcer):
        """Cannot emit BER before it is issued."""
        pac_id = "PAC-TRANS-001"
        
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        
        # BER_REQUIRED state - cannot emit yet
        with pytest.raises(BERNotIssuedError):
            enforcer.emit_ber(pac_id)
    
    def test_must_emit_before_complete(self, enforcer):
        """Must emit BER before completing session."""
        pac_id = "PAC-TRANS-002"
        
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        enforcer.issue_ber(pac_id, "APPROVE")
        
        # Cannot complete without emission
        with pytest.raises(BERNotEmittedError):
            enforcer.complete_session(pac_id)
    
    def test_transition_ber_issued_to_emitted(self, enforcer):
        """BER_ISSUED can transition to BER_EMITTED."""
        pac_id = "PAC-TRANS-003"
        
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        enforcer.issue_ber(pac_id, "APPROVE")
        
        session = enforcer.get_session(pac_id)
        assert session.state == SessionState.BER_ISSUED
        
        enforcer.emit_ber(pac_id)
        
        assert session.state == SessionState.BER_EMITTED
    
    def test_cannot_skip_emission_to_complete(self, enforcer):
        """Cannot transition from BER_ISSUED directly to SESSION_COMPLETE."""
        pac_id = "PAC-TRANS-004"
        
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        enforcer.issue_ber(pac_id, "APPROVE")
        
        session = enforcer.get_session(pac_id)
        
        # Direct transition should raise
        with pytest.raises(BERNotEmittedError):
            session.transition_to(SessionState.SESSION_COMPLETE)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLETE HAPPY PATH
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompleteHappyPath:
    """Test complete PAC lifecycle with emission."""
    
    def test_full_lifecycle_with_artifact_return(self, engine, sample_pac):
        """
        Complete PAC lifecycle must return PDOArtifact (PAC-020 upgrade).
        
        User issues PAC → Agent executes → WRAP returned →
        BER issued AND emitted → PDOArtifact returned to user
        """
        from core.governance.pdo_artifact import PDOArtifact
        
        # 1. User issues PAC (via Orchestration Engine)
        result = engine.dispatch(sample_pac)
        assert result.success
        assert result.pac_id == "PAC-TEST-021"
        
        # 2. Agent executes (simulated)
        # 3. Agent returns WRAP
        # 4. Orchestration Engine receives WRAP, issues AND emits BER, then PDO
        artifact = engine.receive_wrap(
            result.pac_id,
            WRAPStatus.COMPLETE,
            "GID-99",
        )
        
        # 5. User receives PDOArtifact (proving emission) - PAC-020 upgrade
        assert isinstance(artifact, PDOArtifact)
        assert artifact.pac_id == result.pac_id
        assert artifact.outcome_status == "ACCEPTED"  # APPROVE maps to ACCEPTED
        assert artifact.issuer == "GID-00"  # PDO always issued by GID-00
        
        # 6. Loop is closed
        assert engine.is_loop_closed(result.pac_id)
        
        loop = engine.get_loop_state(result.pac_id)
        assert loop.ber_emitted is True
        assert loop.pdo_emitted is True
        assert loop.pdo_artifact == artifact
        # BERArtifact still available
        assert loop.ber_artifact is not None
        assert loop.ber_artifact.decision == "APPROVE"
    
    def test_corrective_ber_returns_artifact(self, engine, sample_pac):
        """Corrective BER also returns PDOArtifact (PAC-020 upgrade)."""
        from core.governance.pdo_artifact import PDOArtifact
        
        result = engine.dispatch(sample_pac)
        
        artifact = engine.receive_wrap(
            result.pac_id,
            WRAPStatus.PARTIAL,  # Triggers CORRECTIVE
            "GID-99",
        )
        
        # PAC-020: Now returns PDOArtifact
        assert isinstance(artifact, PDOArtifact)
        assert artifact.outcome_status == "CORRECTIVE"
    
    def test_enforcer_happy_path_returns_artifact(self):
        """BERLoopEnforcer happy path returns BERArtifact."""
        reset_ber_loop_enforcer()
        enforcer = BERLoopEnforcer(emit_terminal=False)
        
        pac_id = "PAC-HAPPY-001"
        
        # Dispatch
        enforcer.dispatch(pac_id)
        
        # Process WRAP to BER (single call)
        artifact = enforcer.process_wrap_synchronously(
            pac_id,
            "COMPLETE",
            "GID-99",
        )
        
        # Artifact returned
        assert isinstance(artifact, BERArtifact)
        assert artifact.pac_id == pac_id
        assert artifact.decision == "APPROVE"
        
        # Session complete
        session = enforcer.get_session(pac_id)
        assert session.state == SessionState.BER_EMITTED
        assert session.ber_emitted is True


# ═══════════════════════════════════════════════════════════════════════════════
# FAILURE MODE PREVENTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailureModesPrevented:
    """Test that PAC-021 prevents identified failure modes."""
    
    def test_cannot_issue_without_emit(self, enforcer):
        """
        FAILURE MODE: BER issued internally but never emitted.
        
        PAC-021 prevents: BER_ISSUED is non-terminal, must emit.
        """
        pac_id = "PAC-FAIL-001"
        
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        enforcer.issue_ber(pac_id, "APPROVE")
        
        session = enforcer.get_session(pac_id)
        
        # BER_ISSUED is NOT terminal
        assert not session.is_terminal
        assert session.is_ber_issued_not_emitted
        
        # Cannot complete
        with pytest.raises(BERNotEmittedError):
            enforcer.complete_session(pac_id)
    
    def test_artifact_proves_emission(self, enforcer):
        """
        FAILURE MODE: No proof of external emission.
        
        PAC-021 prevents: BERArtifact is immutable proof.
        """
        pac_id = "PAC-FAIL-002"
        
        enforcer.dispatch(pac_id)
        artifact = enforcer.process_wrap_synchronously(
            pac_id, "COMPLETE", "GID-99"
        )
        
        # Artifact is proof of emission
        assert artifact.pac_id is not None
        assert artifact.emitted_at is not None
        assert artifact.is_emitted is True
        
        # Artifact is immutable
        with pytest.raises(Exception):
            artifact.decision = "TAMPERED"
    
    def test_drafting_surface_blocked(self, enforcer):
        """
        FAILURE MODE: Drafting surface handling BER.
        
        PAC-021 prevents: DraftingSurfaceInBERFlowError.
        """
        pac_id = "PAC-FAIL-003"
        
        enforcer.dispatch(pac_id)
        enforcer.receive_wrap(pac_id, "COMPLETE", "GID-99")
        enforcer.issue_ber(pac_id, "APPROVE")
        
        # Drafting surface blocked
        with pytest.raises(DraftingSurfaceInBERFlowError):
            enforcer.emit_ber(pac_id, issuer_gid="DRAFTING_SURFACE")
