"""
Settlement State Machine — Milestone PDO-Gated Transitions
════════════════════════════════════════════════════════════════════════════════

This module implements the settlement state machine with milestone PDO enforcement:
    - INV-SETTLEMENT-002: No milestone without milestone PDO
    - INV-SETTLEMENT-003: No state change without ledger append
    - INV-SETTLEMENT-005: All transitions auditable

ORDER 2 Implementation — Cindy (GID-04)

PAC Reference: PAC-BENSON-CHAINBRIDGE-PDO-SETTLEMENT-EXEC-006C
Effective Date: 2025-12-30

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Set

from core.governance.pdo_artifact import PDO_AUTHORITY, compute_hash
from core.governance.pdo_execution_gate import (
    PDOExecutionGate,
    GateEvaluation,
    GateResult,
    PDOGateError,
    get_pdo_gate,
)
from core.governance.pdo_ledger import (
    PDOLedger,
    LedgerEntry,
    LedgerError,
    get_pdo_ledger,
)


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logger = logging.getLogger("settlement_state_machine")


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

STATE_MACHINE_VERSION = "1.0.0"
"""State machine version."""


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class StateTransitionError(Exception):
    """Base exception for state transition errors."""
    
    def __init__(
        self,
        message: str,
        from_state: str,
        to_state: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to audit dictionary."""
        return {
            "error": self.__class__.__name__,
            "message": str(self),
            "from_state": self.from_state,
            "to_state": self.to_state,
            "context": self.context,
            "timestamp": self.timestamp,
        }


class InvalidTransitionError(StateTransitionError):
    """Raised when transition is not allowed."""
    
    def __init__(self, from_state: str, to_state: str, allowed: Set[str]):
        super().__init__(
            f"INVALID_TRANSITION: Transition from '{from_state}' to '{to_state}' "
            f"not allowed. Valid targets: {sorted(allowed)}",
            from_state=from_state,
            to_state=to_state,
            context={"allowed_transitions": sorted(allowed)},
        )
        self.allowed = allowed


class MilestonePDORequiredError(StateTransitionError):
    """
    Raised when milestone transition attempted without PDO.
    
    INV-SETTLEMENT-002: No milestone without milestone PDO.
    """
    
    def __init__(
        self,
        milestone_id: str,
        from_state: str,
        to_state: str,
        reason: str,
    ):
        super().__init__(
            f"MILESTONE_PDO_REQUIRED: Milestone '{milestone_id}' transition from "
            f"'{from_state}' to '{to_state}' blocked. Reason: {reason}. "
            f"INV-SETTLEMENT-002 enforced.",
            from_state=from_state,
            to_state=to_state,
            context={"milestone_id": milestone_id, "reason": reason},
        )
        self.milestone_id = milestone_id
        self.reason = reason


class LedgerAppendRequiredError(StateTransitionError):
    """
    Raised when ledger append fails during transition.
    
    INV-SETTLEMENT-003: No state change without ledger append.
    """
    
    def __init__(
        self,
        from_state: str,
        to_state: str,
        ledger_error: str,
    ):
        super().__init__(
            f"LEDGER_APPEND_REQUIRED: Transition from '{from_state}' to '{to_state}' "
            f"blocked. Ledger error: {ledger_error}. INV-SETTLEMENT-003 enforced.",
            from_state=from_state,
            to_state=to_state,
            context={"ledger_error": ledger_error},
        )
        self.ledger_error = ledger_error


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT STATE ENUM
# ═══════════════════════════════════════════════════════════════════════════════

class SettlementState(Enum):
    """Settlement lifecycle states."""
    
    # Initial states
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    
    # Active states
    INITIATED = "INITIATED"
    IN_PROGRESS = "IN_PROGRESS"
    MILESTONE_PENDING = "MILESTONE_PENDING"
    MILESTONE_COMPLETE = "MILESTONE_COMPLETE"
    
    # Terminal states
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    CANCELLED = "CANCELLED"


class MilestoneState(Enum):
    """Milestone lifecycle states."""
    
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_VERIFICATION = "AWAITING_VERIFICATION"
    VERIFIED = "VERIFIED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


