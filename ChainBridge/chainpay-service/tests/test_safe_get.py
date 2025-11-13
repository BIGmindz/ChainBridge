"""
Tests for the _safe_get utility function used in ChainPay service.
"""

from app.chainfreight_client import _safe_get, _safe_extract_risk_data
from app.payment_rails import _safe_get as payment_safe_get


def test_safe_get_with_dict() -> None:
    """Test _safe_get with dictionary input."""
    data = {"risk_score": 0.45, "risk_category": "medium", "status": "active"}

    assert _safe_get(data, "risk_score") == 0.45
    assert _safe_get(data, "risk_category") == "medium"
    assert _safe_get(data, "status") == "active"
    assert _safe_get(data, "missing_key") == 0.0  # default
    assert _safe_get(data, "missing_key", "custom") == "custom"


def test_safe_get_with_numeric() -> None:
    """Test _safe_get with numeric input (handles upstream raw floats)."""
    assert _safe_get(0.75, "any_key") == 0.75
    assert _safe_get(42, "any_key") == 42
    assert _safe_get(3.14, "any_key") == 3.14


def test_safe_get_with_none_or_invalid() -> None:
    """Test _safe_get with None or invalid input."""
    assert _safe_get(None, "key") == 0.0
    assert _safe_get("string", "key") == 0.0
    assert _safe_get([], "key") == 0.0
    assert _safe_get({}, "missing", "fallback") == "fallback"


def test_safe_extract_risk_data() -> None:
    """Test the safe risk data extraction function."""
    # Normal API response
    data = {"id": 1, "risk_score": 0.35, "risk_category": "medium", "status": "active"}
    risk_score, risk_category = _safe_extract_risk_data(data)
    assert risk_score == 0.35
    assert risk_category == "medium"

    # Missing risk data
    data_missing = {"id": 1, "status": "active"}
    risk_score, risk_category = _safe_extract_risk_data(data_missing)
    assert risk_score is None
    assert risk_category is None

    # Invalid risk score format
    data_invalid = {
        "risk_score": "invalid",
        "risk_category": 123,
    }  # non-string category
    risk_score, risk_category = _safe_extract_risk_data(data_invalid)
    assert risk_score is None
    assert risk_category == "123"  # converted to string


def test_safe_get_consistency_across_modules() -> None:
    """Ensure _safe_get works consistently across different modules."""
    test_data = {"value": 42.5, "text": "hello"}

    # Both module versions should work the same
    assert _safe_get(test_data, "value") == payment_safe_get(test_data, "value")
    assert _safe_get(test_data, "text") == payment_safe_get(test_data, "text")
    assert _safe_get(test_data, "missing", "default") == payment_safe_get(
        test_data, "missing", "default"
    )


def test_real_world_api_scenarios() -> None:
    """Test scenarios that might occur with real API responses."""
    # ChainIQ returns varying response formats
    chainiq_response_1 = {
        "risk_score": 0.67,
        "risk_category": "high",
        "recommended_action": "manual_review",
    }

    # Sometimes ChainIQ might return just a score
    chainiq_response_2 = 0.23  # Raw float

    # Sometimes missing or null
    chainiq_response_3 = {
        "risk_score": None,
        "risk_category": None,
        "error": "service_unavailable",
    }

    # Test extraction from normal response
    risk_score, risk_category = _safe_extract_risk_data(chainiq_response_1)
    assert risk_score == 0.67
    assert risk_category == "high"

    # Test extraction when some fields are missing/null
    risk_score, risk_category = _safe_extract_risk_data(chainiq_response_3)
    assert risk_score is None
    assert risk_category is None

    # Test handling of numeric input (if ChainIQ returns raw score)
    score_from_raw = _safe_get(chainiq_response_2, "any_key", 0.5)
    assert score_from_raw == 0.23


def test_payment_provider_response_handling() -> None:
    """Test safe handling of payment provider responses."""
    # Stripe response format
    stripe_response = {
        "id": "payout_1234",
        "amount": 100000,
        "currency": "usd",
        "status": "paid",
        "arrival_date": 1699884000,
    }  # cents

    # Extract using _safe_get from payment_rails
    amount_cents = payment_safe_get(stripe_response, "amount", 0)
    status = payment_safe_get(stripe_response, "status", "unknown")
    missing_field = payment_safe_get(stripe_response, "error_code", "none")

    assert amount_cents == 100000
    assert status == "paid"
    assert missing_field == "none"


if __name__ == "__main__":
    # Run tests if script executed directly
    test_safe_get_with_dict()
    test_safe_get_with_numeric()
    test_safe_get_with_none_or_invalid()
    test_safe_extract_risk_data()
    test_safe_get_consistency_across_modules()
    test_real_world_api_scenarios()
    test_payment_provider_response_handling()
    print("✅ All _safe_get tests passed!")
