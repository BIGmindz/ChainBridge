from __future__ import annotations

import pytest

from app.services.payout_engine import (
    PayoutConfigError,
    get_payout_schedule,
)


def test_low_risk_uses_low_tier_schedule() -> None:
    schedule = get_payout_schedule("USD_MXN", risk_score=0.1)
    assert schedule.risk_tier == "LOW"
    assert abs(schedule.total_percentage() - 1.0) < 1e-6
    assert schedule.pickup_percent == pytest.approx(0.20)
    assert schedule.delivered_percent == pytest.approx(0.70)
    assert schedule.claim_percent == pytest.approx(0.10)
    assert schedule.claim_window_days == 3
    assert schedule.requires_manual_review is False


def test_medium_risk_schedule_and_claim_window() -> None:
    schedule = get_payout_schedule("USD_MXN", risk_score=0.5)
    assert schedule.risk_tier == "MEDIUM"
    assert abs(schedule.total_percentage() - 1.0) < 1e-6
    assert schedule.claim_window_days == 5


def test_high_risk_requires_review_for_final_tranche() -> None:
    schedule = get_payout_schedule("USD_MXN", risk_score=0.7)
    assert schedule.risk_tier == "HIGH"
    assert schedule.requires_manual_review is True
    assert schedule.claim_window_days == 7


def test_critical_risk_freezes_payouts() -> None:
    schedule = get_payout_schedule("USD_MXN", risk_score=0.9)
    assert schedule.risk_tier == "CRITICAL"
    assert schedule.freeze_all_payouts is True
    assert schedule.requires_manual_review is True
    assert schedule.pickup_percent == pytest.approx(0.0)
    assert schedule.delivered_percent == pytest.approx(0.0)
    assert schedule.claim_percent == pytest.approx(1.0)


def test_unknown_corridor_raises() -> None:
    with pytest.raises(PayoutConfigError):
        get_payout_schedule("UNKNOWN", risk_score=0.1)


def test_score_to_tier_boundary_inclusive_upper() -> None:
    schedule = get_payout_schedule("USD_MXN", risk_score=1.0)
    assert schedule.risk_tier == "CRITICAL"
