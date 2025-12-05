"""Canonical event pipeline entrypoint for ChainBridge."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List

from chainbridge.events.schemas import RoutingDecision, RoutingResult
from chainbridge.runtime.dispatcher import DispatchError
from chainbridge.runtime import startup

logger = logging.getLogger(__name__)


async def process_event(event: Dict[str, Any]) -> RoutingResult:
    """Normalise, route, and observe metrics for a single event payload."""

    context = await startup.ensure_runtime()

    try:
        normalized_event = context.dispatcher.normalize(event)
    except DispatchError as exc:
        event_id = str(event.get("event_id", "DISPATCH-REJECTED"))
        context.metrics.record_failure(
            reason="dispatch_validation",
            event_type=str(event.get("event_type", "unknown")),
        )
        logger.warning("Rejected event %s during normalization: %s", event_id, exc)
        return RoutingResult(
            event_id=event_id,
            decision=RoutingDecision.REJECTED,
            processing_time_ms=0,
            error_message=str(exc),
        )

    result = await context.router.submit(normalized_event)
    _record_metrics(context, str(normalized_event.event_type.value), result)
    context.metrics.set_dlq_size(context.router.orchestrator.get_metrics().dlq_count)
    return result


async def process_events(events: Iterable[Dict[str, Any]]) -> List[RoutingResult]:
    """Process a batch sequentially (helper for bulk ingestion)."""

    results: List[RoutingResult] = []
    for payload in events:
        results.append(await process_event(payload))
    return results


def _record_metrics(context, event_type: str, result: RoutingResult) -> None:
    if result.decision == RoutingDecision.PROCESSED:
        context.metrics.record_processed(
            event_type=event_type,
            latency_ms=result.processing_time_ms,
            oc_emitted=result.oc_events_emitted,
            settlement=result.settlement_triggers,
            proof_requested=result.proof_requests_emitted,
        )
    else:
        governance_freeze = result.decision == RoutingDecision.REJECTED and (result.error_message or "").lower().find("governance") >= 0
        context.metrics.record_failure(
            reason=result.decision.value.lower(),
            event_type=event_type,
            governance_freeze=governance_freeze,
        )
        if result.decision == RoutingDecision.REJECTED and "proof" in (result.error_message or "").lower():
            context.metrics.record_proof_failure()


__all__ = ["process_event", "process_events"]
