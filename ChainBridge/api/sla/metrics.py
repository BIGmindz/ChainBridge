"""Simple in-memory SLA metrics."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from api.events.bus import EventType, event_bus

_METRICS: Dict[str, datetime] = {}


def update_metric(name: str, when: datetime | None = None) -> None:
    ts = when or datetime.now(timezone.utc)
    _METRICS[name] = ts
    if name == "worker_heartbeat":
        event_bus.publish(
            EventType.WORKER_HEARTBEAT,
            {"metric": name},
            occurred_at=ts,
            actor="worker",
        )


def get_metric(name: str) -> datetime | None:
    return _METRICS.get(name)


def get_sla_snapshot(now: datetime | None = None, window_seconds: int | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    def latency(name: str, threshold: int) -> tuple[float, bool]:
        ts = _METRICS.get(name)
        if not ts:
            return float("inf"), False
        delta = (now - ts).total_seconds()
        if window_seconds is not None and delta > window_seconds:
            return float("inf"), False
        return delta, delta < threshold

    op_latency, op_fresh = latency("operator_queue", 120)
    cash_latency, cash_fresh = latency("payment_intents", 120)
    hooks_latency, hooks_fresh = latency("webhooks", 300)
    worker_latency, worker_fresh = latency("worker_heartbeat", 120)
    hcs_latency, hcs_fresh = latency("hedera_consensus", 300)

    components = {
        "operator_queue": {"fresh": op_fresh, "latency_s": op_latency},
        "cash_view": {"fresh": cash_fresh, "latency_s": cash_latency},
        "webhooks": {"fresh": hooks_fresh, "latency_s": hooks_latency},
        "workers": {"fresh": worker_fresh, "latency_s": worker_latency},
        "hedera_consensus": {"fresh": hcs_fresh, "latency_s": hcs_latency},
    }
    if all(c["fresh"] for c in components.values()):
        status = "HEALTHY"
    elif any(c["latency_s"] > 1200 for c in components.values()):
        status = "CRITICAL"
    else:
        status = "DEGRADED"
    return {"status": status, "components": components}
