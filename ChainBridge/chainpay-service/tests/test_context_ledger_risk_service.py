from __future__ import annotations

from datetime import datetime, timezone

from app.schemas_context_risk import ContextLedgerEvent
from app.services.context_ledger_risk import score_context_event


def _low_risk_event() -> ContextLedgerEvent:
	return ContextLedgerEvent(
		event_id="evt-low-1",
		timestamp=datetime(2025, 1, 1, 10, tzinfo=timezone.utc),
		amount=5_000.0,
		currency="USD",
		corridor_id="US-CA",
		counterparty_id="cp-low",
		counterparty_role="buyer",
		settlement_channel="BANK",
		event_type="SETTLED",
		recent_event_count_24h=2,
		recent_failed_count_7d=0,
		route_notional_7d_usd=10_000.0,
		counterparty_notional_30d_usd=20_000.0,
	)


def _high_risk_event() -> ContextLedgerEvent:
	return ContextLedgerEvent(
		event_id="evt-hi-1",
		timestamp=datetime(2025, 1, 2, 1, tzinfo=timezone.utc),
		amount=300_000.0,
		currency="USD",
		corridor_id="US-BR",
		counterparty_id="cp-hi",
		counterparty_role="seller",
		settlement_channel="XRPL",
		event_type="REVERSAL",
		recent_event_count_24h=50,
		recent_failed_count_7d=7,
		route_notional_7d_usd=2_000_000.0,
		counterparty_notional_30d_usd=4_000_000.0,
	)


def test_score_context_event_low_risk() -> None:
	event = _low_risk_event()
	response = score_context_event(event)

	assert 0.0 <= response.risk_score <= 1.0
	assert 0.0 <= response.anomaly_score <= 1.0
	assert response.risk_band in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
	assert response.trace_id == event.event_id
	assert response.top_features
	assert response.reason_codes


def test_score_context_event_high_risk_reversal() -> None:
	low_response = score_context_event(_low_risk_event())
	high_event = _high_risk_event()
	high_response = score_context_event(high_event)

	assert high_response.risk_score >= low_response.risk_score
	assert high_response.risk_band in {"HIGH", "CRITICAL"}
	# Reversal-driven high-risk events should surface a clear reversal reason.
	assert "REPEATED_REVERSALS_ON_ROUTE" in high_response.reason_codes
	assert high_response.trace_id == high_event.event_id
