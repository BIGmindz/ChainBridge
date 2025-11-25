"""Audit endpoints for fuzzy evaluation."""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas.audit import AuditVector, ReconciliationResult
from app.services.pricing.adjuster import calculate_final_settlement

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/evaluate", response_model=ReconciliationResult)
async def evaluate(payload: AuditVector) -> ReconciliationResult:
    settlement = calculate_final_settlement(
        payload.invoice_amount,
        {"delta_temp_c": payload.delta_temp_c, "duration_mins": payload.duration_mins},
    )
    return ReconciliationResult(**settlement)
