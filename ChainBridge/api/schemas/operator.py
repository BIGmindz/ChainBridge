"""Schemas for Operator endpoints."""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from pydantic import BaseModel


class OperatorQueueItem(BaseModel):
    id: str
    state: str
    amount: float
    pricing_breakdown: Optional[Dict[str, Any]] = None
    risk_score: Optional[float] = None
    readiness_reason: Optional[str] = None
    event_age_seconds: Optional[float] = None
    p95_seconds: Optional[float] = None
    intent_hash: Optional[str] = None


class OperatorQueueResponse(BaseModel):
    items: List[OperatorQueueItem]
    total: int


class RiskSnapshotResponse(BaseModel):
    intent_id: str
    risk_score: Optional[float]
    risk_level: Optional[str]
    features: Optional[dict] = None
    decided_at: Optional[datetime] = None


class OperatorEventStreamItem(BaseModel):
    type: str
    message: str
    created_at: datetime
    severity: str = "info"


class OperatorEventStreamResponse(BaseModel):
    events: List[OperatorEventStreamItem]


class OperatorEventKind(str, Enum):
    webhook_failure = "webhook_failure"
    payment_error = "payment_error"
    payment_confirmed = "payment_confirmed"
    proof_attached = "proof_attached"
    risk_spike = "risk_spike"
    sla_degraded = "sla_degraded"
    info = "info"


class OperatorEventSeverity(str, Enum):
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class OperatorEvent(BaseModel):
    id: str
    kind: OperatorEventKind
    settlement_id: Optional[str] = None
    severity: OperatorEventSeverity
    message: str
    created_at: datetime


class OperatorEventsResponse(BaseModel):
    items: List[OperatorEvent]


class IoTHealthSummaryResponse(BaseModel):
    device_count_active: int
    device_count_offline: int
    stale_gps_count: int
    stale_env_count: int
    last_ingest_age_seconds: int
