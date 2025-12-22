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
]
