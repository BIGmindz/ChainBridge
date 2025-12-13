"""Schemas for ChainIQ risk service.

Risk-specific models for the ChainIQ engine.

NOTE:
- ShipmentRiskRequest/Response may overlap with definitions in app/schemas.py.
- Keep these in sync or converge to a single canonical source to avoid drift.
- Maggie's evaluation and Dan's metrics assume consistent fields across modules.
"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class RiskBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ShipmentFeatures(BaseModel):
    value_usd: float = Field(..., ge=0, description="Shipment value in USD")
    is_hazmat: bool = Field(..., description="Whether the shipment is hazardous")
    is_temp_control: bool = Field(..., description="Whether temperature control is required")
    expected_transit_days: int = Field(..., ge=0, description="Planned transit time in days")
    iot_alert_count: int = Field(..., ge=0, description="Count of IoT alerts in the last 30 days")
    recent_delay_events: int = Field(..., ge=0, description="Recent delay events impacting this lane or carrier")


class CarrierProfile(BaseModel):
    carrier_id: str = Field(..., description="Carrier identifier")
    incident_rate_90d: float = Field(..., ge=0, description="Incident rate over last 90 days")
    tenure_days: int = Field(..., ge=0, description="Carrier tenure in days")
    on_time_rate: float = Field(..., ge=0, le=1, description="On-time delivery rate (0-1 range)")


class LaneProfile(BaseModel):
    origin: str = Field(..., description="Origin location code")
    destination: str = Field(..., description="Destination location code")
    lane_risk_index: float = Field(..., ge=0, description="Composite risk index for the lane")
    border_crossing_count: int = Field(..., ge=0, description="Number of border crossings on this lane")


class RiskScoreResult(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Risk score from the engine")
    band: RiskBand = Field(..., description="Risk band classification")
    reasons: List[str] = Field(default_factory=list, description="Primary risk reasons")
    model_version: str | None = Field(None, description="Model version used for scoring")


class ShipmentRiskRequest(BaseModel):
    shipment_id: str = Field(..., description="Unique shipment identifier")
    carrier_id: str = Field(..., description="Carrier identifier")
    origin: str = Field(..., description="Origin location code")
    destination: str = Field(..., description="Destination location code")
    value_usd: float = Field(..., ge=0, description="Shipment value in USD")
    is_hazmat: bool = Field(..., description="Hazardous materials flag")
    is_temp_control: bool = Field(..., description="Temperature controlled shipment flag")
    expected_transit_days: int = Field(..., ge=0, description="Expected transit days")
    iot_alert_count: int = Field(..., ge=0, description="Recent IoT alerts relevant to the shipment")
    recent_delay_events: int = Field(..., ge=0, description="Recent lane or carrier delay events")


class ShipmentRiskResponse(BaseModel):
    shipment_id: str = Field(..., description="Echoed shipment identifier")
    risk_score: int = Field(..., ge=0, le=100, description="Final risk score")
    risk_band: RiskBand = Field(..., description="Risk band classification")
    explanation: List[str] = Field(default_factory=list, description="Reasons returned by the engine")
    model_version: str = Field(..., description="Model version used for scoring")
    timestamp: str = Field(..., description="UTC ISO timestamp when the score was produced")
    evaluation_id: str = Field(..., description="Unique evaluation identifier for this scoring event")
