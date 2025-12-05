from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.schemas_guardrails import GuardrailStatusSnapshot, TierGuardrailStatus
from app.schemas_analytics import RiskTier
from app.services.analytics_service import (
    DEFAULT_ANALYTICS_VERSION,
    DEFAULT_POLICY,
    USD_MXN_CORRIDOR_ID,
    compute_chainpay_analytics_snapshot,
)


@dataclass(frozen=True)
class GuardrailThresholds:
    max_amber_loss_rate: float
    max_red_loss_rate: float
    max_amber_cash_breach_rate: float
    max_red_cash_breach_rate: float
    max_amber_d2_p95_days: float
    max_red_d2_p95_days: float
    max_amber_unused_reserve_ratio: float
    max_red_unused_reserve_ratio: float


# Thresholds mirror existing classify logic; numbers should stay in sync with doc
GUARDRAIL_THRESHOLDS_USD_MXN = GuardrailThresholds(
    max_amber_loss_rate=0.02,
    max_red_loss_rate=0.05,
    max_amber_cash_breach_rate=0.10,
    max_red_cash_breach_rate=0.20,
    max_amber_d2_p95_days=7.0,
    max_red_d2_p95_days=10.0,
    max_amber_unused_reserve_ratio=0.50,
    max_red_unused_reserve_ratio=0.80,
)


def _get_thresholds_for_corridor(corridor_id: str) -> GuardrailThresholds:
    # Single corridor for now; hook for future corridor-specific thresholds
    return GUARDRAIL_THRESHOLDS_USD_MXN


def _classify_tier(
    *,
    loss_rate: float,
    cash_breach_rate: float,
    d2_p95: float,
    unused_reserve_ratio: float,
    thresholds: GuardrailThresholds,
) -> str:
    """Return GREEN/AMBER/RED using simple threshold bands.

    Rule: any RED threshold breach => RED; else any AMBER => AMBER; else GREEN.
    """

    if (
        loss_rate >= thresholds.max_red_loss_rate
        or cash_breach_rate >= thresholds.max_red_cash_breach_rate
        or d2_p95 >= thresholds.max_red_d2_p95_days
        or unused_reserve_ratio >= thresholds.max_red_unused_reserve_ratio
    ):
        return "RED"

    if (
        loss_rate >= thresholds.max_amber_loss_rate
        or cash_breach_rate >= thresholds.max_amber_cash_breach_rate
        or d2_p95 >= thresholds.max_amber_d2_p95_days
        or unused_reserve_ratio >= thresholds.max_amber_unused_reserve_ratio
    ):
        return "AMBER"

    return "GREEN"


def _compute_tier_reasons(
    *,
    loss_rate: float,
    cash_breach_rate: float,
    d2_p95: float,
    unused_reserve_ratio: float,
    thresholds: GuardrailThresholds,
) -> List[str]:
    reasons: List[str] = []

    if loss_rate >= thresholds.max_red_loss_rate:
        reasons.append("LOSS_RATE_RED")
    elif loss_rate >= thresholds.max_amber_loss_rate:
        reasons.append("LOSS_RATE_AMBER")

    if cash_breach_rate >= thresholds.max_red_cash_breach_rate:
        reasons.append("CASH_SLA_BREACH_RED")
    elif cash_breach_rate >= thresholds.max_amber_cash_breach_rate:
        reasons.append("CASH_SLA_BREACH_AMBER")

    if d2_p95 >= thresholds.max_red_d2_p95_days:
        reasons.append("D2_P95_RED")
    elif d2_p95 >= thresholds.max_amber_d2_p95_days:
        reasons.append("D2_P95_AMBER")

    if unused_reserve_ratio >= thresholds.max_red_unused_reserve_ratio:
        reasons.append("UNUSED_RESERVE_RED")
    elif unused_reserve_ratio >= thresholds.max_amber_unused_reserve_ratio:
        reasons.append("UNUSED_RESERVE_AMBER")

    return reasons


