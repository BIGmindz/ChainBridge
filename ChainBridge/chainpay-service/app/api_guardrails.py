from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas_guardrails import GuardrailStatusSnapshot
from app.services.guardrail_service import evaluate_guardrails_for_corridor
from app.services.analytics_service import DEFAULT_POLICY, USD_MXN_CORRIDOR_ID

router = APIRouter(prefix="/api/chainpay/guardrails", tags=["chainpay-guardrails"])


@router.get("/usd-mxn", response_model=GuardrailStatusSnapshot)
def get_guardrails_usd_mxn(db: Session = Depends(get_db)) -> GuardrailStatusSnapshot:
    """Return guardrail status snapshot for USD→MXN pilot (P0)."""
    return evaluate_guardrails_for_corridor(
        db,
        corridor_id=USD_MXN_CORRIDOR_ID,
        payout_policy_version=DEFAULT_POLICY,
    )
