"""Web3 settlement adapter abstraction."""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.core.config import MARKETPLACE_DEMO_MODE, DEMO_MODE

logger = logging.getLogger(__name__)


@dataclass
class SettlementIntentData:
    intent_id: str
    listing_id: str
    wallet: str
    amount: Decimal
    currency: str


@dataclass
class SettlementResult:
    tx_hash: str
    status: str  # SUCCESS | FAILED
    adapter: str
    failure_reason: Optional[str] = None


class Web3SettlementClient:
    async def settle_intent(self, payload: SettlementIntentData) -> SettlementResult:
        raise NotImplementedError


class DemoWeb3SettlementClient(Web3SettlementClient):
    async def settle_intent(self, payload: SettlementIntentData) -> SettlementResult:
        tx_hash = f"demo_tx_{payload.intent_id}"
        await asyncio.sleep(0.01)
        logger.info(
            "web3.demo.settle",
            extra={
                "listing_id": payload.listing_id,
                "wallet": payload.wallet,
                "amount": float(payload.amount),
                "currency": payload.currency,
                "tx_hash": tx_hash,
            },
        )
        return SettlementResult(tx_hash=tx_hash, status="SUCCESS", adapter="DEMO")


class AsyncWeb3SettlementClient(Web3SettlementClient):  # pragma: no cover - placeholder for future real chain integration
    def __init__(self, rpc_url: str, operator_wallet: Optional[str] = None, operator_key: Optional[str] = None) -> None:
        self.rpc_url = rpc_url
        self.operator_wallet = operator_wallet
        self.operator_key = operator_key

    async def settle_intent(self, payload: SettlementIntentData) -> SettlementResult:
        raise NotImplementedError("AsyncWeb3SettlementClient not wired; provide DEMO_MODE or plugin implementation")


def get_web3_client() -> Web3SettlementClient:
    mode = os.getenv("WEB3_MODE", "").lower()
    rpc_url = os.getenv("WEB3_RPC_URL")
    strict = os.getenv("WEB3_STRICT", "false").lower() in {"1", "true", "yes"}
    if MARKETPLACE_DEMO_MODE or DEMO_MODE or mode == "demo":
        return DemoWeb3SettlementClient()
    if (mode == "real" or not DEMO_MODE) and not rpc_url:
        if strict:
            raise RuntimeError("web3_not_configured")
        logger.warning("web3.rpc.missing", extra={"event": "web3.rpc.missing", "demo_mode": DEMO_MODE})
        return DemoWeb3SettlementClient()
    return AsyncWeb3SettlementClient(
        rpc_url,
        operator_wallet=os.getenv("WEB3_OPERATOR_WALLET"),
        operator_key=os.getenv("WEB3_OPERATOR_KEY"),
    )
