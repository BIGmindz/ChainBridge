"""
ChainBridge Tokenomics Engine — PAX (GID-05)
Implements deterministic, event-driven token reward, burn, and multiplier logic.
"""
import uuid
from typing import Dict, Any

# Milestone reward percentages
MILESTONE_REWARDS = {
    "PICKED_UP": 0.20,
    "IN_TRANSIT_STABLE": 0.70,
    "DELIVERED": 0.10,
}

# Risk multipliers
RISK_MULTIPLIERS = {
    "LOW": 1.10,   # +10%
    "MEDIUM": 1.00,
    "HIGH": 0.90,  # -10%
    "FAIL": 0.0,
}

# ML adjustment ranges
ML_ADJUSTMENTS = {
    "EARLY": 1.10,   # +10%
    "ON_TIME": 1.00,
    "LATE": 0.90,    # -10%
    "FRAUD": 0.0,
}

# Penalty burns
PENALTY_BURNS = {
    "LATE": 0.02,         # 2%
    "RISK_OVERRIDE": 0.05, # 5%
    "FRAUD": 1.0,         # 100%
}


def calculate_base_reward(event: str, base_amount: int) -> int:
    pct = MILESTONE_REWARDS.get(event, 0)
    return int(base_amount * pct)


def apply_risk_multiplier(amount: int, risk_score: str) -> float:
    multiplier = RISK_MULTIPLIERS.get(risk_score, 1.0)
    return amount * multiplier


def apply_ml_adjustments(amount: float, ml_prediction: str) -> float:
    adjustment = ML_ADJUSTMENTS.get(ml_prediction, 1.0)
    return amount * adjustment


def apply_penalty_burns(amount: float, event: str, risk_score: str, ml_prediction: str) -> int:
    burn_pct = 0.0
    if ml_prediction == "FRAUD":
        burn_pct = PENALTY_BURNS["FRAUD"]
    elif event == "DELIVERED" and risk_score == "HIGH":
        burn_pct = PENALTY_BURNS["RISK_OVERRIDE"]
    elif event == "DELIVERED" and ml_prediction == "LATE":
        burn_pct = PENALTY_BURNS["LATE"]
    burn_amount = int(amount * burn_pct)
    return burn_amount


def generate_token_event(
    event: str,
    base_amount: int,
    risk_score: str,
    ml_prediction: str,
    severity: str = "MEDIUM",
    rationale: str = "",
    trace_id: str = None
) -> Dict[str, Any]:
    if not trace_id:
        trace_id = str(uuid.uuid4())
    # Step 1: Base reward
    token_amount = calculate_base_reward(event, base_amount)
    # Step 2: Risk multiplier
    risk_multiplier = RISK_MULTIPLIERS.get(risk_score, 1.0)
    token_after_risk = int(token_amount * risk_multiplier)
    # Step 3: ML adjustment
    ml_adjustment = ML_ADJUSTMENTS.get(ml_prediction, 1.0)
    token_after_ml = int(token_after_risk * ml_adjustment)
    # Step 4: Penalty burns
    burn_amount = apply_penalty_burns(token_after_ml, event, risk_score, ml_prediction)
    # Step 5: Final amount
    final_amount = max(token_after_ml - burn_amount, 0)
    # Step 6: Rationale
    rationale = rationale or f"Event: {event}, Risk: {risk_score}, ML: {ml_prediction}"
    return {
        "token_amount": token_amount,
        "risk_multiplier": risk_multiplier,
        "ml_adjustment": ml_adjustment,
        "burn_amount": burn_amount,
        "final_amount": final_amount,
        "rationale": rationale,
        "severity": severity,
        "trace_id": trace_id,
    }


def issue_token(amount: int) -> None:
    """Stub for future XRPL issuance integration."""
    pass
