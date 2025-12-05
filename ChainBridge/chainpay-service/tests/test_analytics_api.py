from datetime import datetime, timedelta, timezone

from app.models_analytics import SettlementOutcome
from app.services.analytics_service import DEFAULT_POLICY, USD_MXN_CORRIDOR_ID


def test_analytics_empty_snapshot(client):
    resp = client.get("/api/chainpay/analytics/usd-mxn")
    assert resp.status_code == 200
    data = resp.json()
    assert data["corridor_id"] == USD_MXN_CORRIDOR_ID
    assert data["payout_policy_version"] == DEFAULT_POLICY
    assert data["settlement_provider"] == "INTERNAL_LEDGER"
    assert data["tier_health"] == []
    assert data["days_to_cash"] == []
    assert data["sla"] == []


def test_analytics_with_data(db_session, client):
    delivered = datetime(2024, 1, 1, tzinfo=timezone.utc)

    row1 = SettlementOutcome(
        shipment_id="SHIP-200",
        corridor_id=USD_MXN_CORRIDOR_ID,
        payout_policy_version=DEFAULT_POLICY,
        analytics_version="v1",
        risk_tier_initial="LOW",
        cb_usd_total=1000.0,
        cb_usd_reserved_initial=300.0,
        cb_usd_loss_realized=50.0,
        cb_usd_reserved_unused=80.0,
        delivered_timestamp=delivered,
        first_payment_timestamp=delivered + timedelta(days=2),
        final_payment_timestamp=delivered + timedelta(days=5),
        had_claim=True,
    )

    row2 = SettlementOutcome(
        shipment_id="SHIP-201",
        corridor_id=USD_MXN_CORRIDOR_ID,
        payout_policy_version=DEFAULT_POLICY,
        analytics_version="v1",
        risk_tier_initial="LOW",
        cb_usd_total=500.0,
        cb_usd_reserved_initial=200.0,
        cb_usd_loss_realized=20.0,
        cb_usd_reserved_unused=50.0,
        delivered_timestamp=delivered,
        first_payment_timestamp=delivered + timedelta(days=3),
        final_payment_timestamp=delivered + timedelta(days=6),
        had_claim=False,
    )

    db_session.add_all([row1, row2])
    db_session.commit()

    resp = client.get("/api/chainpay/analytics/usd-mxn")
    assert resp.status_code == 200
    data = resp.json()

    assert data["corridor_id"] == USD_MXN_CORRIDOR_ID
    assert data["payout_policy_version"] == DEFAULT_POLICY
    assert data["settlement_provider"] == "INTERNAL_LEDGER"

    tier_health = data["tier_health"]
    assert len(tier_health) == 1
    th = tier_health[0]
    assert th["tier"] == "LOW"
    assert th["shipment_count"] == 2
    assert abs(th["loss_rate"] - (70.0 / 1500.0)) < 1e-6
    assert abs(th["reserve_utilization"] - (70.0 / 500.0)) < 1e-6
    assert abs(th["unused_reserve_ratio"] - (130.0 / 500.0)) < 1e-6

    days_to_cash = data["days_to_cash"]
    assert len(days_to_cash) == 1
    dtc = days_to_cash[0]
    assert dtc["tier"] == "LOW"
    assert dtc["corridor_id"] == USD_MXN_CORRIDOR_ID
    assert abs(dtc["median_days_to_first_cash"] - 2.5) < 1e-6
    assert abs(dtc["p95_days_to_first_cash"] - 3.0) < 1e-6
    assert abs(dtc["median_days_to_final_cash"] - 5.5) < 1e-6
    assert abs(dtc["p95_days_to_final_cash"] - 6.0) < 1e-6

    sla = data["sla"]
    assert len(sla) == 1
    sla_entry = sla[0]
    assert sla_entry["tier"] == "LOW"
    assert sla_entry["total_reviews"] == 1  # had_claim=True counted
    assert sla_entry["claim_review_sla_breach_rate"] == 0.0
    assert sla_entry["manual_review_sla_breach_rate"] == 0.0
    assert sla_entry["cash_breach_count"] == 1
    assert sla_entry["sample_size"] == 2
    assert abs(sla_entry["cash_breach_rate"] - 0.5) < 1e-6
