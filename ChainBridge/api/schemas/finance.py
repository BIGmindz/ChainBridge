"""Pydantic schemas for financing and inventory stakes."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class FinancingQuoteRequest(BaseModel):
    physical_reference: str
    notional_value: Decimal
    currency: str = "USD"
    risk_band: Optional[str] = None


class FinancingQuoteResponse(BaseModel):
    physical_reference: str
    instrument_id: str
    notional_value: float
    currency: str
    max_advance_rate: float
    max_advance_amount: float
    base_apr: float
    risk_adjusted_apr: float
    reason_codes: List[str] = []
    """Reason codes document why the quote is financeable; keep stable for FE."""


class InventoryStakeStatus(str):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REPAID = "REPAID"
    LIQUIDATED = "LIQUIDATED"
    CANCELLED = "CANCELLED"


class InventoryStakeCreate(BaseModel):
    physical_reference: str
    notional_value: Decimal
    principal_amount: Decimal
    currency: str = "USD"
    applied_advance_rate: Decimal
    base_apr: Decimal
    risk_adjusted_apr: Decimal
    created_by: str
    lender_name: Optional[str] = None
    borrower_name: Optional[str] = None
    reason_code: Optional[str] = None


class InventoryStakeResponse(BaseModel):
    id: str
    physical_reference: str
    ricardian_instrument_id: Optional[str] = None
    principal_amount: float
    currency: str
    max_advance_rate: float
    applied_advance_rate: float
    base_apr: float
    risk_adjusted_apr: float
    notional_value: float
    lender_name: Optional[str] = None
    borrower_name: Optional[str] = None
    status: str
    reason_code: Optional[str] = None
    created_by: str
    created_at: datetime

    class Config:
        orm_mode = True
