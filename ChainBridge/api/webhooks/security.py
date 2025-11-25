"""Shared webhook security helpers."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from typing import Dict, Tuple

from fastapi import HTTPException
from starlette.requests import Request

logger = logging.getLogger(__name__)

SECRET_ENV = "CHAINBRIDGE_WEBHOOK_SECRET"
SIGNATURE_HEADER = "X-ChainBridge-Signature"
RATE_LIMIT_COUNT = int(os.getenv("WEBHOOK_RATE_LIMIT", "3"))
RATE_LIMIT_WINDOW = int(os.getenv("WEBHOOK_RATE_WINDOW", "30"))

_RECENT_CALLS: Dict[Tuple[str, str], list[float]] = {}


async def verify_signature(request: Request) -> None:
    secret = os.getenv(SECRET_ENV)
    if not secret:
        logger.info("webhook_signature_demo_mode")
        return
    provided = request.headers.get(SIGNATURE_HEADER)
    if not provided:
        raise HTTPException(status_code=401, detail={"error": "missing_signature"})
    body = await request.body()
    computed = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(provided, computed):
        raise HTTPException(status_code=401, detail={"error": "invalid_signature"})


def enforce_rate_limit(provider: str, payment_intent_id: str | None) -> None:
    now = time.time()
    key = (provider or "unknown", payment_intent_id or "unknown")
    calls = [ts for ts in _RECENT_CALLS.get(key, []) if now - ts <= RATE_LIMIT_WINDOW]
    if len(calls) >= RATE_LIMIT_COUNT:
        logger.warning(
            "webhook_rate_limited",
            extra={"provider": key[0], "payment_intent_id": key[1]},
        )
        raise HTTPException(status_code=429, detail={"error": "rate_limited"})
    calls.append(now)
    _RECENT_CALLS[key] = calls


def reset_rate_limits() -> None:
    _RECENT_CALLS.clear()
