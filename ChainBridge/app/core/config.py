"""Centralised settings for ChainBridge demo stack."""

from __future__ import annotations

import os
from pathlib import Path

from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ModuleNotFoundError:
    # Lightweight fallback for environments that do not have pydantic-settings
    # installed (e.g., bare test environments). This preserves default values
    # and basic environment overrides well enough for the demo stack.
    from pydantic import BaseModel

    class BaseSettings(BaseModel):  # type: ignore[misc]
        class Config:  # pragma: no cover - compatibility shim
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = "ignore"

        def __init__(self, **values):
            env_overrides = {}
            for field in getattr(self.__class__, "model_fields", {}):
                env_val = os.getenv(field)
                if env_val is not None:
                    env_overrides[field] = env_val
            super().__init__(**{**env_overrides, **values})

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT_DIR / "data" / "chainbridge.db"
DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    ENV: str = "local"
    DEMO_MODE: bool = True

    DATABASE_URL: str = f"sqlite:///{DEFAULT_DB_PATH}"
    REDIS_URL: str = "redis://localhost:6379/0"

    WEB3_RPC_URL: Optional[str] = None
    WEB3_OPERATOR_WALLET: Optional[str] = None

    # Fortress stack integration
    HEDERA_OPERATOR_ID: Optional[str] = None
    HEDERA_OPERATOR_KEY: Optional[str] = None
    HEDERA_NETWORK: str = "testnet"
    HEDERA_AUDIT_TOPIC_ID: Optional[str] = None
    CHAINLINK_ROUTER_ADDRESS: Optional[str] = None
    SXT_USER_ID: Optional[str] = None
    SXT_PRIVATE_KEY: Optional[str] = None

    ARQ_QUEUE_NAME: str = "chainbridge_default"

    # Frontend / Vite integration (optional; used by OC + map UX)
    vite_mapbox_token: Optional[str] = None
    vite_api_url: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Ignore unknown extra environment keys so new vars do not
        # cause settings validation failures in Internal Pilot.
        extra = "ignore"


settings = Settings()

# Backwards-compatible module-level flags
DEMO_MODE = settings.DEMO_MODE
DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL
MARKETPLACE_DEMO_MODE = os.getenv("MARKETPLACE_DEMO_MODE", "").lower() in {"1", "true", "yes"} or DEMO_MODE
