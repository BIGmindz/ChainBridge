"""Config-backed payout matrix for ChainPay risk tiers.

NOTE: Values and tiers must remain in sync with
`docs/product/CHAINPAY_RISK_PAYOUT_MATRIX_V1.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal

RiskTier = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@dataclass(frozen=True)
class PayoutConfig:
    score_min: float
    score_max: float
    pickup_percent: float
    delivered_percent: float
    claim_percent: float
    claim_window_days: int
    requires_manual_review: bool = False
    freeze_all_payouts: bool = False


@dataclass(frozen=True)
class CorridorConfig:
    id: str
    risk_tiers: Dict[RiskTier, PayoutConfig]
    claim_window_override_days: int | None = None


USD_MXN_CORRIDOR = CorridorConfig(
    id="USD_MXN",
    risk_tiers={
        "LOW": PayoutConfig(
            score_min=0.0,
            score_max=0.35,
            pickup_percent=0.20,
            delivered_percent=0.70,
            claim_percent=0.10,
            claim_window_days=3,
            requires_manual_review=False,
        ),
        "MEDIUM": PayoutConfig(
            score_min=0.35,
            score_max=0.65,
            pickup_percent=0.15,
            delivered_percent=0.65,
            claim_percent=0.20,
            claim_window_days=5,
            requires_manual_review=False,
        ),
        "HIGH": PayoutConfig(
            score_min=0.65,
            score_max=0.85,
            pickup_percent=0.10,
            delivered_percent=0.60,
            claim_percent=0.30,
            claim_window_days=7,
            requires_manual_review=True,  # Manual review flag for final tranche
        ),
        "CRITICAL": PayoutConfig(
            score_min=0.85,
            score_max=1.0,
            pickup_percent=0.0,
            delivered_percent=0.0,
            claim_percent=1.0,
            claim_window_days=0,
            requires_manual_review=True,
            freeze_all_payouts=True,
        ),
    },
)


CORRIDOR_CONFIGS: Dict[str, CorridorConfig] = {
    "USD_MXN": USD_MXN_CORRIDOR,
}
