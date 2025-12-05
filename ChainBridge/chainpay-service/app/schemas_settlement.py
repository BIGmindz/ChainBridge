"""Pydantic models for the ChainPay settlement API surface."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RiskBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OnchainStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class SettlementStatus(str, Enum):
    PENDING = "PENDING"
    RELEASED = "RELEASED"
    ONCHAIN_CONFIRMED = "ONCHAIN_CONFIRMED"
    FAILED = "FAILED"


class SettleOnchainRequest(BaseModel):
    settlement_id: str = Field(..., min_length=4, max_length=128)
    carrier_wallet: str = Field(..., min_length=4, max_length=128)
    amount: float = Field(..., gt=0)
    asset: str = Field(..., min_length=2, max_length=32)
    risk_band: RiskBand
    trace_id: str = Field(..., min_length=3, max_length=128)
    memo: Optional[str] = Field(None, max_length=280)


class SettleOnchainResponse(BaseModel):
    settlement_id: str
    tx_hash: str
    xrpl_timestamp: str
    status: OnchainStatus


class SettlementDetailResponse(BaseModel):
    settlement_id: str
    status: SettlementStatus
    amount: float
    asset: str
    carrier_wallet: Optional[str]
    risk_band: Optional[RiskBand]
    risk_trace_id: Optional[str]
    memo: Optional[str]
    tx_hash: Optional[str]
    xrpl_timestamp: Optional[str]
    onchain_status: Optional[OnchainStatus]
    ack_count: int = 0


class SettlementAckRequest(BaseModel):
    trace_id: Optional[str] = Field(None, min_length=3, max_length=128)
    consumer_id: Optional[str] = Field(None, min_length=3, max_length=128)
    notes: Optional[str] = Field(None, max_length=280)


class SettlementAckResponse(BaseModel):
    ok: bool
    settlement_id: str
    ack_count: int


__all__ = [
    "RiskBand",
    "OnchainStatus",
    "SettlementStatus",
    "SettleOnchainRequest",
    "SettleOnchainResponse",
    "SettlementDetailResponse",
    "SettlementAckRequest",
    "SettlementAckResponse",
]
