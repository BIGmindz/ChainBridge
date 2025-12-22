"""Phase 2: Fuzzy logic payout confidence tests.

These tests validate the fuzzy logic engine for calculating payout confidence scores.
"""
import pytest

# Namespace isolation handled by conftest.py pre-loading mechanism
from app.services.chain_audit.fuzzy_engine import get_payout_confidence
from app.services.pricing.adjuster import calculate_final_settlement

pytestmark = pytest.mark.phase2


def test_high_confidence_scenario():
    score = get_payout_confidence(4.0, 10.0)
    assert score > 90
    settlement = calculate_final_settlement(100.0, {"delta_temp_c": 1.0, "duration_mins": 10})
    assert settlement["status"] == "FULL_PAYMENT"


def test_partial_penalty_scenario():
    score = get_payout_confidence(4.0, 120.0)
    assert 40 <= score < 90
    settlement = calculate_final_settlement(100.0, {"delta_temp_c": 4.0, "duration_mins": 120})
    assert settlement["status"] in {"PARTIAL_SETTLEMENT", "BLOCKED"}
