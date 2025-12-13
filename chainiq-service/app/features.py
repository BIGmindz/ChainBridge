"""
ChainIQ v0.1 - Feature Engineering

Transforms raw ShipmentRiskContext into model-ready features.

Author: Maggie (GID-10) - ML & Applied AI Lead
"""

from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np

from .schemas import ShipmentRiskContext

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================

# Distance buckets (in km)
DISTANCE_BUCKETS = {
    "SHORT": (0, 500),
    "MEDIUM": (500, 3000),
    "LONG": (3000, 10000),
    "ULTRA_LONG": (10000, float("inf")),
}

# Value buckets (in USD)
VALUE_BUCKETS = {
    "LOW": (0, 10_000),
    "MEDIUM": (10_000, 50_000),
    "HIGH": (50_000, 200_000),
    "VERY_HIGH": (200_000, float("inf")),
}

# Peak season months by hemisphere/trade pattern
PEAK_SEASON_MONTHS = {
    "retail": [10, 11, 12, 1, 2],  # Pre-holiday surge
    "produce": [4, 5, 6, 7, 8],  # Summer harvest
    "default": [11, 12, 1, 2],  # General retail peak
}

# Default historical rates when data is missing
DEFAULT_LANE_INCIDENT_RATE = 0.10
DEFAULT_CARRIER_INCIDENT_RATE = 0.08

# Estimated distances for common trade lanes (fallback)
LANE_DISTANCE_ESTIMATES = {
    ("CN", "US"): 11500,
    ("CN", "EU"): 20000,
    ("US", "EU"): 6500,
    ("CN", "JP"): 2000,
    ("US", "MX"): 2500,
    ("US", "CA"): 3000,
}


# =============================================================================
# FEATURE ENGINEERING FUNCTIONS
# =============================================================================


def bucket_distance(distance_km: Optional[float]) -> str:
    """Bucket distance into categorical."""
    if distance_km is None:
        return "UNKNOWN"
    for bucket_name, (low, high) in DISTANCE_BUCKETS.items():
        if low <= distance_km < high:
            return bucket_name
    return "ULTRA_LONG"


def bucket_value(value_usd: Optional[float]) -> str:
    """Bucket cargo value into categorical."""
    if value_usd is None:
        return "UNKNOWN"
    for bucket_name, (low, high) in VALUE_BUCKETS.items():
        if low <= value_usd < high:
            return bucket_name
    return "VERY_HIGH"


def estimate_distance(origin_country: str, destination_country: str) -> float:
    """Estimate distance when not provided."""
    key = (origin_country.upper(), destination_country.upper())
    reverse_key = (destination_country.upper(), origin_country.upper())

    if key in LANE_DISTANCE_ESTIMATES:
        return LANE_DISTANCE_ESTIMATES[key]
    if reverse_key in LANE_DISTANCE_ESTIMATES:
        return LANE_DISTANCE_ESTIMATES[reverse_key]

    # Very rough fallback based on cross-border
    if origin_country == destination_country:
        return 800  # Domestic average
    return 5000  # International average


def is_peak_season(month: int, commodity_type: Optional[str] = None) -> bool:
    """Determine if month is peak shipping season."""
    season_type = "default"
    if commodity_type:
        commodity_lower = commodity_type.lower()
        if any(kw in commodity_lower for kw in ["fruit", "vegetable", "produce", "food"]):
            season_type = "produce"
        elif any(kw in commodity_lower for kw in ["retail", "consumer", "electronics", "toys"]):
            season_type = "retail"

    return month in PEAK_SEASON_MONTHS.get(season_type, PEAK_SEASON_MONTHS["default"])


def compute_data_quality_score(context: ShipmentRiskContext) -> float:
    """
    Compute a quality score based on how many optional fields are provided.
    Higher score = more complete data = more confident predictions.
    """
    optional_fields = [
        ("carrier_code", 0.15),
        ("distance_km", 0.10),
        ("commodity_type", 0.10),
        ("value_usd", 0.15),
        ("prior_incident_rate_lane", 0.20),
        ("prior_incident_rate_carrier", 0.15),
        ("origin_region", 0.05),
        ("destination_region", 0.05),
        ("actual_departure", 0.05),
    ]

    score = 0.0
    for field_name, weight in optional_fields:
        value = getattr(context, field_name, None)
        if value is not None:
            score += weight

    # Bonus for having events
    if context.events and len(context.events) > 0:
        score += 0.05

    return min(1.0, score)


