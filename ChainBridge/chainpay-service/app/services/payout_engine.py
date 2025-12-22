"""Config-driven payout engine for ChainPay.

Aligns with docs/product/CHAINPAY_RISK_PAYOUT_MATRIX_V1.md
for the pilot corridor(s).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config_payout_matrix import (
    CORRIDOR_CONFIGS,
    CorridorConfig,
    PayoutConfig,
    RiskTier,
)


@dataclass
class PayoutSchedule:
    corridor_id: str
    risk_tier: RiskTier
    pickup_percent: float
    delivered_percent: float
    claim_percent: float
    claim_window_days: int
    requires_manual_review: bool
    freeze_all_payouts: bool = False

    def total_percentage(self) -> float:
        return self.pickup_percent + self.delivered_percent + self.claim_percent


class PayoutConfigError(Exception):
    pass


def get_corridor_config(corridor_id: str) -> CorridorConfig:
    try:
        return CORRIDOR_CONFIGS[corridor_id]
    except KeyError as exc:  # pragma: no cover - defensive
        raise PayoutConfigError(f"Unknown corridor_id={corridor_id!r}") from exc


def map_score_to_tier(corridor_config: CorridorConfig, risk_score: float) -> RiskTier:
    for tier, cfg in corridor_config.risk_tiers.items():
        if cfg.score_min <= risk_score < cfg.score_max or (
            risk_score == 1.0 and cfg.score_max == 1.0
        ):
            return tier  # type: ignore[return-value]
    raise PayoutConfigError(f"Risk score {risk_score} did not map to any tier")


def _validate_totals(tier: RiskTier, corridor_id: str, cfg: PayoutConfig) -> None:
    total = cfg.pickup_percent + cfg.delivered_percent + cfg.claim_percent
    if not abs(total - 1.0) < 1e-6:
        raise PayoutConfigError(
            f"Payout percents do not sum to 1.0 for tier={tier}, corridor={corridor_id}: total={total}"
        )


def get_payout_schedule(
    corridor_id: str,
    risk_score: float,
    *,
    override_tier: Optional[RiskTier] = None,
) -> PayoutSchedule:
    corridor = get_corridor_config(corridor_id)
    tier = override_tier or map_score_to_tier(corridor, risk_score)
    cfg: PayoutConfig = corridor.risk_tiers[tier]

    _validate_totals(tier, corridor_id, cfg)

    claim_window_days = corridor.claim_window_override_days or cfg.claim_window_days

    return PayoutSchedule(
        corridor_id=corridor_id,
        risk_tier=tier,
        pickup_percent=cfg.pickup_percent,
        delivered_percent=cfg.delivered_percent,
        claim_percent=cfg.claim_percent,
        claim_window_days=claim_window_days,
        requires_manual_review=cfg.requires_manual_review,
        freeze_all_payouts=cfg.freeze_all_payouts,
    )
