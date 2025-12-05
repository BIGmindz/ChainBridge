from __future__ import annotations

from collections import defaultdict
import math
from datetime import datetime, timezone
from typing import Iterable, List

from sqlalchemy.orm import Session

from app.models_analytics import SettlementOutcome
from app.schemas_analytics import (
    ChainPayAnalyticsSnapshot,
    DaysToCashMetric,
    RiskTier,
    SlaMetric,
    TierHealthMetric,
)
from app.services.payment_rails_engine import PaymentRailsEngine

USD_MXN_CORRIDOR_ID = "USD_MXN"
DEFAULT_POLICY = "CHAINPAY_V1_USD_MXN_P0"
DEFAULT_ANALYTICS_VERSION = "v1"
_CASH_SLA_TARGET_D2_P95 = {
    "LOW": 5.0,
    "MEDIUM": 7.0,
    "HIGH": 10.0,
    "CRITICAL": 10.0,
}


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    n = len(values)
    mid = n // 2
    if n % 2 == 0:
        return (values[mid - 1] + values[mid]) / 2.0
    return values[mid]


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    if pct <= 0:
        return min(values)
    if pct >= 100:
        return max(values)
    values = sorted(values)
    rank = max(0, math.ceil(pct / 100 * len(values)) - 1)
    rank = min(rank, len(values) - 1)
    return values[rank]


def _days_between(start: datetime | None, end: datetime | None) -> float | None:
    if not start or not end:
        return None
    delta = end - start
    return delta.total_seconds() / 86400.0


def compute_chainpay_analytics_snapshot(
    db: Session,
    *,
    corridor_id: str = USD_MXN_CORRIDOR_ID,
    payout_policy_version: str = DEFAULT_POLICY,
    analytics_version: str = DEFAULT_ANALYTICS_VERSION,
) -> ChainPayAnalyticsSnapshot:
    """Compute Maggie-style analytics snapshot from SettlementOutcome rows.

    The current V1 logic is intentionally simple and deterministic. It aggregates
    per-tier metrics for loss/reserve utilization and days-to-cash. SLA metrics are
    placeholders until richer timings are captured in SettlementOutcome (TODO: Maggie/Cody).
    """

    rows: Iterable[SettlementOutcome] = (
        db.query(SettlementOutcome)
        .filter(
            SettlementOutcome.corridor_id == corridor_id,
            SettlementOutcome.payout_policy_version == payout_policy_version,
            SettlementOutcome.analytics_version == analytics_version,
        )
        .all()
    )

    # Empty snapshot is still considered valid for the corridor/policy
    provider = PaymentRailsEngine(db).default_provider()

    if not rows:
        return ChainPayAnalyticsSnapshot(
            as_of=datetime.now(timezone.utc).isoformat(),
            corridor_id=corridor_id,
            payout_policy_version=payout_policy_version,
            settlement_provider=provider,
            tier_health=[],
            days_to_cash=[],
            sla=[],
        )

    tier_groups: dict[RiskTier, list[SettlementOutcome]] = defaultdict(list)
    for row in rows:
        tier = (row.risk_tier_initial or "UNKNOWN").upper()
        tier_groups[tier].append(row)

    tier_health: list[TierHealthMetric] = []
    days_to_cash: list[DaysToCashMetric] = []
    sla_metrics: list[SlaMetric] = []

    for tier, tier_rows in tier_groups.items():
        total_cb = sum(r.cb_usd_total or 0.0 for r in tier_rows)
        total_loss = sum(r.cb_usd_loss_realized or 0.0 for r in tier_rows)
        total_reserved = sum(r.cb_usd_reserved_initial or 0.0 for r in tier_rows)
        total_reserved_unused = sum(r.cb_usd_reserved_unused or 0.0 for r in tier_rows)

        loss_rate = (total_loss / total_cb) if total_cb else 0.0
        reserve_utilization = (total_loss / total_reserved) if total_reserved else 0.0
        unused_reserve_ratio = (
            total_reserved_unused / total_reserved if total_reserved else 0.0
        )

        tier_health.append(
            TierHealthMetric(
                tier=tier,  # type: ignore[arg-type]
                loss_rate=loss_rate,
                reserve_utilization=reserve_utilization,
                unused_reserve_ratio=unused_reserve_ratio,
                shipment_count=len(tier_rows),
            )
        )

        # Days-to-cash metrics
        first_cash_days: list[float] = []
        final_cash_days: list[float] = []
        d2_days: list[float] = []
        for r in tier_rows:
            first = _days_between(r.delivered_timestamp, r.first_payment_timestamp)
            final = _days_between(r.delivered_timestamp, r.final_payment_timestamp)
            if first is not None:
                first_cash_days.append(first)
            if final is not None:
                final_cash_days.append(final)
                d2_days.append(final)

        days_to_cash.append(
            DaysToCashMetric(
                tier=tier,  # type: ignore[arg-type]
                corridor_id=corridor_id,
                median_days_to_first_cash=_median(first_cash_days),
                p95_days_to_first_cash=_percentile(first_cash_days, 95.0),
                median_days_to_final_cash=_median(final_cash_days),
                p95_days_to_final_cash=_percentile(final_cash_days, 95.0),
                shipment_count=len(tier_rows),
            )
        )

        # SLA metrics – placeholder until richer timestamps are logged
        total_reviews = sum(1 for r in tier_rows if (r.had_claim or r.had_dispute))

        target_d2 = _CASH_SLA_TARGET_D2_P95.get(tier, 10.0)
        cash_breach_count = sum(1 for v in d2_days if v > target_d2)
        sample_size = len(d2_days)
        cash_breach_rate = (cash_breach_count / sample_size) if sample_size else 0.0
        sla_metrics.append(
            SlaMetric(
                corridor_id=corridor_id,
                tier=tier,  # type: ignore[arg-type]
                claim_review_sla_breach_rate=0.0,  # TODO: derive when timestamps available
                manual_review_sla_breach_rate=0.0,  # TODO: derive when timestamps available
                cash_breach_rate=cash_breach_rate,
                cash_breach_count=cash_breach_count,
                sample_size=sample_size,
                total_reviews=total_reviews,
            )
        )

    return ChainPayAnalyticsSnapshot(
        as_of=datetime.now(timezone.utc).isoformat(),
        corridor_id=corridor_id,
        payout_policy_version=payout_policy_version,
        settlement_provider=provider,
        tier_health=sorted(tier_health, key=lambda t: t.tier),
        days_to_cash=sorted(days_to_cash, key=lambda d: d.tier),
        sla=sorted(sla_metrics, key=lambda s: s.tier),
    )
