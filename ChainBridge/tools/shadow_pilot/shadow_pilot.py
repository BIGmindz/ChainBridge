"""Shadow pilot CLI and finance simulation utilities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List, Tuple

import pandas as pd
from pydantic import ValidationError

from .schemas import ShadowSummary, ShipmentResult, ShipmentRow

# Conditional import for path security (may not be available in standalone mode)
try:
    from core.path_security import PathTraversalError, validate_path_within_base

    _HAS_PATH_SECURITY = True
except ImportError:
    _HAS_PATH_SECURITY = False
    PathTraversalError = ValueError  # type: ignore

REQUIRED_COLUMNS = {
    "shipment_id",
    "cargo_value_usd",
    "delivery_timestamp",
    "planned_delivery_timestamp",
    "pickup_timestamp",
    "exception_flag",
    "loss_flag",
    "loss_amount_usd",
}

OPTIONAL_COLUMNS = {"days_to_payment"}

DEFAULT_DAYS_TO_PAYMENT = 45.0


def compute_event_truth_score(row: ShipmentRow) -> float:
    """Compute a simple truth score in the range [0.0, 1.0]."""

    score = 0.0
    if row.delivery_timestamp <= row.planned_delivery_timestamp:
        score += 0.4
    if row.pickup_timestamp is not None:
        score += 0.2
    if row.exception_flag == 0:
        score += 0.2
    if row.loss_flag == 0:
        score += 0.2
    return max(0.0, min(score, 1.0))


def is_financeable(
    row: ShipmentRow,
    truth_score: float,
    min_value: float = 50000.0,
    min_truth: float = 0.7,
) -> bool:
    """Determine if a shipment is financeable."""

    return row.cargo_value_usd >= min_value and truth_score >= min_truth


def _nan_to_none(value):
    return None if pd.isna(value) else value


def _prepare_shipments(df: pd.DataFrame) -> List[ShipmentRow]:
    shipments: List[ShipmentRow] = []
    for raw in df.to_dict(orient="records"):
        normalized = {key: _nan_to_none(value) for key, value in raw.items()}
        try:
            shipments.append(ShipmentRow(**normalized))
        except ValidationError as exc:
            shipment_id = normalized.get("shipment_id", "<unknown>")
            raise ValueError(f"Invalid data for shipment {shipment_id}: {exc}") from exc
    return shipments


def _compute_results(
    shipments: Iterable[ShipmentRow],
    *,
    annual_rate: float,
    advance_rate: float,
    take_rate: float,
    min_value: float,
    min_truth: float,
) -> Tuple[List[ShipmentResult], ShadowSummary]:
    results: List[ShipmentResult] = []

    for shipment in shipments:
        truth_score = compute_event_truth_score(shipment)
        financeable = is_financeable(shipment, truth_score, min_value=min_value, min_truth=min_truth)
        actual_days_to_payment = shipment.days_to_payment if shipment.days_to_payment is not None else DEFAULT_DAYS_TO_PAYMENT
        days_pulled_forward = max(actual_days_to_payment, 0.0)
        financed_amount = shipment.cargo_value_usd * advance_rate if financeable else 0.0
        working_capital_saved = financed_amount * annual_rate * (days_pulled_forward / 365.0) if financeable else 0.0
        protocol_revenue = financed_amount * take_rate if financeable else 0.0
        avoided_loss = shipment.loss_amount_usd if shipment.loss_flag == 1 and truth_score < min_truth else 0.0
        salvage_revenue = shipment.cargo_value_usd * 0.2 * 0.1 if shipment.loss_flag == 1 and truth_score >= min_truth else 0.0

        result = ShipmentResult(
            shipment_id=shipment.shipment_id,
            cargo_value_usd=shipment.cargo_value_usd,
            delivery_timestamp=shipment.delivery_timestamp,
            planned_delivery_timestamp=shipment.planned_delivery_timestamp,
            pickup_timestamp=shipment.pickup_timestamp,
            corridor=shipment.corridor,
            mode=shipment.mode,
            customer_segment=shipment.customer_segment,
            exception_flag=shipment.exception_flag,
            loss_flag=shipment.loss_flag,
            loss_amount_usd=shipment.loss_amount_usd,
            actual_days_to_payment=actual_days_to_payment,
            event_truth_score=truth_score,
            financeable=financeable,
            financed_amount_usd=financed_amount,
            days_pulled_forward=days_pulled_forward,
            working_capital_saved_usd=working_capital_saved,
            protocol_revenue_usd=protocol_revenue,
            avoided_loss_usd=avoided_loss,
            salvage_revenue_usd=salvage_revenue,
        )
        results.append(result)

    summary = _summarize(results)
    return results, summary


def process_shipments(
    df: pd.DataFrame,
    *,
    annual_rate: float,
    advance_rate: float,
    take_rate: float,
    min_value: float = 50000.0,
    min_truth: float = 0.7,
) -> Tuple[pd.DataFrame, ShadowSummary]:
    """Run the full shadow pilot calculation on a dataframe of shipments."""

    shipments = _prepare_shipments(df)
    results, summary = _compute_results(
        shipments,
        annual_rate=annual_rate,
        advance_rate=advance_rate,
        take_rate=take_rate,
        min_value=min_value,
        min_truth=min_truth,
    )
    results_df = pd.DataFrame([result.model_dump() for result in results])
    return results_df, summary


def _summarize(results: Iterable[ShipmentResult]) -> ShadowSummary:
    results_list = list(results)
    total_shipments = len(results_list)
    financeable = [r for r in results_list if r.financeable]
    financeable_count = len(financeable)

    total_gmv_usd = sum(r.cargo_value_usd for r in results_list)
    financeable_gmv_usd = sum(r.cargo_value_usd for r in financeable)
    financed_gmv_usd = sum(r.financed_amount_usd for r in financeable)
    protocol_revenue_usd = sum(r.protocol_revenue_usd for r in results_list)
    working_capital_saved_usd = sum(r.working_capital_saved_usd for r in results_list)
    losses_avoided_usd = sum(r.avoided_loss_usd for r in results_list)
    salvage_revenue_usd = sum(r.salvage_revenue_usd for r in results_list)
    average_days_pulled_forward = sum(r.days_pulled_forward for r in financeable) / financeable_count if financeable_count else 0.0

    return ShadowSummary(
        total_shipments=total_shipments,
        financeable_shipments=financeable_count,
        total_gmv_usd=total_gmv_usd,
        financeable_gmv_usd=financeable_gmv_usd,
        financed_gmv_usd=financed_gmv_usd,
        protocol_revenue_usd=protocol_revenue_usd,
        working_capital_saved_usd=working_capital_saved_usd,
        losses_avoided_usd=losses_avoided_usd,
        salvage_revenue_usd=salvage_revenue_usd,
        average_days_pulled_forward=average_days_pulled_forward,
    )


def _validate_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        missing_fmt = ", ".join(sorted(missing))
        raise ValueError(f"Input missing required columns: {missing_fmt}")
    for optional in OPTIONAL_COLUMNS:
        if optional not in df.columns:
            df[optional] = pd.NA
    return df


def run_shadow_pilot(
    input_path: Path | str,
    out_dir: Path | str,
    *,
    annual_rate: float,
    advance_rate: float,
    take_rate: float,
    min_value: float = 50000.0,
    min_truth: float = 0.7,
    allowed_base: Path | str | None = None,
) -> ShadowSummary:
    """
    Entry point for running the simulation and writing outputs.

    Args:
        input_path: Path to input CSV file
        out_dir: Directory for output files
        annual_rate: Annual financing rate
        advance_rate: Advance rate for financed amount
        take_rate: Protocol take rate
        min_value: Minimum cargo value for financeability
        min_truth: Minimum truth score for financeability
        allowed_base: If provided, validate paths are within this directory
    """
    # Security: Validate paths if security module available and base specified
    if _HAS_PATH_SECURITY and allowed_base:
        base = Path(allowed_base).resolve()
        validate_path_within_base(input_path, base)
        validate_path_within_base(out_dir, base)

    summary, _, results_df = run_shadow_pilot_from_csv(
        Path(input_path),
        annual_rate=annual_rate,
        advance_rate=advance_rate,
        take_rate=take_rate,
        min_value=min_value,
        min_truth=min_truth,
        as_dataframe=True,
    )

    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)

    results_path = destination / "shadow_results.csv"
    summary_path = destination / "summary.json"

    results_df.to_csv(results_path, index=False)
    summary_path.write_text(json.dumps(summary.model_dump(), indent=2))

    return summary


def run_shadow_pilot_from_csv(
    csv_path: Path | str,
    *,
    annual_rate: float,
    advance_rate: float,
    take_rate: float,
    min_value: float = 50000.0,
    min_truth: float = 0.7,
    as_dataframe: bool = False,
) -> Tuple[ShadowSummary, List[ShipmentResult], pd.DataFrame | None]:
    """Programmatic entrypoint: load CSV, compute shipment results and summary."""

    input_file = Path(csv_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    df = pd.read_csv(input_file)
    df = _validate_columns(df.copy())
    shipments = _prepare_shipments(df)
    results, summary = _compute_results(
        shipments,
        annual_rate=annual_rate,
        advance_rate=advance_rate,
        take_rate=take_rate,
        min_value=min_value,
        min_truth=min_truth,
    )

    results_df = pd.DataFrame([result.model_dump() for result in results]) if as_dataframe else None
    return summary, results, results_df


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shadow pilot finance simulator")
    parser.add_argument("--input", required=True, help="Path to shipments_history.csv")
    parser.add_argument("--out-dir", required=True, help="Directory for outputs")
    parser.add_argument(
        "--annual_rate",
        type=float,
        required=True,
        help="Annual rate (e.g. 0.06)",
    )
    parser.add_argument(
        "--advance_rate",
        type=float,
        required=True,
        help="Advance rate (e.g. 0.7)",
    )
    parser.add_argument(
        "--take_rate",
        type=float,
        required=True,
        help="Protocol take rate (e.g. 0.01)",
    )
    parser.add_argument(
        "--min_value",
        type=float,
        default=50000.0,
        help="Minimum cargo value for financeability",
    )
    parser.add_argument(
        "--min_truth",
        type=float,
        default=0.7,
        help="Minimum truth score for financeability",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    run_shadow_pilot(
        args.input,
        args.out_dir,
        annual_rate=args.annual_rate,
        advance_rate=args.advance_rate,
        take_rate=args.take_rate,
        min_value=args.min_value,
        min_truth=args.min_truth,
    )


if __name__ == "__main__":
    main()
