"""Canonical API entrypoints for event ingestion."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from chainbridge.events.schemas import RoutingResult
from chainbridge.runtime.event_pipeline import process_event, process_events


async def ingest_event(event: Dict[str, Any]) -> RoutingResult:
    """Public entrypoint used by FastAPI routes and background workers."""

    return await process_event(event)


async def ingest_events(events: Iterable[Dict[str, Any]]) -> List[RoutingResult]:
    return await process_events(events)


__all__ = ["ingest_event", "ingest_events"]
