"""Shared FastAPI dependencies for Redis/ARQ pools."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

try:  # pragma: no cover - arq is optional at import time
    from arq import create_pool
    from arq.connections import RedisSettings
except Exception:  # pragma: no cover
    create_pool = None  # type: ignore
    RedisSettings = None  # type: ignore

logger = logging.getLogger(__name__)


class InMemoryArq:
    """Demo-friendly ARQ stub that records enqueued jobs."""

    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict[str, Any]]] = []

    async def enqueue_job(self, name: str, payload: dict[str, Any]) -> str:
        self.jobs.append((name, payload))
        return f"demo-{len(self.jobs)}"


_INMEMORY_ARQ = InMemoryArq()


async def get_arq_pool() -> Any:
    """
    Provide an ARQ pool if configured; otherwise fall back to an in-memory stub.
    This keeps API endpoints responsive in local/dev without Redis running.
    """
    if getattr(settings, "DEMO_MODE", False):
        return _INMEMORY_ARQ

    if create_pool is None or RedisSettings is None:
        return _INMEMORY_ARQ

    try:
        redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    except Exception:
        logger.warning("arq.redis_settings_invalid", extra={"redis_url": settings.REDIS_URL})
        return _INMEMORY_ARQ

    try:
        return await create_pool(redis_settings)
    except Exception:
        logger.warning("arq.pool.fallback", extra={"redis_url": settings.REDIS_URL})
        return _INMEMORY_ARQ


def get_inmemory_arq() -> InMemoryArq:
    """Expose the singleton in-memory queue for tests."""
    return _INMEMORY_ARQ
