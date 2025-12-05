"""Pydantic schemas for the shadow pilot tool."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ShipmentRow(BaseModel):
    """Validated input row from the shipments history CSV."""

    model_config = ConfigDict(extra="ignore")

    shipment_id: str = Field(..., description="Unique shipment identifier")
    cargo_value_usd: float = Field(..., description="Declared cargo value in USD")
    delivery_timestamp: datetime = Field(..., description="Actual delivery datetime")
    planned_delivery_timestamp: datetime = Field(..., description="Planned delivery datetime")
    corridor: Optional[str] = Field(None, description="Trade lane or corridor")
    mode: Optional[str] = Field(None, description="Transport mode (air/sea/truck)")
    customer_segment: Optional[str] = Field(None, description="Customer segment tag")
    pickup_timestamp: Optional[datetime] = Field(None, description="Pickup datetime if available")
    exception_flag: int = Field(..., description="1 if shipment had an exception")
    loss_flag: int = Field(..., description="1 if shipment resulted in loss")
    loss_amount_usd: float = Field(0.0, description="Loss amount in USD if the shipment was lost")
    days_to_payment: Optional[float] = Field(None, description="Days from delivery to payment receipt")

    @field_validator("exception_flag", "loss_flag")
    @classmethod
    def _normalize_flag(cls, value: int) -> int:
        return int(value)


class ShipmentResult(BaseModel):
    """Per-shipment result with computed finance metrics."""

    model_config = ConfigDict(extra="ignore")

    shipment_id: str
    cargo_value_usd: float
    delivery_timestamp: datetime
    planned_delivery_timestamp: datetime
    pickup_timestamp: Optional[datetime]
    exception_flag: int
    loss_flag: int
    loss_amount_usd: float
    corridor: Optional[str]
    mode: Optional[str]
    customer_segment: Optional[str]
    actual_days_to_payment: float
    event_truth_score: float
    financeable: bool
    financed_amount_usd: float
    days_pulled_forward: float
    working_capital_saved_usd: float
    protocol_revenue_usd: float
    avoided_loss_usd: float
    salvage_revenue_usd: float


class ShadowSummary(BaseModel):
    """Aggregated metrics suitable for sales-ready reporting."""

    model_config = ConfigDict(extra="ignore")

    total_shipments: int
    financeable_shipments: int
    total_gmv_usd: float
    financeable_gmv_usd: float
    financed_gmv_usd: float
    protocol_revenue_usd: float
    working_capital_saved_usd: float
    losses_avoided_usd: float
    salvage_revenue_usd: float
    average_days_pulled_forward: float
