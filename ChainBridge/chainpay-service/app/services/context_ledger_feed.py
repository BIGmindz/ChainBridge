"""Serialization helpers for the context ledger risk feed."""

from __future__ import annotations

import json
from typing import List, Sequence

from app.models_context_ledger import ContextLedgerEntry
from app.schemas_context_ledger_feed import (
    ContextLedgerRiskEvent,
    ContextLedgerRiskFeed,
    LedgerRiskSnapshot,
)


def _load_json(value: str | None) -> List[str] | dict | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _ensure_str_list(payload: List[str] | dict | None) -> List[str]:
    if isinstance(payload, list):
        return [str(item) for item in payload]
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
    raw_snapshot = metadata.get("risk_snapshot") or metadata.get("risk") or metadata.get("context_risk")
    if not isinstance(raw_snapshot, dict):
        return None
    if raw_snapshot.get("auto_generated"):
        return None
    reason_codes = raw_snapshot.get("reason_codes")
    snapshot = LedgerRiskSnapshot(
        risk_score=float(raw_snapshot.get("risk_score")) if raw_snapshot.get("risk_score") is not None else None,
        risk_band=raw_snapshot.get("risk_band"),
        reason_codes=list(reason_codes) if isinstance(reason_codes, list) else [],
        trace_id=raw_snapshot.get("trace_id"),
        model_version=raw_snapshot.get("model_version"),
    )
    return snapshot


def serialize_entry(entry: ContextLedgerEntry) -> ContextLedgerRiskEvent:
    metadata = _load_json(entry.metadata_json)
    risk_snapshot = _extract_risk_snapshot(metadata)
    reason_codes = _ensure_str_list(_load_json(entry.reason_codes))
    policies = _ensure_str_list(_load_json(entry.policies_applied))
    risk_band = risk_snapshot.risk_band if risk_snapshot and risk_snapshot.risk_band else _derive_band(float(entry.risk_score))

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
        risk=risk_snapshot,
    )


def serialize_feed(entries: Sequence[ContextLedgerEntry]) -> ContextLedgerRiskFeed:
    return ContextLedgerRiskFeed(items=[serialize_entry(entry) for entry in entries])


__all__ = [
    "serialize_entry",
    "serialize_feed",
]
