from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models_analytics import SettlementOutcome
from app.models_settlement import (
    CbUsdAmount,
    SettlementEvent,
    SettlementMilestone,
    SettlementStatus,
)
from app.payment_rails import SettlementProvider


def get_mock_settlement_status(shipment_id: str) -> SettlementStatus:
    """Build a deterministic mock settlement status for a shipment."""
    now = datetime.now(timezone.utc).isoformat()
    cb_usd = CbUsdAmount(total=1000.0, released=700.0, reserved=300.0)

    events = [
        SettlementEvent(
            id=f"{shipment_id}-event-1",
            shipment_id=shipment_id,
            timestamp=now,
            milestone=SettlementMilestone.PICKUP,
            risk_tier="LOW",
            notes="Shipment picked up",
        ),
        SettlementEvent(
            id=f"{shipment_id}-event-2",
            shipment_id=shipment_id,
            timestamp=now,
            milestone=SettlementMilestone.DELIVERED,
            risk_tier="LOW",
            notes="Shipment delivered",
        ),
    ]

    # TODO: Replace this mock with real ChainPay ledger/context + ChainIQ risk once wired.
    return SettlementStatus(
        shipment_id=shipment_id,
        cb_usd=cb_usd,
        events=events,
        current_milestone=SettlementMilestone.DELIVERED,
        risk_score=32.0,
        settlement_provider=SettlementProvider.INTERNAL_LEDGER,
    )


def _parse_timestamp(events: list[SettlementEvent], milestone: SettlementMilestone) -> Optional[datetime]:
    """Return the first timestamp for a given milestone (or None)."""
    for evt in events:
        if evt.milestone == milestone and evt.timestamp:
            try:
                return datetime.fromisoformat(evt.timestamp)
            except ValueError:
                return None
    return None


def record_settlement_outcome(
    db: Session,
    settlement_status: SettlementStatus,
    *,
    corridor_id: Optional[str] = None,
    payout_policy_version: str = "v1",
    analytics_version: str = "v1",
    cb_usd_loss_realized: Optional[float] = None,
    cb_usd_reserved_initial: Optional[float] = None,
    cb_usd_reserved_unused: Optional[float] = None,
    had_claim: bool = False,
    had_dispute: bool = False,
    settlement_status_label: Optional[str] = None,
    payout_pickup_percent: Optional[float] = None,
    payout_delivered_percent: Optional[float] = None,
    payout_claim_percent: Optional[float] = None,
    claim_window_days: Optional[int] = None,
) -> SettlementOutcome:
    """
    Idempotently record or update a settlement outcome row for a shipment.

    Uniqueness is by (shipment_id, analytics_version, payout_policy_version).
    If a row exists, update its fields; otherwise, create a new one.

    Note: This is not yet invoked by any endpoint; future PAC will call this
    when a settlement lifecycle is finalized (e.g., claim window close).
    """

    existing = (
        db.query(SettlementOutcome)
        .filter(
            SettlementOutcome.shipment_id == settlement_status.shipment_id,
            SettlementOutcome.analytics_version == analytics_version,
            SettlementOutcome.payout_policy_version == payout_policy_version,
        )
        .one_or_none()
    )

    pickup_ts = _parse_timestamp(settlement_status.events, SettlementMilestone.PICKUP)
    delivered_ts = _parse_timestamp(settlement_status.events, SettlementMilestone.DELIVERED)
    claim_close_ts = _parse_timestamp(settlement_status.events, SettlementMilestone.CLAIM_WINDOW)

    # Risk tier initial from first event with risk_tier if present
    risk_tier_initial = None
    for evt in settlement_status.events:
        if evt.risk_tier:
            risk_tier_initial = evt.risk_tier
            break

    outcome_fields = dict(
        shipment_id=settlement_status.shipment_id,
        corridor_id=corridor_id,
        risk_score_initial=settlement_status.risk_score,
        risk_tier_initial=risk_tier_initial,
        payout_pickup_percent=payout_pickup_percent,
        payout_delivered_percent=payout_delivered_percent,
        payout_claim_percent=payout_claim_percent,
        claim_window_days=claim_window_days,
        payout_policy_version=payout_policy_version,
        cb_usd_total=settlement_status.cb_usd.total,
        cb_usd_reserved_initial=cb_usd_reserved_initial if cb_usd_reserved_initial is not None else settlement_status.cb_usd.reserved,
        cb_usd_loss_realized=cb_usd_loss_realized,
        cb_usd_reserved_unused=cb_usd_reserved_unused,
        pickup_timestamp=pickup_ts,
        delivered_timestamp=delivered_ts,
        first_payment_timestamp=None,
        final_payment_timestamp=None,
        claim_window_close_timestamp=claim_close_ts,
        had_claim=had_claim,
        had_dispute=had_dispute,
        settlement_status=settlement_status_label,
        analytics_version=analytics_version,
    )

    if existing:
        for key, value in outcome_fields.items():
            setattr(existing, key, value)
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    outcome = SettlementOutcome(**outcome_fields)
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome
