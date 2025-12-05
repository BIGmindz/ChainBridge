# api/realtime/bus.py
"""
ChainBoard Event Bus
====================

In-process pub/sub event bus for real-time updates.
Uses asyncio.Queue for simple, efficient event distribution to SSE clients.
"""

import asyncio
from datetime import datetime
from typing import AsyncIterator, Set
from uuid import uuid4

from api.schemas.chainboard import ControlTowerEvent, ControlTowerEventType

# ============================================================================
# GLOBAL STATE
# ============================================================================

_SUBSCRIBERS: Set[asyncio.Queue[ControlTowerEvent]] = set()
_LOCK = asyncio.Lock()


# ============================================================================
# PUBLIC API
# ============================================================================


def subscribe() -> asyncio.Queue[ControlTowerEvent]:
    """
    Subscribe to the event bus.

    Returns:
        Queue that will receive all published events
    """
    queue: asyncio.Queue[ControlTowerEvent] = asyncio.Queue()
    # Note: For thread safety in production, use asyncio.Lock.
    # For MVP demo with single event loop, direct set access is fine.
    _SUBSCRIBERS.add(queue)
    return queue


def unsubscribe(queue: asyncio.Queue[ControlTowerEvent]) -> None:
    """
    Unsubscribe from the event bus.

    Args:
        queue: Queue returned from subscribe()
    """
    _SUBSCRIBERS.discard(queue)


async def publish_event(
    *,
    type: ControlTowerEventType,
    source: str,
    key: str,
    payload: dict,
) -> None:
    """
    Publish an event to all subscribers.

    Args:
        type: Event type enum
        source: Subsystem name (e.g. "alerts", "iot", "payments")
        key: Primary entity identifier
        payload: Event-specific data
    """
    event = ControlTowerEvent(
        id=f"evt-{uuid4()}",
        type=type,
        timestamp=datetime.utcnow(),
        source=source,
        key=key,
        payload=payload,
    )

    # Get snapshot of subscribers outside the lock
    async with _LOCK:
        subscribers = list(_SUBSCRIBERS)

    # Distribute to all subscribers (non-blocking)
    for q in subscribers:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            # Drop event if subscriber is too slow
            # Acceptable for demo/MVP - prevents one slow client from blocking others
            pass


async def event_stream() -> AsyncIterator[ControlTowerEvent]:
    """
    Async generator that yields events from the bus.

    Automatically subscribes on start and unsubscribes on cleanup.
    Use in SSE endpoint or testing.

    Yields:
        ControlTowerEvent instances as they are published
    """
    queue = subscribe()
    try:
        while True:
            event = await queue.get()
            yield event
    finally:
        unsubscribe(queue)
