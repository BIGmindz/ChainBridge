"""
ChainBridge State Validator

Atlas (GID-05) — System State Engine
Authority: Benson (GID-00)

This module validates state consistency and enforces invariants.
All validation is READ-ONLY — no state modification occurs here.

INVARIANTS ENFORCED:
- INV-S01: One state per artifact
- INV-S02: Forward-only transitions
- INV-S03: No retroactive mutation
- INV-S04: No conflicting truths
- INV-S05: Time monotonicity
- INV-S06: Proof lineage required
- INV-S09: No orphan artifacts
- INV-S10: Transition validity
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from .state_schema import (
    ArtifactType,
    EventStateRecord,
    PDOStateRecord,
    ProofStateRecord,
    SettlementStateRecord,
    ShipmentStateRecord,
    StateTransition,
    is_valid_transition,
)


class ViolationType(str, Enum):
    """Types of state invariant violations."""

    DUPLICATE_STATE = "DUPLICATE_STATE"
    BACKWARD_TRANSITION = "BACKWARD_TRANSITION"
    RETROACTIVE_MUTATION = "RETROACTIVE_MUTATION"
    CONFLICTING_TRUTH = "CONFLICTING_TRUTH"
    TEMPORAL_VIOLATION = "TEMPORAL_VIOLATION"
    MISSING_PROOF = "MISSING_PROOF"
    ORPHAN_ARTIFACT = "ORPHAN_ARTIFACT"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    FINALITY_VIOLATION = "FINALITY_VIOLATION"


class ViolationSeverity(str, Enum):
    """Severity levels for violations."""

    CRITICAL = "CRITICAL"  # Halt system
    HIGH = "HIGH"  # Block operation
    MEDIUM = "MEDIUM"  # Quarantine + investigate
    LOW = "LOW"  # Log + alert


@dataclass
class StateViolation:
    """Record of a state invariant violation."""

    violation_id: str
    violation_type: ViolationType
    severity: ViolationSeverity
    artifact_type: ArtifactType
    artifact_id: str
    description: str
    detected_at: datetime = field(default_factory=datetime.utcnow)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize violation for logging/reporting."""
        return {
            "violation_id": self.violation_id,
            "violation_type": self.violation_type.value,
            "severity": self.severity.value,
            "artifact_type": self.artifact_type.value,
            "artifact_id": self.artifact_id,
            "description": self.description,
            "detected_at": self.detected_at.isoformat(),
            "context": self.context,
        }


@dataclass
class ValidationResult:
    """Result of a state validation operation."""

    is_valid: bool
    violations: list[StateViolation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.utcnow)
    artifact_count: int = 0
    transition_count: int = 0

    @property
    def has_critical_violations(self) -> bool:
        """Check if any critical violations exist."""
        return any(v.severity == ViolationSeverity.CRITICAL for v in self.violations)

    @property
    def violation_count(self) -> int:
        """Total number of violations."""
        return len(self.violations)

    def to_dict(self) -> dict[str, Any]:
        """Serialize result for logging/reporting."""
        return {
            "is_valid": self.is_valid,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": self.warnings,
            "validated_at": self.validated_at.isoformat(),
            "artifact_count": self.artifact_count,
            "transition_count": self.transition_count,
            "has_critical_violations": self.has_critical_violations,
            "violation_count": self.violation_count,
        }


