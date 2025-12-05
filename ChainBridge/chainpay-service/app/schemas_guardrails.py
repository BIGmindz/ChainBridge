from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas_analytics import RiskTier

GuardrailState = str  # Allowed values: "GREEN", "AMBER", "RED"


class TierGuardrailStatus(BaseModel):
    tier: GuardrailState | RiskTier  # keep compatibility with existing tier literals
    state: GuardrailState
    loss_rate: float
    cash_sla_breach_rate: float
    d2_p95_days: float
    unused_reserve_ratio: float
    reasons: List[str] = []  # machine-readable factors driving the state
    summary: Optional[str] = None  # short human string for UI badges


class GuardrailStatusSnapshot(BaseModel):
    corridor_id: str
    payout_policy_version: Optional[str]
    settlement_provider: Optional[str]
    overall_state: GuardrailState
    per_tier: List[TierGuardrailStatus]
    last_evaluated_at: datetime
    overall_reasons: List[str] = []  # union of tier-level reasons contributing to AMBER/RED
    overall_summary: Optional[str] = None
