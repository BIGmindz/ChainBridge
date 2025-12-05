from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel
from app.payment_rails import SettlementProvider

RiskTier = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class TierHealthMetric(BaseModel):
    tier: RiskTier
    loss_rate: float
    reserve_utilization: float
    unused_reserve_ratio: float
    shipment_count: int


class DaysToCashMetric(BaseModel):
    tier: RiskTier
    corridor_id: str
    median_days_to_first_cash: float
    p95_days_to_first_cash: float
    median_days_to_final_cash: float
    p95_days_to_final_cash: float
    shipment_count: int


class SlaMetric(BaseModel):
    corridor_id: str
    tier: RiskTier
    claim_review_sla_breach_rate: float
    manual_review_sla_breach_rate: float
    cash_breach_rate: float
    cash_breach_count: int
    sample_size: int
    total_reviews: int


class ChainPayAnalyticsSnapshot(BaseModel):
    as_of: str
    corridor_id: str
    payout_policy_version: str
    settlement_provider: SettlementProvider
    tier_health: List[TierHealthMetric]
    days_to_cash: List[DaysToCashMetric]
    sla: List[SlaMetric]
