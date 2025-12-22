"""
ChainBridge Canonical State Schema

Atlas (GID-05) — System State Engine
Authority: Benson (GID-00)

This module defines the canonical state schema for all ChainBridge artifacts.
All state representations must conform to these schemas.

INVARIANTS:
- One state per artifact ID
- Forward-only transitions
- No retroactive mutation
- Proof lineage required
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# STATE ENUMS
# =============================================================================


class ShipmentState(str, Enum):
    """Allowed shipment states with defined transition rules."""

    CREATED = "CREATED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    EXCEPTION = "EXCEPTION"
    RESOLVED = "RESOLVED"
    SETTLED = "SETTLED"
    CANCELLED = "CANCELLED"


class SettlementState(str, Enum):
    """Allowed settlement states with defined transition rules."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    FINALIZED = "FINALIZED"
    REJECTED = "REJECTED"
    DISPUTED = "DISPUTED"
    RESOLVED = "RESOLVED"
    BLOCKED = "BLOCKED"


class PDOState(str, Enum):
    """Allowed PDO states with defined transition rules."""

    CREATED = "CREATED"
    SIGNED = "SIGNED"
    VERIFIED = "VERIFIED"
    ACCEPTED = "ACCEPTED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class EventType(str, Enum):
    """Canonical event types for state transitions."""

    SHIPMENT_CREATED = "SHIPMENT_CREATED"
    SHIPMENT_DEPARTED = "SHIPMENT_DEPARTED"
    SHIPMENT_ARRIVED = "SHIPMENT_ARRIVED"
    SHIPMENT_DELIVERED = "SHIPMENT_DELIVERED"
    SHIPMENT_EXCEPTION = "SHIPMENT_EXCEPTION"
    SHIPMENT_RESOLVED = "SHIPMENT_RESOLVED"
    SHIPMENT_CANCELLED = "SHIPMENT_CANCELLED"
    SETTLEMENT_INITIATED = "SETTLEMENT_INITIATED"
    SETTLEMENT_APPROVED = "SETTLEMENT_APPROVED"
    SETTLEMENT_EXECUTED = "SETTLEMENT_EXECUTED"
    SETTLEMENT_FINALIZED = "SETTLEMENT_FINALIZED"
    SETTLEMENT_REJECTED = "SETTLEMENT_REJECTED"
    SETTLEMENT_DISPUTED = "SETTLEMENT_DISPUTED"
    PDO_CREATED = "PDO_CREATED"
    PDO_SIGNED = "PDO_SIGNED"
    PDO_VERIFIED = "PDO_VERIFIED"
    PDO_REJECTED = "PDO_REJECTED"
    RISK_VERDICT_ISSUED = "RISK_VERDICT_ISSUED"
    OVERRIDE_APPLIED = "OVERRIDE_APPLIED"


class ArtifactType(str, Enum):
    """Canonical artifact types in ChainBridge state."""

    SHIPMENT = "SHIPMENT"
    EVENT = "EVENT"
    PDO = "PDO"
    PROOF = "PROOF"
    SETTLEMENT = "SETTLEMENT"
    RISK_VERDICT = "RISK_VERDICT"
    OVERRIDE = "OVERRIDE"


# =============================================================================
# BASE STATE MODELS
# =============================================================================


class StateMetadata(BaseModel):
    """Metadata attached to every state record."""

    version: str = Field(default="1.0.0", description="Schema version")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    proof_id: Optional[str] = Field(default=None, description="Associated proof artifact")
    source_event_id: Optional[str] = Field(default=None, description="Event that triggered this state")
    is_finalized: bool = Field(default=False, description="Whether state is immutable")
    finalized_at: Optional[datetime] = Field(default=None)

    @field_validator("updated_at")
    @classmethod
    def updated_not_before_created(cls, v: datetime, info) -> datetime:
        """Ensure updated_at is not before created_at."""
        created = info.data.get("created_at")
        if created and v < created:
            raise ValueError("updated_at cannot be before created_at")
        return v


