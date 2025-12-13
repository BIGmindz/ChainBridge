"""Pydantic schemas for Risk API endpoints.

These schemas mirror Maggie's ChainIQ contracts and provide the main API's
interface for risk scoring. Callers never need to know ChainIQ's internal
JSON—they talk to these types.

Strong types, zero surprises.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# SHARED NESTED TYPES - Mirrors ChainIQ output contracts
# =============================================================================


class TopFactor(BaseModel):
    """Single explainability factor contributing to risk score.

    Maps from ChainIQ's TopFactor but uses backend-friendly field names.
    """

    name: str = Field(..., description="Feature name (e.g., lane_incident_rate)")
    description: str = Field(..., description="Human-readable explanation")
    direction: Literal["UP", "DOWN"] = Field(..., description="UP = increases risk, DOWN = decreases risk")
    weight: float = Field(..., ge=0, le=100, description="Relative contribution to risk score (0-100)")


class ShipmentEventLite(BaseModel):
    """Minimal event representation for risk context."""

    type: str = Field(..., description="Event type code")
    timestamp: datetime
    location: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# =============================================================================
# INPUT SCHEMAS - What callers send to risk endpoints
# =============================================================================


class ShipmentRiskContext(BaseModel):
    """Input context for risk scoring.

    This is what backend callers provide. The main API transforms this
    to ChainIQ's internal format if needed.
    """

    # Required identifiers
    shipment_id: str = Field(..., description="Unique shipment identifier")

    # Note: tenant_id is NOT in request - it comes from auth context

    # Mode & Route
    mode: Literal["OCEAN", "TRUCK", "AIR", "RAIL", "INTERMODAL"] = Field(..., description="Primary transport mode")
    origin_country: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    origin_region: Optional[str] = Field(None, description="State/province/port region")
    destination_country: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    destination_region: Optional[str] = Field(None, description="State/province/port region")
    lane_id: Optional[str] = Field(None, description="Pre-computed lane identifier")

    # Timing
    planned_departure: datetime = Field(..., description="Scheduled departure (UTC)")
    planned_arrival: datetime = Field(..., description="Scheduled arrival (UTC)")
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None

    # Carrier & Logistics
    carrier_code: Optional[str] = Field(None, description="SCAC or carrier identifier")
    distance_km: Optional[float] = Field(None, ge=0)

    # Cargo Characteristics
    commodity_type: Optional[str] = None
    temperature_controlled: bool = False
    value_usd: Optional[float] = Field(None, ge=0, description="Declared cargo value")

    # Historical/Contextual Features
    events: List[ShipmentEventLite] = Field(default_factory=list)
    prior_incident_rate_lane: Optional[float] = Field(None, ge=0, le=1)
    prior_incident_rate_carrier: Optional[float] = Field(None, ge=0, le=1)
    seasonality_index: Optional[float] = Field(None, description="1.0 = baseline")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shipment_id": "SHP-2024-001234",
                "mode": "OCEAN",
                "origin_country": "CN",
                "origin_region": "Shanghai",
                "destination_country": "US",
                "destination_region": "Los Angeles",
                "planned_departure": "2024-12-01T08:00:00Z",
                "planned_arrival": "2024-12-21T18:00:00Z",
                "carrier_code": "MAEU",
                "value_usd": 250000,
            }
        }
    )


# =============================================================================
# OUTPUT SCHEMAS - What callers receive from risk endpoints
# =============================================================================


class ShipmentRiskAssessment(BaseModel):
    """Risk assessment for a single shipment.

    All scores are 0-100 scale where higher = more risk (except resilience).
    """

    # Identifiers
    shipment_id: str
    assessed_at: datetime = Field(default_factory=datetime.utcnow)
    model_version: Optional[str] = Field(default="chainiq-v0.1")

    # Composite Risk Scores (0-100)
    risk_score: float = Field(..., ge=0, le=100, description="Overall risk")
    operational_risk: Optional[float] = Field(None, ge=0, le=100)
    financial_risk: Optional[float] = Field(None, ge=0, le=100)
    fraud_risk: Optional[float] = Field(None, ge=0, le=100)
    esg_risk: Optional[float] = Field(None, ge=0, le=100)

    # Resilience (inverse of risk, 0-100)
    resilience_score: Optional[float] = Field(None, ge=0, le=100)

    # Decision
    decision: Literal["APPROVE", "HOLD", "TIGHTEN_TERMS", "ESCALATE"] = Field(
        ..., description="Recommended action based on risk thresholds"
    )
    confidence: float = Field(..., ge=0, le=1, description="Model confidence (0-1)")

    # Explainability
    top_factors: List[TopFactor] = Field(default_factory=list)
    summary_reason: str = Field(..., description="Natural language risk summary")
    tags: List[str] = Field(default_factory=list, description="Risk tags for filtering")

    # Data Quality
    data_quality_score: Optional[float] = Field(None, ge=0, le=1)

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# REQUEST/RESPONSE WRAPPERS
# =============================================================================


class RiskScoreRequest(BaseModel):
    """Request body for POST /api/v1/risk/score."""

    shipments: List[ShipmentRiskContext] = Field(..., min_length=1, max_length=100, description="Shipments to score (1-100 per request)")
    include_factors: bool = Field(default=True, description="Include top factors")
    include_summary: bool = Field(default=True, description="Include summary reason")
    max_factors: int = Field(default=5, ge=1, le=10, description="Max factors to return")


class RiskScoreResponse(BaseModel):
    """Response body for POST /api/v1/risk/score."""

    assessments: List[ShipmentRiskAssessment]
    meta: Dict[str, Any] = Field(default_factory=dict, description="Scoring metadata (timing, model info)")


# =============================================================================
# SIMULATION TYPES
# =============================================================================


class RiskSimulationVariant(BaseModel):
    """A single variation for what-if analysis."""

    name: str = Field(..., description="Variation name (e.g., 'alt_carrier')")
    overrides: Dict[str, Any] = Field(..., description="Partial ShipmentRiskContext fields to override")


class RiskSimulationRequest(BaseModel):
    """Request body for POST /api/v1/risk/simulation."""

    base_context: ShipmentRiskContext = Field(..., description="Base shipment context")
    variations: List[RiskSimulationVariant] = Field(..., min_length=1, max_length=10, description="Variations to compare (1-10)")


class RiskSimulationVariantResult(BaseModel):
    """Result for a single simulation variation."""

    name: str
    assessment: ShipmentRiskAssessment
    delta_risk_score: float = Field(description="Difference from base risk score")


class RiskSimulationResponse(BaseModel):
    """Response body for POST /api/v1/risk/simulation."""

    base_assessment: ShipmentRiskAssessment
    variation_assessments: List[RiskSimulationVariantResult]
    recommendation: Optional[str] = Field(None, description="Best variation recommendation if applicable")


# =============================================================================
# HEALTH CHECK
# =============================================================================


class RiskHealthResponse(BaseModel):
    """Health check response from ChainIQ."""

    status: str
    model_version: str
    last_check: datetime