# ═══════════════════════════════════════════════════════════════════════════════
# STATE TRANSITION DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Valid settlement state transitions
SETTLEMENT_TRANSITIONS: Dict[SettlementState, Set[SettlementState]] = {
    SettlementState.DRAFT: {
        SettlementState.PENDING,
        SettlementState.CANCELLED,
    },
    SettlementState.PENDING: {
        SettlementState.INITIATED,
        SettlementState.CANCELLED,
    },
    SettlementState.INITIATED: {
        SettlementState.IN_PROGRESS,
        SettlementState.ABORTED,
        SettlementState.FAILED,
    },
    SettlementState.IN_PROGRESS: {
        SettlementState.MILESTONE_PENDING,
        SettlementState.COMPLETED,
        SettlementState.ABORTED,
        SettlementState.FAILED,
    },
    SettlementState.MILESTONE_PENDING: {
        SettlementState.MILESTONE_COMPLETE,
        SettlementState.IN_PROGRESS,
        SettlementState.ABORTED,
        SettlementState.FAILED,
    },
    SettlementState.MILESTONE_COMPLETE: {
        SettlementState.IN_PROGRESS,
        SettlementState.COMPLETED,
        SettlementState.ABORTED,
    },
    # Terminal states have no outgoing transitions
    SettlementState.COMPLETED: set(),
    SettlementState.FAILED: set(),
    SettlementState.ABORTED: set(),
    SettlementState.CANCELLED: set(),
}

# Valid milestone state transitions
MILESTONE_TRANSITIONS: Dict[MilestoneState, Set[MilestoneState]] = {
    MilestoneState.PENDING: {
        MilestoneState.IN_PROGRESS,
        MilestoneState.SKIPPED,
    },
    MilestoneState.IN_PROGRESS: {
        MilestoneState.AWAITING_VERIFICATION,
        MilestoneState.FAILED,
    },
    MilestoneState.AWAITING_VERIFICATION: {
        MilestoneState.VERIFIED,
        MilestoneState.IN_PROGRESS,  # Re-work
        MilestoneState.FAILED,
    },
    MilestoneState.VERIFIED: {
        MilestoneState.COMPLETED,
    },
    # Terminal states
    MilestoneState.COMPLETED: set(),
    MilestoneState.FAILED: set(),
    MilestoneState.SKIPPED: set(),
}


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSITION RECORDS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SettlementTransition:
    """
    Immutable record of a settlement state transition.
    
    INV-SETTLEMENT-005: All transitions auditable.
    """
    
    transition_id: str
    settlement_id: str
    from_state: SettlementState
    to_state: SettlementState
    pdo_id: str  # PDO authorizing transition
    pac_id: str
    reason: str
    transitioned_at: str
    ledger_entry_id: str
    ledger_entry_hash: str
    gate_evaluation: Optional[GateEvaluation] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "transition_id": self.transition_id,
            "settlement_id": self.settlement_id,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "pdo_id": self.pdo_id,
            "pac_id": self.pac_id,
            "reason": self.reason,
            "transitioned_at": self.transitioned_at,
            "ledger_entry_id": self.ledger_entry_id,
            "ledger_entry_hash": self.ledger_entry_hash,
            "gate_evaluation": self.gate_evaluation.to_dict() if self.gate_evaluation else None,
        }


