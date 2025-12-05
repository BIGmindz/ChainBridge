"""Pydantic schemas for Shadow Pilot APIs."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ShadowPilotSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    input_filename: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class ShadowPilotShipmentResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shipment_id: str
    corridor: Optional[str] = None
    mode: Optional[str] = None
    customer_segment: Optional[str] = None
    cargo_value_usd: float
    event_truth_score: float
    eligible_for_finance: bool
    financed_amount_usd: float
    days_pulled_forward: int
    wc_saved_usd: float
    protocol_revenue_usd: float
    avoided_loss_usd: float
    salvage_revenue_usd: float
    exception_flag: bool
    loss_flag: bool


class ShadowPilotShipmentsPageResponse(BaseModel):
    items: List[ShadowPilotShipmentResultResponse]
    next_cursor: Optional[str] = None


class ShadowPilotIngestRequest(BaseModel):
    run_id: Optional[str] = None
    prospect_name: str
    period_months: int
    input_filename: Optional[str] = None
    notes: Optional[str] = None
