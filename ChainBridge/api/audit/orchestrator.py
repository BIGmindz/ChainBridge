"""Audit orchestrator v0 using in-process event bus."""
from __future__ import annotations

from typing import Iterable

from api.events.bus import EventType, event_bus

HIGH_RISK_BANDS = {"HIGH", "CRITICAL"}
HIGH_AMOUNT_THRESHOLD = 50_000
CROSS_BORDER_CORRIDORS = {"US-MX", "US-CN", "EU-UK"}


def bootstrap_audit_orchestrator() -> None:
    event_bus.subscribe(EventType.SETTLEMENT_EVENT_APPENDED, _on_settlement_event)
    event_bus.subscribe(EventType.PAYMENT_INTENT_UPDATED, _on_intent_updated)


def _on_settlement_event(payload: dict) -> None:
    settlement_id = payload.get("payment_intent_id")
    event_type = payload.get("event_type")
    risk_band = payload.get("risk_band")
    if not settlement_id:
        return
    rules = []
    if event_type in {"CAPTURED", "CASH_RELEASED"} and risk_band in HIGH_RISK_BANDS:
        rules.append("high_risk_on_paid")
    if rules:
        _emit_audit_recommended(settlement_id, rules)


def _on_intent_updated(payload: dict) -> None:
    settlement_id = payload.get("id")
    risk_band = payload.get("risk_band") or payload.get("risk_level")
    corridor = payload.get("corridor")
    amount = payload.get("amount")
    status = payload.get("status")
    rules = []
    if status == "PAID" and is_high_risk_band(risk_band):
        rules.append("high_risk_on_paid")
    if status == "PAID" and corridor in CROSS_BORDER_CORRIDORS and (amount or 0) >= HIGH_AMOUNT_THRESHOLD:
        rules.append("high_value_cross_border_on_paid")
    if is_high_risk_band(risk_band):
        rules.append("risk_spike_high_or_critical")
    if settlement_id and rules:
        _emit_audit_recommended(settlement_id, rules)


def is_high_risk_band(band: str | None) -> bool:
    return band in HIGH_RISK_BANDS if band else False


def _emit_audit_recommended(settlement_id: str, rules: Iterable[str]) -> None:
    event_bus.publish(
        EventType.PAYMENT_INTENT_UPDATED,
        {
            "id": settlement_id,
            "kind": "audit_recommended",
            "severity": "warning",
            "settlement_id": settlement_id,
            "message": "Audit recommended: " + ", ".join(rules),
            "rules": list(rules),
        },
        correlation_id=settlement_id,
        actor="audit",
    )