@dataclass(frozen=True)
class MilestoneTransition:
    """
    Immutable record of a milestone state transition.
    
    INV-SETTLEMENT-002: No milestone without milestone PDO.
    INV-SETTLEMENT-005: All transitions auditable.
    """
    
    transition_id: str
    milestone_id: str
    settlement_id: str
    from_state: MilestoneState
    to_state: MilestoneState
    pdo_id: str  # PDO authorizing transition
    pac_id: str
    reason: str
    transitioned_at: str
    ledger_entry_id: str
    ledger_entry_hash: str
    gate_evaluation: Optional[GateEvaluation] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "transition_id": self.transition_id,
            "milestone_id": self.milestone_id,
            "settlement_id": self.settlement_id,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "pdo_id": self.pdo_id,
            "pac_id": self.pac_id,
            "reason": self.reason,
            "transitioned_at": self.transitioned_at,
            "ledger_entry_id": self.ledger_entry_id,
            "ledger_entry_hash": self.ledger_entry_hash,
            "gate_evaluation": self.gate_evaluation.to_dict() if self.gate_evaluation else None,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MILESTONE RECORD
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MilestoneRecord:
    """
    Milestone tracking record within a settlement.
    """
    
    milestone_id: str
    settlement_id: str
    sequence: int  # Order within settlement
    name: str
    description: str = ""
    
    # State
    state: MilestoneState = MilestoneState.PENDING
    
    # PDO binding
    pdo_id: Optional[str] = None  # PDO that authorized this milestone
    completion_pdo_id: Optional[str] = None  # PDO that completed it
    
    # Timestamps
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Audit
    transitions: List[MilestoneTransition] = field(default_factory=list)
    
    def __post_init__(self):
        """Set created_at if not provided."""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
    
    @property
    def is_terminal(self) -> bool:
        """Check if milestone is in terminal state."""
        return self.state in {
            MilestoneState.COMPLETED,
            MilestoneState.FAILED,
            MilestoneState.SKIPPED,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "milestone_id": self.milestone_id,
            "settlement_id": self.settlement_id,
            "sequence": self.sequence,
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "pdo_id": self.pdo_id,
            "completion_pdo_id": self.completion_pdo_id,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "transitions": [t.to_dict() for t in self.transitions],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════════

class SettlementStateMachine:
    """
    PDO-Gated Settlement State Machine.
    
    Enforces milestone PDO requirements and ledger persistence.
    
    INVARIANTS:
        INV-SETTLEMENT-002: No milestone without milestone PDO
        INV-SETTLEMENT-003: No state change without ledger append
        INV-SETTLEMENT-005: All transitions auditable
    """
    
    def __init__(
        self,
        settlement_id: str,
        initial_state: SettlementState = SettlementState.DRAFT,
        pdo_gate: Optional[PDOExecutionGate] = None,
        pdo_ledger: Optional[PDOLedger] = None,
    ):
        """
        Initialize state machine for a settlement.
        
        Args:
            settlement_id: Settlement this machine tracks
            initial_state: Initial settlement state
            pdo_gate: PDO execution gate (defaults to singleton)
            pdo_ledger: PDO ledger (defaults to singleton)
        """
        self._settlement_id = settlement_id
        self._state = initial_state
        self._gate = pdo_gate or get_pdo_gate()
        self._ledger = pdo_ledger or get_pdo_ledger()
        
        # Milestone registry
        self._milestones: Dict[str, MilestoneRecord] = {}
        self._milestone_order: List[str] = []  # Ordered milestone IDs
        
        # Transition history
        self._settlement_transitions: List[SettlementTransition] = []
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Metadata
        self._created_at = datetime.now(timezone.utc).isoformat()
        
        logger.info(
            f"StateMachine created for settlement {settlement_id} "
            f"(initial: {initial_state.value})"
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SETTLEMENT TRANSITIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def transition(
        self,
        to_state: SettlementState,
        pdo_id: str,
        pac_id: str,
        reason: str,
        evaluator: str = "GID-04",
    ) -> SettlementTransition:
        """
        Transition settlement to new state with PDO verification.
        
        INV-SETTLEMENT-003: No state change without ledger append.
        
        Args:
            to_state: Target state
            pdo_id: PDO authorizing transition
            pac_id: PAC for transition
            reason: Reason for transition
            evaluator: Agent GID performing evaluation
            
        Returns:
            SettlementTransition record
            
        Raises:
            InvalidTransitionError: If transition not allowed
            LedgerAppendRequiredError: If ledger append fails
        """
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            from_state = self._state
            
            # Validate transition is allowed
            allowed = SETTLEMENT_TRANSITIONS.get(from_state, set())
            if to_state not in allowed:
                raise InvalidTransitionError(
                    from_state=from_state.value,
                    to_state=to_state.value,
                    allowed={s.value for s in allowed},
                )
            
            # Verify PDO
            gate_eval = self._gate.verify_pdo_exists(
                pdo_id=pdo_id,
                pac_id=pac_id,
                evaluator=evaluator,
            )
            
            if not gate_eval.is_pass:
                raise StateTransitionError(
                    f"PDO verification failed for transition",
                    from_state=from_state.value,
                    to_state=to_state.value,
                    context={"gate_evaluation": gate_eval.to_dict()},
                )
            
            # Append to ledger (INV-SETTLEMENT-003)
            try:
                ledger_entry = self._append_transition_to_ledger(
                    from_state=from_state,
                    to_state=to_state,
                    pdo_id=pdo_id,
                    pac_id=pac_id,
                    reason=reason,
                )
            except LedgerError as e:
                raise LedgerAppendRequiredError(
                    from_state=from_state.value,
                    to_state=to_state.value,
                    ledger_error=str(e),
                )
            
            # Create transition record
            transition = SettlementTransition(
                transition_id=f"trans_{uuid.uuid4().hex[:12]}",
                settlement_id=self._settlement_id,
                from_state=from_state,
                to_state=to_state,
                pdo_id=pdo_id,
                pac_id=pac_id,
                reason=reason,
                transitioned_at=now,
                ledger_entry_id=ledger_entry.entry_id,
                ledger_entry_hash=ledger_entry.entry_hash,
                gate_evaluation=gate_eval,
            )
            
            # Apply transition
            self._state = to_state
            self._settlement_transitions.append(transition)
            
            logger.info(
                f"Settlement {self._settlement_id}: "
                f"{from_state.value} → {to_state.value} (PDO: {pdo_id})"
            )
            
            return transition
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MILESTONE MANAGEMENT (ORDER 2 — Cindy GID-04)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def add_milestone(
        self,
        milestone_id: str,
        name: str,
        description: str = "",
        pdo_id: Optional[str] = None,
    ) -> MilestoneRecord:
        """
        Add a milestone to the settlement.
        
        Args:
            milestone_id: Unique milestone ID
            name: Milestone name
            description: Milestone description
            pdo_id: Optional PDO that authorized this milestone
            
        Returns:
            MilestoneRecord
        """
        with self._lock:
            if milestone_id in self._milestones:
                raise ValueError(f"Milestone {milestone_id} already exists")
            
            sequence = len(self._milestone_order)
            milestone = MilestoneRecord(
                milestone_id=milestone_id,
                settlement_id=self._settlement_id,
                sequence=sequence,
                name=name,
                description=description,
                pdo_id=pdo_id,
            )
            
            self._milestones[milestone_id] = milestone
            self._milestone_order.append(milestone_id)
            
            logger.info(
                f"Milestone added: {milestone_id} to settlement {self._settlement_id}"
            )
            
            return milestone
    
    def transition_milestone(
        self,
        milestone_id: str,
        to_state: MilestoneState,
        pdo_id: str,
        pac_id: str,
        reason: str,
        evaluator: str = "GID-04",
    ) -> MilestoneTransition:
        """
        Transition milestone to new state with PDO verification.
        
        INV-SETTLEMENT-002: No milestone without milestone PDO.
        INV-SETTLEMENT-003: No state change without ledger append.
        
        Args:
            milestone_id: Milestone to transition
            to_state: Target state
            pdo_id: PDO authorizing transition
            pac_id: PAC for transition
            reason: Reason for transition
            evaluator: Agent GID performing evaluation
            
        Returns:
            MilestoneTransition record
            
        Raises:
            MilestonePDORequiredError: If PDO verification fails
            InvalidTransitionError: If transition not allowed
            LedgerAppendRequiredError: If ledger append fails
        """
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            
            # Get milestone
            milestone = self._milestones.get(milestone_id)
            if milestone is None:
                raise ValueError(f"Milestone {milestone_id} not found")
            
            from_state = milestone.state
            
            # Validate transition is allowed
            allowed = MILESTONE_TRANSITIONS.get(from_state, set())
            if to_state not in allowed:
                raise InvalidTransitionError(
                    from_state=from_state.value,
                    to_state=to_state.value,
                    allowed={s.value for s in allowed},
                )
            
            # Verify PDO (INV-SETTLEMENT-002)
            try:
                gate_eval = self._gate.verify_pdo_exists(
                    pdo_id=pdo_id,
                    pac_id=pac_id,
                    evaluator=evaluator,
                )
                
                if not gate_eval.is_pass:
                    raise MilestonePDORequiredError(
                        milestone_id=milestone_id,
                        from_state=from_state.value,
                        to_state=to_state.value,
                        reason=f"PDO verification failed: {gate_eval.reason.value if gate_eval.reason else 'unknown'}",
                    )
                    
            except PDOGateError as e:
                raise MilestonePDORequiredError(
                    milestone_id=milestone_id,
                    from_state=from_state.value,
                    to_state=to_state.value,
                    reason=str(e),
                )
            
            # Append to ledger (INV-SETTLEMENT-003)
            try:
                ledger_entry = self._append_milestone_transition_to_ledger(
                    milestone_id=milestone_id,
                    from_state=from_state,
                    to_state=to_state,
                    pdo_id=pdo_id,
                    pac_id=pac_id,
                    reason=reason,
                )
            except LedgerError as e:
                raise LedgerAppendRequiredError(
                    from_state=from_state.value,
                    to_state=to_state.value,
                    ledger_error=str(e),
                )
            
            # Create transition record
            transition = MilestoneTransition(
                transition_id=f"mtrans_{uuid.uuid4().hex[:12]}",
                milestone_id=milestone_id,
                settlement_id=self._settlement_id,
                from_state=from_state,
                to_state=to_state,
                pdo_id=pdo_id,
                pac_id=pac_id,
                reason=reason,
                transitioned_at=now,
                ledger_entry_id=ledger_entry.entry_id,
                ledger_entry_hash=ledger_entry.entry_hash,
                gate_evaluation=gate_eval,
            )
            
            # Apply transition
            milestone.state = to_state
            milestone.transitions.append(transition)
            
            # Update timestamps
            if to_state == MilestoneState.IN_PROGRESS and not milestone.started_at:
                milestone.started_at = now
            elif to_state == MilestoneState.COMPLETED:
                milestone.completed_at = now
                milestone.completion_pdo_id = pdo_id
            
            logger.info(
                f"Milestone {milestone_id}: "
                f"{from_state.value} → {to_state.value} (PDO: {pdo_id})"
            )
            
            return transition
    
    def complete_milestone(
        self,
        milestone_id: str,
        pdo_id: str,
        pac_id: str,
        reason: str = "Milestone completed",
        evaluator: str = "GID-04",
    ) -> MilestoneTransition:
        """
        Complete a milestone (convenience method).
        
        Routes through VERIFIED → COMPLETED if not already verified.
        
        Args:
            milestone_id: Milestone to complete
            pdo_id: PDO authorizing completion
            pac_id: PAC for completion
            reason: Reason for completion
            evaluator: Agent GID performing evaluation
            
        Returns:
            MilestoneTransition record for completion
        """
        with self._lock:
            milestone = self._milestones.get(milestone_id)
            if milestone is None:
                raise ValueError(f"Milestone {milestone_id} not found")
            
            # If in AWAITING_VERIFICATION, verify first
            if milestone.state == MilestoneState.AWAITING_VERIFICATION:
                self.transition_milestone(
                    milestone_id=milestone_id,
                    to_state=MilestoneState.VERIFIED,
                    pdo_id=pdo_id,
                    pac_id=pac_id,
                    reason="Verified for completion",
                    evaluator=evaluator,
                )
            
            # Complete
            return self.transition_milestone(
                milestone_id=milestone_id,
                to_state=MilestoneState.COMPLETED,
                pdo_id=pdo_id,
                pac_id=pac_id,
                reason=reason,
                evaluator=evaluator,
            )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LEDGER INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _append_transition_to_ledger(
        self,
        from_state: SettlementState,
        to_state: SettlementState,
        pdo_id: str,
        pac_id: str,
        reason: str,
    ) -> LedgerEntry:
        """Append settlement transition to ledger."""
        return self._ledger.append(
            pdo_id=pdo_id,
            pac_id=pac_id,
            ber_id=f"ber_trans_{self._settlement_id}",
            wrap_id=f"wrap_trans_{self._settlement_id}",
            outcome_status=f"SETTLEMENT_TRANSITION_{to_state.value}",
            issuer=PDO_AUTHORITY,
            pdo_hash=compute_hash({"pdo_id": pdo_id}),
            proof_hash=compute_hash({"settlement_id": self._settlement_id}),
            decision_hash=compute_hash({
                "from": from_state.value,
                "to": to_state.value,
            }),
            outcome_hash=compute_hash({
                "settlement_id": self._settlement_id,
                "transition": f"{from_state.value}_to_{to_state.value}",
                "reason": reason,
            }),
            pdo_created_at=datetime.now(timezone.utc).isoformat(),
        )
    
    def _append_milestone_transition_to_ledger(
        self,
        milestone_id: str,
        from_state: MilestoneState,
        to_state: MilestoneState,
        pdo_id: str,
        pac_id: str,
        reason: str,
    ) -> LedgerEntry:
        """Append milestone transition to ledger."""
        return self._ledger.append(
            pdo_id=pdo_id,
            pac_id=pac_id,
            ber_id=f"ber_milestone_{milestone_id}",
            wrap_id=f"wrap_milestone_{milestone_id}",
            outcome_status=f"MILESTONE_TRANSITION_{to_state.value}",
            issuer=PDO_AUTHORITY,
            pdo_hash=compute_hash({"pdo_id": pdo_id}),
            proof_hash=compute_hash({
                "milestone_id": milestone_id,
                "settlement_id": self._settlement_id,
            }),
            decision_hash=compute_hash({
                "from": from_state.value,
                "to": to_state.value,
            }),
            outcome_hash=compute_hash({
                "milestone_id": milestone_id,
                "transition": f"{from_state.value}_to_{to_state.value}",
                "reason": reason,
            }),
            pdo_created_at=datetime.now(timezone.utc).isoformat(),
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # QUERIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def state(self) -> SettlementState:
        """Get current settlement state."""
        return self._state
    
    @property
    def settlement_id(self) -> str:
        """Get settlement ID."""
        return self._settlement_id
    
    @property
    def is_terminal(self) -> bool:
        """Check if settlement is in terminal state."""
        return self._state in {
            SettlementState.COMPLETED,
            SettlementState.FAILED,
            SettlementState.ABORTED,
            SettlementState.CANCELLED,
        }
    
    def get_milestone(self, milestone_id: str) -> Optional[MilestoneRecord]:
        """Get milestone by ID."""
        return self._milestones.get(milestone_id)
    
    def get_milestones(self) -> List[MilestoneRecord]:
        """Get all milestones in order."""
        return [self._milestones[mid] for mid in self._milestone_order]
    
    def get_next_milestone(self) -> Optional[MilestoneRecord]:
        """Get next non-terminal milestone."""
        for mid in self._milestone_order:
            milestone = self._milestones[mid]
            if not milestone.is_terminal:
                return milestone
        return None
    
    def get_transitions(self) -> List[SettlementTransition]:
        """Get all settlement transitions."""
        return list(self._settlement_transitions)
    
    def get_allowed_transitions(self) -> Set[SettlementState]:
        """Get allowed target states from current state."""
        return SETTLEMENT_TRANSITIONS.get(self._state, set())
    
    def can_transition_to(self, target: SettlementState) -> bool:
        """Check if transition to target is allowed."""
        return target in self.get_allowed_transitions()
    
    @property
    def milestone_count(self) -> int:
        """Get total milestone count."""
        return len(self._milestones)
    
    @property
    def completed_milestone_count(self) -> int:
        """Get completed milestone count."""
        return sum(
            1 for m in self._milestones.values()
            if m.state == MilestoneState.COMPLETED
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "settlement_id": self._settlement_id,
            "state": self._state.value,
            "is_terminal": self.is_terminal,
            "milestones": [m.to_dict() for m in self.get_milestones()],
            "milestone_count": self.milestone_count,
            "completed_milestone_count": self.completed_milestone_count,
            "transitions": [t.to_dict() for t in self._settlement_transitions],
            "created_at": self._created_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # State Machine
    "SettlementStateMachine",
    
    # States
    "SettlementState",
    "MilestoneState",
    
    # Records
    "SettlementTransition",
    "MilestoneTransition",
    "MilestoneRecord",
    
    # Transitions
    "SETTLEMENT_TRANSITIONS",
    "MILESTONE_TRANSITIONS",
    
    # Exceptions
    "StateTransitionError",
    "InvalidTransitionError",
    "MilestonePDORequiredError",
    "LedgerAppendRequiredError",
    
    # Constants
    "STATE_MACHINE_VERSION",
]
