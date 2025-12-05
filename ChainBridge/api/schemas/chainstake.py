"""Pydantic schemas for ChainStake analytics."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class LiquidityOverview(BaseModel):
    total_tvl_usd: float
    total_utilized_usd: float
    overall_realized_apy: float
    active_positions: int


class StakePoolSummary(BaseModel):
    pool_id: str
    label: str
    corridor: str
    tenor_days: int
    transport_mode: str

    tvl_usd: float
    utilized_usd: float
    target_tvl_usd: float

    base_apy: float
    realized_apy: float
    avg_risk_level: RiskLevel

    open_positions: int
    default_rate_bps: float


class StakePositionRead(BaseModel):
    position_id: str
    shipment_id: str
    payment_intent_id: Optional[str]

    pool_id: str
    corridor: str
    notional_usd: float
    staked_at: datetime
    expected_maturity_at: Optional[datetime]
    realized_apy: Optional[float]

    stake_status: str
    risk_level: RiskLevel

    payout_confidence: Optional[float]
    final_payout_amount: Optional[float]
