"""
ChainIQ v0.1 - Explanation Engine

Generates human-readable explanations from model outputs.

Author: Maggie (GID-10) - ML & Applied AI Lead
"""

from typing import Any, Dict, List, Optional

import numpy as np

from .schemas import ShipmentRiskContext, TopFactor

# =============================================================================
# HUMAN-READABLE FEATURE LABELS
# =============================================================================

FEATURE_LABELS = {
    # Lane features
    "distance_km": "Route distance of {value:,.0f} km",
    "is_cross_border": "Cross-border shipment requiring customs",
    "lane_historical_delay_rate": "Lane historically experiences {value:.0%} delays",
    # Carrier features
    "carrier_historical_delay_rate": "Carrier has {value:.0%} historical delay rate",
    # Mode features
    "mode_ocean": "Ocean freight (longer transit, port dependencies)",
    "mode_air": "Air freight (faster but weather-sensitive)",
    "mode_truck": "Truck freight (road conditions, driver availability)",
    "mode_rail": "Rail freight (schedule-dependent)",
    "mode_intermodal": "Intermodal shipment (multiple handoffs)",
    # Temporal features
    "departure_month": "Departure in month {value}",
    "departure_day_of_week": "Departure on weekday {value}",
    "is_peak_season": "Peak shipping season (November-February)",
    "transit_days_planned": "Long transit time ({value:.0f} days planned)",
    # Cargo features
    "is_temperature_controlled": "Temperature-controlled cargo (higher complexity)",
    "value_usd": "High-value cargo (${value:,.0f})",
    "is_high_value": "High-value shipment (>$100K)",
    "value_per_km": "Value density of ${value:.2f}/km",
    # Event features
    "event_count": "{value:.0f} events recorded on this shipment",
    "has_customs_hold": "Customs hold event detected",
    "has_port_congestion": "Port congestion event detected",
    "has_temperature_alarm": "Temperature alarm event detected",
    "has_documentation_issue": "Documentation issue event detected",
    "has_carrier_delay": "Carrier delay event detected",
    "departure_delay_hours": "Departure already delayed by {value:.1f} hours",
    # Contextual
    "seasonality_index": "Seasonal risk factor of {value:.2f}",
    "data_completeness_score": "Data quality score of {value:.0%}",
}

# Inverse labels for when feature DECREASES risk
FEATURE_LABELS_INVERSE = {
    "lane_historical_delay_rate": "Lane has low {value:.0%} historical delay rate",
    "carrier_historical_delay_rate": "Carrier has excellent {value:.0%} on-time rate",
    "is_peak_season": "Off-peak shipping season (lower congestion)",
    "data_completeness_score": "Complete shipment data available ({value:.0%})",
    "transit_days_planned": "Short transit time ({value:.0f} days)",
}


# =============================================================================
# EXPLANATION GENERATION
# =============================================================================


def get_human_label(
    feature_name: str,
    feature_value: Any,
    direction: str,
) -> str:
    """
    Generate human-readable label for a feature contribution.

    Args:
        feature_name: Internal feature name
        feature_value: Raw feature value
        direction: "INCREASES_RISK" or "DECREASES_RISK"

    Returns:
        Human-readable explanation string
    """
    # Choose template based on direction
    if direction == "DECREASES_RISK" and feature_name in FEATURE_LABELS_INVERSE:
        template = FEATURE_LABELS_INVERSE[feature_name]
    elif feature_name in FEATURE_LABELS:
        template = FEATURE_LABELS[feature_name]
    else:
        # Fallback: convert snake_case to Title Case
        readable_name = feature_name.replace("_", " ").title()
        template = f"{readable_name}: {{value}}"

    # Format the template
    try:
        # Handle boolean features
        if isinstance(feature_value, bool) or feature_value in (0, 1, 0.0, 1.0):
            if "{value" in template:
                return template.format(value=feature_value)
            return template

        return template.format(value=feature_value)
    except (ValueError, KeyError):
        return f"{feature_name} = {feature_value}"


