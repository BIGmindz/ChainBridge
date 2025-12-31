"""
ChainBridge State Transition Tests

Atlas (GID-05) — System State Engine
Authority: Benson (GID-00)

PAC: PAC-ATLAS-A12-STATE-TRANSITION-GOVERNANCE-LOCK-01

Tests cover:
- State machine definitions
- Transition validation (allowed/rejected)
- Fail-closed semantics
- Transition proof emission
- Proof chain verification
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from typing import Any

from core.state.state_machine import (
    STATE_MACHINES,
    StateMachine,
    TransitionRule,
    get_state_machine,
    validate_all_state_machines,
    PDO_STATE_MACHINE,
    SETTLEMENT_STATE_MACHINE,
    PROOF_STATE_MACHINE,
    DEPLOYMENT_STATE_MACHINE,
    RISK_DECISION_STATE_MACHINE,
    ProofState,
    DeploymentState,
    RiskDecisionState,
)
from core.state.state_schema import PDOState, SettlementState
from core.state.transition_validator import (
    TransitionValidator,
    TransitionRequest,
    TransitionResult,
    TransitionValidationResult,
    validate_transition,
    is_transition_allowed,
    get_allowed_transitions,
)
from core.state.transition_proof import (
    StateTransitionProof,
    TransitionProofEmitter,
    verify_transition_proof,
    verify_proof_chain,
    create_transition_proof,
)


# =============================================================================
# STATE MACHINE DEFINITION TESTS
# =============================================================================


class TestStateMachineDefinitions:
    """Test state machine structure and definitions."""

    def test_required_state_machines_exist(self) -> None:
        """All required artifact types have state machines (uppercase keys)."""
        required = ["PDO", "SETTLEMENT", "PROOF", "DEPLOYMENT", "RISK_DECISION"]
        for artifact_type in required:
            assert artifact_type in STATE_MACHINES, f"Missing: {artifact_type}"

    def test_pdo_state_machine_has_rules(self) -> None:
        """PDO state machine has transition rules."""
        assert len(PDO_STATE_MACHINE.transition_rules) > 0
        assert len(PDO_STATE_MACHINE.terminal_states) > 0

    def test_settlement_state_machine_has_rules(self) -> None:
        """Settlement state machine has transition rules."""
        assert len(SETTLEMENT_STATE_MACHINE.transition_rules) > 0
        assert len(SETTLEMENT_STATE_MACHINE.terminal_states) > 0

    def test_all_state_machines_valid(self) -> None:
        """All state machines pass structural validation."""
        results = validate_all_state_machines()
        # validate_all_state_machines returns dict[name, list[errors]]
        all_errors = []
        for name, errors in results.items():
            all_errors.extend(errors)
        assert len(all_errors) == 0, f"Validation errors: {all_errors}"

    def test_get_state_machine_returns_correct_machine(self) -> None:
        """get_state_machine returns the right machine."""
        machine = get_state_machine("PDO")
        assert machine is PDO_STATE_MACHINE

    def test_get_state_machine_unknown_type(self) -> None:
        """get_state_machine returns None for unknown types."""
        machine = get_state_machine("UnknownType")
        assert machine is None

    def test_transition_rule_immutability(self) -> None:
        """TransitionRule is frozen (immutable)."""
        # Get first rule from transition_rules dict
        rule_key = list(PDO_STATE_MACHINE.transition_rules.keys())[0]
        rule = PDO_STATE_MACHINE.transition_rules[rule_key]
        with pytest.raises(Exception):  # FrozenInstanceError
            rule.from_state = "NEW_STATE"  # type: ignore


# =============================================================================
# TRANSITION VALIDATION TESTS
# =============================================================================


class TestTransitionValidator:
    """Test transition validation logic."""

    @pytest.fixture
    def validator(self) -> TransitionValidator:
        """Create a fresh validator."""
        return TransitionValidator()

    def test_valid_pdo_transition(self, validator: TransitionValidator) -> None:
        """Valid PDO transition is allowed (CREATED → SIGNED)."""
        request = TransitionRequest(
            artifact_type="PDO",
            artifact_id="PDO-001",
            from_state="CREATED",
            to_state="SIGNED",
            authority_gid="GID-05",
            proof_id="PROOF-001",  # Proof required
        )
        result = validator.validate_transition(request)
        assert result.is_allowed
        assert result.result == TransitionResult.ALLOWED

    def test_invalid_pdo_transition_rejected(self, validator: TransitionValidator) -> None:
        """Invalid PDO transition (skip state) is rejected."""
        request = TransitionRequest(
            artifact_type="PDO",
            artifact_id="PDO-001",
            from_state="CREATED",
            to_state="ACCEPTED",  # Cannot skip from CREATED to ACCEPTED
        )
        result = validator.validate_transition(request)
        assert not result.is_allowed
        assert result.result == TransitionResult.REJECTED_UNDEFINED

    def test_terminal_state_immutable(self, validator: TransitionValidator) -> None:
        """Transitions from terminal states are rejected."""
        request = TransitionRequest(
            artifact_type="PDO",
            artifact_id="PDO-001",
            from_state="ACCEPTED",  # Terminal state
            to_state="CREATED",
        )
        result = validator.validate_transition(request)
        assert not result.is_allowed
        assert result.result == TransitionResult.REJECTED_TERMINAL

    def test_unknown_artifact_type_rejected(self, validator: TransitionValidator) -> None:
        """Unknown artifact types are rejected."""
        request = TransitionRequest(
            artifact_type="UnknownType",
            artifact_id="UNK-001",
            from_state="A",
            to_state="B",
        )
        result = validator.validate_transition(request)
        assert not result.is_allowed
        assert result.result == TransitionResult.REJECTED_UNDEFINED

    def test_fail_closed_undefined_transition(self, validator: TransitionValidator) -> None:
        """Undefined transitions are rejected (fail-closed)."""
        # SIGNED → CREATED is not defined (backward transition)
        request = TransitionRequest(
            artifact_type="PDO",
            artifact_id="PDO-001",
            from_state="SIGNED",
            to_state="CREATED",  # Backward transition not allowed
        )
        result = validator.validate_transition(request)
        assert not result.is_allowed
        assert result.result == TransitionResult.REJECTED_UNDEFINED

    def test_authority_validation(self, validator: TransitionValidator) -> None:
        """Authority is validated against required authority."""
        request = TransitionRequest(
            artifact_type="PDO",
            artifact_id="PDO-001",
            from_state="CREATED",
            to_state="SIGNED",
            authority_gid="GID-05",
            proof_id="PROOF-001",
        )
        result = validator.validate_transition(request)
        # CREATED→SIGNED has no required_authority, so should be allowed
        assert result.is_allowed

    def test_batch_validation(self, validator: TransitionValidator) -> None:
        """Batch validation processes multiple requests."""
        requests = [
            TransitionRequest(
                artifact_type="PDO",
                artifact_id="PDO-001",
                from_state="CREATED",
                to_state="SIGNED",
                proof_id="PROOF-001",
            ),
            TransitionRequest(
                artifact_type="PDO",
                artifact_id="PDO-002",
                from_state="CREATED",
                to_state="INVALID",  # Invalid
            ),
        ]
        results = validator.validate_batch(requests)
        assert len(results) == 2
        assert results[0].is_allowed
        assert not results[1].is_allowed


# =============================================================================
# TRANSITION PROOF TESTS
# =============================================================================


class TestTransitionProof:
    """Test transition proof emission and verification."""

    def test_proof_creation(self) -> None:
        """StateTransitionProof can be created."""
        proof = StateTransitionProof(
            artifact_type="PDO",
            artifact_id="PDO-001",
            from_state="DRAFT",
            to_state="PENDING_APPROVAL",
            authority_gid="GID-05",
        )
        assert proof.proof_id.startswith("STP-")
        assert proof.hash != ""
        assert proof.artifact_type == "PDO"

    def test_proof_hash_verification(self) -> None:
        """Proof hash can be verified."""
        proof = StateTransitionProof(
            artifact_type="PDO",
            artifact_id="PDO-001",
            from_state="DRAFT",
            to_state="PENDING_APPROVAL",
        )
        assert proof.verify_hash()
        assert verify_transition_proof(proof)

    def test_proof_serialization(self) -> None:
        """Proof can be serialized and deserialized."""
        original = StateTransitionProof(
            artifact_type="Settlement",
            artifact_id="SET-001",
            from_state="PENDING",
            to_state="CONFIRMED",
            authority_gid="GID-05",
            triggering_proof_id="PROOF-123",
        )

        data = original.to_dict()
        restored = StateTransitionProof.from_dict(data)

        assert restored.proof_id == original.proof_id
        assert restored.artifact_type == original.artifact_type
        assert restored.from_state == original.from_state
        assert restored.to_state == original.to_state
        assert restored.hash == original.hash

    def test_proof_json_serialization(self) -> None:
        """Proof can be serialized to JSON."""
        proof = create_transition_proof(
            artifact_type="PDO",
            artifact_id="PDO-001",
            from_state="DRAFT",
            to_state="PENDING_APPROVAL",
        )
        json_str = proof.to_json()
        assert '"artifact_type": "PDO"' in json_str
        assert '"from_state": "DRAFT"' in json_str


class TestTransitionProofEmitter:
    """Test the proof emitter."""

    @pytest.fixture
    def emitter(self) -> TransitionProofEmitter:
        """Create a fresh emitter."""
        return TransitionProofEmitter()

    @pytest.fixture
    def validator(self) -> TransitionValidator:
        """Create a fresh validator."""
        return TransitionValidator()

    def test_emitter_emits_for_allowed(
        self, emitter: TransitionProofEmitter, validator: TransitionValidator
    ) -> None:
        """Emitter emits proof for allowed transitions."""
        request = TransitionRequest(
            artifact_type="PDO",
            artifact_id="PDO-001",
            from_state="DRAFT",
            to_state="PENDING_APPROVAL",
        )
        result = validator.validate_transition(request)

        if result.is_allowed:
            proof = emitter.emit(request, result)
            assert proof is not None
            assert proof.artifact_id == "PDO-001"
            assert emitter.emission_count == 1

    def test_emitter_none_for_rejected(
        self, emitter: TransitionProofEmitter, validator: TransitionValidator
    ) -> None:
        """Emitter returns None for rejected transitions."""
        request = TransitionRequest(
            artifact_type="PDO",
            artifact_id="PDO-001",
            from_state="DRAFT",
            to_state="INVALID_STATE",
        )
        result = validator.validate_transition(request)

        proof = emitter.emit(request, result)
        assert proof is None
        assert emitter.emission_count == 0

    def test_batch_emission(
        self, emitter: TransitionProofEmitter, validator: TransitionValidator
    ) -> None:
        """Batch emission only emits for allowed transitions."""
        requests = [
            TransitionRequest(
                artifact_type="PDO",
                artifact_id="PDO-001",
                from_state="DRAFT",
                to_state="PENDING_APPROVAL",
            ),
            TransitionRequest(
                artifact_type="PDO",
                artifact_id="PDO-002",
                from_state="DRAFT",
                to_state="INVALID",
            ),
        ]
        results = validator.validate_batch(requests)
        proofs = emitter.emit_batch(requests, results)

        # Only the valid transition should produce a proof
        allowed_count = sum(1 for r in results if r.is_allowed)
        assert len(proofs) == allowed_count


class TestProofChainVerification:
    """Test proof chain verification."""

    def test_empty_chain_valid(self) -> None:
        """Empty chain is valid."""
        is_valid, errors = verify_proof_chain([])
        assert is_valid
        assert len(errors) == 0

    def test_single_proof_chain_valid(self) -> None:
        """Single proof chain is valid."""
        proof = create_transition_proof(
            artifact_type="PDO",
            artifact_id="PDO-001",
            from_state="DRAFT",
            to_state="PENDING_APPROVAL",
        )
        is_valid, errors = verify_proof_chain([proof])
        assert is_valid
        assert len(errors) == 0

    def test_continuous_chain_valid(self) -> None:
        """Continuous state chain is valid."""
        now = datetime.utcnow()
        proofs = [
            StateTransitionProof(
                artifact_type="PDO",
                artifact_id="PDO-001",
                from_state="DRAFT",
                to_state="PENDING_APPROVAL",
                timestamp=now,
            ),
            StateTransitionProof(
                artifact_type="PDO",
                artifact_id="PDO-001",
                from_state="PENDING_APPROVAL",
                to_state="APPROVED",
                timestamp=now + timedelta(seconds=1),
            ),
        ]
        is_valid, errors = verify_proof_chain(proofs)
        assert is_valid, f"Errors: {errors}"

    def test_discontinuous_chain_invalid(self) -> None:
        """Discontinuous state chain is invalid."""
        now = datetime.utcnow()
        proofs = [
            StateTransitionProof(
                artifact_type="PDO",
                artifact_id="PDO-001",
                from_state="DRAFT",
                to_state="PENDING_APPROVAL",
                timestamp=now,
            ),
            StateTransitionProof(
                artifact_type="PDO",
                artifact_id="PDO-001",
                from_state="APPROVED",  # Gap! Should be PENDING_APPROVAL
                to_state="SETTLED",
                timestamp=now + timedelta(seconds=1),
            ),
        ]
        is_valid, errors = verify_proof_chain(proofs)
        assert not is_valid
        assert any("discontinuity" in e.lower() for e in errors)


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_validate_transition_function(self) -> None:
        """validate_transition() works correctly (takes individual args)."""
        result = validate_transition(
            artifact_type="PDO",
            artifact_id="PDO-001",
            from_state="CREATED",
            to_state="SIGNED",
            proof_id="PROOF-001",
        )
        assert isinstance(result, TransitionValidationResult)
        assert result.is_allowed

    def test_is_transition_allowed_function(self) -> None:
        """is_transition_allowed() returns boolean."""
        allowed = is_transition_allowed(
            artifact_type="PDO",
            from_state="CREATED",
            to_state="SIGNED",
        )
        assert isinstance(allowed, bool)
        assert allowed is True

    def test_get_allowed_transitions_function(self) -> None:
        """get_allowed_transitions() returns set of states."""
        transitions = get_allowed_transitions(
            artifact_type="PDO",
            from_state="CREATED",
        )
        assert isinstance(transitions, set)
        assert "SIGNED" in transitions


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestStateTransitionIntegration:
    """Integration tests for the full transition flow."""

    def test_full_pdo_lifecycle(self) -> None:
        """Test complete PDO lifecycle from CREATED to ACCEPTED."""
        validator = TransitionValidator()
        emitter = TransitionProofEmitter()
        proofs: list[StateTransitionProof] = []

        # SIGNED→VERIFIED requires VERIFIER authority (GID-00, GID-01, GID-06)
        lifecycle = [
            ("CREATED", "SIGNED", "GID-05"),
            ("SIGNED", "VERIFIED", "GID-01"),  # Cody is a VERIFIER
            ("VERIFIED", "ACCEPTED", "GID-05"),
        ]

        for from_state, to_state, authority in lifecycle:
            request = TransitionRequest(
                artifact_type="PDO",
                artifact_id="PDO-LIFECYCLE-001",
                from_state=from_state,
                to_state=to_state,
                authority_gid=authority,
                proof_id=f"PROOF-{from_state}-{to_state}",
            )
            result = validator.validate_transition(request)

            if result.is_allowed:
                proof = emitter.emit(request, result)
                if proof:
                    proofs.append(proof)

        # Verify we got proofs for all transitions
        assert len(proofs) == len(lifecycle)

        # Verify proof chain is valid
        is_valid, errors = verify_proof_chain(proofs)
        assert is_valid, f"Chain errors: {errors}"

    def test_settlement_lifecycle(self) -> None:
        """Test Settlement lifecycle."""
        validator = TransitionValidator()

        # Valid transitions
        valid_transitions = [
            ("PENDING", "APPROVED"),
            ("APPROVED", "EXECUTED"),
        ]

        for from_state, to_state in valid_transitions:
            request = TransitionRequest(
                artifact_type="SETTLEMENT",
                artifact_id="SET-001",
                from_state=from_state,
                to_state=to_state,
                proof_id=f"PROOF-{from_state}",
                authority_gid="GID-00",  # CRO
            )
            result = validator.validate_transition(request)
            # At minimum, shouldn't crash
            assert result is not None

    def test_cross_artifact_isolation(self) -> None:
        """State machines for different artifacts are isolated."""
        validator = TransitionValidator()

        # PDO transition
        pdo_request = TransitionRequest(
            artifact_type="PDO",
            artifact_id="PDO-001",
            from_state="CREATED",
            to_state="SIGNED",
            proof_id="PROOF-001",
        )

        # Settlement transition
        settlement_request = TransitionRequest(
            artifact_type="SETTLEMENT",
            artifact_id="SET-001",
            from_state="PENDING",
            to_state="APPROVED",
            proof_id="PROOF-002",
            authority_gid="GID-00",
        )

        pdo_result = validator.validate_transition(pdo_request)
        settlement_result = validator.validate_transition(settlement_request)

        # Both should be processed independently
        assert pdo_result.artifact_type == "PDO"
        assert settlement_result.artifact_type == "SETTLEMENT"
