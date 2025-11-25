"""
ChainIQ Pydantic Schemas

Request/response models for the ChainIQ service API.
"""

from typing import List, Literal

from pydantic import BaseModel, Field


class ShipmentRiskRequest(BaseModel):
    """
    Request schema for shipment risk scoring.

    Business Context:
    Operators need to decide whether to release payment for a shipment.
    This request provides all context needed for risk assessment.
    """

    shipment_id: str = Field(..., description="Unique shipment identifier", examples=["SHP-1001"])

    route: str = Field(..., description="Origin-destination route code (e.g., CN-US, DE-UK)", examples=["CN-US"])

    carrier_id: str = Field(..., description="Carrier identifier", examples=["CARRIER-001"])

    shipment_value_usd: float = Field(..., ge=0, description="Shipment value in USD", examples=[25000.00])

    days_in_transit: int = Field(..., ge=0, description="Current days in transit", examples=[5])

    expected_days: int = Field(..., ge=0, description="Expected transit days", examples=[7])

    documents_complete: bool = Field(..., description="Whether all required documents are complete", examples=[True])

    shipper_payment_score: int = Field(
        ..., ge=0, le=100, description="Shipper's payment reliability score (0-100, higher is better)", examples=[85]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "shipment_id": "SHP-1001",
                "route": "CN-US",
                "carrier_id": "CARRIER-001",
                "shipment_value_usd": 25000.00,
                "days_in_transit": 5,
                "expected_days": 7,
                "documents_complete": True,
                "shipper_payment_score": 85,
            }
        }


class ShipmentRiskResponse(BaseModel):
    """
    Response schema for shipment risk scoring.

    Business Purpose:
    Provides actionable risk assessment to operators.
    Clear severity + recommended action enables immediate decision-making.
    """

    shipment_id: str = Field(..., description="Shipment identifier (echo from request)")

    risk_score: int = Field(..., ge=0, le=100, description="Risk score (0-100, higher is riskier)")

    severity: str = Field(..., description="Risk severity level", examples=["LOW", "MEDIUM", "HIGH", "CRITICAL"])

    reason_codes: List[str] = Field(default_factory=list, description="List of reason codes explaining the risk score")

    recommended_action: str = Field(
        ...,
        description="Recommended action for operator",
        examples=["RELEASE_PAYMENT", "MANUAL_REVIEW", "HOLD_PAYMENT", "ESCALATE_COMPLIANCE"],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "shipment_id": "SHP-1001",
                "risk_score": 25,
                "severity": "LOW",
                "reason_codes": ["ELEVATED_VALUE"],
                "recommended_action": "RELEASE_PAYMENT",
            }
        }


class RiskHistoryItem(BaseModel):
    """
    Single risk scoring record from history.

    Includes full audit trail with timestamp and original request/response.
    """

    id: int = Field(..., description="Database record ID")
    shipment_id: str = Field(..., description="Shipment identifier")
    scored_at: str = Field(..., description="Timestamp when score was calculated")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    severity: str = Field(..., description="Risk severity level")
    recommended_action: str = Field(..., description="Recommended action")
    reason_codes: List[str] = Field(default_factory=list, description="Reason codes")


class RiskHistoryResponse(BaseModel):
    """
    Response containing risk scoring history for a shipment.
    """

    shipment_id: str = Field(..., description="Shipment identifier")
    total_scores: int = Field(..., description="Total number of scores for this shipment")
    history: List[RiskHistoryItem] = Field(default_factory=list, description="Historical scores")


class RecentRiskResponse(BaseModel):
    """
    Response containing recent risk scores across all shipments.
    """

    total: int = Field(..., description="Total number of records returned")
    scores: List[RiskHistoryItem] = Field(default_factory=list, description="Recent scores")


