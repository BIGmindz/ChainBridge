from __future__ import annotations

import pandas as pd

from api.shadow_pilot.core import run_shadow_pilot_from_dataframe


def _make_minimal_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "shipment_id": "SHIP-1",
                "corridor": "US-MX",
                "mode": "FCL",
                "customer_segment": "SME",
                "cargo_value": 100_000,
                "transit_days": 30,
                "days_to_payment": 60,
                "max_temp_deviation": 1.0,
                "exception_flag": 0,
                "loss_flag": 0,
            },
            {
                "shipment_id": "SHIP-2",
                "corridor": "US-EU",
                "mode": "AIR",
                "customer_segment": "Enterprise",
                "cargo_value": 40_000,  # below financeable threshold
                "transit_days": 15,
                "days_to_payment": 45,
                "max_temp_deviation": 3.0,
                "exception_flag": 0,
                "loss_flag": 0,
            },
        ]
    )


def test_run_shadow_pilot_from_dataframe_basic_shapes():
    df = _make_minimal_df()

    summary, shipments = run_shadow_pilot_from_dataframe(
        df,
        run_id="test_run_1",
        prospect_name="Test Prospect",
        period_months=12,
    )

    assert summary.run_id == "test_run_1"
    assert summary.prospect_name == "Test Prospect"
    assert summary.period_months == 12
    assert summary.total_gmv_usd == 140_000
    assert summary.shipments_evaluated == 2
    assert len(shipments) == 2


def test_financeability_thresholds_and_metrics():
    df = _make_minimal_df()

    summary, shipments = run_shadow_pilot_from_dataframe(
        df,
        run_id="test_run_2",
        prospect_name="Threshold Prospect",
        period_months=12,
    )

    s1 = next(s for s in shipments if s.shipment_id == "SHIP-1")
    s2 = next(s for s in shipments if s.shipment_id == "SHIP-2")

    assert s1.eligible_for_finance is True
    assert s1.financed_amount_usd > 0
    assert s1.days_pulled_forward >= 0
    assert s1.protocol_revenue_usd >= 0

    assert s2.eligible_for_finance is False
    assert s2.financed_amount_usd == 0
    assert s2.protocol_revenue_usd == 0

    assert summary.financeable_gmv_usd == 100_000
    assert summary.shipments_financeable == 1


def test_loss_and_salvage_model_is_stable():
    df = pd.DataFrame(
        [
            {
                "shipment_id": "LOSS-1",
                "corridor": "US-MX",
                "mode": "FCL",
                "customer_segment": "SME",
                "cargo_value": 80_000,
                "transit_days": 30,
                "days_to_payment": 60,
                "max_temp_deviation": 9.0,  # big deviation → low truth score
                "exception_flag": 1,
                "loss_flag": 1,
                "loss_amount_usd": 80_000,
            }
        ]
    )

    summary, shipments = run_shadow_pilot_from_dataframe(
        df,
        run_id="test_run_loss",
        prospect_name="Loss Prospect",
        period_months=12,
    )

    s = shipments[0]

    assert summary.total_gmv_usd == 80_000
    assert s.cargo_value_usd == 80_000
    assert 0.0 <= s.event_truth_score <= 1.0
    assert summary.losses_avoided_usd >= 0
    assert summary.salvage_revenue_usd >= 0
