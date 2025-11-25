"""Finance routes for quotes and inventory stakes.

Contracts (FINANCE-R01 canonical):
- POST /finance/quote:
  * 404 if no RicardianInstrument for physical_reference
  * 400 if instrument exists but status != ACTIVE
  * Risk bands: LOW→80%/12% APR, MED→70%/15%, HIGH→50%/20%
  * Returns numeric fields (notional_value, rates, amounts, APRs) and instrument_id
- GET /finance/stakes/by-physical/{ref} returns list (empty allowed), with stake status in
  {PENDING, ACTIVE, REPAID, LIQUIDATED, CANCELLED}
Any future changes must be additive or versioned.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.finance import InventoryStake
from api.models.legal import RicardianInstrument
from api.schemas.finance import (
    FinancingQuoteRequest,
    FinancingQuoteResponse,
    InventoryStakeCreate,
    InventoryStakeResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/finance", tags=["finance"])


def _latest_instrument(db: Session, physical_reference: str) -> Optional[RicardianInstrument]:
    return (
        db.query(RicardianInstrument)
        .filter(RicardianInstrument.physical_reference == physical_reference)
        .order_by(RicardianInstrument.created_at.desc())
        .first()
    )


def _risk_band_from_payload(payload: FinancingQuoteRequest) -> str:
    if payload.risk_band:
        return payload.risk_band.upper()
    return "MEDIUM"


def compute_financing_quote(db: Session, payload: FinancingQuoteRequest) -> FinancingQuoteResponse:
    instrument = _latest_instrument(db, payload.physical_reference)
    if instrument is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ricardian instrument not found")
    if instrument.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Instrument {instrument.status}")

    band = _risk_band_from_payload(payload)
    if band == "LOW":
        rate = Decimal("80")
        base_apr = Decimal("12")
    elif band == "HIGH":
        rate = Decimal("50")
        base_apr = Decimal("20")
    else:
        rate = Decimal("70")
        base_apr = Decimal("15")

    max_amount = (payload.notional_value * rate / Decimal("100")).quantize(Decimal("0.01"))
    reason_codes = ["RICARDIAN_ACTIVE", f"RISK_BAND_{band}"]

    return FinancingQuoteResponse(
        physical_reference=payload.physical_reference,
        instrument_id=str(instrument.id),
        notional_value=float(payload.notional_value),
        currency=payload.currency,
        max_advance_rate=float(rate),
        max_advance_amount=float(max_amount),
        base_apr=float(base_apr),
        risk_adjusted_apr=float(base_apr),
        reason_codes=reason_codes,
    )


@router.post("/quote", response_model=FinancingQuoteResponse)
def create_financing_quote(payload: FinancingQuoteRequest, db: Session = Depends(get_db)) -> FinancingQuoteResponse:
    quote = compute_financing_quote(db, payload)
    logger.info(
        "finance.quote.generated",
        extra={
            "physical_reference": payload.physical_reference,
            "max_advance_rate": float(quote.max_advance_rate),
            "base_apr": float(quote.base_apr),
        },
    )
    return quote


@router.post("/stakes", response_model=InventoryStakeResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_stake(payload: InventoryStakeCreate, db: Session = Depends(get_db)) -> InventoryStakeResponse:
    # ensure instrument exists and active
    instrument = _latest_instrument(db, payload.physical_reference)
    if instrument is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ricardian instrument not found")
    if instrument.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Instrument {instrument.status}")

    stake = InventoryStake(
        physical_reference=payload.physical_reference,
        ricardian_instrument_id=str(instrument.id),
        principal_amount=float(payload.principal_amount),
        currency=payload.currency,
        max_advance_rate=float(payload.applied_advance_rate),
        applied_advance_rate=float(payload.applied_advance_rate),
        base_apr=float(payload.base_apr),
        risk_adjusted_apr=float(payload.risk_adjusted_apr),
        notional_value=float(payload.notional_value),
        lender_name=payload.lender_name,
        borrower_name=payload.borrower_name,
        status="ACTIVE",
        reason_code=payload.reason_code,
        created_by=payload.created_by,
    )
    db.add(stake)
    db.commit()
    db.refresh(stake)
    logger.info("finance.stake.created", extra={"stake_id": stake.id, "physical_reference": stake.physical_reference})
    return stake


@router.get("/stakes/by-physical/{physical_reference}", response_model=List[InventoryStakeResponse])
def list_stakes_by_physical(physical_reference: str, db: Session = Depends(get_db)) -> List[InventoryStakeResponse]:
    stakes = (
        db.query(InventoryStake)
        .filter(InventoryStake.physical_reference == physical_reference)
        .order_by(InventoryStake.created_at.desc())
        .all()
    )
    return stakes
