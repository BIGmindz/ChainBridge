"""API gateway routes for the ChainPay settlement surface."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.routes.chainpay_context_risk import get_chainpay_db
from chainpay_service.app.schemas_settlement import (
    SettleOnchainRequest,
    SettleOnchainResponse,
    SettlementAckRequest,
    SettlementAckResponse,
    SettlementDetailResponse,
)
from chainpay_service.app.services.settlement_api import (
    SettlementAPIService,
    SettlementConflictError,
    SettlementNotFoundError,
)
from chainpay_service.app.services.xrpl_stub_adapter import XRPLSettlementAdapter

router = APIRouter(prefix="/chainpay", tags=["ChainPay"])
_adapter = XRPLSettlementAdapter()


def _service(db: Session) -> SettlementAPIService:
    return SettlementAPIService(db, xrpl_adapter=_adapter)


@router.post("/settle-onchain", response_model=SettleOnchainResponse)
def submit_settlement(
    payload: SettleOnchainRequest,
    db: Session = Depends(get_chainpay_db),
) -> SettleOnchainResponse:
    service = _service(db)
    try:
        return service.trigger_onchain_settlement(payload)
    except SettlementNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(exc)})
    except SettlementConflictError as exc:
        raise HTTPException(status_code=409, detail={"error": "VALIDATION_ERROR", "message": str(exc)})


@router.get("/settlements/{settlement_id}", response_model=SettlementDetailResponse)
def read_settlement(
    settlement_id: str,
    db: Session = Depends(get_chainpay_db),
) -> SettlementDetailResponse:
    service = _service(db)
    try:
        return service.get_settlement_detail(settlement_id)
    except SettlementNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(exc)})


@router.post("/settlements/{settlement_id}/ack", response_model=SettlementAckResponse)
def ack_settlement(
    settlement_id: str,
    payload: SettlementAckRequest,
    db: Session = Depends(get_chainpay_db),
) -> SettlementAckResponse:
    service = _service(db)
    try:
        return service.record_acknowledgement(settlement_id, payload)
    except SettlementNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(exc)})


__all__ = ["router"]
