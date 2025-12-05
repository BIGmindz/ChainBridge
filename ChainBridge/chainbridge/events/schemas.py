"""
ChainBridge Event Schema Registry

Unified event schemas for IoT, Seeburger/EDI, Token transitions, and internal events.
All events flow through the Global Event Router for deterministic processing.

Version: 1.0.0
Owner: GID-01 Cody (Senior Backend Engineer)
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, validator


# =============================================================================
# EVENT SOURCE TYPES
# =============================================================================


class EventSource(str, Enum):
    """Canonical event sources in ChainBridge."""

    IOT_CHAINSENSE = "IOT_CHAINSENSE"  # GPS, ELD, Temperature, Door, Shock
    SEEBURGER_EDI = "SEEBURGER_EDI"  # EDI 204, 214, 990, etc.
    DOCUMENT_EXTRACTION = "DOCUMENT_EXTRACTION"  # BOL, POD, Rate Con
    TOKEN_ENGINE = "TOKEN_ENGINE"  # Internal token transitions
    CHAINIQ_RISK = "CHAINIQ_RISK"  # Risk engine outputs
    SXT_PROOF = "SXT_PROOF"  # Space and Time proof responses
    CHAINPAY_SETTLEMENT = "CHAINPAY_SETTLEMENT"  # Settlement events
    ALEX_GOVERNANCE = "ALEX_GOVERNANCE"  # Governance decisions
    OPERATOR_CONSOLE = "OPERATOR_CONSOLE"  # Manual operator actions


class EventPriority(int, Enum):
    """Event priority levels for ordering tiebreakers."""

    CRITICAL = 0  # System safety, fraud alerts
    HIGH = 1  # Settlement, governance decisions
    NORMAL = 2  # Standard operational events
    LOW = 3  # Informational, logging


class EventType(str, Enum):
    """Canonical event types processed by the router."""

    # IoT Events
    IOT_TELEMETRY = "IOT_TELEMETRY"
    IOT_GEOFENCE_ENTER = "IOT_GEOFENCE_ENTER"
    IOT_GEOFENCE_EXIT = "IOT_GEOFENCE_EXIT"
    IOT_ALERT_CRITICAL = "IOT_ALERT_CRITICAL"
    IOT_ALERT_WARNING = "IOT_ALERT_WARNING"
    IOT_SILENCE = "IOT_SILENCE"

    # Seeburger/EDI Events
    EDI_TENDER_REQUEST = "EDI_TENDER_REQUEST"  # 204
    EDI_TENDER_RESPONSE = "EDI_TENDER_RESPONSE"  # 990
    EDI_STATUS_UPDATE = "EDI_STATUS_UPDATE"  # 214
    EDI_INVOICE = "EDI_INVOICE"  # 210

    # Document Events
    DOC_BOL_EXTRACTED = "DOC_BOL_EXTRACTED"
    DOC_POD_EXTRACTED = "DOC_POD_EXTRACTED"
    DOC_RATE_CON_EXTRACTED = "DOC_RATE_CON_EXTRACTED"

    # Token Lifecycle Events
    TOKEN_CREATED = "TOKEN_CREATED"
    TOKEN_TRANSITION = "TOKEN_TRANSITION"
    TOKEN_PROOF_ATTACHED = "TOKEN_PROOF_ATTACHED"
    TOKEN_RELATION_ADDED = "TOKEN_RELATION_ADDED"

    # Risk Events
    RISK_SCORE_COMPUTED = "RISK_SCORE_COMPUTED"
    RISK_ANOMALY_DETECTED = "RISK_ANOMALY_DETECTED"
    RISK_THRESHOLD_BREACH = "RISK_THRESHOLD_BREACH"

    # Proof Events
    PROOF_REQUESTED = "PROOF_REQUESTED"
    PROOF_COMPUTED = "PROOF_COMPUTED"
    PROOF_VALIDATED = "PROOF_VALIDATED"
    PROOF_FAILED = "PROOF_FAILED"

    # Settlement Events
    SETTLEMENT_INITIATED = "SETTLEMENT_INITIATED"
    SETTLEMENT_FUNDED = "SETTLEMENT_FUNDED"
    SETTLEMENT_ESCROWED = "SETTLEMENT_ESCROWED"
    SETTLEMENT_PARTIAL_RELEASE = "SETTLEMENT_PARTIAL_RELEASE"
    SETTLEMENT_FINAL_RELEASE = "SETTLEMENT_FINAL_RELEASE"
    SETTLEMENT_COMPLETE = "SETTLEMENT_COMPLETE"

    # Governance Events
    GOVERNANCE_APPROVAL = "GOVERNANCE_APPROVAL"
    GOVERNANCE_REJECTION = "GOVERNANCE_REJECTION"
    GOVERNANCE_HOLD = "GOVERNANCE_HOLD"
    GOVERNANCE_OVERRIDE = "GOVERNANCE_OVERRIDE"

    # Operator Events
    OPERATOR_OVERRIDE = "OPERATOR_OVERRIDE"
    OPERATOR_APPROVAL = "OPERATOR_APPROVAL"
    OPERATOR_DISPUTE = "OPERATOR_DISPUTE"


# =============================================================================
# BASE EVENT SCHEMA
# =============================================================================


class BaseEvent(BaseModel):
    """
    Base event schema for all ChainBridge events.

    All events must contain:
    - Unique event_id (idempotency key)
    - Source identification
    - Timestamp with microsecond precision
    - Parent shipment linkage
    - Actor identification
    - Digital signature for tamper detection
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique event identifier (idempotency key)",
    )
    event_type: EventType = Field(..., description="Canonical event type")
    source: EventSource = Field(..., description="Event source system")
    priority: EventPriority = Field(default=EventPriority.NORMAL, description="Processing priority")

    # Timestamps
    timestamp: datetime = Field(..., description="Event occurrence time (UTC, microsecond precision)")
    ingested_at: Optional[datetime] = Field(default=None, description="Router ingestion time")
    sequence_id: Optional[int] = Field(default=None, description="Monotonic sequence for ordering tiebreaks")

    # Identity & Linkage
    parent_shipment_id: str = Field(..., description="ST-01 shipment identifier", min_length=3)
    actor_id: str = Field(..., description="Actor who triggered the event")
    device_id: Optional[str] = Field(default=None, description="Device ID for IoT events")

    # Payload
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event-specific payload")

    # Security
    signature: Optional[str] = Field(default=None, description="HMAC signature for tamper detection")
    signature_algorithm: str = Field(default="HMAC-SHA256", description="Signature algorithm")

    # Correlation
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for event chains")
    causation_id: Optional[str] = Field(default=None, description="ID of the event that caused this event")

    class Config:
        use_enum_values = False
        json_encoders = {datetime: lambda v: v.isoformat()}

    @validator("timestamp", pre=True)
    def _normalize_timestamp(cls, v):
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @validator("ingested_at", pre=True, always=True)
    def _set_ingested_at(cls, v):
        if v is None:
            return datetime.now(timezone.utc)
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v

    def compute_signature(self, secret_key: bytes) -> str:
        """Compute HMAC-SHA256 signature for the event."""
        canonical = self._canonical_string()
        signature = hmac.new(secret_key, canonical.encode(), hashlib.sha256).hexdigest()
        return signature

    def verify_signature(self, secret_key: bytes) -> bool:
        """Verify the event signature."""
        if not self.signature:
            return False
        expected = self.compute_signature(secret_key)
        return hmac.compare_digest(self.signature, expected)

    def _canonical_string(self) -> str:
        """Create canonical string for signature computation."""
        return f"{self.event_id}|{self.event_type.value}|{self.source.value}|{self.timestamp.isoformat()}|{self.parent_shipment_id}|{self.actor_id}"

    def ordering_key(self) -> tuple:
        """
        Generate ordering key for deterministic event processing.

        Order by:
        1. Timestamp (primary)
        2. Priority (tiebreaker 1)
        3. Source (tiebreaker 2)
        4. Sequence ID (tiebreaker 3)
        """
        return (
            self.timestamp,
            self.priority.value if isinstance(self.priority, EventPriority) else self.priority,
            self.source.value if isinstance(self.source, EventSource) else self.source,
            self.sequence_id or 0,
        )


