"""
ChainBridge Event Orchestrator

Async event processing engine with FIFO ordering, deduplication, and retry mechanisms.
Central hub for deterministic event processing across ChainBridge.

Version: 1.0.0
Owner: GID-01 Cody (Senior Backend Engineer)
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, List, Optional

from .schemas import (
    BaseEvent,
    EventPriority,
    RoutingDecision,
    RoutingResult,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ORCHESTRATOR CONFIGURATION
# =============================================================================


@dataclass
class OrchestratorConfig:
    """Configuration for the event orchestrator."""

    # Queue settings
    max_queue_size: int = 10000
    batch_size: int = 100
    batch_timeout_ms: float = 50.0

    # Performance targets
    target_latency_ms: float = 50.0
    max_events_per_second: int = 5000

    # Retry settings
    max_retries: int = 3
    retry_delay_ms: float = 100.0
    retry_backoff_multiplier: float = 2.0

    # Deduplication
    dedup_window_seconds: int = 300  # 5 minutes
    dedup_cache_size: int = 50000

    # Dead letter queue
    dlq_enabled: bool = True
    dlq_max_size: int = 1000

    # Ordering
    strict_ordering: bool = True
    ordering_window_ms: float = 100.0


# =============================================================================
# EVENT QUEUE
# =============================================================================


class EventQueueStatus(str, Enum):
    """Queue status indicators."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OVERLOADED = "OVERLOADED"
    STOPPED = "STOPPED"


@dataclass
class QueueMetrics:
    """Real-time queue metrics."""

    queue_depth: int = 0
    events_processed: int = 0
    events_per_second: float = 0.0
    avg_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    dedup_hits: int = 0
    retry_count: int = 0
    dlq_count: int = 0
    status: EventQueueStatus = EventQueueStatus.HEALTHY


@dataclass
class PrioritizedEvent:
    """Event wrapper with priority ordering."""

    event: BaseEvent
    sequence_id: int
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    last_error: Optional[str] = None

    def ordering_key(self) -> tuple:
        """Generate ordering key for priority queue."""
        return (
            self.event.priority.value if isinstance(self.event.priority, EventPriority) else self.event.priority,
            self.event.timestamp,
            self.sequence_id,
        )

    def __lt__(self, other: "PrioritizedEvent") -> bool:
        return self.ordering_key() < other.ordering_key()


# =============================================================================
# DEAD LETTER QUEUE
# =============================================================================


@dataclass
class DeadLetterEntry:
    """Entry in the dead letter queue."""

    event: BaseEvent
    error: str
    failed_at: datetime
    retry_count: int
    original_sequence_id: int


class DeadLetterQueue:
    """Queue for events that failed processing."""

    def __init__(self, max_size: int = 1000):
        self._queue: List[DeadLetterEntry] = []
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def push(self, entry: DeadLetterEntry) -> None:
        """Add event to DLQ."""
        async with self._lock:
            if len(self._queue) >= self._max_size:
                # Remove oldest entry
                self._queue.pop(0)
            self._queue.append(entry)
            logger.warning(
                "Event %s added to DLQ: %s",
                entry.event.event_id,
                entry.error,
            )

    async def pop(self) -> Optional[DeadLetterEntry]:
        """Remove and return oldest DLQ entry."""
        async with self._lock:
            if self._queue:
                return self._queue.pop(0)
            return None

    async def peek(self, count: int = 10) -> List[DeadLetterEntry]:
        """View top entries without removing."""
        async with self._lock:
            return self._queue[:count]

    @property
    def size(self) -> int:
        return len(self._queue)


# =============================================================================
# DEDUPLICATION CACHE
# =============================================================================


class DeduplicationCache:
    """LRU cache for event deduplication."""

    def __init__(self, max_size: int = 50000, window_seconds: int = 300):
        self._cache: OrderedDict[str, datetime] = OrderedDict()
        self._max_size = max_size
        self._window_seconds = window_seconds
        self._lock = asyncio.Lock()
        self._hits = 0

    async def is_duplicate(self, event_id: str) -> bool:
        """Check if event is a duplicate."""
        async with self._lock:
            now = datetime.now(timezone.utc)

            # Clean expired entries
            await self._cleanup(now)

            if event_id in self._cache:
                self._hits += 1
                return True

            # Add to cache
            self._cache[event_id] = now

            # Enforce max size
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

            return False

    async def _cleanup(self, now: datetime) -> None:
        """Remove expired entries."""
        expired = []
        for event_id, timestamp in self._cache.items():
            if (now - timestamp).total_seconds() > self._window_seconds:
                expired.append(event_id)
            else:
                break  # OrderedDict is ordered by insertion time

        for event_id in expired:
            del self._cache[event_id]

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def size(self) -> int:
        return len(self._cache)


# =============================================================================
# EVENT ORCHESTRATOR
# =============================================================================


EventHandler = Callable[[BaseEvent], Coroutine[Any, Any, RoutingResult]]


