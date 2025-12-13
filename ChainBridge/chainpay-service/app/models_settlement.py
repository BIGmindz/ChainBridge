from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel
from app.payment_rails import SettlementProvider


class SettlementMilestone(str, Enum):
    PICKUP = "PICKUP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CLAIM_WINDOW = "CLAIM_WINDOW"
    FINALIZED = "FINALIZED"


class SettlementEvent(BaseModel):
    id: str
    shipment_id: str
    timestamp: str  # ISO 8601
    milestone: SettlementMilestone
    risk_tier: Optional[str] = None  # LOW | MEDIUM | HIGH
    notes: Optional[str] = None


class CbUsdAmount(BaseModel):
    total: float
    released: float
    reserved: float


class SettlementStatus(BaseModel):
    shipment_id: str
    cb_usd: CbUsdAmount
    events: List[SettlementEvent]
    current_milestone: SettlementMilestone
    risk_score: Optional[float] = None
    settlement_provider: SettlementProvider = SettlementProvider.INTERNAL_LEDGER
