"""Focused unit tests for payment release helpers and InternalLedgerRail."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

import pytest
from sqlalchemy.orm import Session

from app.models import MilestoneSettlement, PaymentIntent, PaymentStatus
from app.payment_rails import (
    InternalLedgerRail,
    ReleaseStrategy,
    SettlementProvider,
    SettlementResult,
    _safe_get,
    compute_milestone_release,
    get_release_delay_hours,
    should_release_now,
)

MilestoneFactory = Callable[..., MilestoneSettlement]


@pytest.fixture
def make_milestone(db_session: Session, payment_intent_low_risk: PaymentIntent) -> MilestoneFactory:
    def _create(**overrides):
        event_type = overrides.get("event_type", "POD_CONFIRMED")
        data = {
            "payment_intent_id": overrides.get("payment_intent_id", payment_intent_low_risk.id),
            "event_type": event_type,
            "amount": overrides.get("amount", 100.0),
            "currency": overrides.get("currency", "USD"),
            "status": overrides.get("status", PaymentStatus.PENDING),
            "shipment_reference": overrides.get("shipment_reference", f"SHP-{event_type}"),
            "schedule_item_id": overrides.get("schedule_item_id"),
            "milestone_identifier": overrides.get("milestone_identifier"),
        }

        milestone = MilestoneSettlement(**data)
        db_session.add(milestone)
        db_session.commit()
        db_session.refresh(milestone)
        return milestone

    return _create


class TestReleaseStrategyDecisions:
    """Coverage for should_release_now decision matrix."""

    @pytest.mark.parametrize(
        "risk_score,event_type,expected",
        [
            (0.1, "PICKUP_CONFIRMED", ReleaseStrategy.IMMEDIATE),
            (0.5, "POD_CONFIRMED", ReleaseStrategy.IMMEDIATE),
            (0.5, "CLAIM_WINDOW_CLOSED", ReleaseStrategy.DELAYED),
            (0.9, "PICKUP_CONFIRMED", ReleaseStrategy.MANUAL_REVIEW),
            (0.9, "CLAIM_WINDOW_CLOSED", ReleaseStrategy.MANUAL_REVIEW),
        ],
    )
    def test_should_release_now_matrix(self, risk_score: float, event_type: str, expected: ReleaseStrategy) -> None:
        assert should_release_now(risk_score, event_type) == expected


class TestReleaseDelayHours:
    """Ensure release delay helper maps ReleaseStrategy values to delays."""

    @pytest.mark.parametrize(
        "risk_score,event_type,strategy,expected_delay",
        [
            (0.2, "PICKUP_CONFIRMED", ReleaseStrategy.IMMEDIATE, None),
            (0.5, "CLAIM_WINDOW_CLOSED", ReleaseStrategy.DELAYED, 5 * 24),
            (0.9, "POD_CONFIRMED", ReleaseStrategy.MANUAL_REVIEW, None),
            (0.9, "PICKUP_CONFIRMED", ReleaseStrategy.PENDING, None),
        ],
    )
    def test_get_release_delay_hours(self, risk_score: float, event_type: str, strategy: ReleaseStrategy, expected_delay: int | None) -> None:
        assert get_release_delay_hours(risk_score, event_type, strategy) == expected_delay


class TestMilestoneReleasePlan:
    """Validate compute_milestone_release helper follows the config-driven schedule."""

    @pytest.mark.parametrize(
        "risk_band,event_type,expected_pct,expected_strategy,expected_delay",
        [
            ("LOW", "pickup_confirmed", 20.0, ReleaseStrategy.IMMEDIATE, None),
            ("LOW", "mid_transit_verified", 70.0, ReleaseStrategy.IMMEDIATE, None),
            ("LOW", "settlement_released", 10.0, ReleaseStrategy.DELAYED, 3 * 24),
            ("MEDIUM", "pickup_confirmed", 15.0, ReleaseStrategy.IMMEDIATE, None),
            ("MEDIUM", "settlement_released", 20.0, ReleaseStrategy.DELAYED, 5 * 24),
            ("HIGH", "mid_transit_verified", 60.0, ReleaseStrategy.IMMEDIATE, None),
            ("HIGH", "settlement_released", 30.0, ReleaseStrategy.MANUAL_REVIEW, None),
            ("CRITICAL", "pickup_confirmed", 0.0, ReleaseStrategy.MANUAL_REVIEW, None),
            ("CRITICAL", "settlement_released", 100.0, ReleaseStrategy.MANUAL_REVIEW, None),
        ],
    )
    def test_release_plan_matches_matrix(
        self,
        risk_band: str,
        event_type: str,
        expected_pct: float,
        expected_strategy: ReleaseStrategy,
        expected_delay: int | None,
    ) -> None:
        plan = compute_milestone_release(
            risk_band=risk_band,
            event_type=event_type,
            base_total_amount=1000.0,
        )
        assert plan.event_type == event_type
        assert plan.risk_band == risk_band
        assert plan.percentage == expected_pct
        assert plan.release_amount == pytest.approx(1000.0 * expected_pct / 100.0)
        assert plan.strategy == expected_strategy
        assert plan.delay_hours == expected_delay

    def test_alias_event_types_map_to_final_tranche(self) -> None:
        plan = compute_milestone_release(
            risk_band="MEDIUM",
            event_type="CLAIM_WINDOW_CLOSED",
            base_total_amount=5000.0,
        )
        assert plan.event_type == "settlement_released"
        assert plan.percentage == 20.0

    def test_non_milestone_events_return_pending_plan(self) -> None:
        plan = compute_milestone_release(
            risk_band="LOW",
            event_type="context_created",
            base_total_amount=2500.0,
        )
        assert plan.strategy == ReleaseStrategy.PENDING
        assert plan.percentage == 0.0
        assert plan.release_amount == 0.0


class TestSafeGetHelper:
    """Validate fallback behaviour for _safe_get utility."""

    def test_safe_get_from_dict(self) -> None:
        assert _safe_get({"value": 12}, "value") == 12

    def test_safe_get_missing_key_returns_default(self) -> None:
        assert _safe_get({}, "value", default=99) == 99

    def test_safe_get_accepts_numeric(self) -> None:
        assert _safe_get(15.5, "value") == 15.5

    def test_safe_get_handles_non_numeric_string(self) -> None:
        assert _safe_get("nan", "value", default=-1) == -1


class TestInternalLedgerRailSettlements:
    """Hit success and failure paths for InternalLedgerRail."""

    def test_successful_settlement_updates_milestone(
        self,
        db_session: Session,
        make_milestone: MilestoneFactory,
    ) -> None:
        milestone = make_milestone(event_type="POD_CONFIRMED_SUCCESS")
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(
            milestone_id=milestone.id,
            amount=150.0,
            currency="USD",
            recipient_id="wallet-123",
        )

        assert isinstance(result, SettlementResult)
        assert result.success is True
        assert result.provider == SettlementProvider.INTERNAL_LEDGER
        assert result.reference_id and result.reference_id.endswith(f":{milestone.id}")
        assert isinstance(result.released_at, datetime)

        db_session.refresh(milestone)
        assert milestone.status == PaymentStatus.APPROVED
        assert milestone.reference == result.reference_id

    def test_process_settlement_missing_milestone(self, db_session: Session) -> None:
        rail = InternalLedgerRail(db_session)

        result = rail.process_settlement(milestone_id=9999, amount=10.0, currency="USD")

        assert result.success is False
        assert "not found" in (result.error or "")
        assert result.provider == SettlementProvider.INTERNAL_LEDGER

    def test_settlement_preserves_existing_identifiers(
        self,
        db_session: Session,
        make_milestone: MilestoneFactory,
    ) -> None:
        milestone = make_milestone(
            event_type="CLAIM_WINDOW_CLOSED",
            shipment_reference="SHP-LOCK",
            milestone_identifier="SHP-LOCK-M2",
        )

        rail = InternalLedgerRail(db_session)
        result = rail.process_settlement(milestone_id=milestone.id, amount=25.0, currency="USD")

        assert result.success is True
        db_session.refresh(milestone)
        assert milestone.milestone_identifier == "SHP-LOCK-M2"
        assert milestone.shipment_reference == "SHP-LOCK"
