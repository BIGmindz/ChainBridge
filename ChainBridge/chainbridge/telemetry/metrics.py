"""Router metrics + OTEL instrumentation hooks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

try:  # pragma: no cover - optional dependency
    from opentelemetry import metrics as otel_metrics  # type: ignore
    from opentelemetry.metrics import Meter, MeterProvider  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    otel_metrics = None
    Meter = None  # type: ignore
    MeterProvider = None  # type: ignore


@dataclass(frozen=True)
class RouterMetricsSnapshot:
    events_processed_total: int
    events_failed_total: int
    events_in_dlq: int
    router_latency_ms: float
    proofs_requested: int
    proofs_failed: int
    governance_freezes: int
    settlements_triggered: int
    oc_updates_emitted: int
    last_event_timestamp: Optional[datetime]
    last_proof_request: Optional[datetime]
    last_settlement_trigger: Optional[datetime]


class RouterMetricsRecorder:
    """Aggregates in-memory counters and optionally forwards to OTEL."""

    def __init__(self) -> None:
        self._events_processed_total = 0
        self._events_failed_total = 0
        self._events_in_dlq = 0
        self._router_latency_ms = 0.0
        self._proofs_requested = 0
        self._proofs_failed = 0
        self._governance_freezes = 0
        self._settlements_triggered = 0
        self._oc_updates_emitted = 0
        self._last_event_timestamp: Optional[datetime] = None
        self._last_proof_request: Optional[datetime] = None
        self._last_settlement_trigger: Optional[datetime] = None
        self._meter: Optional[Meter] = None
        self._counters: Dict[str, object] = {}
        self._init_meter()

    # ------------------------------------------------------------------
    # Public recording helpers
    # ------------------------------------------------------------------

    def record_processed(self, *, event_type: str, latency_ms: float, oc_emitted: bool, settlement: bool, proof_requested: bool) -> None:
        self._events_processed_total += 1
        self._router_latency_ms = latency_ms
        self._last_event_timestamp = datetime.now(timezone.utc)
        if oc_emitted:
            self._oc_updates_emitted += 1
        if settlement:
            self._settlements_triggered += 1
            self._last_settlement_trigger = datetime.now(timezone.utc)
        if proof_requested:
            self._proofs_requested += 1
            self._last_proof_request = datetime.now(timezone.utc)
        self._emit_counter("events_processed_total", 1, {"event_type": event_type})
        if oc_emitted:
            self._emit_counter("oc_updates_emitted", 1, {})
        if settlement:
            self._emit_counter("settlements_triggered", 1, {})
        if proof_requested:
            self._emit_counter("proofs_requested", 1, {})

    def record_failure(self, *, reason: str, event_type: Optional[str] = None, governance_freeze: bool = False) -> None:
        self._events_failed_total += 1
        if governance_freeze:
            self._governance_freezes += 1
        self._emit_counter("events_failed_total", 1, {"reason": reason, "event_type": event_type or "unknown"})
        if governance_freeze:
            self._emit_counter("governance_freezes", 1, {"reason": reason})

    def record_proof_failure(self) -> None:
        self._proofs_failed += 1
        self._emit_counter("proofs_failed", 1, {})

    def set_dlq_size(self, size: int) -> None:
        self._events_in_dlq = size

    def snapshot(self) -> RouterMetricsSnapshot:
        return RouterMetricsSnapshot(
            events_processed_total=self._events_processed_total,
            events_failed_total=self._events_failed_total,
            events_in_dlq=self._events_in_dlq,
            router_latency_ms=self._router_latency_ms,
            proofs_requested=self._proofs_requested,
            proofs_failed=self._proofs_failed,
            governance_freezes=self._governance_freezes,
            settlements_triggered=self._settlements_triggered,
            oc_updates_emitted=self._oc_updates_emitted,
            last_event_timestamp=self._last_event_timestamp,
            last_proof_request=self._last_proof_request,
            last_settlement_trigger=self._last_settlement_trigger,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_meter(self) -> None:
        if not otel_metrics:  # pragma: no cover - optional instrumentation
            return
        provider = otel_metrics.get_meter_provider()
        if provider is None:
            provider = MeterProvider()
            otel_metrics.set_meter_provider(provider)
        self._meter = provider.get_meter("chainbridge.router")
        try:
            self._counters["events_processed_total"] = self._meter.create_counter("events_processed_total")
            self._counters["events_failed_total"] = self._meter.create_counter("events_failed_total")
            self._counters["oc_updates_emitted"] = self._meter.create_counter("oc_updates_emitted")
            self._counters["settlements_triggered"] = self._meter.create_counter("settlements_triggered")
            self._counters["proofs_requested"] = self._meter.create_counter("proofs_requested")
            self._counters["proofs_failed"] = self._meter.create_counter("proofs_failed")
            self._counters["governance_freezes"] = self._meter.create_counter("governance_freezes")
        except Exception:  # pragma: no cover - OTEL implementations vary
            self._meter = None
            self._counters.clear()

    def _emit_counter(self, name: str, value: int, attributes: Dict[str, object]) -> None:
        counter = self._counters.get(name)
        if counter is None:  # pragma: no cover - optional instrumentation
            return
        try:
            counter.add(value, attributes=attributes)
        except Exception:
            # Defensive: avoid raising if OTEL exporter misbehaves
            pass


__all__ = ["RouterMetricsRecorder", "RouterMetricsSnapshot"]
