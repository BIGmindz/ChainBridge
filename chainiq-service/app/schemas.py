"""
ChainIQ v0.1 - Schemas

Pydantic models for input/output contracts.
These are the glass-box interfaces that Cody's backend mirrors.

Author: Maggie (GID-10) - ML & Applied AI Lead
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# =============================================================================
# INPUT SCHEMAS
# =============================================================================


class ShipmentEventLite(BaseModel):
    """Minimal event representation for risk scoring."""

    type: str = Field(
        ...,
        description="Event type code",
        examples=[
            "DEPARTED_PORT",
            "ARRIVED_PORT",
            "CUSTOMS_HOLD",
            "TEMPERATURE_ALARM",
            "VESSEL_DELAY",
            "PORT_CONGESTION",
            "DOCUMENTATION_ISSUE",
            "CARRIER_DELAY",
        ],
    )
    timestamp: datetime
    location: Optional[str] = Field(None, description="Location code or name")
    metadata: Optional[dict] = Field(default_factory=dict, description="Event-specific data")


class ShipmentRiskContext(BaseModel):
    """
    Input context for ChainIQ risk scoring.

    This is the contract Cody's backend must fulfill when calling ChainIQ.
    Required fields are marked with `...` (no default).
    """

    # === IDENTIFIERS ===
    shipment_id: str = Field(..., description="Unique shipment identifier")
    tenant_id: str = Field(..., description="Customer tenant ID for partitioning/logging")

    # === MODE & ROUTE ===
    mode: Literal["OCEAN", "TRUCK", "AIR", "RAIL", "INTERMODAL"] = Field(..., description="Primary transport mode")
    origin_country: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    origin_region: Optional[str] = Field(None, description="State/province/port region")
    destination_country: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    destination_region: Optional[str] = Field(None, description="State/province/port region")
    lane_id: Optional[str] = Field(None, description="Pre-computed lane identifier (or derived from O/D pair)")

    # === TIMING ===
    planned_departure: datetime = Field(..., description="Scheduled departure datetime (UTC)")
    planned_arrival: datetime = Field(..., description="Scheduled arrival datetime (UTC)")
    actual_departure: Optional[datetime] = Field(None, description="Actual departure (if known)")
    actual_arrival: Optional[datetime] = Field(None, description="Actual arrival (if completed)")

    # === CARRIER & LOGISTICS ===
    carrier_code: Optional[str] = Field(None, description="SCAC or carrier identifier")
    distance_km: Optional[float] = Field(None, ge=0, description="Route distance in kilometers")

    # === CARGO CHARACTERISTICS ===
    commodity_type: Optional[str] = Field(None, description="Commodity classification code")
    temperature_controlled: Optional[bool] = Field(False, description="Requires temp control")
    value_usd: Optional[float] = Field(None, ge=0, description="Declared cargo value in USD")

    # === HISTORICAL/CONTEXTUAL FEATURES ===
    events: List[ShipmentEventLite] = Field(default_factory=list, description="Timeline of events for this shipment")
    prior_incident_rate_lane: Optional[float] = Field(None, ge=0, le=1, description="Historical incident rate for this lane (0-1)")
    prior_incident_rate_carrier: Optional[float] = Field(None, ge=0, le=1, description="Historical incident rate for this carrier (0-1)")
    seasonality_index: Optional[float] = Field(None, description="Seasonal risk multiplier (1.0 = baseline)")

    def derive_lane_id(self) -> str:
        """Derive lane ID from origin/destination if not provided."""
        if self.lane_id:
            return self.lane_id
        origin = f"{self.origin_country}-{self.origin_region or 'ALL'}"
        dest = f"{self.destination_country}-{self.destination_region or 'ALL'}"
        return f"{origin}::{dest}::{self.mode}"

    class Config:
        json_schema_extra = {
            "example": {
                "shipment_id": "SHP-2024-001234",
                "tenant_id": "tenant-acme-corp",
                "mode": "OCEAN",
                "origin_country": "CN",
                "origin_region": "Shanghai",
                "destination_country": "US",
                "destination_region": "Los Angeles",
                "planned_departure": "2024-12-01T08:00:00Z",
                "planned_arrival": "2024-12-21T18:00:00Z",
                "carrier_code": "MAEU",
                "distance_km": 11500,
                "commodity_type": "ELECTRONICS",
                "temperature_controlled": False,
                "value_usd": 250000,
                "events": [{"type": "DEPARTED_PORT", "timestamp": "2024-12-01T10:30:00Z", "location": "CNSHA"}],
                "prior_incident_rate_lane": 0.12,
                "prior_incident_rate_carrier": 0.08,
            }
        }


# =============================================================================
# OUTPUT SCHEMAS
# =============================================================================


class TopFactor(BaseModel):
    """Single explainability factor contributing to risk score."""

    feature_name: str = Field(..., description="Internal feature name")
    direction: Literal["INCREASES_RISK", "DECREASES_RISK"] = Field(..., description="Impact direction on risk")
    magnitude: float = Field(..., ge=0, le=100, description="Relative contribution (0-100 scale)")
    human_label: str = Field(
        ..., description="Human-readable explanation", examples=["Lane historically experiences 15% delays", "Peak shipping season"]
    )


class ShipmentRiskAssessment(BaseModel):
    """
    ChainIQ v0.1 output for a single shipment risk assessment.

    All scores are 0-100 scale where higher = more risk (except resilience).
    This is the glass-box contract that Sonny (UI) and Cody (backend) rely on.
    """

    # === IDENTIFIERS ===
    shipment_id: str = Field(..., description="Echo of input shipment_id")
    assessed_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of this assessment")
    model_version: str = Field(default="chainiq-v0.1", description="Model version tag")

    # === COMPOSITE RISK SCORES ===
    risk_score: float = Field(..., ge=0, le=100, description="Overall risk score (0=safe, 100=critical)")
    operational_risk: float = Field(..., ge=0, le=100, description="Risk of delays, routing issues, capacity problems")
    financial_risk: float = Field(..., ge=0, le=100, description="Risk of cost overruns, claims, value loss")
    fraud_risk: float = Field(..., ge=0, le=100, description="Risk of fraudulent documentation or activity")
    esg_risk: float = Field(default=0.0, ge=0, le=100, description="Environmental/social/governance risk (placeholder for v0)")

    # === RESILIENCE (INVERSE OF RISK) ===
    resilience_score: float = Field(..., ge=0, le=100, description="Overall resilience (100=very resilient, 0=fragile)")

    # === DECISION ===
    decision: Literal["APPROVE", "HOLD", "TIGHTEN_TERMS", "ESCALATE"] = Field(
        ..., description="Recommended action based on risk thresholds"
    )
    decision_confidence: float = Field(..., ge=0, le=1, description="Model confidence in this decision (0-1)")

    # === EXPLAINABILITY ===
    top_factors: List[TopFactor] = Field(..., min_length=1, max_length=10, description="Top contributing factors to risk score")
    summary_reason: str = Field(..., max_length=500, description="Natural language summary of risk assessment")
    tags: List[str] = Field(
        default_factory=list, description="Risk tags for filtering/grouping", examples=[["PORT_CONGESTION", "LANE_VOLATILE", "HIGH_VALUE"]]
    )

    # === METADATA ===
    data_quality_score: float = Field(default=1.0, ge=0, le=1, description="Quality of input data (1=complete, 0=sparse)")

    class Config:
        json_schema_extra = {
            "example": {
                "shipment_id": "SHP-2024-001234",
                "assessed_at": "2024-12-07T14:30:00Z",
                "model_version": "chainiq-v0.1",
                "risk_score": 67.5,
                "operational_risk": 72.0,
                "financial_risk": 58.0,
                "fraud_risk": 12.0,
                "esg_risk": 0.0,
                "resilience_score": 32.5,
                "decision": "TIGHTEN_TERMS",
                "decision_confidence": 0.82,
                "top_factors": [
                    {
                        "feature_name": "lane_incident_rate",
                        "direction": "INCREASES_RISK",
                        "magnitude": 35.2,
                        "human_label": "This lane has 15% historical delay rate",
                    }
                ],
                "summary_reason": "Medium-high risk due to volatile lane during peak season.",
                "tags": ["LANE_VOLATILE", "PEAK_SEASON"],
            }
        }


# =============================================================================
# API REQUEST/RESPONSE WRAPPERS
# =============================================================================


class RiskScoreRequest(BaseModel):
    """Request body for /api/v1/risk/score endpoint."""

    shipments: List[ShipmentRiskContext] = Field(..., min_length=1, max_length=100, description="Shipments to score (1-100 items)")
    include_factors: bool = Field(default=True, description="Include top factors in response")
    include_summary: bool = Field(default=True, description="Include summary reason in response")
    max_factors: int = Field(default=5, ge=1, le=10, description="Max factors to return")


class RiskScoreResponse(BaseModel):
    """Response body for /api/v1/risk/score endpoint."""

    assessments: List[ShipmentRiskAssessment]
    meta: dict = Field(default_factory=dict, description="Metadata about the scoring operation")


class SimulationVariation(BaseModel):
    """A single variation for what-if analysis."""

    name: str = Field(..., description="Name of this variation")
    overrides: dict = Field(..., description="Partial ShipmentRiskContext fields to override")


class RiskSimulationRequest(BaseModel):
    """Request body for /api/v1/risk/simulation endpoint."""

    base_context: ShipmentRiskContext = Field(..., description="Base shipment context")
    variations: List[SimulationVariation] = Field(..., min_length=1, max_length=10, description="Variations to compare")


class VariationResult(BaseModel):
    """Result for a single simulation variation."""

    name: str
    assessment: ShipmentRiskAssessment
    delta_risk_score: float = Field(description="Difference from base risk score")


class RiskSimulationResponse(BaseModel):
    """Response body for /api/v1/risk/simulation endpoint."""

    base_assessment: ShipmentRiskAssessment
    variation_assessments: List[VariationResult]
    recommendation: Optional[dict] = Field(None, description="Best variation recommendation if applicable")


# =============================================================================
# SETTLEMENT POLICY RECOMMENDATION SCHEMAS
# =============================================================================


class SettlementMilestoneRecommendation(BaseModel):
    """
    A single milestone in a recommended settlement policy.

    Each milestone specifies when a percentage of the payment should be released.
    This is a **recommendation** from ChainIQ — ChainPay makes the final decision.
    """

    name: str = Field(..., description="Milestone name (e.g., PICKUP, DELIVERY, CLAIM_WINDOW)")
    event_type: str = Field(..., description="Event code that triggers this milestone (e.g., BOL_ISSUED, POD_RECEIVED)")
    percentage: float = Field(..., ge=0, le=100, description="Percentage of total payment to release at this milestone")
    timing_hint: Optional[str] = Field(None, description="Timing hint (e.g., 'on_delivery', '7_days_post_delivery')")
    conditions: List[str] = Field(default_factory=list, description="Human-readable conditions for this milestone (no PII)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "DELIVERY",
                "event_type": "POD_RECEIVED",
                "percentage": 60.0,
                "timing_hint": "on_delivery",
                "conditions": ["Proof of delivery required", "No damage claims filed"],
            }
        }
    }


class SettlementPolicyRecommendation(BaseModel):
    """
    ChainIQ's recommendation for a shipment's settlement policy.

    This maps risk assessment → suggested payment flow.
    Glass-box, auditable, and explainable in a 2-minute CFO conversation.

    **Key principle**: ChainIQ **recommends**, ChainPay + governance **decide**.
    """

    # === IDENTIFIERS ===
    shipment_id: str = Field(..., description="Shipment this recommendation applies to")
    recommended_at: datetime = Field(default_factory=datetime.utcnow, description="When this recommendation was generated")

    # === RISK CONTEXT ===
    risk_score: float = Field(..., ge=0, le=100, description="Risk score this recommendation is based on")
    risk_band: str = Field(..., description="Risk band label (LOW, MODERATE, HIGH, CRITICAL)")
    decision: Literal["APPROVE", "HOLD", "TIGHTEN_TERMS", "ESCALATE"] = Field(..., description="Risk decision from ChainIQ")

    # === POLICY RECOMMENDATION ===
    recommended_policy_code: str = Field(
        ...,
        description="Short code for the recommended policy template",
        examples=["LOW_RISK_FAST", "MODERATE_BALANCED", "HIGH_RISK_GUARDED", "CRITICAL_REVIEW"],
    )
    milestones: List[SettlementMilestoneRecommendation] = Field(
        ..., min_length=1, description="Recommended milestone-based payment schedule"
    )

    # === RISK ADJUSTMENTS ===
    settlement_delay_hours: Optional[float] = Field(None, ge=0, description="Recommended hold period before first release (hours)")
    hold_percentage: float = Field(default=0.0, ge=0, le=100, description="Percentage to hold until claim window closes")
    requires_manual_approval: bool = Field(default=False, description="Whether human approval is required for release")

    # === EXPLAINABILITY ===
    rationale: str = Field(..., max_length=500, description="Human-readable explanation of this recommendation")
    top_factors: List[TopFactor] = Field(default_factory=list, description="Top risk factors driving this recommendation")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization and filtering")

    model_config = {
        "json_schema_extra": {
            "example": {
                "shipment_id": "SHP-2024-001234",
                "recommended_at": "2024-12-07T15:00:00Z",
                "risk_score": 72.5,
                "risk_band": "HIGH",
                "decision": "TIGHTEN_TERMS",
                "recommended_policy_code": "HIGH_RISK_GUARDED",
                "milestones": [
                    {"name": "PICKUP", "event_type": "BOL_ISSUED", "percentage": 0.0, "timing_hint": None, "conditions": []},
                    {
                        "name": "DELIVERY",
                        "event_type": "POD_RECEIVED",
                        "percentage": 60.0,
                        "timing_hint": "on_delivery",
                        "conditions": ["POD verification required"],
                    },
                    {
                        "name": "CLAIM_WINDOW",
                        "event_type": "CLAIM_WINDOW_CLOSED",
                        "percentage": 40.0,
                        "timing_hint": "7_days_post_delivery",
                        "conditions": ["No claims filed"],
                    },
                ],
                "settlement_delay_hours": 24.0,
                "hold_percentage": 40.0,
                "requires_manual_approval": False,
                "rationale": "Risk score 72 in HIGH band; shifting 40% to claim window due to elevated lane risk and carrier volatility.",
                "top_factors": [
                    {
                        "feature_name": "lane_incident_rate",
                        "direction": "INCREASES_RISK",
                        "magnitude": 35.2,
                        "human_label": "Lane has 15% historical delay rate",
                    }
                ],
                "tags": ["RISK_BAND_HIGH", "SETTLEMENT_TIGHTENED", "CLAIM_WINDOW_EXTENDED"],
            }
        }
    }


# =============================================================================
# SETTLEMENT API REQUEST/RESPONSE WRAPPERS
# =============================================================================


class SettlementRecommendationRequest(BaseModel):
    """Request body for /api/v1/risk/settlement/recommend endpoint."""

    shipments: List[ShipmentRiskContext] = Field(
        ..., min_length=1, max_length=100, description="Shipments to generate settlement recommendations for"
    )


class SettlementRecommendationResponse(BaseModel):
    """Response body for /api/v1/risk/settlement/recommend endpoint."""

    recommendations: List[SettlementPolicyRecommendation]
    meta: dict = Field(default_factory=dict, description="Metadata about the recommendation operation")
