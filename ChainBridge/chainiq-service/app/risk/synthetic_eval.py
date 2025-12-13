from __future__ import annotations

import argparse
import csv
import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from app.risk.engine import compute_risk_score
from app.risk.schemas import CarrierProfile, LaneProfile, ShipmentFeatures


@dataclass
class SyntheticGridConfig:
    mode: Literal["core", "extended"] = "core"
    max_rows: int | None = None


def generate_scenarios(config: SyntheticGridConfig) -> Iterable[dict]:
    """Generate synthetic shipment scenarios based on the configuration mode."""

    # Define feature grids
    if config.mode == "core":
        # Core mode: Reduced grid to avoid combinatorial explosion
        value_usd_grid = [10_000, 150_000]
        is_hazmat_grid = [False, True]
        is_temp_control_grid = [False]  # Fixed to keep size down
        expected_transit_days_grid = [4]  # Fixed
        iot_alert_count_grid = [0, 2]
        recent_delay_events_grid = [0, 2]
        lane_risk_index_grid = [0.1, 0.8]
        border_crossing_count_grid = [0, 1]
        carrier_incident_rate_90d_grid = [0.0, 0.08]
        carrier_tenure_days_grid = [400]  # Fixed
    else:
        # Extended mode: Full grid
        value_usd_grid = [10_000, 50_000, 150_000, 500_000]
        is_hazmat_grid = [False, True]
        is_temp_control_grid = [False, True]
        expected_transit_days_grid = [2, 6, 12]
        iot_alert_count_grid = [0, 1, 3]
        recent_delay_events_grid = [0, 1, 3]
        lane_risk_index_grid = [0.1, 0.4, 0.8]
        border_crossing_count_grid = [0, 1, 2]
        carrier_incident_rate_90d_grid = [0.0, 0.02, 0.08]
        carrier_tenure_days_grid = [90, 400, 1200]

    # Generate cartesian product
    product = itertools.product(
        value_usd_grid,
        is_hazmat_grid,
        is_temp_control_grid,
        expected_transit_days_grid,
        iot_alert_count_grid,
        recent_delay_events_grid,
        lane_risk_index_grid,
        border_crossing_count_grid,
        carrier_incident_rate_90d_grid,
        carrier_tenure_days_grid,
    )

    for i, (
        value_usd,
        is_hazmat,
        is_temp_control,
        expected_transit_days,
        iot_alert_count,
        recent_delay_events,
        lane_risk_index,
        border_crossing_count,
        carrier_incident_rate_90d,
        carrier_tenure_days,
    ) in enumerate(product):

        # Apply max_rows limit if set
        if config.max_rows is not None and i >= config.max_rows:
            break

        yield {
            "scenario_id": i + 1,
            "origin": "US",
            "destination": "MX" if border_crossing_count > 0 else "US",
            "value_usd": value_usd,
            "is_hazmat": is_hazmat,
            "is_temp_control": is_temp_control,
            "expected_transit_days": expected_transit_days,
            "iot_alert_count": iot_alert_count,
            "recent_delay_events": recent_delay_events,
            "lane_risk_index": lane_risk_index,
            "border_crossing_count": border_crossing_count,
            "carrier_incident_rate_90d": carrier_incident_rate_90d,
            "carrier_tenure_days": carrier_tenure_days,
        }


def evaluate_scenarios(config: SyntheticGridConfig) -> list[dict]:
    """Generate and score scenarios."""
    results = []

    for scenario in generate_scenarios(config):
        # Build domain objects
        shipment = ShipmentFeatures(
            value_usd=scenario["value_usd"],
            is_hazmat=scenario["is_hazmat"],
            is_temp_control=scenario["is_temp_control"],
            expected_transit_days=scenario["expected_transit_days"],
            iot_alert_count=scenario["iot_alert_count"],
            recent_delay_events=scenario["recent_delay_events"],
        )

        carrier = CarrierProfile(
            carrier_id="synthetic-carrier",
            incident_rate_90d=scenario["carrier_incident_rate_90d"],
            tenure_days=scenario["carrier_tenure_days"],
            on_time_rate=0.95,  # Default, not used in v1 scoring yet
        )

        lane = LaneProfile(
            origin=scenario["origin"],
            destination=scenario["destination"],
            lane_risk_index=scenario["lane_risk_index"],
            border_crossing_count=scenario["border_crossing_count"],
        )

        # Score
        result = compute_risk_score(shipment, carrier, lane)

        # Enrich scenario with result
        scenario_result = scenario.copy()
        scenario_result["risk_score"] = result.score
        scenario_result["risk_band"] = result.band.value

        results.append(scenario_result)

    return results


def write_csv(rows: list[dict], output_path: Path) -> None:
    """Write evaluated scenarios to CSV."""
    if not rows:
        return

    fieldnames = [
        "scenario_id",
        "origin",
        "destination",
        "value_usd",
        "is_hazmat",
        "is_temp_control",
        "expected_transit_days",
        "iot_alert_count",
        "recent_delay_events",
        "lane_risk_index",
        "border_crossing_count",
        "carrier_incident_rate_90d",
        "carrier_tenure_days",
        "risk_score",
        "risk_band",
    ]

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_synthetic_eval(mode: str = "core", output_path: str | Path = "synthetic_risk_grid_core.csv", max_rows: int | None = None) -> Path:
    """Main entrypoint to run synthetic evaluation."""
    path = Path(output_path)
    config = SyntheticGridConfig(mode=mode, max_rows=max_rows)  # type: ignore

    print(f"Generating synthetic scenarios (mode={mode})...")
    rows = evaluate_scenarios(config)

    print(f"Scoring complete. Writing {len(rows)} rows to {path}...")
    write_csv(rows, path)

    print("Done.")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run synthetic risk evaluation grid.")
    parser.add_argument("--mode", choices=["core", "extended"], default="core", help="Grid mode")
    parser.add_argument("--out", default="synthetic_risk_grid_core.csv", help="Output CSV path")
    parser.add_argument("--max-rows", type=int, default=None, help="Max rows to generate")

    args = parser.parse_args()

    run_synthetic_eval(mode=args.mode, output_path=args.out, max_rows=args.max_rows)