def engineer_features(context: ShipmentRiskContext) -> Dict[str, Any]:
    """
    Transform raw ShipmentRiskContext into model features.

    Returns a dictionary of feature name -> value pairs.
    """
    features = {}

    # === IDENTIFIERS (for logging, not model input) ===
    features["_shipment_id"] = context.shipment_id
    features["_tenant_id"] = context.tenant_id

    # === LANE FEATURES ===
    features["origin_country"] = context.origin_country.upper()
    features["destination_country"] = context.destination_country.upper()
    features["origin_region"] = context.origin_region or "UNKNOWN"
    features["destination_region"] = context.destination_region or "UNKNOWN"
    features["lane_id"] = context.derive_lane_id()

    # Distance
    if context.distance_km is not None:
        features["distance_km"] = context.distance_km
    else:
        features["distance_km"] = estimate_distance(context.origin_country, context.destination_country)
    features["distance_bucket"] = bucket_distance(features["distance_km"])

    # Cross-border flag
    features["is_cross_border"] = int(context.origin_country.upper() != context.destination_country.upper())

    # Historical lane rate
    features["lane_historical_delay_rate"] = (
        context.prior_incident_rate_lane if context.prior_incident_rate_lane is not None else DEFAULT_LANE_INCIDENT_RATE
    )

    # === CARRIER FEATURES ===
    features["carrier_code"] = context.carrier_code or "UNKNOWN"
    features["carrier_historical_delay_rate"] = (
        context.prior_incident_rate_carrier if context.prior_incident_rate_carrier is not None else DEFAULT_CARRIER_INCIDENT_RATE
    )

    # === MODE FEATURES ===
    features["mode"] = context.mode
    features["mode_ocean"] = int(context.mode == "OCEAN")
    features["mode_air"] = int(context.mode == "AIR")
    features["mode_truck"] = int(context.mode == "TRUCK")
    features["mode_rail"] = int(context.mode == "RAIL")
    features["mode_intermodal"] = int(context.mode == "INTERMODAL")

    # === TEMPORAL FEATURES ===
    features["departure_month"] = context.planned_departure.month
    features["departure_day_of_week"] = context.planned_departure.weekday()
    features["departure_quarter"] = (context.planned_departure.month - 1) // 3 + 1
    features["departure_hour"] = context.planned_departure.hour

    # Peak season
    features["is_peak_season"] = int(is_peak_season(context.planned_departure.month, context.commodity_type))

    # Transit duration
    transit_delta = context.planned_arrival - context.planned_departure
    features["transit_days_planned"] = max(0, transit_delta.days)
    features["transit_hours_planned"] = transit_delta.total_seconds() / 3600

    # Lead time (if we had booking date, we'd use it; placeholder)
    features["lead_time_days"] = 7  # Default assumption

    # === CARGO FEATURES ===
    features["commodity_type"] = context.commodity_type or "UNKNOWN"
    features["is_temperature_controlled"] = int(context.temperature_controlled or False)

    # Value
    features["value_usd"] = context.value_usd or 0
    features["value_bucket"] = bucket_value(context.value_usd)
    features["is_high_value"] = int((context.value_usd or 0) > 100_000)

    # Value density proxy
    if features["distance_km"] > 0:
        features["value_per_km"] = features["value_usd"] / features["distance_km"]
    else:
        features["value_per_km"] = 0

    # === EVENT FEATURES ===
    features["event_count"] = len(context.events)

    # Event type flags
    event_types = {e.type.upper() for e in context.events}
    features["has_customs_hold"] = int("CUSTOMS_HOLD" in event_types)
    features["has_port_congestion"] = int("PORT_CONGESTION" in event_types)
    features["has_temperature_alarm"] = int("TEMPERATURE_ALARM" in event_types)
    features["has_documentation_issue"] = int("DOCUMENTATION_ISSUE" in event_types)
    features["has_carrier_delay"] = int("CARRIER_DELAY" in event_types)
    features["has_vessel_delay"] = int("VESSEL_DELAY" in event_types)

    # Time since last event
    if context.events:
        latest_event = max(context.events, key=lambda e: e.timestamp)
        hours_since = (datetime.utcnow() - latest_event.timestamp).total_seconds() / 3600
        features["hours_since_last_event"] = max(0, hours_since)
    else:
        features["hours_since_last_event"] = -1  # No events

    # Departure delay (if actual departure is known)
    if context.actual_departure and context.planned_departure:
        delta_seconds = (context.actual_departure - context.planned_departure).total_seconds()
        features["departure_delay_hours"] = delta_seconds / 3600
    else:
        features["departure_delay_hours"] = 0

    # === CONTEXTUAL FEATURES ===
    features["seasonality_index"] = context.seasonality_index or 1.0
    features["data_completeness_score"] = compute_data_quality_score(context)

    return features


def features_to_array(features: Dict[str, Any], feature_names: list[str]) -> np.ndarray:
    """
    Convert feature dictionary to numpy array in specified order.

    Args:
        features: Dictionary from engineer_features()
        feature_names: Ordered list of feature names for model input

    Returns:
        1D numpy array ready for model.predict()
    """
    arr = np.zeros(len(feature_names), dtype=np.float32)

    for i, name in enumerate(feature_names):
        value = features.get(name, 0)

        # Handle string/categorical as 0 (they should be encoded separately)
        if isinstance(value, str):
            arr[i] = 0
        elif isinstance(value, bool):
            arr[i] = float(value)
        elif value is None:
            arr[i] = 0
        else:
            arr[i] = float(value)

    return arr


# =============================================================================
# FEATURE LIST FOR MODEL
# =============================================================================

# These are the numeric features the baseline model expects
MODEL_FEATURE_NAMES = [
    # Lane
    "distance_km",
    "is_cross_border",
    "lane_historical_delay_rate",
    # Carrier
    "carrier_historical_delay_rate",
    # Mode (one-hot)
    "mode_ocean",
    "mode_air",
    "mode_truck",
    "mode_rail",
    "mode_intermodal",
    # Temporal
    "departure_month",
    "departure_day_of_week",
    "departure_quarter",
    "is_peak_season",
    "transit_days_planned",
    # Cargo
    "is_temperature_controlled",
    "value_usd",
    "is_high_value",
    "value_per_km",
    # Events
    "event_count",
    "has_customs_hold",
    "has_port_congestion",
    "has_temperature_alarm",
    "has_documentation_issue",
    "has_carrier_delay",
    "departure_delay_hours",
    # Contextual
    "seasonality_index",
    "data_completeness_score",
]
