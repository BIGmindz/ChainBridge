"""Schemas for Operator Console endpoints."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


<<<<<<< Updated upstream
class RicardianInstrumentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    TERMINATED = "TERMINATED"




=======
>>>>>>> Stashed changes
class OperatorQueueItem(BaseModel):
    id: str
    state: Literal["READY", "BLOCKED", "WAITING_PROOF", "ERROR"]
    amount: float
    currency: str
    risk_score: Optional[float] = None
    readiness_reason: Optional[str] = None
    event_age_seconds: int
    p95_seconds: Optional[int] = None
    intent_hash: Optional[str] = None
    recon_state: Optional[str] = None
    recon_score: Optional[float] = None
    approved_amount: Optional[float] = None
    held_amount: Optional[float] = None
    has_ricardian_wrapper: bool = False
    ricardian_status: Optional[str] = None


class OperatorQueueResponse(BaseModel):
    items: List[OperatorQueueItem]
    total: int
    page: int
    page_size: int


class RiskFactor(BaseModel):
    code: str
    label: str
    weight: float
    contribution: float


class RiskSnapshotResponse(BaseModel):
    settlement_id: str
    intent_id: Optional[str] = None
    risk_score: Optional[float]
    risk_band: Optional[str]
    engine_mode: str
    factors: List[RiskFactor]
    created_at: Optional[datetime]


class SettlementEventItem(BaseModel):
    id: str
    settlement_id: str
    event_type: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class SettlementEventTimelineResponse(BaseModel):
    items: List[SettlementEventItem]


class OperatorEvent(BaseModel):
    id: str
    kind: Literal[
        "webhook_failure",
        "payment_error",
        "payment_confirmed",
        "proof_attached",
        "risk_spike",
        "sla_degraded",
        "info",
    ]
    settlement_id: Optional[str]
    severity: Literal["info", "warning", "error", "critical"]
    message: str
    created_at: datetime


class OperatorEventsResponse(BaseModel):
    items: List[OperatorEvent]


class OperatorIoTHealthSummary(BaseModel):
    device_count_active: int
    device_count_offline: int
    stale_gps_count: int
    stale_env_count: int
    last_ingest_age_seconds: int
    generated_at: datetime


class ReconciliationLineResult(BaseModel):
    line_id: str
    status: str
    reason_code: str
    contract_amount: float
    billed_amount: float
    approved_amount: float
    held_amount: float
    flags: List[str] = []


class ReconciliationSummary(BaseModel):
    decision: str
    approved_amount: float
    held_amount: float
    recon_score: float
    policy_id: str
    flags: List[str] = []
    lines: List[ReconciliationLineResult] = []


class AuditLaneSummary(BaseModel):
    origin_country: Optional[str] = None
    origin_city: Optional[str] = None
    destination_country: Optional[str] = None
    destination_city: Optional[str] = None
    corridor: Optional[str] = None


class AuditCoreSummary(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None
    shipper_id: Optional[str] = None
    carrier_id: Optional[str] = None
    broker_id: Optional[str] = None
    state: Optional[str] = None
    lane: Optional[AuditLaneSummary] = None


class AuditProofStatus(str, Enum):
    NOT_AVAILABLE = "NOT_AVAILABLE"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    PENDING = "PENDING"


class AuditProofProvider(str, Enum):
    NONE = "NONE"
    SXT = "SXT"
    XRPL = "XRPL"
    CHAINLINK = "CHAINLINK"
    OTHER = "OTHER"


class AuditProofSummary(BaseModel):
    intent_hash: Optional[str] = None
    status: AuditProofStatus
    provider: AuditProofProvider
    last_verified_at: Optional[datetime] = None


class AuditRiskSnapshot(BaseModel):
    score: float
    band: str
    created_at: datetime


class AuditRiskSummary(BaseModel):
    latest_score: Optional[float] = None
    latest_band: Optional[str] = None
    engine_mode: Optional[str] = None
    snapshots: List[AuditRiskSnapshot] = []


class AuditEventItem(BaseModel):
    event_type: str
    at: datetime
    severity: Optional[str] = None


class AuditEventTimeline(BaseModel):
    count: int
    first_at: Optional[datetime] = None
    last_at: Optional[datetime] = None
    items: List[AuditEventItem]


class AuditSLASummary(BaseModel):
    sla_band: Optional[str] = None
    expected_p95_seconds: Optional[int] = None
    actual_seconds: Optional[int] = None
    breach: Optional[bool] = None


class AuditIoTSummary(BaseModel):
    has_iot: Optional[bool] = None
    alerts_count: Optional[int] = None
    temp_excursions: Optional[int] = None
    gps_gaps: Optional[int] = None


class AuditDocumentRef(BaseModel):
    external_id: Optional[str] = None
    source: Optional[str] = None
    available: bool = False


class AuditDocuments(BaseModel):
    bol: AuditDocumentRef = AuditDocumentRef()
    customs: AuditDocumentRef = AuditDocumentRef()
    pod: AuditDocumentRef = AuditDocumentRef()


class AuditMetadata(BaseModel):
    triggered_by_rules: List[str] = []
    auto_generated: bool = False


class AuditLegalWrapper(BaseModel):
    instrument_id: Optional[str] = None
    instrument_type: Optional[str] = None
    physical_reference: Optional[str] = None
    pdf_uri: Optional[str] = None
    pdf_hash: Optional[str] = None
    ricardian_version: Optional[str] = None
    governing_law: Optional[str] = None
    smart_contract_chain: Optional[str] = None
    smart_contract_address: Optional[str] = None
    last_signed_tx_hash: Optional[str] = None
    status: Optional[str] = None
    freeze_reason: Optional[str] = None


class AuditPackResponse(BaseModel):
    settlement_id: str
    generated_at: datetime
    source: str = "virtual_v1"

    core: AuditCoreSummary
    proof_summary: AuditProofSummary
    risk_summary: AuditRiskSummary
    events: AuditEventTimeline
    sla_summary: Optional[AuditSLASummary] = None
    iot_summary: Optional[AuditIoTSummary] = None
    documents: AuditDocuments = AuditDocuments()
    audit_metadata: AuditMetadata = AuditMetadata()
    legal_wrapper: Optional[AuditLegalWrapper] = None
