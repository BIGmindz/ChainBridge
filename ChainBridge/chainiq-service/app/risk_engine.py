"""
ChainIQ Risk Scoring Engine

Deterministic rule-based risk assessment for freight shipments.

Business Purpose:
Answers the question: "Should we release payment for this shipment, or is the risk too high?"

Scoring Factors:
- Route risk (high-risk corridors, sanctioned countries)
- Carrier reliability score
- Shipment value vs. historical norms
- Time in transit vs. expected ETA
- Documentation completeness
- Payment history of shipper

Risk Levels:
- LOW (0-29): Release payment immediately
- MEDIUM (30-59): Manual review recommended
- HIGH (60-79): Hold payment, request proof
- CRITICAL (80-100): Escalate to compliance team

Design Principles:
- Deterministic: Same input → Same output (no randomness)
- Fast: <10ms scoring time
- Transparent: Clear reason codes for every score
- Testable: All logic unit-testable
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from .schemas import IoTSignals, ShipmentRiskRequest

logger = logging.getLogger(__name__)

# Risk scoring constants
RISK_WEIGHTS = {
    "route_risk": 40,  # Sanctioned routes = critical compliance risk
    "carrier_reliability": 20,
    "value_anomaly": 20,
    "eta_deviation": 15,
    "documentation": 10,
    "payment_history": 10,
}


class RiskLevel:
    """Risk level classifications"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def _apply_iot_rules(
    base_score: int,
    reason_codes: List[str],
    iot_signals: Optional[IoTSignals],
) -> Tuple[int, List[str]]:
    """Apply IoT-derived risk adjustments in a transparent, glass-box way.

    This function encodes Maggie's initial IoT rules so that
    ChainSense signals can deterministically move the final risk score.
    """

    if iot_signals is None:
        return base_score, reason_codes

    score = float(base_score)

    # 1) Fresh Damage: any critical alert in last 24h → strong uplift
    if iot_signals.critical_count_24h > 0:
        score += 40
        reason_codes.append("IOT_FRESH_DAMAGE")

    # 2) Ghosting: no telemetry for a prolonged period
    #    >24h = critical, >4h = warning
    if iot_signals.silence_hours is not None:
        if iot_signals.silence_hours >= 24:
            score += 50
            reason_codes.append("IOT_GHOSTING_CRITICAL")
        elif iot_signals.silence_hours >= 4:
            score += 20
            reason_codes.append("IOT_GHOSTING_WARN")

    # 3) Corridor Chaos: systemic instability on the shipment's lane
    if iot_signals.corridor_instability_index is not None:
        if iot_signals.corridor_instability_index >= 0.7:
            score += 10
            reason_codes.append("IOT_CORRIDOR_CHAOS")

    # 4) Dying Battery: poor battery health increases risk of going dark
    if getattr(iot_signals, "battery_health_score", None) is not None:
        if iot_signals.battery_health_score < 0.3:
            score += 20
            reason_codes.append("IOT_DYING_BATTERY")

    # Clamp to sane bounds (0–100)
    score_clamped = max(0.0, min(score, 100.0))
    return int(score_clamped), reason_codes


