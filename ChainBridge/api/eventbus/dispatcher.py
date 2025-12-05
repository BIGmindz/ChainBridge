"""In-memory event bus (demo)."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Dict, List, Union

logger = logging.getLogger(__name__)

Handler = Union[Callable[[dict], Awaitable[None]], Callable[[dict], None]]
_SUBSCRIBERS: Dict[str, List[Handler]] = {}


def subscribe(event_type: str, handler: Handler) -> None:
    _SUBSCRIBERS.setdefault(event_type, []).append(handler)


def publish(event_type: str, payload: dict) -> None:
    handlers = list(_SUBSCRIBERS.get(event_type, []))
    for handler in handlers:
        try:
            result = handler(payload)
            if asyncio.iscoroutine(result):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(result)
                    else:
                        loop.run_until_complete(result)
                except RuntimeError:
                    asyncio.run(result)
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "eventbus_handler_error",
                extra={"event_type": event_type, "error": str(exc)},
            )
    logger.info("eventbus.publish", extra={"event_type": event_type, "handlers": len(handlers)})
