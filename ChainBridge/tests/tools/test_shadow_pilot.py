import json
from pathlib import Path

import pandas as pd
import pytest

from tools.shadow_pilot.shadow_pilot import process_shipments, run_shadow_pilot


def _build_sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "shipment_id": "S1",
                "cargo_value_usd": 100_000,
                "delivery_timestamp": "2024-01-10",
                "planned_delivery_timestamp": "2024-01-12",
                "pickup_timestamp": "2024-01-05",
                "exception_flag": 0,
                "loss_flag": 0,
                "loss_amount_usd": 0,
                "days_to_payment": 45,
            },
            {
                "shipment_id": "S2",
                "cargo_value_usd": 40_000,
                "delivery_timestamp": "2024-02-15",
                "planned_delivery_timestamp": "2024-02-10",
                "pickup_timestamp": None,
                "exception_flag": 1,
                "loss_flag": 1,
                "loss_amount_usd": 5_000,
                "days_to_payment": 30,
            },
            {
                "shipment_id": "S3",
                "cargo_value_usd": 80_000,
                "delivery_timestamp": "2024-03-05",
                "planned_delivery_timestamp": "2024-03-08",
                "pickup_timestamp": "2024-03-01",
                "exception_flag": 0,
                "loss_flag": 1,
                "loss_amount_usd": 12_000,
                "days_to_payment": None,
            },
        ]
    )


def test_shadow_pilot_happy_path(tmp_path: Path) -> None:
    df = _build_sample_df()
    input_path = tmp_path / "shipments.csv"
    df.to_csv(input_path, index=False)
    out_dir = tmp_path / "out"

    summary = run_shadow_pilot(
        input_path,
        out_dir,
        annual_rate=0.06,
        advance_rate=0.7,
        take_rate=0.01,
    )

    summary_data = json.loads((out_dir / "summary.json").read_text())
    assert summary_data["total_gmv_usd"] == pytest.approx(220_000)
    assert summary_data["financeable_gmv_usd"] == pytest.approx(180_000)
    assert summary_data["financed_gmv_usd"] == pytest.approx(126_000)
    assert summary_data["protocol_revenue_usd"] == pytest.approx(1_260)
    assert summary_data["working_capital_saved_usd"] == pytest.approx(
        932.0547, rel=1e-3
    )
    assert summary_data["losses_avoided_usd"] == pytest.approx(5_000)
    assert summary_data["salvage_revenue_usd"] == pytest.approx(1_600)
    assert summary_data["average_days_pulled_forward"] == pytest.approx(45)

    assert summary.total_shipments == 3

    results_df = pd.read_csv(out_dir / "shadow_results.csv")
    row_s2 = results_df.loc[results_df["shipment_id"] == "S2"].iloc[0]
    assert not bool(row_s2["financeable"])
    assert row_s2["avoided_loss_usd"] == pytest.approx(5_000)


def test_no_financeable_shipments() -> None:
    df = pd.DataFrame(
        [
            {
                "shipment_id": "S4",
                "cargo_value_usd": 10_000,
                "delivery_timestamp": "2024-01-02",
                "planned_delivery_timestamp": "2024-01-01",
                "pickup_timestamp": "2024-01-01",
                "exception_flag": 1,
                "loss_flag": 0,
                "loss_amount_usd": 0,
                "days_to_payment": 10,
            }
        ]
    )

    results_df, summary = process_shipments(
        df,
        annual_rate=0.05,
        advance_rate=0.5,
        take_rate=0.01,
    )

    assert summary.financeable_shipments == 0
    assert summary.financed_gmv_usd == 0
    assert summary.average_days_pulled_forward == 0
    assert results_df["financeable"].tolist() == [False]


def test_missing_required_columns(tmp_path: Path) -> None:
    df = _build_sample_df().drop(columns=["pickup_timestamp"])
    input_path = tmp_path / "missing.csv"
    df.to_csv(input_path, index=False)

    with pytest.raises(ValueError) as excinfo:
        run_shadow_pilot(
            input_path,
            tmp_path / "out",
            annual_rate=0.06,
            advance_rate=0.7,
            take_rate=0.01,
        )

    assert "pickup_timestamp" in str(excinfo.value)
