"""Schemas for ChainPay Context Ledger risk scoring."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ContextLedgerEvent(BaseModel):
    event_id: str
    timestamp: datetime
    amount: float
    currency: str
    corridor_id: str
    counterparty_id: str
    counterparty_role: Literal["buyer", "seller", "carrier", "broker", "anchor"]
    settlement_channel: str
    event_type: str
    recent_event_count_24h: Optional[int] = 0
    recent_failed_count_7d: Optional[int] = 0
    route_notional_7d_usd: Optional[float] = 0.0
    counterparty_notional_30d_usd: Optional[float] = 0.0


class RiskScoreResponse(BaseModel):
    risk_score: float = Field(ge=0.0, le=1.0)
    anomaly_score: float = Field(ge=0.0, le=1.0)
    risk_band: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    top_features: list[str]
    reason_codes: list[str]
    trace_id: str
    version: str = "pink-01"