def _build_tier_summary(state: str, reasons: List[str]) -> Optional[str]:
    if state == "GREEN" and not reasons:
        return "GREEN: within guardrails."
    if not reasons:
        return f"{state}: no specific breaches detected."
    joined = ", ".join(reasons)
    return f"{state}: {joined}."


def _build_overall_summary(per_tier: List[TierGuardrailStatus]) -> Tuple[List[str], Optional[str]]:
    overall_reasons: List[str] = []
    for tier in per_tier:
        if tier.state in {"AMBER", "RED"}:
            overall_reasons.extend(tier.reasons)
    if not per_tier:
        return [], "GREEN: no data yet; defaulting to within guardrails."
    states = {t.state for t in per_tier}
    if "RED" in states:
        summary = "RED: breaches present in one or more tiers."
    elif "AMBER" in states:
        summary = "AMBER: watchlist conditions present in one or more tiers."
    else:
        summary = "GREEN: all tiers within guardrails."
    return overall_reasons, summary


def evaluate_guardrails_for_corridor(
    db: Session,
    *,
    corridor_id: str = USD_MXN_CORRIDOR_ID,
    payout_policy_version: str = DEFAULT_POLICY,
    analytics_version: str = DEFAULT_ANALYTICS_VERSION,
) -> GuardrailStatusSnapshot:
    analytics = compute_chainpay_analytics_snapshot(
        db,
        corridor_id=corridor_id,
        payout_policy_version=payout_policy_version,
        analytics_version=analytics_version,
    )

    thresholds = _get_thresholds_for_corridor(corridor_id)

    tier_health_by_tier: Dict[RiskTier, object] = {h.tier: h for h in analytics.tier_health}
    days_by_tier: Dict[RiskTier, object] = {d.tier: d for d in analytics.days_to_cash}
    sla_by_tier: Dict[RiskTier, object] = {s.tier: s for s in analytics.sla}

    per_tier_status: List[TierGuardrailStatus] = []

    for tier, health in tier_health_by_tier.items():
        days = days_by_tier.get(tier)
        sla = sla_by_tier.get(tier)

        loss_rate = getattr(health, "loss_rate", 0.0)
        unused_reserve_ratio = getattr(health, "unused_reserve_ratio", 0.0)
        d2_p95 = getattr(days, "p95_days_to_final_cash", 0.0) if days else 0.0
        cash_breach_rate = getattr(sla, "cash_breach_rate", 0.0) if sla else 0.0

        state = _classify_tier(
            loss_rate=loss_rate,
            cash_breach_rate=cash_breach_rate,
            d2_p95=d2_p95,
            unused_reserve_ratio=unused_reserve_ratio,
            thresholds=thresholds,
        )

        reasons = _compute_tier_reasons(
            loss_rate=loss_rate,
            cash_breach_rate=cash_breach_rate,
            d2_p95=d2_p95,
            unused_reserve_ratio=unused_reserve_ratio,
            thresholds=thresholds,
        )
        summary = _build_tier_summary(state, reasons)

        per_tier_status.append(
            TierGuardrailStatus(
                tier=tier,  # type: ignore[arg-type]
                state=state,
                loss_rate=loss_rate,
                cash_sla_breach_rate=cash_breach_rate,
                d2_p95_days=d2_p95,
                unused_reserve_ratio=unused_reserve_ratio,
                reasons=reasons,
                summary=summary,
            )
        )

    states = {t.state for t in per_tier_status}
    if "RED" in states:
        overall = "RED"
    elif "AMBER" in states:
        overall = "AMBER"
    else:
        overall = "GREEN"

    overall_reasons, overall_summary = _build_overall_summary(per_tier_status)

    return GuardrailStatusSnapshot(
        corridor_id=corridor_id,
        payout_policy_version=payout_policy_version,
        settlement_provider=str(getattr(analytics, "settlement_provider", "")),
        overall_state=overall,
        per_tier=sorted(per_tier_status, key=lambda t: t.tier),
        last_evaluated_at=datetime.now(timezone.utc),
        overall_reasons=overall_reasons,
        overall_summary=overall_summary,
    )
