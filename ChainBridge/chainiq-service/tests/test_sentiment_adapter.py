"""Tests for sentiment adapter."""

import pytest

from app.services.sentiment_adapter import SentimentAdapter, SentimentSnapshot


def test_sentiment_adapter_us_mx_corridor():
    """Test that US-MX corridor returns negative sentiment pattern."""
    adapter = SentimentAdapter()
    sentiment = adapter.get_lane_sentiment("US-MX")

    assert isinstance(sentiment, SentimentSnapshot)
    assert sentiment.lane_sentiment_score == pytest.approx(0.30, abs=0.01)
    assert sentiment.macro_logistics_sentiment_score == pytest.approx(0.45, abs=0.01)
    assert sentiment.sentiment_trend_7d == pytest.approx(-0.10, abs=0.01)
    assert sentiment.sentiment_volatility_30d == pytest.approx(0.20, abs=0.01)
    assert sentiment.sentiment_provider == "SentimentVendor_stub_v0"


def test_sentiment_adapter_us_mx_case_insensitive():
    """Test that corridor matching is case-insensitive."""
    adapter = SentimentAdapter()
    sentiment_lower = adapter.get_lane_sentiment("us-mx")
    sentiment_upper = adapter.get_lane_sentiment("US-MX")
    sentiment_mixed = adapter.get_lane_sentiment("Us-Mx")

    # All should return the same values
    assert sentiment_lower.lane_sentiment_score == sentiment_upper.lane_sentiment_score
    assert sentiment_lower.lane_sentiment_score == sentiment_mixed.lane_sentiment_score


def test_sentiment_adapter_other_corridors():
    """Test that other corridors return positive sentiment pattern."""
    adapter = SentimentAdapter()

    # Test a few different corridors
    for corridor in ["CN-NL", "DE-US", "JP-UK", "SG-AU"]:
        sentiment = adapter.get_lane_sentiment(corridor)

        assert isinstance(sentiment, SentimentSnapshot)
        assert sentiment.lane_sentiment_score == pytest.approx(0.55, abs=0.01)
        assert sentiment.macro_logistics_sentiment_score == pytest.approx(0.60, abs=0.01)
        assert sentiment.sentiment_trend_7d == pytest.approx(0.05, abs=0.01)
        assert sentiment.sentiment_volatility_30d == pytest.approx(0.12, abs=0.01)
        assert sentiment.sentiment_provider == "SentimentVendor_stub_v0"


def test_sentiment_adapter_custom_provider_name():
    """Test that custom provider name is used."""
    custom_provider = "CustomSentimentProvider_v1"
    adapter = SentimentAdapter(provider_name=custom_provider)
    sentiment = adapter.get_lane_sentiment("US-MX")

    assert sentiment.sentiment_provider == custom_provider


def test_sentiment_adapter_initialization():
    """Test that adapter can be initialized with optional parameters."""
    adapter = SentimentAdapter(
        api_key="test-key-123",
        base_url="https://sentiment-api.example.com",
        provider_name="TestProvider",
    )

    assert adapter.api_key == "test-key-123"
    assert adapter.base_url == "https://sentiment-api.example.com"
    assert adapter.provider_name == "TestProvider"
