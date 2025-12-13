from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import AuthenticatedUser, get_current_user
from app.database import get_db
from app.schemas_analytics import ChainPayAnalyticsSnapshot
from app.services.analytics_service import DEFAULT_POLICY, USD_MXN_CORRIDOR_ID, compute_chainpay_analytics_snapshot

router = APIRouter(prefix="/api/chainpay", tags=["chainpay-analytics"])


@router.get("/analytics/usd-mxn", response_model=ChainPayAnalyticsSnapshot)
def get_usd_mxn_analytics(
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ChainPayAnalyticsSnapshot:
    """Return ChainPay analytics snapshot for the USD→MXN pilot corridor.

    Requires authentication.
    """
    snapshot = compute_chainpay_analytics_snapshot(
        db,
        corridor_id=USD_MXN_CORRIDOR_ID,
        payout_policy_version=DEFAULT_POLICY,
    )
    return snapshot
