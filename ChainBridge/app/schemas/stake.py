"""Stake request/response schemas."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class StakeStatus(str, Enum):
    QUEUED = "QUEUED"
    MINTING = "MINTING"
    STAKING = "STAKING"
    LIQUIDITY_SENT = "LIQUIDITY_SENT"
    FAILED = "FAILED"


class StakeRequest(BaseModel):
    shipment_id: str
    payment_intent_id: Optional[str] = None
    wallet_address: str = Field(..., description="Destination wallet for staking proceeds")
    amount_usd: float
    pool_id: str = Field(..., description="Target staking pool identifier")

    @field_validator("wallet_address")
    def validate_wallet(cls, v: str) -> str:
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("invalid_wallet_address")
        return v


class StakeResponse(BaseModel):
    job_id: str
    status: StakeStatus = StakeStatus.QUEUED
