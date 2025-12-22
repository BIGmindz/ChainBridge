"""Standalone Shadow Pilot engine for DataFrame inputs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd

TRADITIONAL_APY = 0.09
CHAIN_BRIDGE_APY = 0.05
LTV_RATIO = 0.70
SALVAGE_RECOVERY_RATE = 0.40


@dataclass
class ShadowPilotShipmentResult:
    run_id: str
    shipment_id: str
    corridor: str | None
    mode: str | None
    customer_segment: str | None
    cargo_value_usd: float
    event_truth_score: float
    eligible_for_finance: bool
    financed_amount_usd: float
    days_pulled_forward: int
    wc_saved_usd: float
    protocol_revenue_usd: float
    avoided_loss_usd: float
    salvage_revenue_usd: float
    exception_flag: int
    loss_flag: int


@dataclass
class ShadowPilotSummary:
    run_id: str
    prospect_name: str
    period_months: int
    total_gmv_usd: float
    financeable_gmv_usd: float
    financed_gmv_usd: float
    protocol_revenue_usd: float
    working_capital_saved_usd: float
    losses_avoided_usd: float
    salvage_revenue_usd: float
    average_days_pulled_forward: float
    shipments_evaluated: int
    shipments_financeable: int
    input_filename: str | None = None
    notes: str | None = None


def _compute_event_truth_score(row: pd.Series) -> float:
    score = 1.0
    temp = row.get("max_temp_deviation")
    if temp is not None and not pd.isna(temp):
        if temp <= 2:
            pass
        elif temp >= 8:
            score -= 0.5
        else:
            score -= 0.5 * ((float(temp) - 2) / (8 - 2))

    exception_flag = row.get("exception_flag")
    if exception_flag is not None and int(exception_flag) == 1:
        score -= 0.2

    loss_flag = row.get("loss_flag")
    if loss_flag is not None and int(loss_flag) == 1:
        score -= 0.3

    return max(0.0, min(1.0, float(score)))


def run_shadow_pilot_from_dataframe(
    df: pd.DataFrame,
    *,
    run_id: str,
    prospect_name: str,
    period_months: int,
    input_filename: str | None = None,
    notes: str | None = None,
    annual_rate: float = CHAIN_BRIDGE_APY,
    advance_rate: float = LTV_RATIO,
    take_rate: float = 0.01,
) -> Tuple[ShadowPilotSummary, List[ShadowPilotShipmentResult]]:
    if "cargo_value_usd" in df.columns:
        df = df.rename(columns={"cargo_value_usd": "cargo_value"})
    if "cargo_value" not in df.columns:
        raise ValueError("Input DataFrame must contain 'cargo_value' or 'cargo_value_usd' column")

    total_gmv = 0.0
    financeable_gmv = 0.0
    financed_gmv = 0.0
    protocol_revenue_total = 0.0
    wc_saved_total = 0.0
    losses_avoided_total = 0.0
    salvage_revenue_total = 0.0

    shipments: List[ShadowPilotShipmentResult] = []
    shipments_evaluated = 0
    shipments_financeable = 0

    for _, row in df.iterrows():
        shipments_evaluated += 1
        shipment_id = str(row.get("shipment_id", f"SHIP-{shipments_evaluated}"))
        corridor = row.get("corridor")
        mode = row.get("mode")
        customer_segment = row.get("customer_segment")

        cargo_value = float(row["cargo_value"])
        transit_days = int(row.get("transit_days", 30))
        days_to_payment = int(row.get("days_to_payment", 45))
        exception_flag = int(row.get("exception_flag", 0))
        loss_flag = int(row.get("loss_flag", 0))
        loss_amount = float(row.get("loss_amount_usd", cargo_value if loss_flag else 0.0))

        total_gmv += cargo_value

        event_truth_score = _compute_event_truth_score(row)
        min_truth = 0.7
        min_value = 50_000.0

        eligible_for_finance = event_truth_score >= min_truth and cargo_value >= min_value
        financed_amount = 0.0
        wc_saved = 0.0
        protocol_revenue = 0.0
        days_pulled_forward = 0
        avoided_loss = 0.0
        salvage_revenue = 0.0

        if eligible_for_finance:
            shipments_financeable += 1
            financeable_gmv += cargo_value
            financed_amount = cargo_value * advance_rate
            financed_gmv += financed_amount

            days_pulled_forward = max(days_to_payment - transit_days, 0)
            wc_saved = financed_amount * annual_rate * (days_pulled_forward / 365.0)
            wc_saved_total += wc_saved

            protocol_revenue = financed_amount * take_rate
            protocol_revenue_total += protocol_revenue

            if loss_flag:
                salvage_revenue = cargo_value * SALVAGE_RECOVERY_RATE
                salvage_revenue_total += salvage_revenue
        else:
            if loss_flag:
                avoided_loss = loss_amount
                losses_avoided_total += avoided_loss

        shipments.append(
            ShadowPilotShipmentResult(
                run_id=run_id,
                shipment_id=shipment_id,
                corridor=str(corridor) if corridor is not None else None,
                mode=str(mode) if mode is not None else None,
                customer_segment=str(customer_segment) if customer_segment is not None else None,
                cargo_value_usd=cargo_value,
                event_truth_score=event_truth_score,
                eligible_for_finance=eligible_for_finance,
                financed_amount_usd=financed_amount,
                days_pulled_forward=days_pulled_forward,
                wc_saved_usd=wc_saved,
                protocol_revenue_usd=protocol_revenue,
                avoided_loss_usd=avoided_loss,
                salvage_revenue_usd=salvage_revenue,
                exception_flag=exception_flag,
                loss_flag=loss_flag,
            )
        )

    average_days_pulled_forward = (
        sum(s.days_pulled_forward for s in shipments if s.eligible_for_finance) / shipments_financeable
        if shipments_financeable > 0
        else 0.0
    )

    summary = ShadowPilotSummary(
        run_id=run_id,
        prospect_name=prospect_name,
        period_months=period_months,
        total_gmv_usd=total_gmv,
        financeable_gmv_usd=financeable_gmv,
        financed_gmv_usd=financed_gmv,
        protocol_revenue_usd=protocol_revenue_total,
        working_capital_saved_usd=wc_saved_total,
        losses_avoided_usd=losses_avoided_total,
        salvage_revenue_usd=salvage_revenue_total,
        average_days_pulled_forward=average_days_pulled_forward,
        shipments_evaluated=shipments_evaluated,
        shipments_financeable=shipments_financeable,
        input_filename=input_filename,
        notes=notes,
    )

    return summary, shipments