def extract_top_factors(
    shap_values: np.ndarray,
    feature_names: List[str],
    feature_values: Dict[str, Any],
    top_n: int = 5,
    min_magnitude: float = 1.0,
) -> List[TopFactor]:
    """
    Convert SHAP values into human-readable TopFactor explanations.

    Args:
        shap_values: 1D array of SHAP contributions for each feature
        feature_names: Ordered list of feature names
        feature_values: Dictionary of feature name -> raw value
        top_n: Maximum number of factors to return
        min_magnitude: Minimum magnitude (%) to include

    Returns:
        List of TopFactor objects, sorted by magnitude descending
    """
    if shap_values.ndim > 1:
        shap_values = shap_values[0]  # Take first sample

    # Calculate total SHAP for normalization
    abs_shap = np.abs(shap_values)
    total_shap = abs_shap.sum()

    if total_shap < 1e-8:
        # Edge case: no meaningful SHAP values
        return [
            TopFactor(
                feature_name="baseline",
                direction="INCREASES_RISK",
                magnitude=100.0,
                human_label="Baseline risk level for this shipment type",
            )
        ]

    # Get indices sorted by absolute SHAP value
    sorted_indices = np.argsort(abs_shap)[::-1]

    factors = []
    for idx in sorted_indices[: top_n * 2]:  # Get extra to filter by magnitude
        feat_name = feature_names[idx]
        shap_val = shap_values[idx]
        raw_val = feature_values.get(feat_name, 0)

        # Determine direction
        direction = "INCREASES_RISK" if shap_val > 0 else "DECREASES_RISK"

        # Calculate magnitude as percentage of total
        magnitude = (abs(shap_val) / total_shap * 100) if total_shap > 0 else 0

        # Skip if below threshold
        if magnitude < min_magnitude:
            continue

        # Generate human label
        human_label = get_human_label(feat_name, raw_val, direction)

        factors.append(
            TopFactor(
                feature_name=feat_name,
                direction=direction,
                magnitude=round(magnitude, 1),
                human_label=human_label,
            )
        )

        if len(factors) >= top_n:
            break

    return factors


def generate_summary_reason(
    risk_score: float,
    decision: str,
    top_factors: List[TopFactor],
    context: Optional[ShipmentRiskContext] = None,
) -> str:
    """
    Generate natural language summary of the risk assessment.

    Args:
        risk_score: Overall risk score (0-100)
        decision: Decision string (APPROVE, HOLD, etc.)
        top_factors: List of TopFactor explanations
        context: Original shipment context (optional, for enrichment)

    Returns:
        Human-readable summary string (max 500 chars)
    """
    # Risk level descriptor
    if risk_score < 30:
        risk_level = "Low risk"
    elif risk_score < 50:
        risk_level = "Moderate risk"
    elif risk_score < 70:
        risk_level = "Elevated risk"
    elif risk_score < 85:
        risk_level = "High risk"
    else:
        risk_level = "Critical risk"

    # Extract top increasing and decreasing factors
    increasing = [f for f in top_factors if f.direction == "INCREASES_RISK"][:2]
    decreasing = [f for f in top_factors if f.direction == "DECREASES_RISK"][:1]

    # Build summary parts
    parts = [f"{risk_level} ({risk_score:.0f}/100)"]

    if increasing:
        drivers = " and ".join([f.human_label.lower() for f in increasing])
        parts.append(f"driven by {drivers}")

    if decreasing:
        parts.append(f"Partially offset by {decreasing[0].human_label.lower()}")

    # Decision rationale
    decision_rationale = {
        "APPROVE": "Recommend standard payment terms.",
        "TIGHTEN_TERMS": "Recommend tightened payment terms or milestone holds.",
        "HOLD": "Recommend manual review before proceeding.",
        "ESCALATE": "Requires senior review due to critical risk indicators.",
    }
    parts.append(decision_rationale.get(decision, ""))

    # Combine and truncate
    summary = " ".join(parts)
    if len(summary) > 500:
        summary = summary[:497] + "..."

    return summary


