"""
ChainBridge Canonical State Machines

Atlas (GID-05) — System State Engine
Authority: Benson (GID-00)

PAC: PAC-ATLAS-A12-STATE-TRANSITION-GOVERNANCE-LOCK-01

This module defines explicit lifecycle state machines for all governed artifacts.
Every artifact follows a declared lifecycle with:
- Initial state
- Allowed transitions
- Terminal states
- Authority requirements

INVARIANTS:
- All transitions must be declared
- Implicit transitions are forbidden
- Terminal states are immutable
- Replay determinism preserved
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Set, Dict, FrozenSet


# =============================================================================
# PROOF STATE ENUM (New in A12)
# =============================================================================


class ProofState(str, Enum):
    """Allowed proof artifact states with defined transition rules."""

    CREATED = "CREATED"
    SIGNED = "SIGNED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    FINALIZED = "FINALIZED"


# =============================================================================
# DEPLOYMENT STATE ENUM (New in A12)
# =============================================================================


class DeploymentState(str, Enum):
    """Allowed deployment states with defined transition rules."""

    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEPLOYED = "DEPLOYED"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    ROLLED_BACK = "ROLLED_BACK"
    DEPRECATED = "DEPRECATED"


# =============================================================================
# RISK DECISION STATE ENUM (New in A12)
# =============================================================================


class RiskDecisionState(str, Enum):
    """Allowed risk decision states with defined transition rules."""

    PENDING = "PENDING"
    EVALUATED = "EVALUATED"
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    REVIEW = "REVIEW"
    ESCALATED = "ESCALATED"
    OVERRIDE_APPLIED = "OVERRIDE_APPLIED"
    FINALIZED = "FINALIZED"


# =============================================================================
# TRANSITION RULE TYPE
# =============================================================================


@dataclass(frozen=True)
class TransitionRule:
    """Defines a single allowed state transition."""

    from_state: str
    to_state: str
    requires_proof: bool = True
    required_authority: Optional[str] = None  # GID or role
    description: str = ""

    def __hash__(self) -> int:
        return hash((self.from_state, self.to_state))


# =============================================================================
# STATE MACHINE DEFINITION
# =============================================================================


@dataclass
class StateMachine:
    """
    Canonical state machine definition for an artifact type.
    
    Defines the complete lifecycle including:
    - All valid states
    - Initial state
    - Terminal states (no outgoing transitions)
    - Allowed transitions with authority requirements
    """

    name: str
    states: FrozenSet[str]
    initial_state: str
    terminal_states: FrozenSet[str]
    transitions: Dict[str, Set[str]]
    transition_rules: Dict[tuple[str, str], TransitionRule] = field(default_factory=dict)

    def is_valid_transition(self, from_state: str, to_state: str) -> bool:
        """Check if a transition is explicitly allowed."""
        if from_state not in self.states:
            return False
        if to_state not in self.states:
            return False
        if from_state in self.terminal_states:
            return False  # No transitions from terminal states
        return to_state in self.transitions.get(from_state, set())

    def get_allowed_transitions(self, from_state: str) -> Set[str]:
        """Get all allowed target states from a given state."""
        if from_state in self.terminal_states:
            return set()
        return self.transitions.get(from_state, set())

    def is_terminal(self, state: str) -> bool:
        """Check if a state is terminal (no outgoing transitions)."""
        return state in self.terminal_states

    def is_initial(self, state: str) -> bool:
        """Check if a state is the initial state."""
        return state == self.initial_state

    def get_transition_rule(
        self, from_state: str, to_state: str
    ) -> Optional[TransitionRule]:
        """Get the transition rule for a specific transition."""
        return self.transition_rules.get((from_state, to_state))

    def validate_machine_integrity(self) -> list[str]:
        """
        Validate the state machine definition is internally consistent.
        
        Returns list of errors (empty if valid).
        """
        errors: list[str] = []

        # Initial state must be in states
        if self.initial_state not in self.states:
            errors.append(f"Initial state '{self.initial_state}' not in states")

        # Terminal states must be in states
        for ts in self.terminal_states:
            if ts not in self.states:
                errors.append(f"Terminal state '{ts}' not in states")

        # All transition targets must be valid states
        for from_state, targets in self.transitions.items():
            if from_state not in self.states:
                errors.append(f"Transition source '{from_state}' not in states")
            for to_state in targets:
                if to_state not in self.states:
                    errors.append(
                        f"Transition target '{to_state}' from '{from_state}' not in states"
                    )

        # Terminal states should have no outgoing transitions
        for ts in self.terminal_states:
            if ts in self.transitions and self.transitions[ts]:
                errors.append(
                    f"Terminal state '{ts}' has outgoing transitions: {self.transitions[ts]}"
                )

        # Check reachability from initial state
        reachable = self._compute_reachable_states()
        unreachable = self.states - reachable
        if unreachable:
            errors.append(f"Unreachable states from initial: {unreachable}")

        return errors

    def _compute_reachable_states(self) -> Set[str]:
        """Compute all states reachable from the initial state."""
        reachable: Set[str] = {self.initial_state}
        frontier: Set[str] = {self.initial_state}

        while frontier:
            current = frontier.pop()
            for target in self.transitions.get(current, set()):
                if target not in reachable:
                    reachable.add(target)
                    frontier.add(target)

        return reachable


# =============================================================================
# CANONICAL STATE MACHINE DEFINITIONS
# =============================================================================


# Import existing enums from state_schema
from .state_schema import PDOState, SettlementState, ShipmentState


# PDO State Machine
PDO_STATE_MACHINE = StateMachine(
    name="PDO",
    states=frozenset(s.value for s in PDOState),
    initial_state=PDOState.CREATED.value,
    terminal_states=frozenset([
        PDOState.ACCEPTED.value,
        PDOState.REJECTED.value,
        PDOState.EXPIRED.value,
    ]),
    transitions={
        PDOState.CREATED.value: {PDOState.SIGNED.value, PDOState.EXPIRED.value},
        PDOState.SIGNED.value: {PDOState.VERIFIED.value, PDOState.VERIFICATION_FAILED.value},
        PDOState.VERIFIED.value: {PDOState.ACCEPTED.value},
        PDOState.VERIFICATION_FAILED.value: {PDOState.REJECTED.value},
        PDOState.ACCEPTED.value: set(),
        PDOState.REJECTED.value: set(),
        PDOState.EXPIRED.value: set(),
    },
    transition_rules={
        (PDOState.CREATED.value, PDOState.SIGNED.value): TransitionRule(
            from_state=PDOState.CREATED.value,
            to_state=PDOState.SIGNED.value,
            requires_proof=True,
            required_authority=None,  # Any agent
            description="PDO signed by originator",
        ),
        (PDOState.SIGNED.value, PDOState.VERIFIED.value): TransitionRule(
            from_state=PDOState.SIGNED.value,
            to_state=PDOState.VERIFIED.value,
            requires_proof=True,
            required_authority="VERIFIER",
            description="PDO verification successful",
        ),
        (PDOState.VERIFIED.value, PDOState.ACCEPTED.value): TransitionRule(
            from_state=PDOState.VERIFIED.value,
            to_state=PDOState.ACCEPTED.value,
            requires_proof=True,
            required_authority="SYSTEM",
            description="PDO accepted (automated)",
        ),
    },
)


# Settlement State Machine
SETTLEMENT_STATE_MACHINE = StateMachine(
    name="SETTLEMENT",
    states=frozenset(s.value for s in SettlementState),
    initial_state=SettlementState.PENDING.value,
    terminal_states=frozenset([SettlementState.FINALIZED.value]),
    transitions={
        SettlementState.PENDING.value: {
            SettlementState.APPROVED.value,
            SettlementState.REJECTED.value,
            SettlementState.BLOCKED.value,
        },
        SettlementState.APPROVED.value: {SettlementState.EXECUTED.value},
        SettlementState.EXECUTED.value: {SettlementState.FINALIZED.value},
        SettlementState.REJECTED.value: {SettlementState.DISPUTED.value},
        SettlementState.DISPUTED.value: {SettlementState.RESOLVED.value},
        SettlementState.RESOLVED.value: {SettlementState.FINALIZED.value},
        SettlementState.BLOCKED.value: {
            SettlementState.PENDING.value,
            SettlementState.REJECTED.value,
        },
        SettlementState.FINALIZED.value: set(),
    },
    transition_rules={
        (SettlementState.PENDING.value, SettlementState.APPROVED.value): TransitionRule(
            from_state=SettlementState.PENDING.value,
            to_state=SettlementState.APPROVED.value,
            requires_proof=True,
            required_authority="CRO",
            description="Settlement approved by CRO",
        ),
        (SettlementState.APPROVED.value, SettlementState.EXECUTED.value): TransitionRule(
            from_state=SettlementState.APPROVED.value,
            to_state=SettlementState.EXECUTED.value,
            requires_proof=True,
            required_authority="SYSTEM",
            description="Settlement executed (automated)",
        ),
        (SettlementState.EXECUTED.value, SettlementState.FINALIZED.value): TransitionRule(
            from_state=SettlementState.EXECUTED.value,
            to_state=SettlementState.FINALIZED.value,
            requires_proof=True,
            required_authority="SYSTEM",
            description="Settlement finalized (immutable)",
        ),
    },
)


# Proof State Machine (New in A12)
PROOF_STATE_MACHINE = StateMachine(
    name="PROOF",
    states=frozenset(s.value for s in ProofState),
    initial_state=ProofState.CREATED.value,
    terminal_states=frozenset([
        ProofState.FINALIZED.value,
        ProofState.REJECTED.value,
    ]),
    transitions={
        ProofState.CREATED.value: {ProofState.SIGNED.value},
        ProofState.SIGNED.value: {ProofState.VERIFIED.value, ProofState.REJECTED.value},
        ProofState.VERIFIED.value: {ProofState.FINALIZED.value},
        ProofState.FINALIZED.value: set(),
        ProofState.REJECTED.value: set(),
    },
    transition_rules={
        (ProofState.CREATED.value, ProofState.SIGNED.value): TransitionRule(
            from_state=ProofState.CREATED.value,
            to_state=ProofState.SIGNED.value,
            requires_proof=False,  # Initial proof creation
            required_authority=None,
            description="Proof signed by creator",
        ),
        (ProofState.SIGNED.value, ProofState.VERIFIED.value): TransitionRule(
            from_state=ProofState.SIGNED.value,
            to_state=ProofState.VERIFIED.value,
            requires_proof=True,
            required_authority="VERIFIER",
            description="Proof verification successful",
        ),
        (ProofState.VERIFIED.value, ProofState.FINALIZED.value): TransitionRule(
            from_state=ProofState.VERIFIED.value,
            to_state=ProofState.FINALIZED.value,
            requires_proof=True,
            required_authority="SYSTEM",
            description="Proof finalized (immutable)",
        ),
    },
)


# Deployment State Machine (New in A12)
DEPLOYMENT_STATE_MACHINE = StateMachine(
    name="DEPLOYMENT",
    states=frozenset(s.value for s in DeploymentState),
    initial_state=DeploymentState.PROPOSED.value,
    terminal_states=frozenset([
        DeploymentState.REJECTED.value,
        DeploymentState.ROLLED_BACK.value,
        DeploymentState.DEPRECATED.value,
    ]),
    transitions={
        DeploymentState.PROPOSED.value: {
            DeploymentState.APPROVED.value,
            DeploymentState.REJECTED.value,
        },
        DeploymentState.APPROVED.value: {DeploymentState.DEPLOYED.value},
        DeploymentState.DEPLOYED.value: {DeploymentState.VERIFIED.value},
        DeploymentState.VERIFIED.value: {
            DeploymentState.ACTIVE.value,
            DeploymentState.ROLLED_BACK.value,
        },
        DeploymentState.ACTIVE.value: {DeploymentState.DEPRECATED.value},
        DeploymentState.REJECTED.value: set(),
        DeploymentState.ROLLED_BACK.value: set(),
        DeploymentState.DEPRECATED.value: set(),
    },
    transition_rules={
        (DeploymentState.PROPOSED.value, DeploymentState.APPROVED.value): TransitionRule(
            from_state=DeploymentState.PROPOSED.value,
            to_state=DeploymentState.APPROVED.value,
            requires_proof=True,
            required_authority="GID-00",  # Benson only
            description="Deployment approved by Benson",
        ),
        (DeploymentState.APPROVED.value, DeploymentState.DEPLOYED.value): TransitionRule(
            from_state=DeploymentState.APPROVED.value,
            to_state=DeploymentState.DEPLOYED.value,
            requires_proof=True,
            required_authority="GID-07",  # Dan (DevOps)
            description="Deployment executed by Dan",
        ),
        (DeploymentState.VERIFIED.value, DeploymentState.ACTIVE.value): TransitionRule(
            from_state=DeploymentState.VERIFIED.value,
            to_state=DeploymentState.ACTIVE.value,
            requires_proof=True,
            required_authority="SYSTEM",
            description="Deployment activated (automated)",
        ),
    },
)


# Risk Decision State Machine (New in A12)
RISK_DECISION_STATE_MACHINE = StateMachine(
    name="RISK_DECISION",
    states=frozenset(s.value for s in RiskDecisionState),
    initial_state=RiskDecisionState.PENDING.value,
    terminal_states=frozenset([RiskDecisionState.FINALIZED.value]),
    transitions={
        RiskDecisionState.PENDING.value: {RiskDecisionState.EVALUATED.value},
        RiskDecisionState.EVALUATED.value: {
            RiskDecisionState.ALLOWED.value,
            RiskDecisionState.BLOCKED.value,
            RiskDecisionState.REVIEW.value,
        },
        RiskDecisionState.ALLOWED.value: {RiskDecisionState.FINALIZED.value},
        RiskDecisionState.BLOCKED.value: {RiskDecisionState.FINALIZED.value},
        RiskDecisionState.REVIEW.value: {RiskDecisionState.ESCALATED.value},
        RiskDecisionState.ESCALATED.value: {RiskDecisionState.OVERRIDE_APPLIED.value},
        RiskDecisionState.OVERRIDE_APPLIED.value: {RiskDecisionState.FINALIZED.value},
        RiskDecisionState.FINALIZED.value: set(),
    },
    transition_rules={
        (RiskDecisionState.PENDING.value, RiskDecisionState.EVALUATED.value): TransitionRule(
            from_state=RiskDecisionState.PENDING.value,
            to_state=RiskDecisionState.EVALUATED.value,
            requires_proof=True,
            required_authority="RISK_ENGINE",
            description="Risk evaluation completed",
        ),
        (RiskDecisionState.REVIEW.value, RiskDecisionState.ESCALATED.value): TransitionRule(
            from_state=RiskDecisionState.REVIEW.value,
            to_state=RiskDecisionState.ESCALATED.value,
            requires_proof=True,
            required_authority="RISK_AGENT",
            description="Risk decision escalated for human review",
        ),
        (RiskDecisionState.ESCALATED.value, RiskDecisionState.OVERRIDE_APPLIED.value): TransitionRule(
            from_state=RiskDecisionState.ESCALATED.value,
            to_state=RiskDecisionState.OVERRIDE_APPLIED.value,
            requires_proof=True,
            required_authority="HUMAN_PLUS_2_AGENTS",
            description="Override applied with multi-party approval",
        ),
    },
)


# Shipment State Machine (extends existing)
SHIPMENT_STATE_MACHINE = StateMachine(
    name="SHIPMENT",
    states=frozenset(s.value for s in ShipmentState),
    initial_state=ShipmentState.CREATED.value,
    terminal_states=frozenset([
        ShipmentState.SETTLED.value,
        ShipmentState.CANCELLED.value,
    ]),
    transitions={
        ShipmentState.CREATED.value: {
            ShipmentState.IN_TRANSIT.value,
            ShipmentState.CANCELLED.value,
        },
        ShipmentState.IN_TRANSIT.value: {
            ShipmentState.DELIVERED.value,
            ShipmentState.EXCEPTION.value,
            ShipmentState.CANCELLED.value,
        },
        ShipmentState.DELIVERED.value: {ShipmentState.SETTLED.value},
        ShipmentState.EXCEPTION.value: {ShipmentState.RESOLVED.value},
        ShipmentState.RESOLVED.value: {ShipmentState.SETTLED.value},
        ShipmentState.SETTLED.value: set(),
        ShipmentState.CANCELLED.value: set(),
    },
)


# =============================================================================
# STATE MACHINE REGISTRY
# =============================================================================


STATE_MACHINES: Dict[str, StateMachine] = {
    "PDO": PDO_STATE_MACHINE,
    "SETTLEMENT": SETTLEMENT_STATE_MACHINE,
    "PROOF": PROOF_STATE_MACHINE,
    "DEPLOYMENT": DEPLOYMENT_STATE_MACHINE,
    "RISK_DECISION": RISK_DECISION_STATE_MACHINE,
    "SHIPMENT": SHIPMENT_STATE_MACHINE,
}


def get_state_machine(artifact_type: str) -> Optional[StateMachine]:
    """Get the state machine for an artifact type."""
    return STATE_MACHINES.get(artifact_type.upper())


def validate_all_state_machines() -> Dict[str, list[str]]:
    """Validate all registered state machines and return any errors."""
    results: Dict[str, list[str]] = {}
    for name, machine in STATE_MACHINES.items():
        errors = machine.validate_machine_integrity()
        results[name] = errors
    return results
