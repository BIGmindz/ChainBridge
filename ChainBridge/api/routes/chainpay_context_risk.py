"""API gateway routes for the ChainPay context-ledger risk feed."""

from __future__ import annotations

import json
from typing import Generator, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from chainpay_service.app.database import SessionLocal as ChainPaySessionLocal
from chainpay_service.app.models_context_ledger import ContextLedgerEntry
from chainpay_service.app.schemas_context_ledger_feed import (
    ContextLedgerRiskEvent,
    ContextLedgerRiskFeed,
    LedgerRiskSnapshot,
)

router = APIRouter(prefix="/chainpay/context-ledger", tags=["ChainPay"])


def get_chainpay_db() -> Generator[Session, None, None]:
    db = ChainPaySessionLocal()
    try:
        yield db
    finally:
        db.close()


def _load_json(value: str | None) -> dict | list | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _ensure_list(value: list | None) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _derive_band(score: float) -> str:
    if score >= 90:
        return "CRITICAL"
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def _extract_risk_snapshot(metadata: dict | None) -> LedgerRiskSnapshot | None:
    if not isinstance(metadata, dict):
        return None
    raw = metadata.get("risk_snapshot") or metadata.get("risk") or metadata.get("context_risk")
    if not isinstance(raw, dict):
        return None
    reason_codes = raw.get("reason_codes")
    return LedgerRiskSnapshot(
        risk_score=float(raw.get("risk_score")) if raw.get("risk_score") is not None else None,
        risk_band=raw.get("risk_band"),
        reason_codes=list(reason_codes) if isinstance(reason_codes, list) else [],
        trace_id=raw.get("trace_id"),
        model_version=raw.get("model_version"),
    )


def _serialize_entry(entry: ContextLedgerEntry) -> ContextLedgerRiskEvent:
    metadata = _load_json(entry.metadata_json)
    reason_codes = _ensure_list(_load_json(entry.reason_codes))
    policies = _ensure_list(_load_json(entry.policies_applied))
    snapshot = _extract_risk_snapshot(metadata if isinstance(metadata, dict) else None)
    risk_band = snapshot.risk_band if snapshot and snapshot.risk_band else _derive_band(float(entry.risk_score))

    return ContextLedgerRiskEvent(
        id=str(entry.id),
        shipment_id=entry.shipment_id,
        payer_id=entry.payer_id,
        payee_id=entry.payee_id,
        amount=float(entry.amount),
        currency=entry.currency,
        corridor=entry.corridor,
        decision_type=entry.decision_type,
        decision_status=entry.decision_status,
        occurred_at=entry.created_at,
        agent_id=entry.agent_id,
        gid=entry.gid,
        role_tier=entry.role_tier,
        risk_score=float(entry.risk_score),
        risk_band=risk_band,
        reason_codes=reason_codes,
        policies_applied=policies,
        risk=snapshot,
    )


@router.get(
    "/risk",
    response_model=ContextLedgerRiskFeed,
    summary="Recent context-ledger events with risk snapshots",
)
def get_chainpay_context_risk_feed(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_chainpay_db),
) -> ContextLedgerRiskFeed:
    safe_limit = max(1, min(limit, 200))
    entries = (
        db.query(ContextLedgerEntry)
        .order_by(ContextLedgerEntry.created_at.desc(), ContextLedgerEntry.id.desc())
        .limit(safe_limit)
        .all()
    )
    items = [_serialize_entry(entry) for entry in entries]
    return ContextLedgerRiskFeed(items=items)


__all__ = ["router", "get_chainpay_db"]
