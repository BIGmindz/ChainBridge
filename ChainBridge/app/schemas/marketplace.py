"""Pydantic schemas for ChainSalvage marketplace."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SalvageConditionReport(BaseModel):
    confidence_score: float
    final_payout: float
    reason: str


class ListingCreate(BaseModel):
    shipment_id: str
    token_id: str
    start_price: float
    buy_now_price: Optional[float] = None
    expires_at: Optional[datetime] = None
    condition: Optional[SalvageConditionReport] = None


class ListingResponse(ListingCreate):
    id: str
    status: str


class BidRequest(BaseModel):
    listing_id: str
    bidder_wallet: str = Field(..., description="Wallet placing the bid")
    amount: float

    @field_validator("bidder_wallet")
    def validate_wallet(cls, v: str) -> str:
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("invalid_wallet_address")
        return v


class DutchAuctionState(BaseModel):
    listing_id: str
    current_price: float
    next_drop_at: Optional[datetime]
    is_active: bool


class BuyNowRequest(BaseModel):
    listing_id: str
    buyer_wallet: str
    max_acceptable_price: float


class BuyIntentStatus(str, Enum):
    QUEUED = "QUEUED"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class PriceQuoteResponse(BaseModel):
    listing_id: str
    auction_state_version: str
    price: float
    currency: str = "USDC"
    quoted_at: datetime
    proof_nonce: str


class BuyIntentCreateRequest(BaseModel):
    wallet_address: str
    client_price: float
    proof_nonce: str
    listing_id: str

    @field_validator("wallet_address")
    def validate_wallet(cls, v: str) -> str:
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("invalid_wallet_address")
        return v

    @field_validator("client_price")
    def validate_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError("client_price_negative")
        return v


class BuyIntentResponse(BaseModel):
    intent_id: str
    status: BuyIntentStatus
    price: float
    currency: str
    expires_at: datetime