class StateValidator:
    """
    Validates ChainBridge state consistency.

    This class is READ-ONLY. It does not modify any state.
    All methods return validation results without side effects.
    """

    def __init__(self) -> None:
        """Initialize the validator."""
        self._violation_counter = 0

    def _generate_violation_id(self) -> str:
        """Generate unique violation ID."""
        self._violation_counter += 1
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"VIO-{timestamp}-{self._violation_counter:04d}"

    def validate_transition(
        self,
        transition: StateTransition,
        current_state: Optional[str] = None,
        current_timestamp: Optional[datetime] = None,
        is_finalized: bool = False,
    ) -> ValidationResult:
        """
        Validate a proposed state transition.

        Checks:
        - INV-S02: Forward-only (timestamp must advance)
        - INV-S03: No retroactive mutation (if finalized)
        - INV-S06: Proof lineage required
        - INV-S10: Transition validity
        """
        violations: list[StateViolation] = []
        warnings: list[str] = []

        # INV-S03: No retroactive mutation
        if is_finalized:
            violations.append(
                StateViolation(
                    violation_id=self._generate_violation_id(),
                    violation_type=ViolationType.FINALITY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    artifact_type=transition.artifact_type,
                    artifact_id=transition.artifact_id,
                    description="Cannot transition finalized artifact",
                    context={"from_state": transition.from_state, "to_state": transition.to_state},
                )
            )

        # INV-S02: Forward-only transitions
        if current_timestamp and transition.timestamp <= current_timestamp:
            violations.append(
                StateViolation(
                    violation_id=self._generate_violation_id(),
                    violation_type=ViolationType.BACKWARD_TRANSITION,
                    severity=ViolationSeverity.CRITICAL,
                    artifact_type=transition.artifact_type,
                    artifact_id=transition.artifact_id,
                    description="Transition timestamp must be after current state timestamp",
                    context={
                        "current_timestamp": current_timestamp.isoformat(),
                        "transition_timestamp": transition.timestamp.isoformat(),
                    },
                )
            )

        # INV-S06: Proof lineage required
        if not transition.proof_id:
            violations.append(
                StateViolation(
                    violation_id=self._generate_violation_id(),
                    violation_type=ViolationType.MISSING_PROOF,
                    severity=ViolationSeverity.HIGH,
                    artifact_type=transition.artifact_type,
                    artifact_id=transition.artifact_id,
                    description="State transition requires proof_id",
                    context={"from_state": transition.from_state, "to_state": transition.to_state},
                )
            )

        # INV-S10: Transition validity
        if current_state and current_state != transition.from_state:
            violations.append(
                StateViolation(
                    violation_id=self._generate_violation_id(),
                    violation_type=ViolationType.CONFLICTING_TRUTH,
                    severity=ViolationSeverity.CRITICAL,
                    artifact_type=transition.artifact_type,
                    artifact_id=transition.artifact_id,
                    description="Transition from_state does not match current state",
                    context={
                        "current_state": current_state,
                        "transition_from_state": transition.from_state,
                    },
                )
            )

        if not is_valid_transition(
            transition.artifact_type,
            transition.from_state,
            transition.to_state,
        ):
            violations.append(
                StateViolation(
                    violation_id=self._generate_violation_id(),
                    violation_type=ViolationType.INVALID_TRANSITION,
                    severity=ViolationSeverity.HIGH,
                    artifact_type=transition.artifact_type,
                    artifact_id=transition.artifact_id,
                    description=f"Invalid transition: {transition.from_state} → {transition.to_state}",
                    context={
                        "from_state": transition.from_state,
                        "to_state": transition.to_state,
                    },
                )
            )

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            transition_count=1,
        )

    def validate_event_sequence(
        self,
        events: list[EventStateRecord],
    ) -> ValidationResult:
        """
        Validate a sequence of events for temporal ordering.

        Checks:
        - INV-S05: Time monotonicity
        """
        violations: list[StateViolation] = []
        warnings: list[str] = []

        if not events:
            return ValidationResult(is_valid=True, warnings=["Empty event sequence"])

        # Sort by sequence number for validation
        sorted_events = sorted(events, key=lambda e: e.sequence_number)

        prev_timestamp: Optional[datetime] = None
        prev_sequence: Optional[int] = None

        for event in sorted_events:
            # Check timestamp monotonicity
            if prev_timestamp and event.timestamp < prev_timestamp:
                violations.append(
                    StateViolation(
                        violation_id=self._generate_violation_id(),
                        violation_type=ViolationType.TEMPORAL_VIOLATION,
                        severity=ViolationSeverity.HIGH,
                        artifact_type=ArtifactType.EVENT,
                        artifact_id=event.event_id,
                        description="Event timestamp violates time monotonicity",
                        context={
                            "event_timestamp": event.timestamp.isoformat(),
                            "previous_timestamp": prev_timestamp.isoformat(),
                            "sequence_number": event.sequence_number,
                        },
                    )
                )

            # Check sequence number continuity
            if prev_sequence is not None and event.sequence_number != prev_sequence + 1:
                warnings.append(
                    f"Gap in sequence numbers: {prev_sequence} → {event.sequence_number}"
                )

            prev_timestamp = event.timestamp
            prev_sequence = event.sequence_number

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            artifact_count=len(events),
        )

    def validate_proof_lineage(
        self,
        artifact_id: str,
        artifact_type: ArtifactType,
        proof_ids: list[str],
        state_proof_id: Optional[str],
    ) -> ValidationResult:
        """
        Validate proof lineage for an artifact.

        Checks:
        - INV-S06: Proof lineage required
        - INV-S07: State-proof bidirectional binding
        """
        violations: list[StateViolation] = []
        warnings: list[str] = []

        # INV-S06: Proof lineage required
        if not state_proof_id:
            violations.append(
                StateViolation(
                    violation_id=self._generate_violation_id(),
                    violation_type=ViolationType.MISSING_PROOF,
                    severity=ViolationSeverity.HIGH,
                    artifact_type=artifact_type,
                    artifact_id=artifact_id,
                    description="Artifact has no associated proof_id",
                    context={},
                )
            )
        elif state_proof_id not in proof_ids:
            # INV-S07: Bidirectional binding check
            violations.append(
                StateViolation(
                    violation_id=self._generate_violation_id(),
                    violation_type=ViolationType.ORPHAN_ARTIFACT,
                    severity=ViolationSeverity.MEDIUM,
                    artifact_type=artifact_type,
                    artifact_id=artifact_id,
                    description="State references proof_id that does not exist",
                    context={"referenced_proof_id": state_proof_id},
                )
            )

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            artifact_count=1,
        )

    def validate_no_duplicate_states(
        self,
        artifact_id: str,
        artifact_type: ArtifactType,
        state_records: list[Any],
    ) -> ValidationResult:
        """
        Validate that only one state exists per artifact.

        Checks:
        - INV-S01: One state per artifact
        - INV-S04: No conflicting truths
        """
        violations: list[StateViolation] = []

        if len(state_records) > 1:
            violations.append(
                StateViolation(
                    violation_id=self._generate_violation_id(),
                    violation_type=ViolationType.DUPLICATE_STATE,
                    severity=ViolationSeverity.CRITICAL,
                    artifact_type=artifact_type,
                    artifact_id=artifact_id,
                    description=f"Multiple state records found: {len(state_records)}",
                    context={"record_count": len(state_records)},
                )
            )

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            artifact_count=len(state_records),
        )

    def validate_orphan_check(
        self,
        artifact_id: str,
        artifact_type: ArtifactType,
        parent_reference: Optional[str],
        is_genesis: bool = False,
    ) -> ValidationResult:
        """
        Validate artifact has proper parent reference.

        Checks:
        - INV-S09: No orphan artifacts
        """
        violations: list[StateViolation] = []

        if not parent_reference and not is_genesis:
            violations.append(
                StateViolation(
                    violation_id=self._generate_violation_id(),
                    violation_type=ViolationType.ORPHAN_ARTIFACT,
                    severity=ViolationSeverity.MEDIUM,
                    artifact_type=artifact_type,
                    artifact_id=artifact_id,
                    description="Artifact has no parent reference and is not marked as genesis",
                    context={"is_genesis": is_genesis},
                )
            )

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            artifact_count=1,
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def validate_state_transition(
    transition: StateTransition,
    current_state: Optional[str] = None,
    current_timestamp: Optional[datetime] = None,
    is_finalized: bool = False,
) -> ValidationResult:
    """Convenience function for transition validation."""
    validator = StateValidator()
    return validator.validate_transition(
        transition=transition,
        current_state=current_state,
        current_timestamp=current_timestamp,
        is_finalized=is_finalized,
    )


def validate_event_ordering(events: list[EventStateRecord]) -> ValidationResult:
    """Convenience function for event sequence validation."""
    validator = StateValidator()
    return validator.validate_event_sequence(events)
