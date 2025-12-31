# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Control Plane Tests
# PAC-JEFFREY-P01: Benson Execution Control Plane UI — Multi-Agent Build
# CORRECTIVE REISSUANCE · GOLD STANDARD
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for Control Plane state model and governance invariants.

REVIEW ORDERS (PAC-JEFFREY-P01):
- Validate ACK enforcement
- Validate fail-closed behavior
- Validate schema-backed UI states
- Validate multi-agent WRAP aggregation (Section 7)
- Validate RG-01 Review Gate (Section 8)
- Validate BSRG-01 Self-Review Gate (Section 9)
- Validate ACK latency settlement binding (Section 6)
- Validate ledger commit attestation (Section 11)

STOP_FAIL CONDITIONS:
- Any execution without ACK → FAIL
- Any implied approval → FAIL
- Any missing audit artifact → FAIL

Author: Benson Execution Orchestrator (GID-00)
Backend Lane: CODY (GID-01)
"""

import pytest
from datetime import datetime, timezone

from core.governance.control_plane import (
    ACK_LATENCY_THRESHOLD_MS,
    AgentACK,
    AgentACKState,
    BensonSelfReviewBSRG01,
    BERRecord,
    BERState,
    ControlPlaneState,
    ControlPlaneStateError,
    LedgerCommitAttestation,
    MultiAgentWRAPSet,
    PACLifecycleState,
    PositiveClosure,
    ReviewGateRG01,
    SettlementEligibility,
    TrainingSignal,
    WRAPArtifact,
    WRAPValidationState,
    VALID_PAC_TRANSITIONS,
    check_ack_latency_eligibility,
    create_agent_ack,
    create_bsrg01,
    create_control_plane_state,
    create_ledger_commit_attestation,
    create_multi_agent_wrap_set,
    create_positive_closure,
    create_review_gate_rg01,
    create_training_signal,
    transition_state,
    validate_transition,
)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: STATE MODEL VALIDITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestPACLifecycleStates:
    """Test PAC lifecycle state definitions."""

    def test_all_states_defined(self):
        """Verify all expected states are defined."""
        expected_states = {
            "DRAFT", "ACK_PENDING", "EXECUTING", "WRAP_PENDING",
            "WRAP_SUBMITTED", "WRAP_VALIDATED", "BER_ISSUED", "SETTLED",
            "ACK_TIMEOUT", "ACK_REJECTED", "EXECUTION_FAILED",
            "WRAP_REJECTED", "SETTLEMENT_BLOCKED",
        }
        actual_states = {s.value for s in PACLifecycleState}
        assert actual_states == expected_states

    def test_terminal_states_have_no_transitions(self):
        """Terminal states must have no valid outbound transitions."""
        terminal_states = [
            PACLifecycleState.SETTLED,
            PACLifecycleState.ACK_TIMEOUT,
            PACLifecycleState.ACK_REJECTED,
            PACLifecycleState.EXECUTION_FAILED,
            PACLifecycleState.WRAP_REJECTED,
            PACLifecycleState.SETTLEMENT_BLOCKED,
        ]
        for state in terminal_states:
            assert VALID_PAC_TRANSITIONS[state] == [], f"{state} should have no transitions"

    def test_happy_path_transitions_complete(self):
        """Happy path must be complete: DRAFT → SETTLED."""
        happy_path = [
            (PACLifecycleState.DRAFT, PACLifecycleState.ACK_PENDING),
            (PACLifecycleState.ACK_PENDING, PACLifecycleState.EXECUTING),
            (PACLifecycleState.EXECUTING, PACLifecycleState.WRAP_PENDING),
            (PACLifecycleState.WRAP_PENDING, PACLifecycleState.WRAP_SUBMITTED),
            (PACLifecycleState.WRAP_SUBMITTED, PACLifecycleState.WRAP_VALIDATED),
            (PACLifecycleState.WRAP_VALIDATED, PACLifecycleState.BER_ISSUED),
            (PACLifecycleState.BER_ISSUED, PACLifecycleState.SETTLED),
        ]
        for from_state, to_state in happy_path:
            assert to_state in VALID_PAC_TRANSITIONS[from_state], \
                f"Missing transition: {from_state} → {to_state}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ACK ENFORCEMENT (INV-CP-001)
# ═══════════════════════════════════════════════════════════════════════════════

class TestACKEnforcement:
    """Test ACK enforcement invariants."""

    def test_create_agent_ack_has_pending_state(self):
        """New ACK requests must start in PENDING state."""
        ack = create_agent_ack(
            pac_id="PAC-TEST-001",
            agent_gid="GID-01",
            agent_name="TestAgent",
            order_id="ORDER-1",
        )
        assert ack.state == AgentACKState.PENDING

    def test_ack_has_deadline(self):
        """ACK must have a deadline set."""
        ack = create_agent_ack(
            pac_id="PAC-TEST-001",
            agent_gid="GID-01",
            agent_name="TestAgent",
            order_id="ORDER-1",
            deadline_seconds=300,
        )
        assert ack.deadline_at is not None
        deadline = datetime.fromisoformat(ack.deadline_at)
        requested = datetime.fromisoformat(ack.requested_at)
        # Deadline should be after requested time
        assert deadline > requested

    def test_ack_hash_computed(self):
        """ACK must have a hash for audit trail."""
        ack = create_agent_ack(
            pac_id="PAC-TEST-001",
            agent_gid="GID-01",
            agent_name="TestAgent",
            order_id="ORDER-1",
        )
        assert ack.ack_hash is not None
        assert len(ack.ack_hash) == 64  # SHA-256 hex digest

    def test_control_plane_all_acks_received_false_when_pending(self):
        """all_acks_received must be False when any ACK is pending."""
        state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
        
        # Add a pending ACK
        ack = create_agent_ack("PAC-TEST", "GID-01", "Agent1", "ORDER-1")
        state.agent_acks["GID-01"] = ack
        
        assert state.all_acks_received() is False

    def test_control_plane_all_acks_received_true_when_all_acknowledged(self):
        """all_acks_received must be True only when ALL ACKs are ACKNOWLEDGED."""
        state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
        
        # Add acknowledged ACKs
        for gid, name in [("GID-01", "Agent1"), ("GID-02", "Agent2")]:
            ack = create_agent_ack("PAC-TEST", gid, name, f"ORDER-{gid}")
            ack.state = AgentACKState.ACKNOWLEDGED
            ack.acknowledged_at = datetime.now(timezone.utc).isoformat()
            state.agent_acks[gid] = ack
        
        assert state.all_acks_received() is True


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: FAIL-CLOSED BEHAVIOR (INV-CP-004)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailClosedBehavior:
    """Test FAIL_CLOSED governance behavior."""

    def test_rejected_ack_blocks_settlement(self):
        """Rejected ACK must block settlement."""
        state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
        
        # Add one acknowledged, one rejected
        ack1 = create_agent_ack("PAC-TEST", "GID-01", "Agent1", "ORDER-1")
        ack1.state = AgentACKState.ACKNOWLEDGED
        state.agent_acks["GID-01"] = ack1
        
        ack2 = create_agent_ack("PAC-TEST", "GID-02", "Agent2", "ORDER-2")
        ack2.state = AgentACKState.REJECTED
        ack2.rejection_reason = "Task out of scope"
        state.agent_acks["GID-02"] = ack2
        
        assert state.has_rejected_acks() is True
        assert state.compute_settlement_eligibility() == SettlementEligibility.BLOCKED

    def test_timeout_ack_blocks_settlement(self):
        """Timeout ACK must block settlement."""
        state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
        
        ack = create_agent_ack("PAC-TEST", "GID-01", "Agent1", "ORDER-1")
        ack.state = AgentACKState.TIMEOUT
        state.agent_acks["GID-01"] = ack
        
        assert state.has_timed_out_acks() is True
        assert state.compute_settlement_eligibility() == SettlementEligibility.BLOCKED

    def test_failed_lifecycle_state_blocks_settlement(self):
        """Failed lifecycle states must block settlement."""
        failed_states = [
            PACLifecycleState.ACK_TIMEOUT,
            PACLifecycleState.ACK_REJECTED,
            PACLifecycleState.EXECUTION_FAILED,
            PACLifecycleState.WRAP_REJECTED,
            PACLifecycleState.SETTLEMENT_BLOCKED,
        ]
        for failed_state in failed_states:
            state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
            state.lifecycle_state = failed_state
            assert state.compute_settlement_eligibility() == SettlementEligibility.BLOCKED, \
                f"{failed_state} should block settlement"

    def test_invalid_state_transition_raises_error(self):
        """Invalid state transitions must raise ControlPlaneStateError."""
        # Try DRAFT → SETTLED (skipping required steps)
        with pytest.raises(ControlPlaneStateError):
            validate_transition(PACLifecycleState.DRAFT, PACLifecycleState.SETTLED)
        
        # Try SETTLED → anything (terminal state)
        with pytest.raises(ControlPlaneStateError):
            validate_transition(PACLifecycleState.SETTLED, PACLifecycleState.DRAFT)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: STATE TRANSITIONS WITH AUDIT TRAIL (INV-CP-003)
# ═══════════════════════════════════════════════════════════════════════════════

class TestStateTransitions:
    """Test deterministic state transitions with audit trail."""

    def test_transition_records_audit_entry(self):
        """State transitions must record audit entries."""
        state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
        
        transition_state(
            state,
            PACLifecycleState.ACK_PENDING,
            reason="PAC dispatched",
            actor="GID-00",
        )
        
        assert len(state.state_transitions) == 1
        entry = state.state_transitions[0]
        assert entry["from_state"] == PACLifecycleState.DRAFT.value
        assert entry["to_state"] == PACLifecycleState.ACK_PENDING.value
        assert entry["reason"] == "PAC dispatched"
        assert entry["actor"] == "GID-00"
        assert "timestamp" in entry

    def test_transition_updates_lifecycle_state(self):
        """State transitions must update lifecycle_state."""
        state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
        assert state.lifecycle_state == PACLifecycleState.DRAFT
        
        transition_state(state, PACLifecycleState.ACK_PENDING, "Test", "SYSTEM")
        assert state.lifecycle_state == PACLifecycleState.ACK_PENDING

    def test_transition_updates_timestamp(self):
        """State transitions must update updated_at timestamp."""
        state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
        original_updated = state.updated_at
        
        # Small delay to ensure timestamp differs
        import time
        time.sleep(0.01)
        
        transition_state(state, PACLifecycleState.ACK_PENDING, "Test", "SYSTEM")
        assert state.updated_at != original_updated


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BER ELIGIBILITY (INV-CP-005)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBERAndSettlement:
    """Test BER and settlement eligibility logic."""

    def test_settlement_eligible_requires_issued_ber(self):
        """Settlement eligibility requires ISSUED BER."""
        state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
        state.lifecycle_state = PACLifecycleState.BER_ISSUED
        
        # Add all acknowledged ACKs
        ack = create_agent_ack("PAC-TEST", "GID-01", "Agent1", "ORDER-1")
        ack.state = AgentACKState.ACKNOWLEDGED
        state.agent_acks["GID-01"] = ack
        
        # Add valid WRAP
        wrap = WRAPArtifact(
            wrap_id="WRAP-TEST-001",
            pac_id="PAC-TEST",
            agent_gid="GID-01",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            validation_state=WRAPValidationState.VALID,
            artifact_refs=["artifact-1"],
        )
        state.wraps["WRAP-TEST-001"] = wrap
        
        # Add issued BER
        state.ber = BERRecord(
            ber_id="BER-TEST-001",
            pac_id="PAC-TEST",
            wrap_id="WRAP-TEST-001",
            state=BERState.ISSUED,
            issued_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert state.compute_settlement_eligibility() == SettlementEligibility.ELIGIBLE

    def test_settlement_blocked_without_ber(self):
        """Settlement must be PENDING without BER."""
        state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
        state.lifecycle_state = PACLifecycleState.WRAP_VALIDATED
        state.ber = None
        
        assert state.compute_settlement_eligibility() == SettlementEligibility.PENDING


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: WRAP VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestWRAPValidation:
    """Test WRAP artifact validation."""

    def test_wrap_hash_computed(self):
        """WRAP must have a hash for integrity."""
        wrap = WRAPArtifact(
            wrap_id="WRAP-TEST-001",
            pac_id="PAC-TEST",
            agent_gid="GID-01",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            validation_state=WRAPValidationState.PENDING,
        )
        assert wrap.wrap_hash is not None
        assert len(wrap.wrap_hash) == 64

    def test_missing_ack_validation_state_defined(self):
        """MISSING_ACK validation state must exist."""
        assert WRAPValidationState.MISSING_ACK is not None
        assert WRAPValidationState.MISSING_ACK.value == "MISSING_ACK"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SERIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestSerialization:
    """Test state serialization for API responses."""

    def test_control_plane_state_to_dict(self):
        """Control plane state must serialize to dict."""
        state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
        
        # Add ACK
        ack = create_agent_ack("PAC-TEST", "GID-01", "Agent1", "ORDER-1")
        state.agent_acks["GID-01"] = ack
        
        result = state.to_dict()
        
        assert result["pac_id"] == "PAC-TEST"
        assert result["runtime_id"] == "RUNTIME-TEST"
        assert result["lifecycle_state"] == "DRAFT"
        assert "GID-01" in result["agent_acks"]
        assert "ack_summary" in result
        assert result["ack_summary"]["total"] == 1
        assert result["ack_summary"]["pending"] == 1

    def test_to_dict_includes_latency_summary(self):
        """Serialization must include latency summary."""
        state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
        
        ack = create_agent_ack("PAC-TEST", "GID-01", "Agent1", "ORDER-1")
        ack.state = AgentACKState.ACKNOWLEDGED
        ack.latency_ms = 250
        state.agent_acks["GID-01"] = ack
        
        result = state.to_dict()
        assert result["ack_summary"]["latency"]["avg_ms"] == 250


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: MULTI-AGENT WRAP SET (PAC-JEFFREY-P01 SECTION 7)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiAgentWRAPSet:
    """Test multi-agent WRAP aggregation."""

    def test_create_wrap_set_with_expected_agents(self):
        """WRAP set must be created with expected agents list."""
        wrap_set = create_multi_agent_wrap_set(
            pac_id="PAC-TEST",
            executing_agents=["GID-00", "GID-01", "GID-02"],
        )
        assert wrap_set.pac_id == "PAC-TEST"
        assert wrap_set.expected_agents == ["GID-00", "GID-01", "GID-02"]
        assert wrap_set.is_complete() is False
        assert len(wrap_set.get_missing_agents()) == 3

    def test_wrap_set_add_wrap(self):
        """Adding WRAP should update collected_wraps."""
        wrap_set = create_multi_agent_wrap_set("PAC-TEST", ["GID-01", "GID-02"])
        
        wrap = WRAPArtifact(
            wrap_id="WRAP-001",
            pac_id="PAC-TEST",
            agent_gid="GID-01",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            validation_state=WRAPValidationState.VALID,
        )
        wrap_set.add_wrap(wrap)
        
        assert "GID-01" in wrap_set.collected_wraps
        assert wrap_set.get_missing_agents() == ["GID-02"]

    def test_wrap_set_rejects_unexpected_agent(self):
        """WRAP from unexpected agent must be rejected."""
        wrap_set = create_multi_agent_wrap_set("PAC-TEST", ["GID-01"])
        
        wrap = WRAPArtifact(
            wrap_id="WRAP-001",
            pac_id="PAC-TEST",
            agent_gid="GID-99",  # Not in expected list
            submitted_at=datetime.now(timezone.utc).isoformat(),
            validation_state=WRAPValidationState.VALID,
        )
        
        with pytest.raises(ControlPlaneStateError):
            wrap_set.add_wrap(wrap)

    def test_wrap_set_complete_when_all_collected(self):
        """is_complete should be True when all expected WRAPs collected."""
        wrap_set = create_multi_agent_wrap_set("PAC-TEST", ["GID-01", "GID-02"])
        
        for gid in ["GID-01", "GID-02"]:
            wrap = WRAPArtifact(
                wrap_id=f"WRAP-{gid}",
                pac_id="PAC-TEST",
                agent_gid=gid,
                submitted_at=datetime.now(timezone.utc).isoformat(),
                validation_state=WRAPValidationState.VALID,
            )
            wrap_set.add_wrap(wrap)
        
        assert wrap_set.is_complete() is True
        assert wrap_set.aggregation_completed_at is not None

    def test_wrap_set_all_valid_false_when_invalid(self):
        """all_valid should be False when any WRAP is invalid."""
        wrap_set = create_multi_agent_wrap_set("PAC-TEST", ["GID-01", "GID-02"])
        
        wrap1 = WRAPArtifact(
            wrap_id="WRAP-001",
            pac_id="PAC-TEST",
            agent_gid="GID-01",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            validation_state=WRAPValidationState.VALID,
        )
        wrap2 = WRAPArtifact(
            wrap_id="WRAP-002",
            pac_id="PAC-TEST",
            agent_gid="GID-02",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            validation_state=WRAPValidationState.INVALID,  # Invalid
        )
        wrap_set.add_wrap(wrap1)
        wrap_set.add_wrap(wrap2)
        
        assert wrap_set.all_valid() is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: REVIEW GATE RG-01 (PAC-JEFFREY-P01 SECTION 8)
# ═══════════════════════════════════════════════════════════════════════════════

class TestReviewGateRG01:
    """Test RG-01 Review Gate."""

    def test_create_review_gate(self):
        """Review gate must be created with BENSON as reviewer."""
        rg01 = create_review_gate_rg01("PAC-TEST")
        assert rg01.pac_id == "PAC-TEST"
        assert rg01.reviewer == "BENSON"
        assert rg01.result is None

    def test_review_gate_evaluate_pass(self):
        """RG-01 should PASS when all WRAPs complete, valid, with Training Signals and Closures."""
        wrap_set = create_multi_agent_wrap_set("PAC-TEST", ["GID-01"])
        wrap = WRAPArtifact(
            wrap_id="WRAP-001",
            pac_id="PAC-TEST",
            agent_gid="GID-01",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            validation_state=WRAPValidationState.VALID,
        )
        wrap_set.add_wrap(wrap)
        
        # PAC-JEFFREY-P02R: Training Signals required
        training_signal = create_training_signal(
            pac_id="PAC-TEST",
            agent_gid="GID-01",
            agent_name="Agent-01",
            signal_type="LEARNING",
            observation="Test observation",
            constraint_learned="Test constraint",
            recommended_enforcement="Test enforcement",
        )
        
        # PAC-JEFFREY-P02R: Positive Closures required
        positive_closure = create_positive_closure(
            pac_id="PAC-TEST",
            agent_gid="GID-01",
            agent_name="Agent-01",
            scope_complete=True,
            no_violations=True,
            ready_for_next_stage=True,
        )
        
        rg01 = create_review_gate_rg01("PAC-TEST")
        result = rg01.evaluate(
            wrap_set,
            training_signals=[training_signal],
            positive_closures=[positive_closure],
        )
        
        assert result is True
        assert rg01.result == "PASS"
        assert rg01.evaluated_at is not None
        assert len(rg01.fail_reasons) == 0
        assert rg01.training_signals_present is True
        assert rg01.positive_closures_present is True

    def test_review_gate_evaluate_fail_missing_wraps(self):
        """RG-01 should FAIL when WRAPs missing."""
        wrap_set = create_multi_agent_wrap_set("PAC-TEST", ["GID-01", "GID-02"])
        # Only add one WRAP
        wrap = WRAPArtifact(
            wrap_id="WRAP-001",
            pac_id="PAC-TEST",
            agent_gid="GID-01",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            validation_state=WRAPValidationState.VALID,
        )
        wrap_set.add_wrap(wrap)
        
        # Add signals and closures for the agent that submitted
        training_signal = create_training_signal(
            pac_id="PAC-TEST",
            agent_gid="GID-01",
            agent_name="Agent-01",
            signal_type="LEARNING",
            observation="Test observation",
            constraint_learned="Test constraint",
            recommended_enforcement="Test enforcement",
        )
        positive_closure = create_positive_closure(
            pac_id="PAC-TEST",
            agent_gid="GID-01",
            agent_name="Agent-01",
        )
        
        rg01 = create_review_gate_rg01("PAC-TEST")
        result = rg01.evaluate(
            wrap_set,
            training_signals=[training_signal],
            positive_closures=[positive_closure],
        )
        
        assert result is False
        assert rg01.result == "FAIL"
        assert len(rg01.fail_reasons) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BSRG-01 SELF-REVIEW GATE (PAC-JEFFREY-P01 SECTION 9)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBSRG01:
    """Test BSRG-01 Benson Self-Review Gate."""

    def test_create_bsrg01(self):
        """BSRG-01 must be created with self_attestation=False."""
        bsrg = create_bsrg01("PAC-TEST")
        assert bsrg.pac_id == "PAC-TEST"
        assert bsrg.self_attestation is False

    def test_bsrg01_attest(self):
        """BSRG-01 attest should set self_attestation=True."""
        bsrg = create_bsrg01("PAC-TEST")
        result = bsrg.attest(
            violations=None,
            training_signals=[{"signal": "test"}],
        )
        
        assert result is True
        assert bsrg.self_attestation is True
        assert bsrg.violations == []
        assert len(bsrg.training_signals) == 1
        assert bsrg.attested_at is not None

    def test_bsrg01_attest_with_violations(self):
        """BSRG-01 attest with violations should record them."""
        bsrg = create_bsrg01("PAC-TEST")
        bsrg.attest(violations=["Minor drift detected"])
        
        assert bsrg.violations == ["Minor drift detected"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ACK LATENCY SETTLEMENT BINDING (PAC-JEFFREY-P01 SECTION 6)
# ═══════════════════════════════════════════════════════════════════════════════

class TestACKLatencyBinding:
    """Test ACK latency settlement eligibility binding."""

    def test_check_ack_latency_eligible_within_threshold(self):
        """ACK latency within threshold should be eligible."""
        state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
        
        ack = create_agent_ack("PAC-TEST", "GID-01", "Agent1", "ORDER-1")
        ack.state = AgentACKState.ACKNOWLEDGED
        ack.latency_ms = 1000  # 1 second, well under 5 second threshold
        state.agent_acks["GID-01"] = ack
        
        result = check_ack_latency_eligibility(state)
        assert result["eligible"] is True
        assert result["reason"] is None

    def test_check_ack_latency_ineligible_over_threshold(self):
        """ACK latency over threshold should be ineligible."""
        state = create_control_plane_state("PAC-TEST", "RUNTIME-TEST")
        
        ack = create_agent_ack("PAC-TEST", "GID-01", "Agent1", "ORDER-1")
        ack.state = AgentACKState.ACKNOWLEDGED
        ack.latency_ms = 10000  # 10 seconds, over 5 second threshold
        state.agent_acks["GID-01"] = ack
        
        result = check_ack_latency_eligibility(state)
        assert result["eligible"] is False
        assert "exceeds threshold" in result["reason"]

    def test_ack_latency_threshold_constant_defined(self):
        """ACK latency threshold constant must be defined."""
        assert ACK_LATENCY_THRESHOLD_MS == 5000


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: LEDGER COMMIT ATTESTATION (PAC-JEFFREY-P01 SECTION 11)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLedgerCommitAttestation:
    """Test ledger commit attestation."""

    def test_create_ledger_attestation(self):
        """Ledger attestation must be created with WRAP and BER hashes."""
        wrap_set = create_multi_agent_wrap_set("PAC-TEST", ["GID-01"])
        wrap = WRAPArtifact(
            wrap_id="WRAP-001",
            pac_id="PAC-TEST",
            agent_gid="GID-01",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            validation_state=WRAPValidationState.VALID,
        )
        wrap_set.add_wrap(wrap)
        
        ber = BERRecord(
            ber_id="BER-001",
            pac_id="PAC-TEST",
            wrap_id="WRAP-001",
            state=BERState.ISSUED,
        )
        
        attestation = create_ledger_commit_attestation("PAC-TEST", wrap_set, ber)
        
        assert attestation.pac_id == "PAC-TEST"
        assert len(attestation.wrap_hashes) == 1
        assert attestation.ber_hash == ber.ber_hash
        assert attestation.attestation_hash is not None