class ReplayResponse(BaseModel):
    """
    Response from deterministic replay of a risk score.

    Shows both original and replayed scores for comparison.
    """

    shipment_id: str = Field(..., description="Shipment identifier")
    original_score: int = Field(..., description="Original risk score")
    original_severity: str = Field(..., description="Original severity")
    original_scored_at: str = Field(..., description="When original score was calculated")
    replayed_score: int = Field(..., description="Replayed risk score")
    replayed_severity: str = Field(..., description="Replayed severity")
    replayed_reason_codes: List[str] = Field(default_factory=list, description="Replayed reason codes")
    replayed_action: str = Field(..., description="Replayed recommended action")
    match: bool = Field(..., description="Whether original and replayed scores match")


class PaymentQueueItem(BaseModel):
    """
    Single shipment in the payment hold queue.

    Business Context:
    These are shipments where risk scoring determined payment should NOT
    be auto-released. Operators must review and make manual decision.
    """

    shipment_id: str = Field(..., description="Shipment identifier")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., description="Risk severity level")
    recommended_action: str = Field(..., description="Recommended action")
    route: str = Field(..., description="Origin-destination route")
    carrier_id: str = Field(..., description="Carrier identifier")
    shipment_value_usd: float = Field(..., ge=0, description="Shipment value in USD")
    last_scored_at: str = Field(..., description="When risk was last assessed")


class PaymentQueueResponse(BaseModel):
    """
    Response containing shipments requiring payment review.

    Business Purpose:
    Payment hold queue shows operators which shipments need manual review
    before payment release. Filters to HIGH/CRITICAL severity or explicit
    HOLD/MANUAL_REVIEW/ESCALATE actions.
    """

    items: List[PaymentQueueItem] = Field(default_factory=list, description="Shipments pending review")
    total_pending: int = Field(..., description="Total number of shipments in hold queue")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "shipment_id": "SHP-1004",
                        "risk_score": 75,
                        "severity": "HIGH",
                        "recommended_action": "HOLD_PAYMENT",
                        "route": "IR-RU",
                        "carrier_id": "CARRIER-001",
                        "shipment_value_usd": 50000.00,
                        "last_scored_at": "2025-11-15T10:30:00Z",
                    }
                ],
                "total_pending": 1,
            }
        }


class EntityHistoryRecord(BaseModel):
    """
    Single historical record for an entity.

    Contains the complete audit trail for a single scoring event.
    """

    timestamp: str = Field(..., description="When the score was calculated (ISO 8601)")
    score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    severity: str = Field(..., description="Risk severity level")
    recommended_action: str = Field(..., description="Recommended action at time of scoring")
    reason_codes: List[str] = Field(default_factory=list, description="Reason codes explaining the score")
    payload: dict = Field(..., description="Original request payload (full context)")


class EntityHistoryResponse(BaseModel):
    """
    Complete scoring history for an entity.

    Business Purpose:
    Provides full audit trail for compliance, trend analysis, and decision review.
    Enables operators to see how risk assessment evolved over time.

    Use Cases:
    - Compliance audit: "Show me all risk assessments for SHP-1004"
    - Trend analysis: "Did risk increase or decrease over time?"
    - Decision review: "What context led to the HOLD_PAYMENT decision?"
    """

    entity_id: str = Field(..., description="Entity identifier (shipment_id)")
    total_records: int = Field(..., description="Total number of historical records")
    history: List[EntityHistoryRecord] = Field(
        default_factory=list, description="Historical scoring records in reverse chronological order"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "SHP-1004",
                "total_records": 3,
                "history": [
                    {
                        "timestamp": "2025-11-15T10:30:00Z",
                        "score": 75,
                        "severity": "HIGH",
                        "recommended_action": "HOLD_PAYMENT",
                        "reason_codes": ["SANCTIONS_RISK", "ELEVATED_VALUE"],
                        "payload": {
                            "shipment_id": "SHP-1004",
                            "route": "IR-RU",
                            "carrier_id": "CARRIER-001",
                            "shipment_value_usd": 50000.0,
                        },
                    }
                ],
            }
        }


