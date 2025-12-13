from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas_context_risk import ContextLedgerEvent, RiskScoreResponse


def test_context_ledger_event_valid_payload() -> None:
    event = ContextLedgerEvent(
        event_id="evt-123",
        timestamp=datetime(2025, 1, 1, 12, tzinfo=timezone.utc),
        amount=12_500.25,
        currency="USD",
        corridor_id="US-CA",
        counterparty_id="carrier-22",
        counterparty_role="carrier",
        settlement_channel="BANK",
        event_type="SETTLED",
        recent_event_count_24h=3,
        recent_failed_count_7d=1,
        route_notional_7d_usd=150_000.0,
        counterparty_notional_30d_usd=600_000.0,
    )

    payload = event.model_dump()
    assert payload["event_id"] == "evt-123"
    assert payload["amount"] == 12_500.25
    assert payload["recent_event_count_24h"] == 3
    assert payload["counterparty_notional_30d_usd"] == 600_000.0


def test_context_ledger_event_rejects_missing_amount() -> None:
    with pytest.raises(ValidationError):
        ContextLedgerEvent(
            event_id="evt-missing-amount",
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            currency="USD",
            corridor_id="US-CA",
            counterparty_id="carrier-22",
            counterparty_role="carrier",
            settlement_channel="BANK",
            event_type="PENDING",
        )


def test_context_ledger_event_rejects_invalid_role() -> None:
    with pytest.raises(ValidationError):
        ContextLedgerEvent(
            event_id="evt-invalid-role",
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            amount=1.0,
            currency="USD",
            corridor_id="US-CA",
            counterparty_id="carrier-22",
            counterparty_role="unknown",  # type: ignore[arg-type]
            settlement_channel="BANK",
            event_type="SETTLED",
        )


def test_risk_score_response_serialization() -> None:
    response = RiskScoreResponse(
        risk_score=0.42,
        anomaly_score=0.15,
        risk_band="MEDIUM",
        top_features=["amount_log", "risk_score"],
        reason_codes=["BASELINE_MONITORING"],
        trace_id="evt-123",
    )

    data = response.model_dump()
    assert data["risk_score"] == 0.42
    assert data["risk_band"] == "MEDIUM"
    assert data["version"] == "pink-01"


def test_risk_score_response_rejects_invalid_band() -> None:
    with pytest.raises(ValidationError):
        RiskScoreResponse(
            risk_score=0.9,
            anomaly_score=0.4,
            risk_band="VERY_HIGH",  # type: ignore[arg-type]
            top_features=[],
            reason_codes=[],
            trace_id="evt-999",
        )
