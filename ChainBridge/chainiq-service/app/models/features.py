"""
Feature schema models for ChainIQ ML.

This module defines the canonical feature set used for ML risk and anomaly scoring.
All features are shipment-level attributes that have been normalized and enriched.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ShipmentFeaturesV0(BaseModel):
    """
    Shipment-level feature vector for ML risk and anomaly scoring.

    This schema represents the v0.1 feature set and will evolve as the ML pipeline matures.
    All numeric features should be normalized/scaled appropriately before training.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # IDENTIFIERS & CONTEXT
    # ─────────────────────────────────────────────────────────────────────────
    shipment_id: str = Field(description="Unique shipment identifier")
    corridor: str = Field(description="Trade corridor (e.g., 'US-MX', 'CN-NL')")
    origin_country: str = Field(description="ISO 3166-1 alpha-2 country code for origin")
    destination_country: str = Field(description="ISO 3166-1 alpha-2 country code for destination")
    mode: str = Field(description="Transport mode: air, ocean, rail, truck")
    commodity_category: str = Field(description="High-level commodity classification")
    financing_type: str = Field(description="Type of financing: LC, OA, DP, etc.")
    counterparty_risk_bucket: str = Field(description="Counterparty risk tier: low, medium, high")

    # ─────────────────────────────────────────────────────────────────────────
    # OPERATIONAL / TRANSIT
    # ─────────────────────────────────────────────────────────────────────────
    planned_transit_hours: float = Field(description="Planned transit time in hours")
    actual_transit_hours: Optional[float] = Field(default=None, description="Actual transit time (null if in-transit)")
    eta_deviation_hours: float = Field(description="Hours of deviation from ETA (can be negative)")
    num_route_deviations: int = Field(description="Count of route deviations detected")
    max_route_deviation_km: float = Field(description="Maximum single route deviation in km")
    total_dwell_hours: float = Field(description="Total cumulative dwell time")
    max_single_dwell_hours: float = Field(description="Longest single dwell event in hours")
    handoff_count: int = Field(description="Number of custody handoffs")
    max_custody_gap_hours: float = Field(description="Longest gap in custody chain tracking (hours)")
    delay_flag: int = Field(description="Binary flag: 1 if shipment is delayed, 0 otherwise")

    # ─────────────────────────────────────────────────────────────────────────
    # IoT / CONDITION MONITORING
    # ─────────────────────────────────────────────────────────────────────────
    has_iot_telemetry: int = Field(description="Binary flag: 1 if IoT sensors present, 0 otherwise")
    temp_mean: Optional[float] = Field(default=None, description="Mean temperature (°C) if IoT available")
    temp_std: Optional[float] = Field(default=None, description="Std dev of temperature if IoT available")
    temp_min: Optional[float] = Field(default=None, description="Min temperature if IoT available")
    temp_max: Optional[float] = Field(default=None, description="Max temperature if IoT available")
    temp_out_of_range_pct: Optional[float] = Field(default=None, description="% of time temp was out of acceptable range")
    sensor_uptime_pct: Optional[float] = Field(default=None, description="% uptime of IoT sensors during transit")

    # ─────────────────────────────────────────────────────────────────────────
    # DOCUMENTATION / COLLATERAL
    # ─────────────────────────────────────────────────────────────────────────
    doc_count: int = Field(description="Total number of documents attached to shipment")
    missing_required_docs: int = Field(description="Count of missing required documents")
    duplicate_doc_flag: int = Field(description="Binary flag: 1 if duplicate documents detected")
    doc_inconsistency_flag: int = Field(description="Binary flag: 1 if inconsistencies detected across documents")
    doc_age_days: float = Field(description="Average age of documents in days")
    collateral_value: float = Field(description="USD value of collateral backing shipment")
    collateral_value_bucket: str = Field(description="Discretized collateral range: low, medium, high")

    # ─────────────────────────────────────────────────────────────────────────
    # HISTORICAL / ENTITY BEHAVIOR
    # ─────────────────────────────────────────────────────────────────────────
    shipper_on_time_pct_90d: float = Field(description="% of shipments by this shipper delivered on-time in last 90d")
    carrier_on_time_pct_90d: float = Field(description="% of shipments by this carrier delivered on-time in last 90d")
    corridor_disruption_index_90d: float = Field(description="Normalized disruption index for this corridor over 90d")
    prior_exceptions_count_180d: int = Field(description="Count of exceptions for this shipper/corridor in last 180d")
    prior_losses_flag: int = Field(description="Binary flag: 1 if prior losses on this corridor/shipper")

    # ─────────────────────────────────────────────────────────────────────────
    # SENTIMENT / EXTERNAL SIGNALS
    # ─────────────────────────────────────────────────────────────────────────
    lane_sentiment_score: float = Field(description="Sentiment score [0,1] for this specific lane/corridor")
    macro_logistics_sentiment_score: float = Field(description="Global logistics sentiment score [0,1]")
    sentiment_trend_7d: float = Field(description="7-day trend of sentiment scores (can be negative if worsening)")
    sentiment_volatility_30d: float = Field(description="30-day rolling volatility of sentiment")
    sentiment_provider: str = Field(description="Name of sentiment data provider/stub")

    # ─────────────────────────────────────────────────────────────────────────
    # TRAINING LABELS (Optional – only present for historical training data)
    # ─────────────────────────────────────────────────────────────────────────
    realized_loss_flag: Optional[int] = Field(default=None, description="Binary label: 1 if shipment resulted in loss")
    loss_amount: Optional[float] = Field(default=None, description="USD amount of loss if realized_loss_flag=1")
    fraud_confirmed: Optional[int] = Field(default=None, description="Binary label: 1 if fraud was confirmed")
    severe_exception: Optional[int] = Field(default=None, description="Binary label: 1 if a severe exception occurred")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "shipment_id": "SH-2025-001234",
                "corridor": "US-MX",
                "origin_country": "US",
                "destination_country": "MX",
                "mode": "truck",
                "commodity_category": "electronics",
                "financing_type": "LC",
                "counterparty_risk_bucket": "medium",
                "planned_transit_hours": 48.0,
                "actual_transit_hours": 52.5,
                "eta_deviation_hours": 4.5,
                "num_route_deviations": 1,
                "max_route_deviation_km": 12.3,
                "total_dwell_hours": 6.0,
                "max_single_dwell_hours": 3.5,
                "handoff_count": 3,
                "max_custody_gap_hours": 2.0,
                "delay_flag": 1,
                "has_iot_telemetry": 1,
                "temp_mean": 22.5,
                "temp_std": 1.8,
                "temp_min": 18.0,
                "temp_max": 26.0,
                "temp_out_of_range_pct": 0.02,
                "sensor_uptime_pct": 0.98,
                "doc_count": 12,
                "missing_required_docs": 1,
                "duplicate_doc_flag": 0,
                "doc_inconsistency_flag": 0,
                "doc_age_days": 3.2,
                "collateral_value": 250000.0,
                "collateral_value_bucket": "medium",
                "shipper_on_time_pct_90d": 0.87,
                "carrier_on_time_pct_90d": 0.91,
                "corridor_disruption_index_90d": 0.35,
                "prior_exceptions_count_180d": 2,
                "prior_losses_flag": 0,
                "lane_sentiment_score": 0.30,
                "macro_logistics_sentiment_score": 0.45,
                "sentiment_trend_7d": -0.10,
                "sentiment_volatility_30d": 0.20,
                "sentiment_provider": "SentimentVendor_stub_v0",
            }
        }
