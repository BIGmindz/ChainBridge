from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedUser, get_current_user, verify_shipment_access
from app.models_settlement import SettlementStatus
from app.services.settlement_service import get_mock_settlement_status

router = APIRouter(prefix="/api/chainpay", tags=["chainpay"])


@router.get("/settlements/{shipment_id}", response_model=SettlementStatus)
async def get_settlement_status(
    shipment_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> SettlementStatus:
    """Retrieve settlement status for a shipment (mock-backed).

    Requires authentication. User must have access to the shipment.
    """
    # IDOR protection: verify user can access this shipment
    verify_shipment_access(shipment_id, user)
    return get_mock_settlement_status(shipment_id)
