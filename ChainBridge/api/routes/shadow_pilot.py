"""Shadow Pilot ingestion and retrieval endpoints."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.database import SessionLocal, get_db
from api.jobs.shadow_pilot_jobs import run_shadow_pilot_job
from api.models.shadow_pilot import ShadowPilotRun, ShadowPilotShipment
from api.schemas.shadow_pilot import ShadowPilotShipmentsPageResponse, ShadowPilotSummaryResponse
from api.security import get_current_admin_user
from core.path_security import PathTraversalError, safe_filename, safe_join

router = APIRouter(prefix="/shadow-pilot", tags=["shadow-pilot"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB default guardrail


def _settings() -> dict:
    return {
        "data_dir": Path(os.getenv("SHADOW_PILOT_DATA_DIR", "data/shadow_pilot")),
        "annual_rate": float(os.getenv("SHADOW_PILOT_ANNUAL_RATE_DEFAULT", "0.06")),
        "advance_rate": float(os.getenv("SHADOW_PILOT_ADVANCE_RATE_DEFAULT", "0.7")),
        "take_rate": float(os.getenv("SHADOW_PILOT_TAKE_RATE_DEFAULT", "0.01")),
        "min_value": float(os.getenv("SHADOW_PILOT_MIN_VALUE", "50000")),
        "min_truth": float(os.getenv("SHADOW_PILOT_MIN_TRUTH", "0.7")),
    }


async def _save_upload(file: UploadFile, destination: Path) -> None:
    size = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 512)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="upload too large")
            out.write(chunk)
    await file.close()


async def _enqueue_or_run_inline(run_id: str, csv_path: Path, config: dict) -> str:
    try:
        from arq import create_pool  # type: ignore
        from arq.connections import RedisSettings  # type: ignore
    except Exception:
        await run_shadow_pilot_job({"SessionLocal": SessionLocal}, run_id, str(csv_path), config)
        return "processed-inline"

    try:
        redis = await create_pool(RedisSettings())
        job = await redis.enqueue_job("run_shadow_pilot_job", run_id, str(csv_path), config)
        return str(job)
    except Exception:  # pragma: no cover - ARQ optional
        await run_shadow_pilot_job({"SessionLocal": SessionLocal}, run_id, str(csv_path), config)
        return "processed-inline"


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_shadow_pilot(
    prospect_name: str = Form(...),
    period_months: int = Form(...),
    run_id: Optional[str] = Form(None),
    input_filename: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_admin_user),
) -> dict:
    settings = _settings()
    resolved_run_id = run_id or f"shadow_{uuid4().hex}"
    existing = db.query(ShadowPilotRun).filter(ShadowPilotRun.run_id == resolved_run_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="run_id already exists")

    raw_name = input_filename or (file.filename or "shipments.csv")
    try:
        safe_name = safe_filename(raw_name)
    except PathTraversalError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")

    try:
        destination = safe_join(settings["data_dir"], f"{resolved_run_id}_{safe_name}")
    except PathTraversalError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    await _save_upload(file, destination)

    run = ShadowPilotRun(
        run_id=resolved_run_id,
        prospect_name=prospect_name,
        period_months=period_months,
        input_filename=safe_name,
        notes=notes,
    )
    db.add(run)
    db.commit()

    job_config = {
        "prospect_name": prospect_name,
        "period_months": period_months,
        "input_filename": safe_name,
        "notes": notes,
        "annual_rate": settings["annual_rate"],
        "advance_rate": settings["advance_rate"],
        "take_rate": settings["take_rate"],
        "min_value": settings["min_value"],
        "min_truth": settings["min_truth"],
    }
    job_id = await _enqueue_or_run_inline(resolved_run_id, destination, job_config)
    return {"run_id": resolved_run_id, "status": "queued", "job_id": job_id}


@router.get("/summaries", response_model=List[ShadowPilotSummaryResponse])
def list_shadow_pilot_summaries(db: Session = Depends(get_db), user=Depends(get_current_admin_user)) -> List[ShadowPilotSummaryResponse]:
    runs = db.query(ShadowPilotRun).order_by(ShadowPilotRun.created_at.desc()).all()
    return runs


@router.get("/summaries/{run_id}", response_model=ShadowPilotSummaryResponse)
def get_shadow_pilot_summary(
    run_id: str, db: Session = Depends(get_db), user=Depends(get_current_admin_user)
) -> ShadowPilotSummaryResponse:
    run = db.query(ShadowPilotRun).filter(ShadowPilotRun.run_id == run_id).first()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return run


@router.get("/runs/{run_id}/shipments", response_model=ShadowPilotShipmentsPageResponse)
def list_shadow_pilot_shipments(
    run_id: str,
    cursor: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    user=Depends(get_current_admin_user),
) -> ShadowPilotShipmentsPageResponse:
    if limit <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit must be positive")

    run = db.query(ShadowPilotRun).filter(ShadowPilotRun.run_id == run_id).first()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    query = db.query(ShadowPilotShipment).filter(ShadowPilotShipment.run_id == run_id).order_by(ShadowPilotShipment.id)
    if cursor:
        try:
            cursor_id = int(cursor)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid cursor")
        query = query.filter(ShadowPilotShipment.id > cursor_id)

    items = query.limit(limit + 1).all()
    has_next = len(items) > limit
    trimmed = items[:limit]
    next_cursor = str(trimmed[-1].id) if has_next else None

    return ShadowPilotShipmentsPageResponse(items=trimmed, next_cursor=next_cursor)
