"""
Tokenomics Engine Unit Tests — PAX (GID-05)
"""
import pytest

from chainpay_service.app.tokenomics.token_engine import (
    apply_ml_adjustments,
    apply_penalty_burns,
    apply_risk_multiplier,
    calculate_base_reward,
    generate_token_event,
)

def test_low_risk_boost():
    result = generate_token_event(
        event="PICKED_UP",
        base_amount=1000,
        risk_score="LOW",
        ml_prediction="ON_TIME",
        severity="LOW",
        rationale="Low risk boost",
    )
    assert result["final_amount"] > 200

def test_high_risk_reduction():
    result = generate_token_event(
        event="IN_TRANSIT_STABLE",
        base_amount=1000,
        risk_score="HIGH",
        ml_prediction="ON_TIME",
        severity="HIGH",
        rationale="High risk reduction",
    )
    assert result["final_amount"] < 700

def test_risk_fail_zero():
    result = generate_token_event(
        event="DELIVERED",
        base_amount=1000,
        risk_score="FAIL",
        ml_prediction="ON_TIME",
        severity="CRITICAL",
        rationale="Risk fail zero",
    )
    assert result["final_amount"] == 0

def test_ml_early_bonus():
    result = generate_token_event(
        event="PICKED_UP",
        base_amount=1000,
        risk_score="MEDIUM",
        ml_prediction="EARLY",
        severity="MEDIUM",
        rationale="ML early bonus",
    )
    assert result["final_amount"] > 200

def test_ml_fraud_penalty():
    result = generate_token_event(
        event="DELIVERED",
        base_amount=1000,
        risk_score="MEDIUM",
        ml_prediction="FRAUD",
        severity="CRITICAL",
        rationale="ML fraud penalty",
    )
    assert result["final_amount"] == 0
    assert result["burn_amount"] == int(result["token_amount"] * 1.0)

def test_late_delivery_burn():
    result = generate_token_event(
        event="DELIVERED",
        base_amount=1000,
        risk_score="MEDIUM",
        ml_prediction="LATE",
        severity="MEDIUM",
        rationale="Late delivery burn",
    )
    assert result["burn_amount"] == int(result["token_amount"] * 0.02)

def test_milestone_payout_sequence():
    picked_up = generate_token_event("PICKED_UP", 1000, "MEDIUM", "ON_TIME")
    in_transit = generate_token_event("IN_TRANSIT_STABLE", 1000, "MEDIUM", "ON_TIME")
    delivered = generate_token_event("DELIVERED", 1000, "MEDIUM", "ON_TIME")
    total = picked_up["final_amount"] + in_transit["final_amount"] + delivered["final_amount"]
    assert total == 1000
