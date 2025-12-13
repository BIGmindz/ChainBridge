"""Shared governance data models for GID Kernel components."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class SettlementContext(BaseModel):
    shipment_id: str
    payer: str
    payee: str
    amount: Decimal
    currency: str
    corridor: str
    economic_justification: Optional[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("amount")
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Settlement amount must be positive")
        return value


class VerificationResult(BaseModel):
    field: str
    verified: bool
    source: Optional[str] = None
    details: Optional[str] = None


class GovernanceDecision(BaseModel):
    status: str
    reason_codes: List[str]
    # Risk score in 0–100 scale (aligns with legacy risk engines and tests)
    risk_score: float = Field(ge=0.0, le=100.0)
    policies_applied: List[str]
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class AgentMeta:
    agent_id: str
    gid: str
    role_tier: int
    gid_hgp_version: str
