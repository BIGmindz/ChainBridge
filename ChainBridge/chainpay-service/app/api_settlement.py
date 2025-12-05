from __future__ import annotations

from fastapi import APIRouter

from app.models_settlement import SettlementStatus
from app.services.settlement_service import get_mock_settlement_status

router = APIRouter(prefix="/api/chainpay", tags=["chainpay"])


@router.get("/settlements/{shipment_id}", response_model=SettlementStatus)
async def get_settlement_status(shipment_id: str) -> SettlementStatus:
    """Retrieve settlement status for a shipment (mock-backed)."""
    return get_mock_settlement_status(shipment_id)
