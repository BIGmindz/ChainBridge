"""Schemas for the context ledger risk feed endpoint."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LedgerRiskSnapshot(BaseModel):
    risk_score: Optional[float] = Field(None, ge=0.0)
    risk_band: Optional[str] = None
    reason_codes: List[str] = Field(default_factory=list)
    trace_id: Optional[str] = None
    model_version: Optional[str] = None

    class Config:
        orm_mode = True


class ContextLedgerRiskEvent(BaseModel):
    id: str
    shipment_id: Optional[str]
    payer_id: Optional[str]
    payee_id: Optional[str]
    amount: float
    currency: str
    corridor: Optional[str]
    decision_type: str
    decision_status: str
    occurred_at: datetime
    agent_id: str
    gid: str
    role_tier: int
    risk_score: float
    risk_band: str
    reason_codes: List[str] = Field(default_factory=list)
    policies_applied: List[str] = Field(default_factory=list)
    risk: Optional[LedgerRiskSnapshot] = None

    class Config:
        orm_mode = True


class ContextLedgerRiskFeed(BaseModel):
    items: List[ContextLedgerRiskEvent]

    class Config:
        orm_mode = True


__all__ = [
    "ContextLedgerRiskEvent",
    "ContextLedgerRiskFeed",
    "LedgerRiskSnapshot",
]