# =============================================================================
# IOT EVENT SCHEMAS
# =============================================================================


class IoTTelemetryPayload(BaseModel):
    """Payload for IoT telemetry events."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    speed_mph: float = Field(..., ge=0)
    speed_mps: float = Field(..., ge=0)
    heading: float = Field(default=0, ge=0, le=360)
    engine_state: str
    ignition: bool
    idle_time_seconds: int = Field(default=0, ge=0)
    battery_voltage: Optional[float] = Field(default=None)
    position_accuracy_m: float = Field(default=10.0)
    temperature_celsius: Optional[float] = Field(default=None)
    door_state: Optional[Literal["OPEN", "CLOSED"]] = Field(default=None)
    shock_detected: bool = Field(default=False)
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class IoTAlertPayload(BaseModel):
    """Payload for IoT alert events."""

    alert_type: str = Field(
        ...,
        description="Alert type: TEMPERATURE, SHOCK, DOOR, BATTERY, GEOFENCE, SILENCE",
    )
    severity: Literal["CRITICAL", "WARNING", "INFO"] = Field(...)
    threshold_value: Optional[float] = Field(default=None)
    actual_value: Optional[float] = Field(default=None)
    message: str = Field(...)
    location: Optional[Dict[str, float]] = Field(default=None)


class IoTGeofencePayload(BaseModel):
    """Payload for geofence events."""

    geofence_id: str = Field(...)
    geofence_name: str = Field(...)
    geofence_type: Literal["SHIPPER_PICKUP", "CONSIGNEE", "TERMINAL", "BORDER", "CUSTOM"] = Field(...)
    action: Literal["ENTER", "EXIT"] = Field(...)
    dwell_time_seconds: Optional[int] = Field(default=None)
    location: Dict[str, float] = Field(...)


class IoTTelemetryEvent(BaseEvent):
    """IoT telemetry event from ChainSense."""

    event_type: Literal[EventType.IOT_TELEMETRY] = EventType.IOT_TELEMETRY
    source: Literal[EventSource.IOT_CHAINSENSE] = EventSource.IOT_CHAINSENSE
    payload: IoTTelemetryPayload


class IoTAlertEvent(BaseEvent):
    """IoT alert event (critical or warning)."""

    event_type: Literal[EventType.IOT_ALERT_CRITICAL, EventType.IOT_ALERT_WARNING] = Field(...)
    source: Literal[EventSource.IOT_CHAINSENSE] = EventSource.IOT_CHAINSENSE
    payload: IoTAlertPayload


class IoTGeofenceEvent(BaseEvent):
    """IoT geofence event."""

    event_type: Literal[EventType.IOT_GEOFENCE_ENTER, EventType.IOT_GEOFENCE_EXIT] = Field(...)
    source: Literal[EventSource.IOT_CHAINSENSE] = EventSource.IOT_CHAINSENSE
    payload: IoTGeofencePayload


# =============================================================================
# SEEBURGER/EDI EVENT SCHEMAS
# =============================================================================


class EDIPayload(BaseModel):
    """Base payload for EDI events."""

    edi_type: str = Field(..., description="EDI transaction type (204, 214, 990, 210)")
    edi_version: str = Field(default="X12_4010")
    interchange_control_number: str = Field(...)
    sender_id: str = Field(...)
    receiver_id: str = Field(...)
    raw_segments: Optional[List[str]] = Field(default=None)


class EDI214Payload(EDIPayload):
    """EDI 214 Status Update payload."""

    edi_type: Literal["214"] = "214"
    status_code: str = Field(..., description="EDI status code (AG, AF, X1, etc.)")
    status_reason: Optional[str] = Field(default=None)
    location_code: Optional[str] = Field(default=None)
    location_name: Optional[str] = Field(default=None)
    appointment_time: Optional[datetime] = Field(default=None)
    actual_time: Optional[datetime] = Field(default=None)
    equipment_number: Optional[str] = Field(default=None)
    driver_name: Optional[str] = Field(default=None)


class EDI204Payload(EDIPayload):
    """EDI 204 Tender Request payload."""

    edi_type: Literal["204"] = "204"
    shipper_id: str = Field(...)
    carrier_id: str = Field(...)
    origin: Dict[str, str] = Field(...)
    destination: Dict[str, str] = Field(...)
    pickup_date: datetime = Field(...)
    delivery_date: datetime = Field(...)
    weight_lbs: Optional[float] = Field(default=None)
    equipment_type: Optional[str] = Field(default=None)
    rate_amount: Optional[float] = Field(default=None)
    rate_currency: str = Field(default="USD")


class EDIStatusEvent(BaseEvent):
    """Seeburger EDI 214 Status Update event."""

    event_type: Literal[EventType.EDI_STATUS_UPDATE] = EventType.EDI_STATUS_UPDATE
    source: Literal[EventSource.SEEBURGER_EDI] = EventSource.SEEBURGER_EDI
    payload: EDI214Payload


class EDITenderEvent(BaseEvent):
    """Seeburger EDI 204 Tender Request event."""

    event_type: Literal[EventType.EDI_TENDER_REQUEST] = EventType.EDI_TENDER_REQUEST
    source: Literal[EventSource.SEEBURGER_EDI] = EventSource.SEEBURGER_EDI
    payload: EDI204Payload


# =============================================================================
# TOKEN LIFECYCLE EVENT SCHEMAS
# =============================================================================


class TokenEventPayload(BaseModel):
    """Payload for token lifecycle events."""

    token_id: str = Field(...)
    token_type: str = Field(..., description="Token type: ST-01, MT-01, AT-02, IT-01, PT-01, etc.")
    previous_state: Optional[str] = Field(default=None)
    new_state: str = Field(...)
    metadata_changes: Dict[str, Any] = Field(default_factory=dict)
    relation_changes: Dict[str, Any] = Field(default_factory=dict)
    proof_hash: Optional[str] = Field(default=None)
    governance_id: Optional[str] = Field(default=None)


class TokenCreatedEvent(BaseEvent):
    """Token creation event."""

    event_type: Literal[EventType.TOKEN_CREATED] = EventType.TOKEN_CREATED
    source: Literal[EventSource.TOKEN_ENGINE] = EventSource.TOKEN_ENGINE
    payload: TokenEventPayload


class TokenTransitionEvent(BaseEvent):
    """Token state transition event."""

    event_type: Literal[EventType.TOKEN_TRANSITION] = EventType.TOKEN_TRANSITION
    source: Literal[EventSource.TOKEN_ENGINE] = EventSource.TOKEN_ENGINE
    payload: TokenEventPayload


class TokenProofAttachedEvent(BaseEvent):
    """Token proof attachment event."""

    event_type: Literal[EventType.TOKEN_PROOF_ATTACHED] = EventType.TOKEN_PROOF_ATTACHED
    source: Literal[EventSource.TOKEN_ENGINE] = EventSource.TOKEN_ENGINE
    payload: TokenEventPayload


# =============================================================================
# RISK EVENT SCHEMAS
# =============================================================================


class RiskScorePayload(BaseModel):
    """Payload for risk scoring events."""

    risk_score: int = Field(..., ge=0, le=100)
    risk_label: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(...)
    confidence: float = Field(..., ge=0, le=1)
    explanation: str = Field(...)
    feature_contributions: Dict[str, float] = Field(default_factory=dict)
    anomaly_flags: List[str] = Field(default_factory=list)
    recommended_action: str = Field(...)
    requires_proof: bool = Field(default=False)


class RiskAnomalyPayload(BaseModel):
    """Payload for anomaly detection events."""

    anomaly_type: str = Field(...)
    anomaly_score: float = Field(..., ge=0, le=1)
    affected_tokens: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    recommended_action: str = Field(...)


class RiskScoreEvent(BaseEvent):
    """Risk score computation event."""

    event_type: Literal[EventType.RISK_SCORE_COMPUTED] = EventType.RISK_SCORE_COMPUTED
    source: Literal[EventSource.CHAINIQ_RISK] = EventSource.CHAINIQ_RISK
    payload: RiskScorePayload


class RiskAnomalyEvent(BaseEvent):
    """Risk anomaly detection event."""

    event_type: Literal[EventType.RISK_ANOMALY_DETECTED] = EventType.RISK_ANOMALY_DETECTED
    source: Literal[EventSource.CHAINIQ_RISK] = EventSource.CHAINIQ_RISK
    payload: RiskAnomalyPayload


# =============================================================================
# PROOF EVENT SCHEMAS
# =============================================================================


class ProofPayload(BaseModel):
    """Payload for proof events."""

    proof_id: str = Field(...)
    proof_type: str = Field(..., description="Proof type: DETENTION, LAYOVER, REWEIGH, MILEAGE, etc.")
    proof_hash: Optional[str] = Field(default=None)
    proof_source: str = Field(default="SxT")
    target_token_id: str = Field(...)
    target_token_type: str = Field(...)
    input_data_hash: str = Field(...)
    computation_time_ms: Optional[int] = Field(default=None)
    validated: bool = Field(default=False)
    validation_errors: List[str] = Field(default_factory=list)


class ProofRequestedEvent(BaseEvent):
    """Proof request event."""

    event_type: Literal[EventType.PROOF_REQUESTED] = EventType.PROOF_REQUESTED
    source: Literal[EventSource.TOKEN_ENGINE] = EventSource.TOKEN_ENGINE
    payload: ProofPayload


class ProofComputedEvent(BaseEvent):
    """Proof computation complete event."""

    event_type: Literal[EventType.PROOF_COMPUTED] = EventType.PROOF_COMPUTED
    source: Literal[EventSource.SXT_PROOF] = EventSource.SXT_PROOF
    payload: ProofPayload


class ProofValidatedEvent(BaseEvent):
    """Proof validation event."""

    event_type: Literal[EventType.PROOF_VALIDATED] = EventType.PROOF_VALIDATED
    source: Literal[EventSource.SXT_PROOF] = EventSource.SXT_PROOF
    payload: ProofPayload


# =============================================================================
# SETTLEMENT EVENT SCHEMAS
# =============================================================================


class SettlementPayload(BaseModel):
    """Payload for settlement events."""

    settlement_id: str = Field(...)
    pt01_id: str = Field(...)
    it01_id: str = Field(...)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD")
    escrow_account: Optional[str] = Field(default=None)
    xrpl_tx_hash: Optional[str] = Field(default=None)
    release_type: Optional[Literal["PARTIAL", "FINAL"]] = Field(default=None)
    release_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    reason: Optional[str] = Field(default=None)


class SettlementInitiatedEvent(BaseEvent):
    """Settlement initiation event."""

    event_type: Literal[EventType.SETTLEMENT_INITIATED] = EventType.SETTLEMENT_INITIATED
    source: Literal[EventSource.CHAINPAY_SETTLEMENT] = EventSource.CHAINPAY_SETTLEMENT
    payload: SettlementPayload


class SettlementCompleteEvent(BaseEvent):
    """Settlement completion event."""

    event_type: Literal[EventType.SETTLEMENT_COMPLETE] = EventType.SETTLEMENT_COMPLETE
    source: Literal[EventSource.CHAINPAY_SETTLEMENT] = EventSource.CHAINPAY_SETTLEMENT
    payload: SettlementPayload


# =============================================================================
# GOVERNANCE EVENT SCHEMAS
# =============================================================================


class GovernancePayload(BaseModel):
    """Payload for governance events."""

    governance_id: str = Field(...)
    decision: Literal["APPROVED", "REJECTED", "HOLD", "OVERRIDE"] = Field(...)
    target_token_id: str = Field(...)
    target_token_type: str = Field(...)
    policy_match_id: Optional[str] = Field(default=None)
    mantra_check: Dict[str, bool] = Field(default_factory=lambda: {"proof": False, "pipes": False, "cash": False})
    reason: str = Field(...)
    operator_id: Optional[str] = Field(default=None)
    override_code: Optional[str] = Field(default=None)
    expiry: Optional[datetime] = Field(default=None)


class GovernanceApprovalEvent(BaseEvent):
    """Governance approval event."""

    event_type: Literal[EventType.GOVERNANCE_APPROVAL] = EventType.GOVERNANCE_APPROVAL
    source: Literal[EventSource.ALEX_GOVERNANCE] = EventSource.ALEX_GOVERNANCE
    priority: EventPriority = EventPriority.HIGH
    payload: GovernancePayload


class GovernanceRejectionEvent(BaseEvent):
    """Governance rejection event."""

    event_type: Literal[EventType.GOVERNANCE_REJECTION] = EventType.GOVERNANCE_REJECTION
    source: Literal[EventSource.ALEX_GOVERNANCE] = EventSource.ALEX_GOVERNANCE
    priority: EventPriority = EventPriority.HIGH
    payload: GovernancePayload


# =============================================================================
# ROUTING RESULT SCHEMAS
# =============================================================================


class RoutingDecision(str, Enum):
    """Router decision outcomes."""

    PROCESSED = "PROCESSED"
    DEDUPED = "DEDUPED"
    REJECTED = "REJECTED"
    QUEUED = "QUEUED"
    DEAD_LETTERED = "DEAD_LETTERED"


class RoutingResult(BaseModel):
    """Result of event routing."""

    event_id: str = Field(...)
    decision: RoutingDecision = Field(...)
    tokens_affected: List[str] = Field(default_factory=list)
    tokens_created: List[str] = Field(default_factory=list)
    downstream_events: List[str] = Field(default_factory=list)
    risk_signals_emitted: bool = Field(default=False)
    proof_requests_emitted: bool = Field(default=False)
    settlement_triggers: bool = Field(default=False)
    oc_events_emitted: bool = Field(default=False)
    processing_time_ms: float = Field(...)
    error_message: Optional[str] = Field(default=None)
    governance_required: bool = Field(default=False)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "EventSource",
    "EventPriority",
    "EventType",
    "RoutingDecision",
    # Base
    "BaseEvent",
    # IoT Events
    "IoTTelemetryPayload",
    "IoTAlertPayload",
    "IoTGeofencePayload",
    "IoTTelemetryEvent",
    "IoTAlertEvent",
    "IoTGeofenceEvent",
    # EDI Events
    "EDIPayload",
    "EDI214Payload",
    "EDI204Payload",
    "EDIStatusEvent",
    "EDITenderEvent",
    # Token Events
    "TokenEventPayload",
    "TokenCreatedEvent",
    "TokenTransitionEvent",
    "TokenProofAttachedEvent",
    # Risk Events
    "RiskScorePayload",
    "RiskAnomalyPayload",
    "RiskScoreEvent",
    "RiskAnomalyEvent",
    # Proof Events
    "ProofPayload",
    "ProofRequestedEvent",
    "ProofComputedEvent",
    "ProofValidatedEvent",
    # Settlement Events
    "SettlementPayload",
    "SettlementInitiatedEvent",
    "SettlementCompleteEvent",
    # Governance Events
    "GovernancePayload",
    "GovernanceApprovalEvent",
    "GovernanceRejectionEvent",
    # Routing
    "RoutingResult",
]
