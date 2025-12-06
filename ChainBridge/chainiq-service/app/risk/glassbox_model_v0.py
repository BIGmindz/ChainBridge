# app/risk/glassbox_model_v0.py
from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class RuleContribution(TypedDict):
    rule_id: str
    description: str
    contribution: int


class RiskScoreResult(TypedDict):
    risk_score: int                 # 0–100
    risk_band: str                  # "LOW" | "MEDIUM" | "HIGH"
    input_snapshot: Dict[str, Any]
    rules_fired: List[RuleContribution]
    explanation: Dict[str, Any]


# Simple config for v0 (easy to tweak, versioned by code hash/semver)
LANE_RISK_WEIGHTS = {
    "HIGH_RISK": 30,
    "MEDIUM_RISK": 15,
    "LOW_RISK": 0,
}

AMOUNT_WEIGHTS = {
    "SMALL": 0,
    "MEDIUM": 10,
    "LARGE": 20,
}

HISTORY_WEIGHTS = {
    "HAS_DISPUTES": 20,
    "HAS_LATE_DELIVERIES": 10,
}


def classify_lane(shipment: Dict[str, Any]) -> str:
    # TODO: for now, use simple region-based classifier or placeholder
    # e.g., treat certain countries/regions as HIGH_RISK.
    # In v0, just return "MEDIUM_RISK" as a safe default if nothing is known.
    origin = shipment.get("origin_country")
    destination = shipment.get("destination_country")

    # placeholder logic
    high_risk_countries = {"XYZ"}  # to be defined
    if origin in high_risk_countries or destination in high_risk_countries:
        return "HIGH_RISK"
    return "MEDIUM_RISK"


def classify_amount(shipment: Dict[str, Any]) -> str:
    amount = shipment.get("amount", 0)
    if amount < 10000:
        return "SMALL"
    if amount < 100000:
        return "MEDIUM"
    return "LARGE"


def score_shipment_risk(shipment: Dict[str, Any], context: Dict[str, Any]) -> RiskScoreResult:
    """
    Deterministic, glass-box risk score for a single shipment.

    This is ChainIQ Risk v0. It must remain interpretable and map directly into DecisionLog fields.
    See CHAINIQ_GLASSBOX_RISK_V0.md and CHAINBRIDGE_AUDIT_PROOFPACK_SPEC.md for semantics.
    """
    rules: List[RuleContribution] = []
    total_score = 0

    # Lane risk
    lane_category = classify_lane(shipment)
    lane_weight = LANE_RISK_WEIGHTS.get(lane_category, LANE_RISK_WEIGHTS["MEDIUM_RISK"])
    total_score += lane_weight
    rules.append(
        {
            "rule_id": f"LANE_{lane_category}",
            "description": f"Lane classified as {lane_category}",
            "contribution": lane_weight,
        }
    )

    # Amount
    amount_band = classify_amount(shipment)
    amount_weight = AMOUNT_WEIGHTS.get(amount_band, 0)
    total_score += amount_weight
    rules.append(
        {
            "rule_id": f"AMOUNT_{amount_band}",
            "description": f"Shipment amount classified as {amount_band}",
            "contribution": amount_weight,
        }
    )

    # History flags from context (disputes, late deliveries)
    has_disputes = bool(context.get("has_disputes", False))
    has_late_deliveries = bool(context.get("has_late_deliveries", False))

    if has_disputes:
        w = HISTORY_WEIGHTS["HAS_DISPUTES"]
        total_score += w
        rules.append(
            {
                "rule_id": "HISTORY_HAS_DISPUTES",
                "description": "Counterparty has dispute history",
                "contribution": w,
            }
        )

    if has_late_deliveries:
        w = HISTORY_WEIGHTS["HAS_LATE_DELIVERIES"]
        total_score += w
        rules.append(
            {
                "rule_id": "HISTORY_HAS_LATE_DELIVERIES",
                "description": "Counterparty has late delivery history",
                "contribution": w,
            }
        )

    # Clamp score to [0, 100]
    risk_score = max(0, min(int(total_score), 100))

    if risk_score < 35:
        band = "LOW"
    elif risk_score < 70:
        band = "MEDIUM"
    else:
        band = "HIGH"

    input_snapshot = {
        "lane_category": lane_category,
        "amount_band": amount_band,
        "amount": shipment.get("amount"),
        "origin_country": shipment.get("origin_country"),
        "destination_country": shipment.get("destination_country"),
        "has_disputes": has_disputes,
        "has_late_deliveries": has_late_deliveries,
    }

    explanation: Dict[str, Any] = {
        "summary": f"Risk scored as {risk_score} ({band}) based on lane, amount, and history.",
        "details": {
            "rules_fired_count": len(rules),
        },
    }

    return {
        "risk_score": risk_score,
        "risk_band": band,
        "input_snapshot": input_snapshot,
        "rules_fired": rules,
        "explanation": explanation,
    }