class EventOrchestrator:
    """
    Async event orchestrator for ChainBridge.

    Features:
    - Priority-based FIFO ordering
    - Event deduplication
    - Batch processing for burst handling
    - Retry with exponential backoff
    - Dead letter queue for failed events
    - Real-time metrics
    """

    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        handler: Optional[EventHandler] = None,
    ):
        self._config = config or OrchestratorConfig()
        self._handler = handler

        # Queues
        self._queue: asyncio.PriorityQueue[PrioritizedEvent] = asyncio.PriorityQueue(maxsize=self._config.max_queue_size)
        self._dlq = DeadLetterQueue(max_size=self._config.dlq_max_size)
        self._dedup_cache = DeduplicationCache(
            max_size=self._config.dedup_cache_size,
            window_seconds=self._config.dedup_window_seconds,
        )

        # State
        self._sequence_counter = 0
        self._running = False
        self._processing_task: Optional[asyncio.Task] = None

        # Metrics
        self._metrics = QueueMetrics()
        self._latencies: List[float] = []
        self._processed_timestamps: List[datetime] = []

        # Locks
        self._sequence_lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # Public Interface
    # -------------------------------------------------------------------------

    def set_handler(self, handler: EventHandler) -> None:
        """Set the event handler function."""
        self._handler = handler

    async def start(self) -> None:
        """Start the orchestrator processing loop."""
        if self._running:
            logger.warning("Orchestrator already running")
            return

        self._running = True
        self._processing_task = asyncio.create_task(self._processing_loop())
        logger.info("Event orchestrator started")

    async def stop(self) -> None:
        """Stop the orchestrator gracefully."""
        self._running = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        self._metrics.status = EventQueueStatus.STOPPED
        logger.info("Event orchestrator stopped")

    async def submit(self, event: BaseEvent) -> RoutingResult:
        """
        Submit an event for processing.

        Args:
            event: The event to process.

        Returns:
            RoutingResult with processing outcome.
        """
        start_time = time.perf_counter()

        # Check for duplicate
        if await self._dedup_cache.is_duplicate(event.event_id):
            self._metrics.dedup_hits = self._dedup_cache.hits
            return RoutingResult(
                event_id=event.event_id,
                decision=RoutingDecision.DEDUPED,
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        # Assign sequence ID
        async with self._sequence_lock:
            self._sequence_counter += 1
            sequence_id = self._sequence_counter

        event.sequence_id = sequence_id
        event.ingested_at = datetime.now(timezone.utc)

        # Process immediately if handler is set and we're running synchronously
        if self._handler and not self._running:
            return await self._process_event(PrioritizedEvent(event=event, sequence_id=sequence_id))

        # Queue for async processing
        prioritized = PrioritizedEvent(event=event, sequence_id=sequence_id)

        try:
            self._queue.put_nowait(prioritized)
            self._metrics.queue_depth = self._queue.qsize()

            return RoutingResult(
                event_id=event.event_id,
                decision=RoutingDecision.QUEUED,
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        except asyncio.QueueFull:
            logger.error("Event queue full, rejecting event %s", event.event_id)
            self._metrics.status = EventQueueStatus.OVERLOADED
            return RoutingResult(
                event_id=event.event_id,
                decision=RoutingDecision.REJECTED,
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
                error_message="Queue full",
            )

    async def submit_batch(self, events: List[BaseEvent]) -> List[RoutingResult]:
        """Submit a batch of events."""
        results = []
        for event in events:
            result = await self.submit(event)
            results.append(result)
        return results

    async def process_one(self, event: BaseEvent) -> RoutingResult:
        """
        Process a single event synchronously (blocking).

        Bypasses the queue for immediate processing.
        """
        if not self._handler:
            return RoutingResult(
                event_id=event.event_id,
                decision=RoutingDecision.REJECTED,
                processing_time_ms=0,
                error_message="No handler configured",
            )

        # Dedup check
        if await self._dedup_cache.is_duplicate(event.event_id):
            return RoutingResult(
                event_id=event.event_id,
                decision=RoutingDecision.DEDUPED,
                processing_time_ms=0,
            )

        # Assign sequence
        async with self._sequence_lock:
            self._sequence_counter += 1
            sequence_id = self._sequence_counter

        event.sequence_id = sequence_id
        event.ingested_at = datetime.now(timezone.utc)

        prioritized = PrioritizedEvent(event=event, sequence_id=sequence_id)
        return await self._process_event(prioritized)

    def get_metrics(self) -> QueueMetrics:
        """Get current queue metrics."""
        self._update_metrics()
        return self._metrics

    async def get_dlq_entries(self, count: int = 10) -> List[DeadLetterEntry]:
        """Get entries from the dead letter queue."""
        return await self._dlq.peek(count)

    async def retry_dlq_entry(self) -> Optional[RoutingResult]:
        """Retry the oldest DLQ entry."""
        entry = await self._dlq.pop()
        if not entry:
            return None

        # Re-submit with fresh sequence ID
        return await self.submit(entry.event)

    # -------------------------------------------------------------------------
    # Processing Loop
    # -------------------------------------------------------------------------

    async def _processing_loop(self) -> None:
        """Main processing loop."""
        self._metrics.status = EventQueueStatus.HEALTHY

        while self._running:
            try:
                batch = await self._collect_batch()
                if not batch:
                    await asyncio.sleep(0.001)  # Yield to event loop
                    continue

                # Sort batch by ordering key for deterministic processing
                batch.sort(key=lambda p: p.ordering_key())

                for prioritized in batch:
                    if not self._running:
                        break
                    await self._process_event(prioritized)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in processing loop: %s", e)
                self._metrics.status = EventQueueStatus.DEGRADED
                await asyncio.sleep(0.1)

    async def _collect_batch(self) -> List[PrioritizedEvent]:
        """Collect a batch of events from the queue."""
        batch: List[PrioritizedEvent] = []
        deadline = time.perf_counter() + (self._config.batch_timeout_ms / 1000)

        while len(batch) < self._config.batch_size:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                break

            try:
                prioritized = await asyncio.wait_for(self._queue.get(), timeout=remaining)
                batch.append(prioritized)
            except asyncio.TimeoutError:
                break

        return batch

    async def _process_event(self, prioritized: PrioritizedEvent) -> RoutingResult:
        """Process a single event with retry logic."""
        start_time = time.perf_counter()
        event = prioritized.event

        try:
            if not self._handler:
                raise ValueError("No handler configured")

            result = await self._handler(event)
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Record metrics
            self._record_latency(latency_ms)
            self._metrics.events_processed += 1

            # Update result with latency
            result.processing_time_ms = latency_ms

            logger.debug(
                "Processed event %s in %.2fms: %s",
                event.event_id,
                latency_ms,
                result.decision,
            )

            return result

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error("Error processing event %s: %s", event.event_id, e)

            prioritized.retry_count += 1
            prioritized.last_error = str(e)

            # Retry logic
            if prioritized.retry_count < self._config.max_retries:
                self._metrics.retry_count += 1
                delay = self._config.retry_delay_ms * (self._config.retry_backoff_multiplier ** (prioritized.retry_count - 1))
                await asyncio.sleep(delay / 1000)
                return await self._process_event(prioritized)

            # Dead letter queue
            if self._config.dlq_enabled:
                await self._dlq.push(
                    DeadLetterEntry(
                        event=event,
                        error=str(e),
                        failed_at=datetime.now(timezone.utc),
                        retry_count=prioritized.retry_count,
                        original_sequence_id=prioritized.sequence_id,
                    )
                )
                self._metrics.dlq_count = self._dlq.size

            return RoutingResult(
                event_id=event.event_id,
                decision=RoutingDecision.DEAD_LETTERED,
                processing_time_ms=latency_ms,
                error_message=str(e),
            )

    # -------------------------------------------------------------------------
    # Metrics
    # -------------------------------------------------------------------------

    def _record_latency(self, latency_ms: float) -> None:
        """Record latency measurement."""
        self._latencies.append(latency_ms)
        self._processed_timestamps.append(datetime.now(timezone.utc))

        # Keep only recent measurements
        max_samples = 1000
        if len(self._latencies) > max_samples:
            self._latencies = self._latencies[-max_samples:]
            self._processed_timestamps = self._processed_timestamps[-max_samples:]

    def _update_metrics(self) -> None:
        """Update computed metrics."""
        self._metrics.queue_depth = self._queue.qsize()
        self._metrics.dedup_hits = self._dedup_cache.hits
        self._metrics.dlq_count = self._dlq.size

        if self._latencies:
            self._metrics.avg_latency_ms = sum(self._latencies) / len(self._latencies)
            sorted_latencies = sorted(self._latencies)
            p99_idx = int(len(sorted_latencies) * 0.99)
            self._metrics.p99_latency_ms = sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)]

        # Calculate events per second
        if self._processed_timestamps:
            now = datetime.now(timezone.utc)
            recent = [ts for ts in self._processed_timestamps if (now - ts).total_seconds() < 1.0]
            self._metrics.events_per_second = len(recent)

        # Update status
        if not self._running:
            self._metrics.status = EventQueueStatus.STOPPED
        elif self._metrics.queue_depth > self._config.max_queue_size * 0.9:
            self._metrics.status = EventQueueStatus.OVERLOADED
        elif self._metrics.avg_latency_ms > self._config.target_latency_ms * 2:
            self._metrics.status = EventQueueStatus.DEGRADED
        else:
            self._metrics.status = EventQueueStatus.HEALTHY


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "EventOrchestrator",
    "OrchestratorConfig",
    "EventQueueStatus",
    "QueueMetrics",
    "DeadLetterQueue",
    "DeadLetterEntry",
    "DeduplicationCache",
    "PrioritizedEvent",
]
