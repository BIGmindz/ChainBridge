"""
ChainBridge State Module

Atlas (GID-05) — System State Engine
Authority: Benson (GID-00)

This module provides canonical state management for ChainBridge.
All state operations are READ-ONLY unless explicitly authorized.
"""

from .state_schema import (
    ArtifactType,
    EventStateRecord,
    EventType,
    OverrideStateRecord,
    PDOState,
    PDOStateRecord,
    ProofStateRecord,
    RiskVerdictStateRecord,
    SettlementState,
    SettlementStateRecord,
    ShipmentState,
    ShipmentStateRecord,
    StateMetadata,
    StateTransition,
    get_terminal_states,
    is_valid_transition,
    PDO_TRANSITIONS,
    SETTLEMENT_TRANSITIONS,
    SHIPMENT_TRANSITIONS,
)
from .state_validator import (
    StateValidator,
    StateViolation,
    ValidationResult,
    ViolationSeverity,
    ViolationType,
    validate_event_ordering,
    validate_state_transition,
)
from .state_replay import (
    ReplayResult,
    ReplayState,
    StateReplayEngine,
    replay_artifact_events,
    verify_replay_determinism,
)
from .state_machine import (
    StateMachine,
    TransitionRule,
    ProofState,
    DeploymentState,
    RiskDecisionState,
    STATE_MACHINES,
    PDO_STATE_MACHINE,
    SETTLEMENT_STATE_MACHINE,
    PROOF_STATE_MACHINE,
    DEPLOYMENT_STATE_MACHINE,
    RISK_DECISION_STATE_MACHINE,
    SHIPMENT_STATE_MACHINE,
    get_state_machine,
    validate_all_state_machines,
)
from .transition_validator import (
    TransitionValidator,
    TransitionRequest,
    TransitionResult,
    TransitionValidationResult,
    validate_transition,
    is_transition_allowed,
    get_allowed_transitions,
)
from .transition_proof import (
    StateTransitionProof,
    TransitionProofEmitter,
    verify_transition_proof,
    verify_proof_chain,
    create_transition_proof,
)

__all__ = [
    # Schema
    "ArtifactType",
    "EventStateRecord",
    "EventType",
    "OverrideStateRecord",
    "PDOState",
    "PDOStateRecord",
    "ProofStateRecord",
    "RiskVerdictStateRecord",
    "SettlementState",
    "SettlementStateRecord",
    "ShipmentState",
    "ShipmentStateRecord",
    "StateMetadata",
    "StateTransition",
    "get_terminal_states",
    "is_valid_transition",
    "PDO_TRANSITIONS",
    "SETTLEMENT_TRANSITIONS",
    "SHIPMENT_TRANSITIONS",
    # Validator
    "StateValidator",
    "StateViolation",
    "ValidationResult",
    "ViolationSeverity",
    "ViolationType",
    "validate_event_ordering",
    "validate_state_transition",
    # Replay
    "ReplayResult",
    "ReplayState",
    "StateReplayEngine",
    "replay_artifact_events",
    "verify_replay_determinism",
    # State Machines (A12)
    "StateMachine",
    "TransitionRule",
    "ProofState",
    "DeploymentState",
    "RiskDecisionState",
    "STATE_MACHINES",
    "PDO_STATE_MACHINE",
    "SETTLEMENT_STATE_MACHINE",
    "PROOF_STATE_MACHINE",
    "DEPLOYMENT_STATE_MACHINE",
    "RISK_DECISION_STATE_MACHINE",
    "SHIPMENT_STATE_MACHINE",
    "get_state_machine",
    "validate_all_state_machines",
    # Transition Validator (A12)
    "TransitionValidator",
    "TransitionRequest",
    "TransitionResult",
    "TransitionValidationResult",
    "validate_transition",
    "is_transition_allowed",
    "get_allowed_transitions",
    # Transition Proof (A12)
    "StateTransitionProof",
    "TransitionProofEmitter",
    "verify_transition_proof",
    "verify_proof_chain",
    "create_transition_proof",
]
