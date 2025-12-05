"""Payment rail selector for ChainPay.

Chooses the active rail (internal ledger vs CB-USDx) based on a simple flag
so business logic can stay agnostic. V1 defaults to the internal ledger rail.
"""

import os
from typing import Optional

from sqlalchemy.orm import Session

from app.payment_rails import CbUsdxRail, InternalLedgerRail, PaymentRail, SettlementProvider


class PaymentRailsEngine:
    """Factory/selector for ChainPay payment rails.

    References:
    - CHAINPAY_ONCHAIN_SETTLEMENT.md
    - CHAINPAY_CB_USDX_PRODUCT_MAP.md
    """

    def __init__(self, db: Session, *, use_cb_usdx: Optional[bool] = None) -> None:
        self._db = db
        env_flag = _read_bool_env("CHAINPAY_USE_CB_USDX_RAIL", default=False)
        self._use_cb_usdx = env_flag if use_cb_usdx is None else use_cb_usdx

    def get_immediate_rail(self) -> PaymentRail:
        """Return the rail to use for immediate settlements."""
        if self._use_cb_usdx:
            return CbUsdxRail(self._db)
        return InternalLedgerRail(self._db)

    def default_provider(self) -> SettlementProvider:
        return SettlementProvider.CB_USDX if self._use_cb_usdx else SettlementProvider.INTERNAL_LEDGER


def _read_bool_env(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
