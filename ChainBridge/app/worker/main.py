"""ARQ worker configuration for ChainBridge demo stack."""
from __future__ import annotations

from app.core.config import settings


class WorkerSettings:
    functions = [
        "app.worker.settlement.execute_dutch_settlement",
        "app.worker.tasks.execute_blockchain_staking",
    ]
    redis_settings = {
        "host": "localhost",
        "port": 6379,
        "database": 0,
    }
    queue_name = settings.ARQ_QUEUE_NAME
