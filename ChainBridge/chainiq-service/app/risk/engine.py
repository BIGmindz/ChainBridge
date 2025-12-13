"""ChainIQ Risk Engine v1 (Maggie spec).

Deterministic, additive rules with transparent reasoning for each contribution.
"""

from app.risk.schemas import CarrierProfile, LaneProfile, RiskBand, RiskScoreResult, ShipmentFeatures

MODEL_VERSION = "chainiq_v1_maggie"


def compute_risk_score(
    shipment: ShipmentFeatures,
    carrier_profile: CarrierProfile,
    lane_profile: LaneProfile,
) -> RiskScoreResult:
    """Compute a risk score using Maggie's v1 weighted model."""

    score = 0.0
    reasons: list[str] = []

    # 1) Base score (route)
    base_risk = lane_profile.lane_risk_index * 60
    score += base_risk
    if base_risk > 20:
        reasons.append(f"Lane Risk Contribution: {int(base_risk)}")

    # 2) Static amplifiers (shipment + lane)
    if shipment.value_usd > 100_000:
        score += 15
        reasons.append("High Value (>$100k)")

    if shipment.is_hazmat:
        score += 10
        reasons.append("Hazmat Cargo")

    if shipment.is_temp_control:
        score += 5
        reasons.append("Temp Control Risk")

    if shipment.expected_transit_days > 10:
        score += 5
        reasons.append("Long Duration (>10 days)")

    if lane_profile.border_crossing_count > 0:
        points = min(15, lane_profile.border_crossing_count * 5)
        score += points
        reasons.append(f"Border Crossings (+{points})")

    # 3) Carrier performance
    if carrier_profile.incident_rate_90d > 0.05:
        score += 20
        reasons.append(f"High Carrier Incident Rate ({carrier_profile.incident_rate_90d:.1%})")
    elif carrier_profile.incident_rate_90d < 0.01 and carrier_profile.tenure_days > 365:
        score -= 10
        reasons.append("Trusted Carrier Discount")

    # 4) Dynamic triggers (real-time events)
    if shipment.recent_delay_events > 0:
        points = min(15, shipment.recent_delay_events * 5)
        score += points
        reasons.append(f"Recent Delays (+{points})")

    if shipment.iot_alert_count > 0:
        points = min(30, shipment.iot_alert_count * 10)
        score += points
        reasons.append(f"IoT Alerts (+{points})")

    # 5) Clamp and band
    final_score = max(0, min(100, int(score)))
    if final_score >= 70:
        band = RiskBand.HIGH
    elif final_score >= 40:
        band = RiskBand.MEDIUM
    else:
        band = RiskBand.LOW

    return RiskScoreResult(score=final_score, band=band, reasons=reasons, model_version=MODEL_VERSION)