def generate_risk_tags(
    context: ShipmentRiskContext,
    features: Dict[str, Any],
    risk_score: float,
) -> List[str]:
    """
    Generate semantic tags for filtering and grouping.

    Args:
        context: Original shipment context
        features: Engineered features dictionary
        risk_score: Overall risk score (0-100)

    Returns:
        List of tag strings
    """
    tags = []

    # Value-based tags
    if (context.value_usd or 0) > 100_000:
        tags.append("HIGH_VALUE")
    elif (context.value_usd or 0) > 50_000:
        tags.append("MEDIUM_VALUE")

    # Lane volatility
    if features.get("lane_historical_delay_rate", 0) > 0.15:
        tags.append("LANE_VOLATILE")
    elif features.get("lane_historical_delay_rate", 0) > 0.10:
        tags.append("LANE_MODERATE_RISK")

    # Seasonal
    if features.get("is_peak_season"):
        tags.append("PEAK_SEASON")

    # Event-based tags
    if features.get("has_customs_hold"):
        tags.append("CUSTOMS_RISK")
    if features.get("has_port_congestion"):
        tags.append("PORT_CONGESTION")
    if features.get("has_temperature_alarm"):
        tags.append("TEMPERATURE_ALERT")
    if features.get("has_documentation_issue"):
        tags.append("DOCUMENTATION_ISSUE")

    # Mode-specific tags
    if context.mode == "OCEAN" and features.get("transit_days_planned", 0) > 25:
        tags.append("LONG_HAUL_OCEAN")
    elif context.mode == "AIR":
        tags.append("AIR_FREIGHT")

    # Temperature controlled
    if context.temperature_controlled:
        tags.append("TEMP_CONTROLLED")

    # Risk level tags
    if risk_score >= 80:
        tags.append("CRITICAL_RISK")
    elif risk_score >= 60:
        tags.append("HIGH_RISK")
    elif risk_score >= 40:
        tags.append("MEDIUM_RISK")
    else:
        tags.append("LOW_RISK")

    # Data quality
    if features.get("data_completeness_score", 1) < 0.5:
        tags.append("INCOMPLETE_DATA")

    return tags


# =============================================================================
# CONFIDENCE ESTIMATION
# =============================================================================


def estimate_decision_confidence(
    risk_score: float,
    data_quality: float,
    decision: str,
    threshold_margins: Dict[str, float],
) -> float:
    """
    Estimate confidence in the decision based on margin from thresholds.

    Args:
        risk_score: Overall risk score (0-100)
        data_quality: Data completeness score (0-1)
        decision: The decision made
        threshold_margins: Dict with decision threshold values

    Returns:
        Confidence score (0-1)
    """
    # Base confidence from data quality
    base_confidence = 0.5 + (data_quality * 0.3)

    # Margin-based confidence adjustment
    # The further from a threshold, the more confident
    approve_max = threshold_margins.get("approve_max", 30)
    tighten_max = threshold_margins.get("tighten_terms_max", 70)
    hold_max = threshold_margins.get("hold_max", 85)

    if decision == "APPROVE":
        margin = (approve_max - risk_score) / approve_max if risk_score < approve_max else 0
        margin_bonus = margin * 0.2
    elif decision == "TIGHTEN_TERMS":
        # Distance from either threshold
        margin = min(abs(risk_score - approve_max), abs(risk_score - tighten_max)) / (tighten_max - approve_max)
        margin_bonus = margin * 0.15
    elif decision == "HOLD":
        margin = (hold_max - risk_score) / (hold_max - tighten_max) if risk_score < hold_max else 0
        margin_bonus = margin * 0.1
    else:  # ESCALATE
        margin = (risk_score - hold_max) / (100 - hold_max) if risk_score > hold_max else 0
        margin_bonus = margin * 0.15

    confidence = min(0.95, base_confidence + margin_bonus)
    return round(confidence, 2)
