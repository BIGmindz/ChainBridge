"""ARQ worker functions for staking and liquidation."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def mint_and_stake_task(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Mint RWA token, log audit, archive telemetry, and request oracle verification."""
    payload = ctx.get("payload") or ctx
    logger.info("worker.mint_and_stake.start", extra={"payload": payload})

    from app.services.data.sxt_client import archive_telemetry
    from app.services.ledger.hedera_engine import (
        log_audit_event_async,
        mint_rwa_token_async,
    )
    from app.services.oracle.chainlink_client import (
        estimate_gas_cost,
        request_verification,
    )

    telemetry = payload.get("telemetry") if isinstance(payload, dict) else {}
    shipment_id = str(payload.get("shipment_id") or payload.get("id") or "UNKNOWN")
    metadata_hash = str(payload.get("metadata_hash") or payload.get("ricardian_hash") or shipment_id)
    supply = int(payload.get("token_supply") or 1)

    archive_telemetry(telemetry or {})
    token_id = await mint_rwa_token_async(metadata_hash=metadata_hash, amount=supply)
    audit_receipt = await log_audit_event_async(shipment_id, {"metadata_hash": metadata_hash, "telemetry": telemetry})
    oracle_req = request_verification(shipment_id, payload.get("oracle_payload"))

    tx_hash = f"hedera:{token_id}"
    gas_cost = oracle_req.get("gas_cost_usd") or estimate_gas_cost()

    logger.info(
        "worker.mint_and_stake.complete",
        extra={
            "shipment_id": shipment_id,
            "token_id": token_id,
            "audit_status": audit_receipt.get("status"),
            "oracle_request_id": oracle_req.get("request_id"),
            "gas_cost_usd": gas_cost,
        },
    )
    return {
        "status": "STAKE_COMPLETE",
        "payload": payload,
        "token_id": token_id,
        "audit": audit_receipt,
        "oracle_request": oracle_req,
        "tx_hash": tx_hash,
        "chainlink_gas_cost_usd": gas_cost,
    }


async def liquidate_asset_task(ctx: Dict[str, Any]) -> Dict[str, Any]:
    payload = ctx.get("payload") or ctx
    logger.warning("worker.liquidate.start", extra={"payload": payload})
    await asyncio.sleep(0)
    try:
        from app.services.marketplace.auctioneer import create_liquidation_listing

        listing = create_liquidation_listing(payload.get("shipment_id"))
        logger.info("worker.liquidate.listing_created", extra={"listing_id": listing.id})
    except Exception as exc:  # pragma: no cover
        logger.warning("worker.liquidate.listing_failed", extra={"error": str(exc)})
    logger.warning("worker.liquidate.complete", extra={"payload": payload})
    return {"status": "LIQUIDATED", "payload": payload}
