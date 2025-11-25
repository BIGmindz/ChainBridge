"""Hedera HTS/HCS integration for RWA minting and audit logging."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from functools import lru_cache
from typing import Any, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from hedera import (
        AccountId,
        Client,
        PrivateKey,
        TokenCreateTransaction,
        TokenSupplyType,
        TokenType,
        TopicId,
        TopicMessageSubmitTransaction,
    )

    _HEDERA_AVAILABLE = True
except ImportError:  # pragma: no cover - graceful fallback
    _HEDERA_AVAILABLE = False
    AccountId = PrivateKey = Client = TopicId = None  # type: ignore


def _default_token_id(metadata_hash: str) -> str:
    # Deterministic demo-friendly TokenId
    return f"0.0.{abs(hash(metadata_hash)) % 1_000_000}"


@lru_cache(maxsize=1)
def _client() -> Client | None:
    if settings.DEMO_MODE or not _HEDERA_AVAILABLE:
        return None
    if not settings.HEDERA_OPERATOR_ID or not settings.HEDERA_OPERATOR_KEY:
        logger.warning("hedera.config.missing_operator")
        return None
    network = (settings.HEDERA_NETWORK or "testnet").lower()
    client = Client.forMainnet() if network == "mainnet" else Client.forTestnet()
    client.setOperator(AccountId.fromString(settings.HEDERA_OPERATOR_ID), PrivateKey.fromString(settings.HEDERA_OPERATOR_KEY))
    return client


def mint_rwa_token_sync(metadata_hash: str, amount: int = 1) -> str:
    """
    Mint an RWA NFT (finite supply) and return TokenId.
    Falls back to deterministic TokenId when SDK/config is unavailable.
    """
    start = time.time()
    client = _client()
    if client is None:  # demo or offline path
        token_id = _default_token_id(metadata_hash)
        logger.info("hedera.mint.demo", extra={"token_id": token_id})
        return token_id

    try:
        treasury = AccountId.fromString(settings.HEDERA_OPERATOR_ID)  # type: ignore[arg-type]
        tx = (
            TokenCreateTransaction()
            .setTokenName("ChainBridge RWA")
            .setTokenSymbol("CB-RWA")
            .setTokenMemo(metadata_hash[:100])
            .setTokenType(TokenType.NON_FUNGIBLE_UNIQUE)
            .setSupplyType(TokenSupplyType.FINITE)
            .setMaxSupply(max(1, amount))
            .setTreasuryAccountId(treasury)
        )
        receipt = tx.execute(client).getReceipt(client)
        token_id = str(receipt.tokenId)
        logger.info("hedera.mint.success", extra={"token_id": token_id, "latency_ms": int((time.time() - start) * 1000)})
        return token_id
    except Exception as exc:  # pragma: no cover - guardrail
        logger.warning("hedera.mint.failed", extra={"error": str(exc)})
        return _default_token_id(metadata_hash)


async def mint_rwa_token_async(metadata_hash: str, amount: int = 1) -> str:
    """Async wrapper to offload blocking SDK calls."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: mint_rwa_token_sync(metadata_hash, amount))


def log_audit_event_sync(shipment_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Publish audit event to HCS. Returns ledger receipt metadata.
    Falls back to synthetic receipt when offline/demo.
    """
    payload = {"shipment_id": shipment_id, **event_data}
    client = _client()
    topic_id = settings.HEDERA_AUDIT_TOPIC_ID
    start = time.time()
    if client is None or not topic_id:
        message_id = f"demo-{abs(hash(json.dumps(payload, sort_keys=True))) % 1_000_000}"
        logger.info("hedera.audit.demo", extra={"message_id": message_id})
        return {"message_id": message_id, "status": "RECORDED_DEMO"}

    try:
        topic = TopicId.fromString(topic_id)  # type: ignore[arg-type]
        tx = TopicMessageSubmitTransaction().setTopicId(topic).setMessage(json.dumps(payload, separators=(",", ":")))
        receipt = tx.execute(client).getReceipt(client)
        latency_ms = int((time.time() - start) * 1000)
        try:
            from api.sla.metrics import update_metric  # lazy import to avoid circular

            update_metric("hedera_consensus")  # type: ignore[arg-type]
        except Exception:
            pass
        logger.info("hedera.audit.success", extra={"message_id": str(receipt.topicId) if hasattr(receipt, "topicId") else None, "latency_ms": latency_ms})
        return {
            "message_id": str(getattr(receipt, "topicId", topic_id)),
            "status": "RECORDED",
            "latency_ms": latency_ms,
        }
    except Exception as exc:  # pragma: no cover - guardrail
        logger.warning("hedera.audit.failed", extra={"error": str(exc)})
        return {"message_id": f"demo-{shipment_id}", "status": "FAILED"}


async def log_audit_event_async(shipment_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Async wrapper to offload blocking SDK calls."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: log_audit_event_sync(shipment_id, event_data))


# Backwards compatibility aliases
mint_rwa_token = mint_rwa_token_sync
log_audit_event = log_audit_event_sync