# Sunny: define the Pydantic models for the Better Options Advisor.
# See RouteOption, PaymentRailOption, and OptionsAdvisorResponse below.


class RouteOption(BaseModel):
    """
    Alternative route option for a shipment.

    Represents a different origin-destination path or carrier choice
    that could reduce risk or improve cost/timing.
    """

    option_id: str = Field(..., description="Unique identifier for this option")
    route: str = Field(..., description="Route code (e.g., IR-TR-EU)")
    carrier_id: str | None = Field(None, description="Carrier identifier for this route")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score for this option")
    risk_delta: int = Field(..., description="Risk improvement vs current (positive = safer)")
    eta_delta_days: int = Field(..., description="ETA change vs current (+2 = 2 days slower, -1 = 1 day faster)")
    cost_delta_usd: float = Field(..., description="Cost change vs current (positive = more expensive)")
    notes: list[str] = Field(default_factory=list, description="Additional context or warnings")


class PaymentRailOption(BaseModel):
    """
    Alternative payment rail option for a shipment.

    Represents a different payment method (SWIFT, crypto, ACH, etc.)
    that could reduce risk or improve settlement speed/fees.
    """

    option_id: str = Field(..., description="Unique identifier for this option")
    payment_rail: str = Field(..., description="Payment rail name (e.g., USDC-Polygon, SWIFT)")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score for this payment method")
    risk_delta: int = Field(..., description="Risk improvement vs current (positive = safer)")
    settlement_speed: str = Field(..., description="Settlement speed (e.g., T+0, T+1, T+3)")
    fees_delta_usd: float = Field(..., description="Fee change vs current (positive = more expensive)")
    notes: list[str] = Field(default_factory=list, description="Additional context or warnings")


class OptionsAdvisorResponse(BaseModel):
    """
    Better Options Advisor response with alternative routes and payment rails.

    Business Purpose:
    Helps operators reduce risk by suggesting better route/payment combinations
    tailored to their risk appetite (conservative, balanced, aggressive).

    Sunny: define the Pydantic models for the Better Options Advisor.
    """

    shipment_id: str = Field(..., description="Shipment identifier")
    current_risk_score: int = Field(..., ge=0, le=100, description="Current risk score")
    current_route: str | None = Field(None, description="Current route")
    current_carrier_id: str | None = Field(None, description="Current carrier ID")
    current_payment_rail: str | None = Field(None, description="Current payment rail")
    risk_appetite: Literal["conservative", "balanced", "aggressive"] = Field(
        default="balanced", description="Risk appetite setting for option recommendations"
    )
    route_options: list[RouteOption] = Field(default_factory=list, description="Alternative route options")
    payment_options: list[PaymentRailOption] = Field(
        default_factory=list, description="Alternative payment rail options"
    )


# Sunny: define the Pydantic models for the Better Options Advisor.


class RiskSnapshot(BaseModel):
    """
    Latest risk assessment snapshot for a shipment.

    Business Purpose:
    Lightweight representation of current risk state without full history.
    Used in ProofPack for Space and Time integration.
    """

    shipment_id: str = Field(..., description="Shipment identifier")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., description="Risk severity level")
    recommended_action: str = Field(..., description="Recommended action")
    reason_codes: list[str] = Field(default_factory=list, description="Reason codes explaining the score")
    last_scored_at: str = Field(..., description="Timestamp of last scoring (ISO-8601)")


