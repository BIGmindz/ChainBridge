import math

from api.services.chain_audit.fuzzy_engine import get_payout_confidence
from api.services.pricing.adjuster import calculate_final_settlement


def test_fuzzy_engine_scenario_a_high_confidence():
    score = get_payout_confidence(4.0, 10.0)
    assert score > 90


def test_fuzzy_engine_scenario_b_partial():
    score = get_payout_confidence(3.0, 120.0)
    assert 50 <= score <= 60


def test_adjuster_full_partial_blocked():
    settlement = calculate_final_settlement(100.0, {"max_temp_deviation": 1.0, "breach_duration_minutes": 5})
    assert settlement["status"] == "FULL_PAYMENT"
    assert settlement["final_payout"] == 100.0

    blocked = calculate_final_settlement(100.0, {"max_temp_deviation": 10.0, "breach_duration_minutes": 300})
    assert blocked["status"] == "BLOCKED"
    assert blocked["final_payout"] == 0.0

    partial = calculate_final_settlement(100.0, {"max_temp_deviation": 3.0, "breach_duration_minutes": 60})
    assert partial["status"] == "PARTIAL_SETTLEMENT"
    assert 0 < partial["final_payout"] < 100.0
    expected_penalty = (95 - partial["confidence_score"]) * 0.5
    expected_final = max(0.0, 100.0 - 100.0 * (expected_penalty / 100.0))
    assert math.isclose(partial["final_payout"], round(expected_final, 2))
