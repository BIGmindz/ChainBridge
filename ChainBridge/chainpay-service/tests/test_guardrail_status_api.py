from datetime import datetime, timedelta, timezone

from app.models_analytics import SettlementOutcome
from app.services.analytics_service import DEFAULT_POLICY, USD_MXN_CORRIDOR_ID


def test_guardrails_empty_db(client):
    resp = client.get("/api/chainpay/guardrails/usd-mxn")
    assert resp.status_code == 200
    data = resp.json()
    assert data["corridor_id"] == USD_MXN_CORRIDOR_ID
    assert data["payout_policy_version"] == DEFAULT_POLICY
    # With no data we expect a benign GREEN / empty tiers snapshot
    assert data["overall_state"] == "GREEN"
    assert data["per_tier"] == []
    assert data["overall_reasons"] == []
    assert data["overall_summary"].startswith("GREEN")


def test_guardrails_green_state(db_session, client):
    delivered = datetime(2024, 1, 1, tzinfo=timezone.utc)

    row = SettlementOutcome(
        shipment_id="SHIP-GREEN",
        corridor_id=USD_MXN_CORRIDOR_ID,
        payout_policy_version=DEFAULT_POLICY,
        analytics_version="v1",
        risk_tier_initial="LOW",
        cb_usd_total=1000.0,
        cb_usd_reserved_initial=400.0,
        cb_usd_loss_realized=5.0,  # 0.5% loss rate
        cb_usd_reserved_unused=100.0,  # 25% unused reserve
        delivered_timestamp=delivered,
        first_payment_timestamp=delivered + timedelta(days=2),
        final_payment_timestamp=delivered + timedelta(days=3),
        had_claim=False,
    )

    db_session.add(row)
    db_session.commit()

    resp = client.get("/api/chainpay/guardrails/usd-mxn")
    assert resp.status_code == 200
    data = resp.json()

    assert data["overall_state"] == "GREEN"
    assert data["overall_reasons"] == []
    assert data["overall_summary"] == "GREEN: all tiers within guardrails."
    assert len(data["per_tier"]) == 1
    tier = data["per_tier"][0]
    assert tier["tier"] == "LOW"
    assert tier["state"] == "GREEN"
    assert tier["loss_rate"] < 0.02
    assert tier["cash_sla_breach_rate"] == 0.0
    assert tier["d2_p95_days"] <= 3.0
    assert tier["unused_reserve_ratio"] < 0.5
    assert tier["reasons"] == []
    assert tier["summary"] == "GREEN: within guardrails."


def test_guardrails_red_state(db_session, client):
    delivered = datetime(2024, 1, 1, tzinfo=timezone.utc)

    row = SettlementOutcome(
        shipment_id="SHIP-RED",
        corridor_id=USD_MXN_CORRIDOR_ID,
        payout_policy_version=DEFAULT_POLICY,
        analytics_version="v1",
        risk_tier_initial="LOW",
        cb_usd_total=1000.0,
        cb_usd_reserved_initial=300.0,
        cb_usd_loss_realized=120.0,  # 12% loss rate -> RED
        cb_usd_reserved_unused=300.0,  # 100% unused -> RED threshold
        delivered_timestamp=delivered,
        first_payment_timestamp=delivered + timedelta(days=2),
        final_payment_timestamp=delivered + timedelta(days=12),  # p95 D2 breach
        had_claim=True,
    )

    db_session.add(row)
    db_session.commit()

    resp = client.get("/api/chainpay/guardrails/usd-mxn")
    assert resp.status_code == 200
    data = resp.json()

    assert data["overall_state"] == "RED"
    assert data["overall_reasons"] == [
        "LOSS_RATE_RED",
        "CASH_SLA_BREACH_RED",
        "D2_P95_RED",
        "UNUSED_RESERVE_RED",
    ]
    assert data["overall_summary"] == "RED: breaches present in one or more tiers."
    assert len(data["per_tier"]) == 1
    tier = data["per_tier"][0]
    assert tier["tier"] == "LOW"
    assert tier["state"] == "RED"
    assert tier["loss_rate"] >= 0.05
    assert tier["d2_p95_days"] >= 10.0
    assert tier["unused_reserve_ratio"] >= 0.8
    assert tier["reasons"] == [
        "LOSS_RATE_RED",
        "CASH_SLA_BREACH_RED",
        "D2_P95_RED",
        "UNUSED_RESERVE_RED",
    ]
    assert tier["summary"] == "RED: LOSS_RATE_RED, CASH_SLA_BREACH_RED, D2_P95_RED, UNUSED_RESERVE_RED."

"""
If desired, an AMBER scenario can be added by seeding values between the amber/red
bands. For now we cover empty/green/red to keep CI fast and deterministic.
"""
