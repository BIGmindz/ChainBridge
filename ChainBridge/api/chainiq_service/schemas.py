"""Pydantic schemas describing shipment health and risk summaries."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class DocumentHealth(BaseModel):
    """Summarizes ChainDocs completeness for a shipment."""

    present_count: int
    missing_count: int
    missing_documents: List[str]
    completeness_pct: int
    required_total: int
    optional_total: int
    blocking_gap_count: int
    blocking_documents: List[str]
    mletr_compliant_pct: Optional[int] = None
    version_churn_score: Optional[int] = None


class SettlementHealth(BaseModel):
    """Summarizes ChainPay milestones and float position."""

    milestones_total: int
    milestones_paid: int
    milestones_pending: int
    milestones_held: int
    completion_pct: int
    float_reduction_estimate: Optional[float] = None
    next_milestone: Optional[str] = None


class RiskSummary(BaseModel):
    """Encapsulates derived risk scoring metadata."""

    score: int
    level: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    drivers: List[str]


class ShipmentHealthResponse(BaseModel):
    """Top-level payload returned by Shipment Health endpoint."""

    shipment_id: str
    document_health: DocumentHealth
    settlement_health: SettlementHealth
    risk: RiskSummary
    recommended_actions: List[str]


class AtRiskShipmentSummary(BaseModel):
    """Summarizes latest snapshot for at-risk shipments."""

    shipment_id: str
    corridor_code: Optional[str] = None
    mode: Optional[str] = None
    incoterm: Optional[str] = None
    template_name: Optional[str] = None
    completeness_pct: int
    blocking_gap_count: int
    risk_score: int
    risk_level: str
    last_snapshot_at: datetime
    latest_snapshot_status: Optional[str] = None
    latest_snapshot_updated_at: Optional[datetime] = None


class SnapshotExportEventSummary(BaseModel):
    """Represents snapshot export outbox entries."""

    id: int
    snapshot_id: int
    target_system: str
    status: str
    claimed_by: Optional[str] = None
    claimed_at: Optional[datetime] = None
    retry_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    reason: Optional[str] = None
    last_error: Optional[str] = None


class SnapshotExportEventUpdateRequest(BaseModel):
    """Payload for marking snapshot export events processed."""

    status: str
    last_error: Optional[str] = None
    retryable: bool = True


class SnapshotExportEventCreateRequest(BaseModel):
    """Payload for creating a manual snapshot export request."""

    shipment_id: str
    reason: Optional[str] = None
