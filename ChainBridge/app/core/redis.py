"""Redis helper stub for price cache."""

from __future__ import annotations

from typing import Any, Optional

try:
    import aioredis  # type: ignore
except Exception:  # pragma: no cover
    aioredis = None  # type: ignore


async def get_redis(url: str | None = None) -> Optional[Any]:
    if aioredis is None:
        return None
    return await aioredis.from_url(url or "redis://localhost")
