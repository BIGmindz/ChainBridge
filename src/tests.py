"""
Tests Module

Contains unit tests for the signal engine and other components.
"""

import math

import pandas as pd

from .signal_engine import calculate_rsi_from_ohlcv, wilder_rsi


def test_rsi_flatline():
    """Test RSI calculation for flat price series."""
    s = pd.Series([100] * 20, dtype=float)
    rsi = wilder_rsi(s, 14)
    assert 45 <= rsi <= 55, f"Expected RSI near 50, got {rsi}"


def test_rsi_uptrend():
    """Test RSI calculation for uptrending price series."""
    s = pd.Series(range(1, 30), dtype=float)
    rsi = wilder_rsi(s, 14)
    assert rsi > 60, f"Expected RSI > 60, got {rsi}"


def test_rsi_downtrend():
    """Test RSI calculation for downtrending price series."""
    s = pd.Series(range(30, 1, -1), dtype=float)
    rsi = wilder_rsi(s, 14)
    assert rsi < 40, f"Expected RSI < 40, got {rsi}"


def test_rsi_no_losses_near_max():
    """Test RSI calculation for continuous uptrend (near 100)."""
    s = pd.Series(range(1, 60), dtype=float)
    rsi = wilder_rsi(s, 14)
    assert rsi >= 95 or math.isclose(rsi, 100.0, rel_tol=0.01), f"Expected RSI near 100, got {rsi}"


def test_insufficient_ohlcv_returns_nan():
    """Test that insufficient OHLCV data returns NaN."""
    short_ohlcv = [[0, 0, 0, 0, 100.0, 0.0] for _ in range(10)]
    rsi_val = calculate_rsi_from_ohlcv(short_ohlcv, period=14)
    assert isinstance(rsi_val, float) and math.isnan(rsi_val), f"Expected NaN, got {rsi_val}"


def run_tests():
    """Run all tests."""
    tests = [
        test_rsi_flatline,
        test_rsi_uptrend,
        test_rsi_downtrend,
        test_rsi_no_losses_near_max,
        test_insufficient_ohlcv_returns_nan,
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as ae:
            failures += 1
            print(f"FAIL: {t.__name__}: {ae}")
        except Exception as e:
            failures += 1
            print(f"ERROR: {t.__name__}: {type(e).__name__}: {e}")
    if failures:
        raise SystemExit(f"Tests failed: {failures}")
    print("All tests passed.")
