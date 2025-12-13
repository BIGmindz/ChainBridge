"""ARQ tasks for ChainStake staking pipeline."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

try:
    from arq import create_pool
    from arq.connections import ArqRedis
except Exception:  # pragma: no cover - keep optional
    create_pool = None  # type: ignore
    ArqRedis = None  # type: ignore


async def enqueue_stake_request(redis: "ArqRedis", payload: Dict[str, Any]) -> str:
    """Enqueue a stake request; returns job id."""
    if redis is None:
        raise RuntimeError("ARQ not configured")
    job = await redis.enqueue_job("execute_blockchain_staking", payload)
    return str(job)


async def execute_blockchain_staking(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Worker entrypoint: mint & stake asynchronously."""
    payload = ctx.get("payload") or ctx
    logger.info("stake_worker.start", extra={"payload": payload})
    # Placeholder: in real flow this would call AsyncWeb3 + IPFS pinning
    ricardian_metadata = payload.get("ricardian_metadata") or {}
    await asyncio.sleep(0)  # yield control
    logger.info("stake_worker.complete", extra={"payload": payload})
    return {"status": "STAKE_COMPLETE", "ricardian_metadata": ricardian_metadata}


async def create_redis_pool(settings) -> "ArqRedis":
    if create_pool is None:
        raise RuntimeError("ARQ not installed")
    return await create_pool(settings)
