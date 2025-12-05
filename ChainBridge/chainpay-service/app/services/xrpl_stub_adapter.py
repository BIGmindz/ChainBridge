"""Deterministic XRPL settlement adapter for offline test environments."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from ..schemas_settlement import OnchainStatus


class XRPLSettlementAdapter:
    """Stub XRPL adapter that fabricates predictable settlement artifacts."""

    def __init__(self, *, confirm_threshold: float = 25_000.0) -> None:
        self.confirm_threshold = confirm_threshold

    def submit_payment(
        self,
        *,
        settlement_id: str,
        amount: float,
        asset: str,
        carrier_wallet: str,
        memo: str | None = None,
    ) -> dict:
        base = f"{settlement_id}:{carrier_wallet}:{amount:.4f}:{asset}:{memo or ''}"
        tx_hash = hashlib.sha256(base.encode("utf-8")).hexdigest()
        timestamp = datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        status = OnchainStatus.CONFIRMED if amount <= self.confirm_threshold else OnchainStatus.SUBMITTED
        return {
            "status": status,
            "tx_hash": tx_hash,
            "xrpl_timestamp": timestamp,
        }


__all__ = ["XRPLSettlementAdapter"]
