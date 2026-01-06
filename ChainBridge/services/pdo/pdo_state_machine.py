"""
PDO State Machine - State management for Payment Decision Objects.

PAC Reference: PAC-OCC-P02
Constitutional Authority: OCC_CONSTITUTION_v1.0, Article V
Invariants Enforced: INV-OCC-008 (State Determinism), INV-OVR-006 (Override Marker Permanence)

This module implements a deterministic state machine for PDOs that:
1. Tracks all state transitions with full audit trail
2. Applies override markers that cannot be removed
3. Ensures deterministic replay capability
4. Enforces fail-closed semantics on invalid transitions
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class PDOState(str, Enum):
    """
    Valid states for Payment Decision Objects.
    
    Constitutional basis: State transitions must be deterministic
    and auditable per INV-OCC-008.
    """
    # Initial states
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    
    # Agent decision states
    AGENT_APPROVED = "AGENT_APPROVED"
    AGENT_BLOCKED = "AGENT_BLOCKED"
    AGENT_FLAGGED = "AGENT_FLAGGED"
    
    # Policy decision states
    POLICY_APPROVED = "POLICY_APPROVED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    
    # Operator decision states (override)
    OPERATOR_APPROVED = "OPERATOR_APPROVED"
    OPERATOR_BLOCKED = "OPERATOR_BLOCKED"
    OPERATOR_MODIFIED = "OPERATOR_MODIFIED"
    
    # Processing states
    IN_REVIEW = "IN_REVIEW"
    ESCALATED = "ESCALATED"
    
    # Terminal states
    SETTLED = "SETTLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class TransitionType(str, Enum):
    """Type of state transition."""
    AGENT = "AGENT"          # Automated agent decision
    POLICY = "POLICY"        # Policy engine decision
    OPERATOR = "OPERATOR"    # Human operator action
    SYSTEM = "SYSTEM"        # System event (timeout, etc.)


# Valid state transitions matrix
# Format: source_state -> set of valid (target_state, transition_type) pairs
VALID_TRANSITIONS: dict[PDOState, set[tuple[PDOState, TransitionType]]] = {
    PDOState.PENDING: {
        (PDOState.SUBMITTED, TransitionType.SYSTEM),
        (PDOState.CANCELLED, TransitionType.OPERATOR),
    },
    PDOState.SUBMITTED: {
        (PDOState.AGENT_APPROVED, TransitionType.AGENT),
        (PDOState.AGENT_BLOCKED, TransitionType.AGENT),
        (PDOState.AGENT_FLAGGED, TransitionType.AGENT),
        (PDOState.CANCELLED, TransitionType.OPERATOR),
    },
    PDOState.AGENT_APPROVED: {
        (PDOState.POLICY_APPROVED, TransitionType.POLICY),
        (PDOState.POLICY_BLOCKED, TransitionType.POLICY),
        (PDOState.IN_REVIEW, TransitionType.OPERATOR),
        (PDOState.OPERATOR_BLOCKED, TransitionType.OPERATOR),  # Override
    },
    PDOState.AGENT_BLOCKED: {
        (PDOState.IN_REVIEW, TransitionType.OPERATOR),
        (PDOState.OPERATOR_APPROVED, TransitionType.OPERATOR),  # Override
        (PDOState.REJECTED, TransitionType.SYSTEM),
    },
    PDOState.AGENT_FLAGGED: {
        (PDOState.IN_REVIEW, TransitionType.OPERATOR),
        (PDOState.ESCALATED, TransitionType.OPERATOR),
        (PDOState.OPERATOR_APPROVED, TransitionType.OPERATOR),
        (PDOState.OPERATOR_BLOCKED, TransitionType.OPERATOR),
    },
    PDOState.POLICY_APPROVED: {
        (PDOState.SETTLED, TransitionType.SYSTEM),
        (PDOState.OPERATOR_BLOCKED, TransitionType.OPERATOR),  # Override
        (PDOState.OPERATOR_MODIFIED, TransitionType.OPERATOR),  # Override
    },
    PDOState.POLICY_BLOCKED: {
        (PDOState.REJECTED, TransitionType.SYSTEM),
        (PDOState.IN_REVIEW, TransitionType.OPERATOR),
        (PDOState.OPERATOR_APPROVED, TransitionType.OPERATOR),  # Override
    },
    PDOState.OPERATOR_APPROVED: {
        (PDOState.SETTLED, TransitionType.SYSTEM),
        (PDOState.OPERATOR_MODIFIED, TransitionType.OPERATOR),
    },
    PDOState.OPERATOR_BLOCKED: {
        (PDOState.REJECTED, TransitionType.SYSTEM),
        (PDOState.OPERATOR_APPROVED, TransitionType.OPERATOR),  # Re-override (different operator)
    },
    PDOState.OPERATOR_MODIFIED: {
        (PDOState.SETTLED, TransitionType.SYSTEM),
        (PDOState.OPERATOR_APPROVED, TransitionType.OPERATOR),
        (PDOState.OPERATOR_BLOCKED, TransitionType.OPERATOR),
    },
    PDOState.IN_REVIEW: {
        (PDOState.ESCALATED, TransitionType.OPERATOR),
        (PDOState.OPERATOR_APPROVED, TransitionType.OPERATOR),
        (PDOState.OPERATOR_BLOCKED, TransitionType.OPERATOR),
        (PDOState.EXPIRED, TransitionType.SYSTEM),
    },
    PDOState.ESCALATED: {
        (PDOState.OPERATOR_APPROVED, TransitionType.OPERATOR),
        (PDOState.OPERATOR_BLOCKED, TransitionType.OPERATOR),
        (PDOState.EXPIRED, TransitionType.SYSTEM),
    },
    # Terminal states - no outbound transitions
    PDOState.SETTLED: set(),
    PDOState.REJECTED: set(),
    PDOState.CANCELLED: set(),
    PDOState.EXPIRED: set(),
}


@dataclass(frozen=True)
class PDOTransition:
    """
    A single state transition record.
    
    Immutable for hash chain integrity per INV-OCC-008.
    """
    id: str
    pdo_id: str
    from_state: PDOState
    to_state: PDOState
    transition_type: TransitionType
    actor_id: str  # Operator ID for OPERATOR, Agent GID for AGENT, "SYSTEM" for SYSTEM
    timestamp: datetime
    reason: str
    is_override: bool
    override_id: str | None  # Links to override record if override
    hash_previous: str | None
    hash_current: str
    
    @staticmethod
    def compute_hash(
        pdo_id: str,
        from_state: PDOState,
        to_state: PDOState,
        actor_id: str,
        timestamp: datetime,
        hash_previous: str | None,
    ) -> str:
        """Compute hash for transition record."""
        content = (
            f"{pdo_id}|{from_state.value}|{to_state.value}|"
            f"{actor_id}|{timestamp.isoformat()}|{hash_previous or 'GENESIS'}"
        )
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class PDO:
    """
    Payment Decision Object.
    
    Tracks current state and maintains override markers per INV-OVR-006.
    """
    id: str
    value: float
    currency: str
    current_state: PDOState
    created_at: datetime
    updated_at: datetime
    
    # Override tracking per INV-OVR-006
    is_overridden: bool = False
    override_id: str | None = None
    override_timestamp: datetime | None = None
    original_decision: PDOState | None = None
    
    # Additional metadata
    original_operator_id: str | None = None  # For INV-OVR-010 (no self-override)
    metadata: dict[str, Any] = field(default_factory=dict)


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""


class PDONotFoundError(Exception):
    """Raised when PDO is not found."""


class PDOStateMachine:
    """
    Deterministic state machine for PDO lifecycle management.
    
    Constitutional Invariants Enforced:
    - INV-OCC-008: State Determinism - All transitions are deterministic
    - INV-OVR-006: Override Marker Permanence - Override markers cannot be removed
    - INV-OVR-009: Override Replay Determinism - State changes are replayable
    
    Fail-closed semantics: Invalid transitions are rejected.
    """
    
    # Singleton enforcement
    _INSTANCE: PDOStateMachine | None = None
    _LOCK = threading.Lock()
    
    def __init__(
        self,
        on_transition: Callable[[PDOTransition], None] | None = None,
        on_override: Callable[[PDO, PDOTransition], None] | None = None,
    ) -> None:
        """
        Initialize PDO State Machine.
        
        Args:
            on_transition: Callback for all state transitions
            on_override: Callback specifically for override transitions
        """
        self._pdos: dict[str, PDO] = {}
        self._transitions: dict[str, list[PDOTransition]] = {}  # pdo_id -> transitions
        self._last_hash: dict[str, str] = {}  # pdo_id -> last transition hash
        self._lock = threading.Lock()
        self._on_transition = on_transition
        self._on_override = on_override
        
        # Metrics
        self._transition_count = 0
        self._override_count = 0
        self._rejection_count = 0
        
    @classmethod
    def get_instance(cls) -> PDOStateMachine:
        """Get singleton instance."""
        if cls._INSTANCE is None:
            with cls._LOCK:
                if cls._INSTANCE is None:
                    cls._INSTANCE = cls()
        return cls._INSTANCE
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton for testing."""
        with cls._LOCK:
            cls._INSTANCE = None
    
    def register_pdo(self, pdo: PDO) -> None:
        """
        Register a new PDO with the state machine.
        
        Args:
            pdo: PDO to register
        """
        with self._lock:
            self._pdos[pdo.id] = pdo
            self._transitions[pdo.id] = []
            self._last_hash[pdo.id] = None
    
    def get_pdo(self, pdo_id: str) -> PDO | None:
        """Get PDO by ID."""
        with self._lock:
            return self._pdos.get(pdo_id)
    
    def transition(
        self,
        pdo_id: str,
        to_state: PDOState,
        transition_type: TransitionType,
        actor_id: str,
        reason: str,
        override_id: str | None = None,
    ) -> PDOTransition:
        """
        Perform a state transition.
        
        Args:
            pdo_id: ID of PDO to transition
            to_state: Target state
            transition_type: Type of transition
            actor_id: ID of actor performing transition
            reason: Reason for transition
            override_id: Override record ID if this is an override
            
        Returns:
            PDOTransition record
            
        Raises:
            PDONotFoundError: If PDO not found
            InvalidTransitionError: If transition is invalid
        """
        with self._lock:
            # Get PDO
            pdo = self._pdos.get(pdo_id)
            if pdo is None:
                raise PDONotFoundError(f"PDO not found: {pdo_id}")
            
            # Validate transition
            valid_targets = VALID_TRANSITIONS.get(pdo.current_state, set())
            if (to_state, transition_type) not in valid_targets:
                self._rejection_count += 1
                raise InvalidTransitionError(
                    f"Invalid transition: {pdo.current_state.value} -> {to_state.value} "
                    f"via {transition_type.value} is not permitted"
                )
            
            # Determine if this is an override
            is_override = (
                transition_type == TransitionType.OPERATOR
                and pdo.current_state in (
                    PDOState.AGENT_APPROVED,
                    PDOState.AGENT_BLOCKED,
                    PDOState.POLICY_APPROVED,
                    PDOState.POLICY_BLOCKED,
                )
                and to_state in (
                    PDOState.OPERATOR_APPROVED,
                    PDOState.OPERATOR_BLOCKED,
                    PDOState.OPERATOR_MODIFIED,
                )
            )
            
            # Create transition record
            timestamp = datetime.now(timezone.utc)
            transition_id = f"TR-{pdo_id}-{self._transition_count + 1}"
            
            hash_current = PDOTransition.compute_hash(
                pdo_id=pdo_id,
                from_state=pdo.current_state,
                to_state=to_state,
                actor_id=actor_id,
                timestamp=timestamp,
                hash_previous=self._last_hash.get(pdo_id),
            )
            
            transition = PDOTransition(
                id=transition_id,
                pdo_id=pdo_id,
                from_state=pdo.current_state,
                to_state=to_state,
                transition_type=transition_type,
                actor_id=actor_id,
                timestamp=timestamp,
                reason=reason,
                is_override=is_override,
                override_id=override_id,
                hash_previous=self._last_hash.get(pdo_id),
                hash_current=hash_current,
            )
            
            # Update PDO state
            old_state = pdo.current_state
            pdo.current_state = to_state
            pdo.updated_at = timestamp
            
            # Apply override markers per INV-OVR-006
            if is_override:
                pdo.is_overridden = True
                pdo.override_id = override_id
                pdo.override_timestamp = timestamp
                pdo.original_decision = old_state
                self._override_count += 1
                
                # Invoke override callback
                if self._on_override:
                    self._on_override(pdo, transition)
            
            # Record transition
            self._transitions[pdo_id].append(transition)
            self._last_hash[pdo_id] = hash_current
            self._transition_count += 1
            
            # Invoke transition callback
            if self._on_transition:
                self._on_transition(transition)
            
            return transition
    
    def get_transitions(self, pdo_id: str) -> list[PDOTransition]:
        """
        Get all transitions for a PDO.
        
        Returns:
            List of transitions in chronological order
        """
        with self._lock:
            return list(self._transitions.get(pdo_id, []))
    
    def get_valid_transitions(self, pdo_id: str) -> list[tuple[PDOState, TransitionType]]:
        """
        Get valid transitions from current state.
        
        Args:
            pdo_id: PDO ID
            
        Returns:
            List of (target_state, transition_type) tuples
        """
        with self._lock:
            pdo = self._pdos.get(pdo_id)
            if pdo is None:
                return []
            
            return list(VALID_TRANSITIONS.get(pdo.current_state, set()))
    
    def verify_hash_chain(self, pdo_id: str) -> tuple[bool, str | None]:
        """
        Verify hash chain integrity for a PDO's transitions.
        
        Returns:
            (is_valid, error_message)
        """
        with self._lock:
            transitions = self._transitions.get(pdo_id, [])
            if not transitions:
                return True, None
            
            for i, tr in enumerate(transitions):
                expected_previous = None if i == 0 else transitions[i - 1].hash_current
                
                if tr.hash_previous != expected_previous:
                    return False, f"Hash chain broken at transition {tr.id}"
                
                computed = PDOTransition.compute_hash(
                    pdo_id=tr.pdo_id,
                    from_state=tr.from_state,
                    to_state=tr.to_state,
                    actor_id=tr.actor_id,
                    timestamp=tr.timestamp,
                    hash_previous=tr.hash_previous,
                )
                
                if computed != tr.hash_current:
                    return False, f"Hash mismatch at transition {tr.id}"
            
            return True, None
    
    def get_state_at_time(
        self, pdo_id: str, timestamp: datetime
    ) -> PDOState | None:
        """
        Get PDO state at a specific point in time (replay support).
        
        Args:
            pdo_id: PDO ID
            timestamp: Point in time
            
        Returns:
            State at that time, or None if PDO didn't exist
        """
        with self._lock:
            transitions = self._transitions.get(pdo_id, [])
            
            # Find last transition before timestamp
            state = PDOState.PENDING
            for tr in transitions:
                if tr.timestamp <= timestamp:
                    state = tr.to_state
                else:
                    break
            
            return state
    
    def get_metrics(self) -> dict[str, int]:
        """Return state machine metrics."""
        with self._lock:
            return {
                "pdo_count": len(self._pdos),
                "transition_count": self._transition_count,
                "override_count": self._override_count,
                "rejection_count": self._rejection_count,
            }
    
    def is_terminal_state(self, state: PDOState) -> bool:
        """Check if a state is terminal (no outbound transitions)."""
        return len(VALID_TRANSITIONS.get(state, set())) == 0
