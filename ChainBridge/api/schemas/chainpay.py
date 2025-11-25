"""Pydantic models for ChainPay settlement plans."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ChainPayMilestone(BaseModel):
    """Represents a payout milestone in a settlement plan."""

    event: str  # e.g. "BOL_ISSUED"
    payout_pct: float  # 0.4 means 40%
    status: str  # "PAID" | "PENDING" | "HELD"
    paid_at: Optional[str] = None  # ISO timestamp when applicable


class DocRiskSnapshot(BaseModel):
    """Surface document-driven risk metadata to ChainPay clients."""

    score: int
    level: str
    missing_blocking_docs: List[str]


class PaymentIntentShipmentSummary(BaseModel):
    """Lightweight shipment context for PaymentIntent listings."""

    corridor_code: Optional[str] = None
    mode: Optional[str] = None
    incoterm: Optional[str] = None


class ChainPaySettlementPlan(BaseModel):
    """API response describing the settlement plan for a shipment."""

    shipment_id: str
    template_id: str
    total_value: float
    milestones: List[ChainPayMilestone]
    float_reduction_estimate: float  # 0.99 = 99% reduction
    doc_risk: Optional[DocRiskSnapshot] = None


class ChainPaySettlementPlanCreate(BaseModel):
    """Payload for creating or replacing a settlement plan."""

    template_id: str
    total_value: float
    milestones: List[ChainPayMilestone]
    float_reduction_estimate: float = 0.99


class PaymentIntentCreate(BaseModel):
    """Creation payload for PaymentIntents derived from shipments."""

    shipment_id: str
    amount: float
    currency: str
    counterparty: str
    notes: Optional[str] = None


class PaymentIntentRead(BaseModel):
    """Detailed view of a PaymentIntent."""

    id: str
    shipment_id: str
    latest_risk_snapshot_id: Optional[int] = None
    amount: float
    currency: str
    status: str
    has_proof: bool = False
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    proof_pack_id: Optional[str] = None
    counterparty: Optional[str] = None
    freight_reference: Optional[str] = None
    notes: Optional[str] = None
    clearing_partner: Optional[str] = None
    intent_hash: Optional[str] = None
    risk_gate_reason: Optional[str] = None
    compliance_blocks: Optional[list[str]] = None
    ready_at: Optional[datetime] = None
    calculated_amount: Optional[float] = None
    pricing_breakdown: Optional[dict] = None
    recon_state: Optional[str] = None
    recon_score: Optional[float] = None
    recon_policy_id: Optional[str] = None
    approved_amount: Optional[float] = None
    held_amount: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class PaymentIntentListItem(BaseModel):
    """Operator-friendly listing entry for PaymentIntents."""

    id: str
    shipment_id: str
    amount: float
    currency: str
    status: str
    ready_for_payment: bool
    has_proof: bool
    recon_state: Optional[str] = None
    recon_score: Optional[float] = None
    approved_amount: Optional[float] = None
    held_amount: Optional[float] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    corridor_code: Optional[str] = None
    mode: Optional[str] = None
    incoterm: Optional[str] = None
    counterparty: Optional[str] = None
    proof_attached: bool
    shipment_summary: Optional[PaymentIntentShipmentSummary] = None
    created_at: datetime
    updated_at: datetime
    clearing_partner: Optional[str] = None
    intent_hash: Optional[str] = None


class SettlementEventRead(BaseModel):
    """Detailed settlement event."""

    id: str
    payment_intent_id: str
    event_type: str
    status: str
    amount: float
    currency: str
    occurred_at: datetime
    metadata: Optional[dict] = None
    sequence: int


class SettlementEventListItem(BaseModel):
    """List item for settlement events."""

    id: str
    payment_intent_id: str
    event_type: str
    status: str
    amount: float
    currency: str
    occurred_at: datetime
    metadata: Optional[dict] = None
    sequence: int


class SettlementEventCreate(BaseModel):
    """Payload to append a settlement event."""

    event_type: str
    status: str
    amount: float
    currency: str
    occurred_at: Optional[datetime] = None
    metadata: Optional[dict] = None
    actor: Optional[str] = None


class SettlementEventUpdate(BaseModel):
    """Payload to replace/update an existing settlement event."""

    event_type: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    occurred_at: Optional[datetime] = None
    metadata: Optional[dict] = None
    actor: Optional[str] = None


class ProofAttachmentRequest(BaseModel):
    """Payload to attach a ProofPack/Docs bundle to a PaymentIntent."""

    proof_pack_id: str


class PaymentIntentSummary(BaseModel):
    """Aggregate counts for operator dashboards."""

    total: int
    awaiting_proof: int
    ready_for_payment: int
    blocked_by_risk: int