class ProofPackResponse(BaseModel):
    """
    Complete ChainIQ/ChainPay state bundle for a shipment.

    Business Purpose:
    Aggregates all relevant risk, history, queue, and options data into a single
    response for Space and Time integration, on-chain attestation, or compliance audits.

    This is the "proof pack" that can be:
    - Mirrored to Space and Time for verifiable analytics
    - Attached to on-chain settlement transactions
    - Used for regulatory compliance reporting
    - Archived for audit trails

    All fields except shipment_id, version, and generated_at are optional to support
    partial data scenarios (e.g., new shipment with no history yet).
    """

    shipment_id: str = Field(..., description="Shipment identifier")
    version: str = Field(default="proofpack-v1", description="ProofPack schema version")
    generated_at: str = Field(..., description="When this ProofPack was generated (ISO-8601 UTC)")
    risk_snapshot: RiskSnapshot | None = Field(None, description="Latest risk assessment")
    history: EntityHistoryResponse | None = Field(None, description="Complete risk scoring history")
    payment_queue_entry: PaymentQueueItem | None = Field(None, description="Current payment queue entry if pending")
    options_advisor: OptionsAdvisorResponse | None = Field(None, description="Safer route/payment alternatives")


class SimulationRequest(BaseModel):
    """
    Request to simulate a risk assessment for a selected option.

    Business Purpose:
    Allows operators to test "what if" scenarios without mutating production data.
    Used for safe exploration of route/payment rail alternatives before committing.
    """

    option_type: Literal["route", "payment_rail"] = Field(..., description="Type of option to simulate")
    option_id: str = Field(..., description="Identifier of the specific option to test")


class SimulationResultResponse(BaseModel):
    """
    Result of a sandbox risk simulation.

    Business Purpose:
    Shows the impact of selecting an option without persisting any changes.
    Enables risk-free testing of Better Options Advisor recommendations.

    The risk_delta is positive when the option reduces risk:
    - risk_delta > 0: Option is safer (simulated score is lower)
    - risk_delta < 0: Option is riskier (simulated score is higher)
    - risk_delta = 0: No change in risk
    """

    shipment_id: str = Field(..., description="Shipment identifier")
    option_type: Literal["route", "payment_rail"] = Field(..., description="Type of option simulated")
    option_id: str = Field(..., description="Identifier of the simulated option")
    baseline_risk_score: int = Field(..., ge=0, le=100, description="Current risk score before simulation")
    simulated_risk_score: int = Field(..., ge=0, le=100, description="Projected risk score with this option")
    baseline_severity: str = Field(..., description="Current severity level")
    simulated_severity: str = Field(..., description="Projected severity level with this option")
    risk_delta: int = Field(..., description="Risk improvement (positive = safer, negative = riskier)")
    notes: list[str] = Field(default_factory=list, description="Simulation metadata and caveats")


class AtRiskShipmentSummary(BaseModel):
    """
    Summary of an at-risk shipment for fleet-level monitoring.

    Business Purpose:
    Enables operators to monitor fleet-wide risk exposure and prioritize interventions.
    Used in the Control Tower to identify shipments needing immediate attention.
    """

    shipment_id: str = Field(..., description="Unique shipment identifier")
    route: str = Field(..., description="Origin-destination route code")
    carrier_id: str = Field(..., description="Carrier identifier")
    corridor_code: str = Field(..., description="High-level corridor classification")
    risk_score: int = Field(..., ge=0, le=100, description="Current risk score (0-100)")
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., description="Risk severity category")
    days_in_transit: int = Field(..., ge=0, description="Current days in transit")
    shipment_value_usd: float = Field(..., ge=0, description="Shipment value in USD")
    completeness_pct: int = Field(..., ge=0, le=100, description="Data completeness percentage")
    blocking_gap_count: int = Field(..., ge=0, description="Number of critical data gaps")
    last_updated: str = Field(..., description="When this risk assessment was last updated (ISO-8601 UTC)")


class AtRiskShipmentsResponse(BaseModel):
    """
    Response containing list of at-risk shipments for fleet monitoring.

    Business Purpose:
    Provides prioritized list of shipments requiring operator attention.
    Enables fleet-level risk visibility and proactive intervention.
    """

    shipments: List[AtRiskShipmentSummary] = Field(..., description="List of at-risk shipments")
    total_count: int = Field(..., description="Total number of at-risk shipments matching criteria")
    min_risk_score: int = Field(..., description="Minimum risk score filter applied")
    max_results: int = Field(..., description="Maximum results limit applied")
