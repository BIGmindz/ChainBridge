"""Stake endpoint enqueuing async staking jobs."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.worker.tasks import enqueue_stake_request
from app.schemas.stake import StakeRequest, StakeResponse, StakeStatus
from app.core.deps import get_arq_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory/stake", tags=["chainstake"])
get_arq = get_arq_pool


@router.post("/requests", response_model=StakeResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_stake_request(payload: StakeRequest, redis: Any = Depends(get_arq_pool)) -> StakeResponse:
    if payload.amount_usd <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="amount_must_be_positive")
    if redis is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ARQ pool not configured")
    try:
        job_id = await enqueue_stake_request(redis, payload.model_dump())
    except Exception as exc:  # pragma: no cover - defensive path
        logger.warning("stake_api.enqueue_failed", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="queue_unavailable")
    logger.info("stake_api.enqueued", extra={"job_id": job_id, "shipment_id": payload.shipment_id, "pool_id": payload.pool_id})
    return StakeResponse(job_id=job_id, status=StakeStatus.QUEUED)