class StateTransition(BaseModel):
    """Record of a state transition for audit trail."""

    transition_id: str = Field(..., description="Unique transition identifier")
    artifact_type: ArtifactType
    artifact_id: str
    from_state: str
    to_state: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    proof_id: str = Field(..., description="Proof artifact authorizing transition")
    actor_id: Optional[str] = Field(default=None, description="Agent or human that triggered")
    reason: Optional[str] = Field(default=None)

    @field_validator("to_state")
    @classmethod
    def transition_not_to_same_state(cls, v: str, info) -> str:
        """Prevent no-op transitions."""
        from_state = info.data.get("from_state")
        if from_state and v == from_state:
            raise ValueError("Cannot transition to the same state")
        return v


# =============================================================================
# DOMAIN STATE MODELS
# =============================================================================


class ShipmentStateRecord(BaseModel):
    """Canonical shipment state representation."""

    shipment_id: str = Field(..., description="Primary key")
    state: ShipmentState
    origin: str
    destination: str
    carrier_id: Optional[str] = None
    expected_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    metadata: StateMetadata = Field(default_factory=StateMetadata)
    transition_history: list[str] = Field(default_factory=list, description="List of transition IDs")


class EventStateRecord(BaseModel):
    """Canonical event state representation."""

    event_id: str = Field(..., description="Primary key")
    event_type: EventType
    artifact_type: ArtifactType
    artifact_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sequence_number: int = Field(..., ge=0, description="Monotonic sequence within artifact")
    payload_hash: str = Field(..., description="SHA256 of event payload")
    metadata: StateMetadata = Field(default_factory=StateMetadata)

    @field_validator("sequence_number")
    @classmethod
    def sequence_must_be_positive(cls, v: int) -> int:
        """Sequence numbers must be non-negative."""
        if v < 0:
            raise ValueError("sequence_number must be >= 0")
        return v


class PDOStateRecord(BaseModel):
    """Canonical PDO state representation."""

    pdo_id: str = Field(..., description="Primary key")
    state: PDOState
    decision_subject: str
    actor_id: str
    policy_reference: str
    decision: str
    signature: Optional[str] = None
    signature_algorithm: Optional[str] = None
    verified_at: Optional[datetime] = None
    metadata: StateMetadata = Field(default_factory=StateMetadata)


class ProofStateRecord(BaseModel):
    """Canonical proof artifact state representation."""

    proof_id: str = Field(..., description="Primary key")
    proof_type: str
    artifact_type: ArtifactType
    artifact_id: str
    content_hash: str = Field(..., description="SHA256 of proof content")
    signature: str
    signer_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: StateMetadata = Field(default_factory=StateMetadata)


class SettlementStateRecord(BaseModel):
    """Canonical settlement state representation."""

    settlement_id: str = Field(..., description="Primary key")
    state: SettlementState
    shipment_id: str
    amount: float = Field(..., ge=0)
    currency: str = Field(default="CB-USDx")
    payer_id: str
    payee_id: str
    pdo_id: Optional[str] = None
    executed_at: Optional[datetime] = None
    metadata: StateMetadata = Field(default_factory=StateMetadata)


