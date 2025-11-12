"""Test RSI scenarios and edge cases."""

import math
import os
import sys
from typing import Type, Callable, Any

# Ensure the repository root is on sys.path so tests can import benson_rsi_bot
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def raises(
    exc_type: Type[BaseException], func: Callable[..., Any], *args: Any, **kwargs: Any
) -> None:
    """Simple replacement for pytest.raises to avoid external dependency."""
    if not isinstance(exc_type, type) or not issubclass(exc_type, BaseException):
        raise TypeError("exc_type must be an Exception type")
    try:
        func(*args, **kwargs)
    except exc_type:
        return
    except Exception as e:
        raise AssertionError(
            f"Expected {exc_type.__name__}, but got {type(e).__name__}: {e}"
        )
    raise AssertionError(f"Expected {exc_type.__name__} to be raised")
    raise AssertionError(f"Expected {exc_type.__name__} to be raised")


def test_rsi_flatline():
    """Test RSI calculation with flatline prices."""
    from benson_rsi_bot import wilder_rsi

    prices = [100.0] * 20
    rsi = wilder_rsi(prices)
    assert 40 <= rsi <= 60, "Flatline prices should give neutral RSI"


def test_rsi_uptrend():
    """Test RSI calculation with clear uptrend."""
    from benson_rsi_bot import wilder_rsi

    prices = list(range(100, 120))  # type: ignore
    rsi = wilder_rsi(prices)
    assert rsi > 70, "Uptrend should give overbought RSI"


def test_rsi_downtrend():
    """Test RSI calculation with clear downtrend."""
    from benson_rsi_bot import wilder_rsi

    prices = list(range(120, 100, -1))  # type: ignore
    rsi = wilder_rsi(prices)
    assert rsi < 30, "Downtrend should give oversold RSI"


def test_rsi_insufficient_data():
    """Test RSI calculation with insufficient data."""
    from benson_rsi_bot import wilder_rsi

    prices = [100.0, 101.0]
    raises(ValueError, wilder_rsi, prices)


def test_rsi_edge_cases():
    """Test RSI calculation with edge cases."""
    from benson_rsi_bot import wilder_rsi

    # Test with NaN
    prices_with_nan = [100.0, math.nan, 102.0]
    raises(ValueError, wilder_rsi, prices_with_nan)

    # Test with zero prices
    zero_prices = [0.0] * 20
    rsi: float = float(wilder_rsi(zero_prices))  # type: ignore
    assert 40 <= rsi <= 60, "Zero prices should give neutral RSI"

    # Test with very large price jumps
    volatile_prices = [100.0] * 10 + [1000000.0] * 10
    rsi: float = float(wilder_rsi(volatile_prices))  # type: ignore
    assert rsi > 70, "Large upward move should give overbought RSI"
