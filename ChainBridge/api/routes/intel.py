"""Intel endpoints for global snapshot KPIs."""

from __future__ import annotations

import time
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas.intel import GlobalSnapshot, LiveShipmentPosition, OCIntelFeedResponse
from api.security import get_current_admin_user
from api.services.global_intel import compute_global_intel_from_positions
from api.services.intel_feed import build_oc_feed
from api.services.live_positions import intel_positions

router = APIRouter(prefix="/intel", tags=["intel"])
logger = logging.getLogger(__name__)

_rate_limit_window_seconds = 60
_rate_limit_requests = 20
_rate_limit_buckets: dict[str, list[float]] = {}


def enforce_rate_limit(request: Request):
    client = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - _rate_limit_window_seconds
    bucket = [ts for ts in _rate_limit_buckets.get(client, []) if ts >= window_start]
    if len(bucket) >= _rate_limit_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMIT",
                "message": "Intel API rate limit exceeded (20 rpm per client)",
            },
        )
    bucket.append(now)
    _rate_limit_buckets[client] = bucket


@router.get("/global-snapshot", response_model=GlobalSnapshot)
async def get_global_snapshot(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_admin_user),
    _: None = Depends(enforce_rate_limit),
) -> GlobalSnapshot:
    try:
        positions = [LiveShipmentPosition.model_validate(p) for p in intel_positions(db)]
        snapshot = compute_global_intel_from_positions(positions)
        return snapshot.model_dump(by_alias=True)
    except Exception as exc:
        logger.exception(
            "intel_global_snapshot_failed",
            extra={"endpoint": "/intel/global-snapshot"},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "INTEL_SNAPSHOT_ERROR",
                "message": "Unable to compute global snapshot at this time.",
            },
        ) from exc


@router.get("/live-positions", response_model=List[LiveShipmentPosition])
async def get_live_positions(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_admin_user),
    _: None = Depends(enforce_rate_limit),
) -> List[LiveShipmentPosition]:
    try:
        positions = intel_positions(db)
        validated = [LiveShipmentPosition.model_validate(p) for p in positions]
        return [p.model_dump(by_alias=True) for p in validated]
    except Exception as exc:
        logger.exception(
            "intel_live_positions_failed",
            extra={"endpoint": "/intel/live-positions"},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "INTEL_LIVE_POSITIONS_ERROR",
                "message": "Unable to load intel live positions. Please retry shortly.",
            },
        ) from exc


@router.get("/oc-feed", response_model=OCIntelFeedResponse)
async def get_oc_feed(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_admin_user),
    _: None = Depends(enforce_rate_limit),
) -> OCIntelFeedResponse:
    try:
        feed = build_oc_feed(db)
        return OCIntelFeedResponse.model_validate(feed).model_dump(by_alias=True)
    except Exception as exc:
        logger.exception("intel_oc_feed_failed", extra={"endpoint": "/intel/oc-feed"})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "INTEL_FEED_ERROR",
                "message": "Unable to build OC intel feed at this time.",
            },
        ) from exc
