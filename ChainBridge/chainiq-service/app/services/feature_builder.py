"""
Feature builder for ChainIQ ML.

Transforms raw shipment data into the canonical ShipmentFeaturesV0 schema,
enriching with sentiment data and normalizing fields.
"""

from typing import Any, Dict

from app.models.features import ShipmentFeaturesV0
from app.services.sentiment_adapter import SentimentAdapter


class FeatureBuilder:
    """
    Builds ML feature vectors from raw shipment data.

    Responsibilities:
    - Extract and normalize features from raw shipment dictionaries
    - Enrich with external data sources (sentiment, weather, etc.)
    - Validate and type-check all features
    - Return standardized ShipmentFeaturesV0 instances
    """

    def __init__(self, sentiment_adapter: SentimentAdapter | None = None):
        """
        Initialize the feature builder.

        Args:
            sentiment_adapter: Sentiment data provider. If None, uses default stub adapter.
        """
        self.sentiment_adapter = sentiment_adapter or SentimentAdapter()

    def build_features(self, raw_shipment: Dict[str, Any]) -> ShipmentFeaturesV0:
        """
        Build a complete feature vector from raw shipment data.

        This method:
        1. Extracts all base features from raw_shipment
        2. Calls sentiment adapter to enrich with sentiment data
        3. Constructs and validates ShipmentFeaturesV0

        Args:
            raw_shipment: Dictionary containing raw shipment data.
                         Must include at minimum: shipment_id, corridor, and all
                         required fields from ShipmentFeaturesV0 schema.

        Returns:
            Fully populated ShipmentFeaturesV0 instance

        Raises:
            KeyError: If required fields are missing from raw_shipment
            ValidationError: If fields don't match expected types/constraints
        """
        # Extract corridor for sentiment lookup
        corridor = raw_shipment["corridor"]

        # Get sentiment data for this corridor
        sentiment = self.sentiment_adapter.get_lane_sentiment(corridor)

        # Build the complete feature vector
        # Note: We assume raw_shipment is already normalized with correct types.
        # In production, you may want to add additional parsing/validation here.
        features = ShipmentFeaturesV0(
            # Identifiers & context
            shipment_id=raw_shipment["shipment_id"],
            corridor=corridor,
            origin_country=raw_shipment["origin_country"],
            destination_country=raw_shipment["destination_country"],
            mode=raw_shipment["mode"],
            commodity_category=raw_shipment["commodity_category"],
            financing_type=raw_shipment["financing_type"],
            counterparty_risk_bucket=raw_shipment["counterparty_risk_bucket"],
            # Operational / transit
            planned_transit_hours=raw_shipment["planned_transit_hours"],
            actual_transit_hours=raw_shipment.get("actual_transit_hours"),
            eta_deviation_hours=raw_shipment["eta_deviation_hours"],
            num_route_deviations=raw_shipment["num_route_deviations"],
            max_route_deviation_km=raw_shipment["max_route_deviation_km"],
            total_dwell_hours=raw_shipment["total_dwell_hours"],
            max_single_dwell_hours=raw_shipment["max_single_dwell_hours"],
            handoff_count=raw_shipment["handoff_count"],
            max_custody_gap_hours=raw_shipment["max_custody_gap_hours"],
            delay_flag=raw_shipment["delay_flag"],
            # IoT / condition
            has_iot_telemetry=raw_shipment["has_iot_telemetry"],
            temp_mean=raw_shipment.get("temp_mean"),
            temp_std=raw_shipment.get("temp_std"),
            temp_min=raw_shipment.get("temp_min"),
            temp_max=raw_shipment.get("temp_max"),
            temp_out_of_range_pct=raw_shipment.get("temp_out_of_range_pct"),
            sensor_uptime_pct=raw_shipment.get("sensor_uptime_pct"),
            # Documentation / collateral
            doc_count=raw_shipment["doc_count"],
            missing_required_docs=raw_shipment["missing_required_docs"],
            duplicate_doc_flag=raw_shipment["duplicate_doc_flag"],
            doc_inconsistency_flag=raw_shipment["doc_inconsistency_flag"],
            doc_age_days=raw_shipment["doc_age_days"],
            collateral_value=raw_shipment["collateral_value"],
            collateral_value_bucket=raw_shipment["collateral_value_bucket"],
            # Historical
            shipper_on_time_pct_90d=raw_shipment["shipper_on_time_pct_90d"],
            carrier_on_time_pct_90d=raw_shipment["carrier_on_time_pct_90d"],
            corridor_disruption_index_90d=raw_shipment["corridor_disruption_index_90d"],
            prior_exceptions_count_180d=raw_shipment["prior_exceptions_count_180d"],
            prior_losses_flag=raw_shipment["prior_losses_flag"],
            # Sentiment (from adapter)
            lane_sentiment_score=sentiment.lane_sentiment_score,
            macro_logistics_sentiment_score=sentiment.macro_logistics_sentiment_score,
            sentiment_trend_7d=sentiment.sentiment_trend_7d,
            sentiment_volatility_30d=sentiment.sentiment_volatility_30d,
            sentiment_provider=sentiment.sentiment_provider,
            # Training labels (optional)
            realized_loss_flag=raw_shipment.get("realized_loss_flag"),
            loss_amount=raw_shipment.get("loss_amount"),
            fraud_confirmed=raw_shipment.get("fraud_confirmed"),
            severe_exception=raw_shipment.get("severe_exception"),
        )

        return features