def calculate_risk_score(
    route: str,
    carrier_id: str,
    shipment_value_usd: float,
    days_in_transit: int,
    expected_days: int,
    documents_complete: bool,
    shipper_payment_score: int,  # 0-100, higher is better
    *,
    request: Optional[ShipmentRiskRequest] = None,
) -> Tuple[int, str, List[str], str]:
    """
    Calculate risk score for a shipment.

    Args:
        route: Origin-destination route (e.g., "CN-US", "DE-UK")
        carrier_id: Carrier identifier
        shipment_value_usd: Shipment value in USD
        days_in_transit: Current days in transit
        expected_days: Expected transit days
        documents_complete: Whether all documents are complete
        shipper_payment_score: Shipper's payment reliability (0-100)

    Returns:
        Tuple of (risk_score, severity, reason_codes, recommended_action)

    Example:
        >>> score, severity, reasons, action = calculate_risk_score(
        ...     route="IR-RU",
        ...     carrier_id="CARRIER-001",
        ...     shipment_value_usd=50000,
        ...     days_in_transit=5,
        ...     expected_days=7,
        ...     documents_complete=False,
        ...     shipper_payment_score=40
        ... )
        >>> score >= 60  # HIGH risk
        True
    """
    risk_score = 0
    reason_codes: List[str] = []

    # 1. Route Risk (0-40 points)
    # Sanctioned countries get maximum route risk
    sanctioned_routes = {"IR-", "-IR", "RU-", "-RU", "KP-", "-KP", "SY-", "-SY"}
    high_risk_routes = {"AF-", "-AF", "SD-", "-SD", "YE-", "-YE"}

    route_points = 0
    if any(pattern in route for pattern in sanctioned_routes):
        route_points = 40
        reason_codes.append("HIGH_RISK_ROUTE")
    elif any(pattern in route for pattern in high_risk_routes):
        route_points = 20
        reason_codes.append("MEDIUM_RISK_ROUTE")

    risk_score += route_points

    # 2. Carrier Reliability (0-20 points)
    # Inverted: unreliable carriers score higher
    known_unreliable_carriers = {"CARRIER-999", "CARRIER-UNKNOWN"}

    carrier_points = 0
    if carrier_id in known_unreliable_carriers:
        carrier_points = 20
        reason_codes.append("UNRELIABLE_CARRIER")
    elif carrier_id.startswith("CARRIER-NEW-"):
        carrier_points = 10
        reason_codes.append("NEW_CARRIER")

    risk_score += carrier_points

    # 3. Value Anomaly (0-20 points)
    # Flag unusually high values (>=$100k)
    value_points = 0
    if shipment_value_usd >= 100000:
        value_points = 20
        reason_codes.append("HIGH_VALUE_SHIPMENT")
    elif shipment_value_usd >= 50000:
        value_points = 10
        reason_codes.append("ELEVATED_VALUE")

    risk_score += value_points

    # 4. ETA Deviation (0-15 points)
    eta_deviation = days_in_transit - expected_days

    eta_points = 0
    if eta_deviation > 3:
        eta_points = 15
        reason_codes.append("SIGNIFICANT_DELAY")
    elif eta_deviation > 1:
        eta_points = 8
        reason_codes.append("MINOR_DELAY")
    elif eta_deviation < -2:
        # Suspiciously early (possible fraud)
        eta_points = 12
        reason_codes.append("SUSPICIOUSLY_EARLY")

    risk_score += eta_points

    # 5. Documentation Completeness (0-10 points)
    doc_points = 0
    if not documents_complete:
        doc_points = 10
        reason_codes.append("INCOMPLETE_DOCUMENTATION")

    risk_score += doc_points

    # 6. Payment History (0-10 points)
    # Inverted: bad payment history scores higher
    payment_points = 0
    if shipper_payment_score < 30:
        payment_points = 10
        reason_codes.append("POOR_PAYMENT_HISTORY")
    elif shipper_payment_score < 60:
        payment_points = 5
        reason_codes.append("FAIR_PAYMENT_HISTORY")

    risk_score += payment_points

    # 7. IoT-derived adjustments (if IoT signals provided)
    iot_signals = request.iot_signals if request is not None else None
    risk_score, reason_codes = _apply_iot_rules(risk_score, reason_codes, iot_signals)

    # Determine severity
    if risk_score < 30:
        severity = RiskLevel.LOW
        recommended_action = "RELEASE_PAYMENT"
    elif risk_score < 60:
        severity = RiskLevel.MEDIUM
        recommended_action = "MANUAL_REVIEW"
    elif risk_score < 80:
        severity = RiskLevel.HIGH
        recommended_action = "HOLD_PAYMENT"
    else:
        severity = RiskLevel.CRITICAL
        recommended_action = "ESCALATE_COMPLIANCE"

    # Log the scoring decision
    logger.info(
        "Risk score calculated: score=%d, severity=%s, reasons=%s",
        risk_score,
        severity,
        ",".join(reason_codes) if reason_codes else "NONE",
    )

    return risk_score, severity, reason_codes, recommended_action
