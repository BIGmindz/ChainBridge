"""Centralised settings for ChainBridge demo stack."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT_DIR / "data" / "chainbridge.db"
DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    ENV: str = "local"
    DEMO_MODE: bool = True

    DATABASE_URL: str = f"sqlite:///{DEFAULT_DB_PATH}"
    REDIS_URL: str = "redis://localhost:6379/0"

    WEB3_RPC_URL: str | None = None
    WEB3_OPERATOR_WALLET: str | None = None

    # Fortress stack integration
    HEDERA_OPERATOR_ID: str | None = None
    HEDERA_OPERATOR_KEY: str | None = None
    HEDERA_NETWORK: str = "testnet"
    HEDERA_AUDIT_TOPIC_ID: str | None = None
    CHAINLINK_ROUTER_ADDRESS: str | None = None
    SXT_USER_ID: str | None = None
    SXT_PRIVATE_KEY: str | None = None

    ARQ_QUEUE_NAME: str = "chainbridge_default"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Backwards-compatible module-level flags
DEMO_MODE = settings.DEMO_MODE
DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL
MARKETPLACE_DEMO_MODE = os.getenv("MARKETPLACE_DEMO_MODE", "").lower() in {"1", "true", "yes"} or DEMO_MODE
