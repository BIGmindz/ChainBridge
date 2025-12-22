"""
ChainBridge State Replay Engine

Atlas (GID-05) — System State Engine
Authority: Benson (GID-00)

This module provides deterministic state replay from event logs.
Replay is READ-ONLY and used for audit, verification, and dispute resolution.

INVARIANT ENFORCED:
- INV-S08: Replay Determinism — replay(event_log) = current_state
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .state_schema import (
    ArtifactType,
    EventStateRecord,
    EventType,
    PDOState,
    SettlementState,
    ShipmentState,
    is_valid_transition,
)
from .state_validator import StateValidator, ValidationResult, ViolationSeverity


@dataclass
class ReplayState:
    """Intermediate state during replay."""

    artifact_type: ArtifactType
    artifact_id: str
    current_state: str
    last_timestamp: datetime
    event_count: int = 0
    transition_count: int = 0
    state_hash: str = ""

    def compute_hash(self) -> str:
        """Compute deterministic hash of current state."""
        state_data = {
            "artifact_type": self.artifact_type.value,
            "artifact_id": self.artifact_id,
            "current_state": self.current_state,
            "last_timestamp": self.last_timestamp.isoformat(),
            "event_count": self.event_count,
            "transition_count": self.transition_count,
        }
        serialized = json.dumps(state_data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()


@dataclass
class ReplayResult:
    """Result of a state replay operation."""

    is_deterministic: bool
    final_state: Optional[ReplayState] = None
    expected_state: Optional[str] = None
    computed_state: Optional[str] = None
    state_hash: str = ""
    expected_hash: str = ""
    events_processed: int = 0
    transitions_applied: int = 0
    validation_errors: list[str] = field(default_factory=list)
    replayed_at: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0

    @property
    def hashes_match(self) -> bool:
        """Check if computed hash matches expected."""
        return self.state_hash == self.expected_hash if self.expected_hash else True

    def to_dict(self) -> dict[str, Any]:
        """Serialize result for logging/reporting."""
        return {
            "is_deterministic": self.is_deterministic,
            "final_state": self.final_state.current_state if self.final_state else None,
            "expected_state": self.expected_state,
            "computed_state": self.computed_state,
            "state_hash": self.state_hash,
            "expected_hash": self.expected_hash,
            "hashes_match": self.hashes_match,
            "events_processed": self.events_processed,
            "transitions_applied": self.transitions_applied,
            "validation_errors": self.validation_errors,
            "replayed_at": self.replayed_at.isoformat(),
            "duration_ms": self.duration_ms,
        }


class StateReplayEngine:
    """
    Deterministic state replay from event logs.

    This engine processes events in order and computes the resulting state.
    It is READ-ONLY and does not modify any persistent state.

    Used for:
    - Audit verification
    - Dispute resolution
    - State consistency checks
    - Disaster recovery validation
    """

    # Event type to state transition mappings
    EVENT_STATE_MAPPINGS: dict[EventType, dict[ArtifactType, str]] = {
        EventType.SHIPMENT_CREATED: {ArtifactType.SHIPMENT: ShipmentState.CREATED.value},
        EventType.SHIPMENT_DEPARTED: {ArtifactType.SHIPMENT: ShipmentState.IN_TRANSIT.value},
        EventType.SHIPMENT_DELIVERED: {ArtifactType.SHIPMENT: ShipmentState.DELIVERED.value},
        EventType.SHIPMENT_EXCEPTION: {ArtifactType.SHIPMENT: ShipmentState.EXCEPTION.value},
        EventType.SHIPMENT_RESOLVED: {ArtifactType.SHIPMENT: ShipmentState.RESOLVED.value},
        EventType.SHIPMENT_CANCELLED: {ArtifactType.SHIPMENT: ShipmentState.CANCELLED.value},
        EventType.SETTLEMENT_INITIATED: {ArtifactType.SETTLEMENT: SettlementState.PENDING.value},
        EventType.SETTLEMENT_APPROVED: {ArtifactType.SETTLEMENT: SettlementState.APPROVED.value},
        EventType.SETTLEMENT_EXECUTED: {ArtifactType.SETTLEMENT: SettlementState.EXECUTED.value},
        EventType.SETTLEMENT_FINALIZED: {ArtifactType.SETTLEMENT: SettlementState.FINALIZED.value},
        EventType.SETTLEMENT_REJECTED: {ArtifactType.SETTLEMENT: SettlementState.REJECTED.value},
        EventType.SETTLEMENT_DISPUTED: {ArtifactType.SETTLEMENT: SettlementState.DISPUTED.value},
        EventType.PDO_CREATED: {ArtifactType.PDO: PDOState.CREATED.value},
        EventType.PDO_SIGNED: {ArtifactType.PDO: PDOState.SIGNED.value},
        EventType.PDO_VERIFIED: {ArtifactType.PDO: PDOState.VERIFIED.value},
        EventType.PDO_REJECTED: {ArtifactType.PDO: PDOState.REJECTED.value},
    }

    def __init__(self) -> None:
        """Initialize the replay engine."""
        self._validator = StateValidator()

    def replay_events(
        self,
        events: list[EventStateRecord],
        artifact_type: ArtifactType,
        artifact_id: str,
        expected_final_state: Optional[str] = None,
        expected_hash: Optional[str] = None,
    ) -> ReplayResult:
        """
        Replay a sequence of events and compute the resulting state.

        Args:
            events: Ordered list of events to replay
            artifact_type: Type of artifact being replayed
            artifact_id: ID of the artifact
            expected_final_state: Optional expected final state for verification
            expected_hash: Optional expected state hash for verification

        Returns:
            ReplayResult with computed state and verification status
        """
        start_time = datetime.utcnow()
        validation_errors: list[str] = []

        if not events:
            return ReplayResult(
                is_deterministic=True,
                validation_errors=["No events to replay"],
                events_processed=0,
            )

        # Sort events by sequence number for deterministic processing
        sorted_events = sorted(events, key=lambda e: (e.sequence_number, e.timestamp))

        # Validate event sequence ordering
        validation_result = self._validator.validate_event_sequence(sorted_events)
        if not validation_result.is_valid:
            for v in validation_result.violations:
                validation_errors.append(f"{v.violation_type.value}: {v.description}")

        # Initialize replay state with first event
        first_event = sorted_events[0]
        initial_state = self._get_state_from_event(first_event)

        if not initial_state:
            return ReplayResult(
                is_deterministic=False,
                validation_errors=[f"Cannot determine initial state from event type: {first_event.event_type}"],
                events_processed=1,
            )

        replay_state = ReplayState(
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            current_state=initial_state,
            last_timestamp=first_event.timestamp,
            event_count=1,
        )

        # Process remaining events
        for event in sorted_events[1:]:
            new_state = self._get_state_from_event(event)

            if not new_state:
                # Non-state-changing event, just update timestamp
                replay_state.last_timestamp = event.timestamp
                replay_state.event_count += 1
                continue

            # Validate transition
            if not is_valid_transition(artifact_type, replay_state.current_state, new_state):
                validation_errors.append(
                    f"Invalid transition: {replay_state.current_state} → {new_state} "
                    f"at event {event.event_id}"
                )

            # Apply transition
            replay_state.current_state = new_state
            replay_state.last_timestamp = event.timestamp
            replay_state.event_count += 1
            replay_state.transition_count += 1

        # Compute final hash
        replay_state.state_hash = replay_state.compute_hash()

        # Determine if replay is deterministic
        is_deterministic = True

        if expected_final_state and replay_state.current_state != expected_final_state:
            is_deterministic = False
            validation_errors.append(
                f"State mismatch: expected {expected_final_state}, "
                f"computed {replay_state.current_state}"
            )

        if expected_hash and replay_state.state_hash != expected_hash:
            is_deterministic = False
            validation_errors.append(
                f"Hash mismatch: expected {expected_hash}, "
                f"computed {replay_state.state_hash}"
            )

        # Also fail if there were any validation errors during replay
        if validation_errors:
            is_deterministic = False

        end_time = datetime.utcnow()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        return ReplayResult(
            is_deterministic=is_deterministic,
            final_state=replay_state,
            expected_state=expected_final_state,
            computed_state=replay_state.current_state,
            state_hash=replay_state.state_hash,
            expected_hash=expected_hash or "",
            events_processed=replay_state.event_count,
            transitions_applied=replay_state.transition_count,
            validation_errors=validation_errors,
            replayed_at=end_time,
            duration_ms=duration_ms,
        )

    def _get_state_from_event(self, event: EventStateRecord) -> Optional[str]:
        """
        Extract the target state from an event type.

        Returns None if the event doesn't map to a state change.
        """
        mappings = self.EVENT_STATE_MAPPINGS.get(event.event_type, {})
        return mappings.get(event.artifact_type)

    def verify_state_consistency(
        self,
        events: list[EventStateRecord],
        artifact_type: ArtifactType,
        artifact_id: str,
        current_state: str,
        current_hash: str,
    ) -> ReplayResult:
        """
        Verify that replaying events produces the current state.

        This is the primary consistency check used for audits.
        """
        return self.replay_events(
            events=events,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            expected_final_state=current_state,
            expected_hash=current_hash,
        )

    def compute_state_at_time(
        self,
        events: list[EventStateRecord],
        artifact_type: ArtifactType,
        artifact_id: str,
        target_time: datetime,
    ) -> ReplayResult:
        """
        Compute the state at a specific point in time.

        Useful for historical queries and dispute resolution.
        """
        # Filter events up to target time
        filtered_events = [e for e in events if e.timestamp <= target_time]

        return self.replay_events(
            events=filtered_events,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def replay_artifact_events(
    events: list[EventStateRecord],
    artifact_type: ArtifactType,
    artifact_id: str,
    expected_state: Optional[str] = None,
) -> ReplayResult:
    """Convenience function for event replay."""
    engine = StateReplayEngine()
    return engine.replay_events(
        events=events,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        expected_final_state=expected_state,
    )


def verify_replay_determinism(
    events: list[EventStateRecord],
    artifact_type: ArtifactType,
    artifact_id: str,
    current_state: str,
    current_hash: str,
) -> bool:
    """Check if replay produces deterministic result matching current state."""
    engine = StateReplayEngine()
    result = engine.verify_state_consistency(
        events=events,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        current_state=current_state,
        current_hash=current_hash,
    )
    return result.is_deterministic
