"""Rate limiting utilities for gateway requests.

Limits are enforced per user, per agent, and per endpoint before any
Gateway execution occurs.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable, Deque, Dict


class RateLimitError(Exception):
    """Raised when a rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: float,
        scope: str | None = None,
        key: str | None = None,
        limit: int | None = None,
        remaining: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.scope = scope
        self.key = key
        self.limit = limit
        self.remaining = remaining


@dataclass(frozen=True)
class RateLimitConfig:
    """Configuration for rate limits within a sliding window."""

    per_user: int = 60
    per_agent: int = 120
    per_endpoint: int = 300
    window_seconds: int = 60


@dataclass(frozen=True)
class RequestContext:
    """Who is calling which endpoint."""

    user_id: str
    agent_id: str
    endpoint: str


class RateLimiter:
    """Simple sliding-window rate limiter."""

    def __init__(self, config: RateLimitConfig | None = None, time_provider: Callable[[], float] | None = None) -> None:
        self.config = config or RateLimitConfig()
        self._clock = time_provider or time.time
        self._buckets: Dict[str, Dict[str, Deque[float]]] = {
            "user": defaultdict(deque),
            "agent": defaultdict(deque),
            "endpoint": defaultdict(deque),
        }

    def enforce(self, context: RequestContext) -> None:
        """Enforce per-user, per-agent, and per-endpoint limits."""

        now = self._clock()
        self._consume("user", context.user_id, self.config.per_user, now)
        self._consume("agent", context.agent_id, self.config.per_agent, now)
        self._consume("endpoint", context.endpoint, self.config.per_endpoint, now)

    def snapshot(self, context: RequestContext) -> Dict[str, int]:
        """Return current bucket occupancy for observability headers."""

        return {
            "user": len(self._buckets["user"][context.user_id]),
            "agent": len(self._buckets["agent"][context.agent_id]),
            "endpoint": len(self._buckets["endpoint"][context.endpoint]),
        }

    def _consume(self, scope: str, key: str, limit: int, now: float) -> None:
        bucket = self._buckets[scope][key]
        self._evict_old(bucket, now)

        if len(bucket) >= limit:
            retry_after = self._retry_after(bucket, now)
            raise RateLimitError(
                f"Rate limit exceeded for {scope}:{key}",
                retry_after=retry_after,
                scope=scope,
                key=key,
                limit=limit,
                remaining=max(limit - len(bucket), 0),
            )

        bucket.append(now)

    def _evict_old(self, bucket: Deque[float], now: float) -> None:
        window_start = now - self.config.window_seconds
        while bucket and bucket[0] < window_start:
            bucket.popleft()

    def _retry_after(self, bucket: Deque[float], now: float) -> float:
        if not bucket:
            return 0.0
        oldest = bucket[0]
        elapsed = now - oldest
        return max(self.config.window_seconds - elapsed, 0.0)