class RiskVerdictStateRecord(BaseModel):
    """Canonical risk verdict state representation."""

    verdict_id: str = Field(..., description="Primary key")
    artifact_type: ArtifactType
    artifact_id: str
    decision: str = Field(..., description="ALLOW, BLOCK, REVIEW")
    risk_score: float = Field(..., ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
    policy_version: str
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: StateMetadata = Field(default_factory=StateMetadata)


class OverrideStateRecord(BaseModel):
    """Canonical override state representation."""

    override_id: str = Field(..., description="Primary key")
    artifact_type: ArtifactType
    artifact_id: str
    override_type: str = Field(..., description="RISK_BYPASS, STATE_CORRECTION, MANUAL_SETTLEMENT")
    actor_id: str
    actor_type: str = Field(..., description="HUMAN or AGENT")
    justification: str
    approval_chain: list[str] = Field(default_factory=list, description="List of approver IDs")
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: StateMetadata = Field(default_factory=StateMetadata)


# =============================================================================
# TRANSITION RULES
# =============================================================================


SHIPMENT_TRANSITIONS: dict[ShipmentState, set[ShipmentState]] = {
    ShipmentState.CREATED: {ShipmentState.IN_TRANSIT, ShipmentState.CANCELLED},
    ShipmentState.IN_TRANSIT: {
        ShipmentState.DELIVERED,
        ShipmentState.EXCEPTION,
        ShipmentState.CANCELLED,
    },
    ShipmentState.DELIVERED: {ShipmentState.SETTLED},
    ShipmentState.EXCEPTION: {ShipmentState.RESOLVED},
    ShipmentState.RESOLVED: {ShipmentState.SETTLED},
    ShipmentState.SETTLED: set(),  # Terminal state
    ShipmentState.CANCELLED: set(),  # Terminal state
}


SETTLEMENT_TRANSITIONS: dict[SettlementState, set[SettlementState]] = {
    SettlementState.PENDING: {
        SettlementState.APPROVED,
        SettlementState.REJECTED,
        SettlementState.BLOCKED,
    },
    SettlementState.APPROVED: {SettlementState.EXECUTED},
    SettlementState.EXECUTED: {SettlementState.FINALIZED},
    SettlementState.FINALIZED: set(),  # Terminal state
    SettlementState.REJECTED: {SettlementState.DISPUTED},
    SettlementState.DISPUTED: {SettlementState.RESOLVED},
    SettlementState.RESOLVED: {SettlementState.FINALIZED},
    SettlementState.BLOCKED: {SettlementState.PENDING, SettlementState.REJECTED},
}


PDO_TRANSITIONS: dict[PDOState, set[PDOState]] = {
    PDOState.CREATED: {PDOState.SIGNED, PDOState.EXPIRED},
    PDOState.SIGNED: {PDOState.VERIFIED, PDOState.VERIFICATION_FAILED},
    PDOState.VERIFIED: {PDOState.ACCEPTED},
    PDOState.ACCEPTED: set(),  # Terminal state
    PDOState.VERIFICATION_FAILED: {PDOState.REJECTED},
    PDOState.REJECTED: set(),  # Terminal state
    PDOState.EXPIRED: set(),  # Terminal state
}


def is_valid_transition(
    artifact_type: ArtifactType,
    from_state: str,
    to_state: str,
) -> bool:
    """
    Check if a state transition is valid according to defined rules.

    Returns True if the transition is allowed, False otherwise.
    """
    if artifact_type == ArtifactType.SHIPMENT:
        try:
            from_enum = ShipmentState(from_state)
            to_enum = ShipmentState(to_state)
            return to_enum in SHIPMENT_TRANSITIONS.get(from_enum, set())
        except ValueError:
            return False

    elif artifact_type == ArtifactType.SETTLEMENT:
        try:
            from_enum = SettlementState(from_state)
            to_enum = SettlementState(to_state)
            return to_enum in SETTLEMENT_TRANSITIONS.get(from_enum, set())
        except ValueError:
            return False

    elif artifact_type == ArtifactType.PDO:
        try:
            from_enum = PDOState(from_state)
            to_enum = PDOState(to_state)
            return to_enum in PDO_TRANSITIONS.get(from_enum, set())
        except ValueError:
            return False

    # For other artifact types, allow any transition (not yet constrained)
    return True


def get_terminal_states(artifact_type: ArtifactType) -> set[str]:
    """Get the terminal (final) states for an artifact type."""
    if artifact_type == ArtifactType.SHIPMENT:
        return {s.value for s, targets in SHIPMENT_TRANSITIONS.items() if not targets}
    elif artifact_type == ArtifactType.SETTLEMENT:
        return {s.value for s, targets in SETTLEMENT_TRANSITIONS.items() if not targets}
    elif artifact_type == ArtifactType.PDO:
        return {s.value for s, targets in PDO_TRANSITIONS.items() if not targets}
    return set()
