"""Breach monitor to detect margin calls."""

from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)


def send_emergency_alert(message: str) -> None:
    logger.warning("breach_monitor.alert", extra={"message": message})


def monitor_collateral_health(
    *,
    current_asset_value: float,
    outstanding_loan_balance: float,
    alert_fn: Callable[[str], None] = send_emergency_alert,
) -> bool:
    """Return True if margin call triggered."""
    threshold = (current_asset_value or 0.0) * 0.85
    if threshold < (outstanding_loan_balance or 0.0):
        alert_fn("MARGIN CALL")
        return True
    return False
