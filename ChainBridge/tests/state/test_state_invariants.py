"""
Tests for ChainBridge State Invariants

Atlas (GID-05) — System State Engine
Authority: Benson (GID-00)

These tests verify the state invariants defined in A11_SYSTEM_STATE_INVARIANT_LOCK.md
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from core.state import (
    ArtifactType,
    EventStateRecord,
    EventType,
    PDOState,
    SettlementState,
    ShipmentState,
    StateMetadata,
    StateTransition,
    StateValidator,
    ValidationResult,
    ViolationSeverity,
    ViolationType,
    get_terminal_states,
    is_valid_transition,
    validate_event_ordering,
    validate_state_transition,
    SHIPMENT_TRANSITIONS,
    SETTLEMENT_TRANSITIONS,
    PDO_TRANSITIONS,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def validator() -> StateValidator:
    """Create a fresh StateValidator instance."""
    return StateValidator()


@pytest.fixture
def sample_transition() -> StateTransition:
    """Create a sample valid state transition."""
    return StateTransition(
        transition_id=f"TRX-{uuid4().hex[:8]}",
        artifact_type=ArtifactType.SHIPMENT,
        artifact_id=f"SHIP-{uuid4().hex[:8]}",
        from_state=ShipmentState.CREATED.value,
        to_state=ShipmentState.IN_TRANSIT.value,
        timestamp=datetime.utcnow(),
        proof_id=f"PRF-{uuid4().hex[:8]}",
        actor_id="agent:cody",
        reason="Shipment departed",
    )


@pytest.fixture
def sample_events() -> list[EventStateRecord]:
    """Create a sample event sequence."""
    base_time = datetime.utcnow()
    artifact_id = f"SHIP-{uuid4().hex[:8]}"

    return [
        EventStateRecord(
            event_id=f"EVT-{uuid4().hex[:8]}",
            event_type=EventType.SHIPMENT_CREATED,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=artifact_id,
            timestamp=base_time,
            sequence_number=0,
            payload_hash="hash0",
            metadata=StateMetadata(),
        ),
        EventStateRecord(
            event_id=f"EVT-{uuid4().hex[:8]}",
            event_type=EventType.SHIPMENT_DEPARTED,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=artifact_id,
            timestamp=base_time + timedelta(hours=1),
            sequence_number=1,
            payload_hash="hash1",
            metadata=StateMetadata(),
        ),
        EventStateRecord(
            event_id=f"EVT-{uuid4().hex[:8]}",
            event_type=EventType.SHIPMENT_DELIVERED,
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id=artifact_id,
            timestamp=base_time + timedelta(hours=24),
            sequence_number=2,
            payload_hash="hash2",
            metadata=StateMetadata(),
        ),
    ]


# =============================================================================
# INV-S01: ONE STATE PER ARTIFACT
# =============================================================================


class TestInvS01OneStatePerArtifact:
    """Tests for INV-S01: One state per artifact ID."""

    def test_single_state_valid(self, validator: StateValidator) -> None:
        """Single state record is valid."""
        result = validator.validate_no_duplicate_states(
            artifact_id="SHIP-001",
            artifact_type=ArtifactType.SHIPMENT,
            state_records=["state1"],
        )
        assert result.is_valid
        assert result.violation_count == 0

    def test_duplicate_states_detected(self, validator: StateValidator) -> None:
        """Multiple state records trigger violation."""
        result = validator.validate_no_duplicate_states(
            artifact_id="SHIP-001",
            artifact_type=ArtifactType.SHIPMENT,
            state_records=["state1", "state2"],
        )
        assert not result.is_valid
        assert result.violation_count == 1
        assert result.violations[0].violation_type == ViolationType.DUPLICATE_STATE
        assert result.violations[0].severity == ViolationSeverity.CRITICAL


# =============================================================================
# INV-S02: FORWARD-ONLY TRANSITIONS
# =============================================================================


class TestInvS02ForwardOnlyTransitions:
    """Tests for INV-S02: Forward-only state transitions."""

    def test_forward_transition_valid(
        self, validator: StateValidator, sample_transition: StateTransition
    ) -> None:
        """Forward timestamp transition is valid."""
        past_time = datetime.utcnow() - timedelta(hours=1)
        result = validator.validate_transition(
            transition=sample_transition,
            current_timestamp=past_time,
        )
        assert result.is_valid

    def test_backward_transition_rejected(
        self, validator: StateValidator, sample_transition: StateTransition
    ) -> None:
        """Backward timestamp transition is rejected."""
        future_time = datetime.utcnow() + timedelta(hours=1)
        result = validator.validate_transition(
            transition=sample_transition,
            current_timestamp=future_time,
        )
        assert not result.is_valid
        assert any(
            v.violation_type == ViolationType.BACKWARD_TRANSITION
            for v in result.violations
        )


# =============================================================================
# INV-S03: NO RETROACTIVE MUTATION
# =============================================================================


class TestInvS03NoRetroactiveMutation:
    """Tests for INV-S03: No retroactive mutation of finalized state."""

    def test_non_finalized_transition_allowed(
        self, validator: StateValidator, sample_transition: StateTransition
    ) -> None:
        """Non-finalized artifact can transition."""
        result = validator.validate_transition(
            transition=sample_transition,
            is_finalized=False,
        )
        # Should not have finality violation
        assert not any(
            v.violation_type == ViolationType.FINALITY_VIOLATION
            for v in result.violations
        )

    def test_finalized_transition_blocked(
        self, validator: StateValidator, sample_transition: StateTransition
    ) -> None:
        """Finalized artifact cannot transition."""
        result = validator.validate_transition(
            transition=sample_transition,
            is_finalized=True,
        )
        assert not result.is_valid
        assert any(
            v.violation_type == ViolationType.FINALITY_VIOLATION
            for v in result.violations
        )
        assert any(
            v.severity == ViolationSeverity.CRITICAL
            for v in result.violations
            if v.violation_type == ViolationType.FINALITY_VIOLATION
        )


# =============================================================================
# INV-S04: NO CONFLICTING TRUTHS
# =============================================================================


class TestInvS04NoConflictingTruths:
    """Tests for INV-S04: No conflicting truths across sources."""

    def test_matching_state_valid(
        self, validator: StateValidator, sample_transition: StateTransition
    ) -> None:
        """Transition from_state matches current state."""
        result = validator.validate_transition(
            transition=sample_transition,
            current_state=ShipmentState.CREATED.value,
        )
        # Should not have conflicting truth violation
        assert not any(
            v.violation_type == ViolationType.CONFLICTING_TRUTH
            for v in result.violations
        )

    def test_mismatched_state_detected(
        self, validator: StateValidator, sample_transition: StateTransition
    ) -> None:
        """Transition from_state mismatch detected."""
        result = validator.validate_transition(
            transition=sample_transition,
            current_state=ShipmentState.DELIVERED.value,  # Different from CREATED
        )
        assert not result.is_valid
        assert any(
            v.violation_type == ViolationType.CONFLICTING_TRUTH
            for v in result.violations
        )


# =============================================================================
# INV-S05: TIME MONOTONICITY
# =============================================================================


class TestInvS05TimeMonotonicity:
    """Tests for INV-S05: Time monotonicity in event sequences."""

    def test_monotonic_sequence_valid(
        self, validator: StateValidator, sample_events: list[EventStateRecord]
    ) -> None:
        """Properly ordered events pass validation."""
        result = validator.validate_event_sequence(sample_events)
        assert result.is_valid

    def test_non_monotonic_sequence_rejected(
        self, validator: StateValidator, sample_events: list[EventStateRecord]
    ) -> None:
        """Out-of-order timestamps detected."""
        # Swap timestamps to create violation
        sample_events[1].timestamp = sample_events[0].timestamp - timedelta(hours=1)

        result = validator.validate_event_sequence(sample_events)
        assert not result.is_valid
        assert any(
            v.violation_type == ViolationType.TEMPORAL_VIOLATION
            for v in result.violations
        )


# =============================================================================
# INV-S06: PROOF LINEAGE REQUIRED
# =============================================================================


class TestInvS06ProofLineageRequired:
    """Tests for INV-S06: Proof lineage required for state changes."""

    def test_transition_with_proof_valid(
        self, validator: StateValidator, sample_transition: StateTransition
    ) -> None:
        """Transition with proof_id is valid."""
        assert sample_transition.proof_id  # Ensure proof exists
        result = validator.validate_transition(transition=sample_transition)
        assert not any(
            v.violation_type == ViolationType.MISSING_PROOF
            for v in result.violations
        )

    def test_transition_without_proof_rejected(
        self, validator: StateValidator
    ) -> None:
        """Transition without proof_id is rejected."""
        transition = StateTransition(
            transition_id="TRX-001",
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id="SHIP-001",
            from_state=ShipmentState.CREATED.value,
            to_state=ShipmentState.IN_TRANSIT.value,
            timestamp=datetime.utcnow(),
            proof_id="",  # Empty proof
        )
        result = validator.validate_transition(transition=transition)
        assert not result.is_valid
        assert any(
            v.violation_type == ViolationType.MISSING_PROOF
            for v in result.violations
        )


# =============================================================================
# INV-S09: NO ORPHAN ARTIFACTS
# =============================================================================


class TestInvS09NoOrphanArtifacts:
    """Tests for INV-S09: No orphan artifacts."""

    def test_artifact_with_parent_valid(self, validator: StateValidator) -> None:
        """Artifact with parent reference is valid."""
        result = validator.validate_orphan_check(
            artifact_id="SHIP-002",
            artifact_type=ArtifactType.SHIPMENT,
            parent_reference="ORDER-001",
            is_genesis=False,
        )
        assert result.is_valid

    def test_genesis_artifact_valid(self, validator: StateValidator) -> None:
        """Genesis artifact without parent is valid."""
        result = validator.validate_orphan_check(
            artifact_id="SHIP-001",
            artifact_type=ArtifactType.SHIPMENT,
            parent_reference=None,
            is_genesis=True,
        )
        assert result.is_valid

    def test_orphan_artifact_detected(self, validator: StateValidator) -> None:
        """Orphan artifact without parent or genesis flag detected."""
        result = validator.validate_orphan_check(
            artifact_id="SHIP-003",
            artifact_type=ArtifactType.SHIPMENT,
            parent_reference=None,
            is_genesis=False,
        )
        assert not result.is_valid
        assert any(
            v.violation_type == ViolationType.ORPHAN_ARTIFACT
            for v in result.violations
        )


# =============================================================================
# INV-S10: TRANSITION VALIDITY
# =============================================================================


class TestInvS10TransitionValidity:
    """Tests for INV-S10: Only declared transitions are permitted."""

    def test_valid_shipment_transitions(self) -> None:
        """Valid shipment state transitions are allowed."""
        valid_transitions = [
            (ShipmentState.CREATED.value, ShipmentState.IN_TRANSIT.value),
            (ShipmentState.CREATED.value, ShipmentState.CANCELLED.value),
            (ShipmentState.IN_TRANSIT.value, ShipmentState.DELIVERED.value),
            (ShipmentState.IN_TRANSIT.value, ShipmentState.EXCEPTION.value),
            (ShipmentState.DELIVERED.value, ShipmentState.SETTLED.value),
            (ShipmentState.EXCEPTION.value, ShipmentState.RESOLVED.value),
            (ShipmentState.RESOLVED.value, ShipmentState.SETTLED.value),
        ]
        for from_state, to_state in valid_transitions:
            assert is_valid_transition(ArtifactType.SHIPMENT, from_state, to_state), \
                f"Expected {from_state} → {to_state} to be valid"

    def test_invalid_shipment_transitions(self) -> None:
        """Invalid shipment state transitions are blocked."""
        invalid_transitions = [
            (ShipmentState.SETTLED.value, ShipmentState.CREATED.value),  # Terminal → any
            (ShipmentState.CANCELLED.value, ShipmentState.IN_TRANSIT.value),  # Terminal → any
            (ShipmentState.DELIVERED.value, ShipmentState.CREATED.value),  # Backward
            (ShipmentState.CREATED.value, ShipmentState.SETTLED.value),  # Skip steps
        ]
        for from_state, to_state in invalid_transitions:
            assert not is_valid_transition(ArtifactType.SHIPMENT, from_state, to_state), \
                f"Expected {from_state} → {to_state} to be invalid"

    def test_valid_settlement_transitions(self) -> None:
        """Valid settlement state transitions are allowed."""
        valid_transitions = [
            (SettlementState.PENDING.value, SettlementState.APPROVED.value),
            (SettlementState.APPROVED.value, SettlementState.EXECUTED.value),
            (SettlementState.EXECUTED.value, SettlementState.FINALIZED.value),
            (SettlementState.PENDING.value, SettlementState.REJECTED.value),
            (SettlementState.REJECTED.value, SettlementState.DISPUTED.value),
        ]
        for from_state, to_state in valid_transitions:
            assert is_valid_transition(ArtifactType.SETTLEMENT, from_state, to_state), \
                f"Expected {from_state} → {to_state} to be valid"

    def test_valid_pdo_transitions(self) -> None:
        """Valid PDO state transitions are allowed."""
        valid_transitions = [
            (PDOState.CREATED.value, PDOState.SIGNED.value),
            (PDOState.SIGNED.value, PDOState.VERIFIED.value),
            (PDOState.VERIFIED.value, PDOState.ACCEPTED.value),
            (PDOState.SIGNED.value, PDOState.VERIFICATION_FAILED.value),
            (PDOState.VERIFICATION_FAILED.value, PDOState.REJECTED.value),
        ]
        for from_state, to_state in valid_transitions:
            assert is_valid_transition(ArtifactType.PDO, from_state, to_state), \
                f"Expected {from_state} → {to_state} to be valid"


# =============================================================================
# TERMINAL STATES
# =============================================================================


class TestTerminalStates:
    """Tests for terminal state identification."""

    def test_shipment_terminal_states(self) -> None:
        """Shipment terminal states are correctly identified."""
        terminals = get_terminal_states(ArtifactType.SHIPMENT)
        assert ShipmentState.SETTLED.value in terminals
        assert ShipmentState.CANCELLED.value in terminals
        assert ShipmentState.CREATED.value not in terminals

    def test_settlement_terminal_states(self) -> None:
        """Settlement terminal states are correctly identified."""
        terminals = get_terminal_states(ArtifactType.SETTLEMENT)
        assert SettlementState.FINALIZED.value in terminals
        assert SettlementState.PENDING.value not in terminals

    def test_pdo_terminal_states(self) -> None:
        """PDO terminal states are correctly identified."""
        terminals = get_terminal_states(ArtifactType.PDO)
        assert PDOState.ACCEPTED.value in terminals
        assert PDOState.REJECTED.value in terminals
        assert PDOState.EXPIRED.value in terminals
        assert PDOState.CREATED.value not in terminals


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_validate_state_transition_function(self) -> None:
        """validate_state_transition convenience function works."""
        transition = StateTransition(
            transition_id="TRX-001",
            artifact_type=ArtifactType.SHIPMENT,
            artifact_id="SHIP-001",
            from_state=ShipmentState.CREATED.value,
            to_state=ShipmentState.IN_TRANSIT.value,
            timestamp=datetime.utcnow(),
            proof_id="PRF-001",
        )
        result = validate_state_transition(transition)
        assert isinstance(result, ValidationResult)

    def test_validate_event_ordering_function(
        self, sample_events: list[EventStateRecord]
    ) -> None:
        """validate_event_ordering convenience function works."""
        result = validate_event_ordering(sample_events)
        assert isinstance(result, ValidationResult)
        assert result.is_valid
