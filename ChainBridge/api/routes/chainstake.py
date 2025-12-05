"""ChainStake v1 skeleton endpoints."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.chainstake_analytics import (
    get_liquidity_overview,
    list_pool_positions,
    list_stake_pools,
)
from api.chainstake_service import create_stake_job, execute_stake_job
from api.database import get_db
from api.models.chainpay import StakeJob
from api.schemas.chainstake import (
    LiquidityOverview,
    StakePoolSummary,
    StakePositionRead,
)

router = APIRouter(prefix="/stake", tags=["stake"])


class StakeJobCreate(BaseModel):
    requested_amount: float
    payment_intent_id: Optional[str] = None
    auto_execute: bool = True


class StakeJobRead(BaseModel):
    id: str
    shipment_id: str
    payment_intent_id: Optional[str]
    status: str
    requested_amount: float
    settled_amount: Optional[float]
    failure_reason: Optional[str]

    class Config:
        from_attributes = True


def _serialize(job: StakeJob) -> StakeJobRead:
    return StakeJobRead.model_validate(job)


@router.post("/shipments/{shipment_id}", response_model=StakeJobRead)
def create_stake(shipment_id: str, payload: StakeJobCreate, db: Session = Depends(get_db)) -> StakeJobRead:
    try:
        job = create_stake_job(
            db,
            shipment_id=shipment_id,
            requested_amount=payload.requested_amount,
            payment_intent_id=payload.payment_intent_id,
        )
        if payload.auto_execute:
            job = execute_stake_job(db, job)
        return _serialize(job)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/jobs", response_model=List[StakeJobRead])
def list_stake_jobs(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    shipment_id: Optional[str] = Query(None),
    payment_intent_id: Optional[str] = Query(None),
) -> List[StakeJobRead]:
    query = db.query(StakeJob)
    if status:
        query = query.filter(StakeJob.status == status)
    if shipment_id:
        query = query.filter(StakeJob.shipment_id == shipment_id)
    if payment_intent_id:
        query = query.filter(StakeJob.payment_intent_id == payment_intent_id)
    jobs = query.order_by(StakeJob.created_at.desc()).all()
    return [_serialize(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=StakeJobRead)
def get_stake_job(job_id: str, db: Session = Depends(get_db)) -> StakeJobRead:
    job = db.query(StakeJob).filter(StakeJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="stake job not found")
    return _serialize(job)


@router.get("/overview", response_model=LiquidityOverview)
def liquidity_overview(db: Session = Depends(get_db)) -> LiquidityOverview:
    return get_liquidity_overview(db)


@router.get("/pools", response_model=List[StakePoolSummary])
def stake_pools(db: Session = Depends(get_db)) -> List[StakePoolSummary]:
    return list_stake_pools(db)


@router.get("/pools/{pool_id}/positions", response_model=List[StakePositionRead])
def pool_positions(pool_id: str, db: Session = Depends(get_db)) -> List[StakePositionRead]:
    positions = list_pool_positions(db, pool_id)
    return positions
