#!/usr/bin/env python3
"""
TEST VOLATILITY TARGETING INTEGRATION
Test the new volatility targeting position sizing functionality
"""

import pandas as pd
import numpy as np
from datetime import datetime
from risk_management_utils import vol_target_position_size, calculate_realized_volatility
from budget_manager import BudgetManager

def test_volatility_targeting():
    """Test the volatility targeting functionality"""
    print("🧪 TESTING VOLATILITY TARGETING INTEGRATION")
    print("=" * 50)

    # Test 1: Basic volatility targeting function
    print("\n1️⃣ Testing vol_target_position_size function...")

    # Create sample price data with known volatility
    np.random.seed(42)
    base_price = 50000
    # Create trending price data
    trend = np.linspace(0, 1000, 200)
    noise = np.random.normal(0, 500, 200)
    prices = base_price + trend + noise
    price_series = pd.Series(prices)

    max_capital = 10000  # $10,000 max risk
    target_vol = 0.25    # 25% target volatility

    position_size = vol_target_position_size(
        price_series=price_series,
        max_capital_at_risk=max_capital,
        target_ann_vol=target_vol,
        ewm_span=100
    )

    print(f"   Calculated Position Size: ${position_size:.2f}")
    print(f"   Max Capital at Risk: ${max_capital:.2f}")
    print(f"   Target Volatility: {target_vol:.1%}")

    # Test 2: BudgetManager integration
    print("\n2️⃣ Testing BudgetManager with volatility targeting...")

    # Create budget manager with volatility targeting enabled
    budget_manager = BudgetManager(initial_capital=50000)

    # Update risk parameters for volatility targeting
    risk_params = {
        'position_size_method': 'volatility_targeting',
        'target_volatility': 0.25,
        'volatility_lookback': 100,
        'max_risk_per_trade': 0.02
    }
    budget_manager.risk_parameters.update(risk_params)

    # Test position size calculation
    try:
        position_calc = budget_manager.calculate_position_size(
            symbol="BTC/USD",
            signal_confidence=0.8,
            volatility=0.02,
            price=50000,
            price_series=price_series
        )
        print(f"   Calculated Position Size: ${position_calc['size']:.2f}")
        print(f"   Position Size %: {position_calc['size_pct']:.3f}")
        print(f"   Method Used: {position_calc['method']}")
        print(f"   Confidence Used: {position_calc['confidence_used']}")
    except TypeError as e:
        print(f"   ⚠️  Parameter not supported: {e}")
        # Fallback to basic calculation
        position_calc = budget_manager.calculate_position_size(
            symbol="BTC/USD",
            signal_confidence=0.8,
            volatility=0.02,
            price=50000
        )
        print(f"   Fallback Position Size: ${position_calc['size']:.2f}")
        print(f"   Method Used: {position_calc['method']}")

    # Test 3: Compare with other methods
    print("\n3️⃣ Comparing position sizing methods...")

    methods = ['kelly', 'fixed', 'volatility_adjusted', 'volatility_targeting']

    for method in methods:
        test_manager = BudgetManager(initial_capital=50000)
        test_params = test_manager.risk_parameters.copy()
        test_params['position_size_method'] = method
        test_manager.risk_parameters.update(test_params)

        try:
            calc = test_manager.calculate_position_size(
                symbol="BTC/USD",
                signal_confidence=0.8,
                volatility=0.02,
                price=50000,
                price_series=price_series if method == 'volatility_targeting' else None
            )
        except TypeError:
            # Fallback for older version without price_series
            calc = test_manager.calculate_position_size(
                symbol="BTC/USD",
                signal_confidence=0.8,
                volatility=0.02,
                price=50000
            )

        print(f"   {method:20} | ${calc['size']:>8.2f} | {calc['size_pct']:.3f}")

    # Test 4: Edge cases
    print("\n4️⃣ Testing edge cases...")

    # Test with insufficient data
    short_series = pd.Series([50000, 50001, 50002])
    small_position = vol_target_position_size(
        price_series=short_series,
        max_capital_at_risk=10000,
        target_ann_vol=0.25,
        ewm_span=100
    )
    print(f"   Small Data Position Size: ${small_position:.2f}")

    # Test with zero volatility
    flat_series = pd.Series([50000] * 200)
    flat_position = vol_target_position_size(
        price_series=flat_series,
        max_capital_at_risk=10000,
        target_ann_vol=0.25,
        ewm_span=100
    )
    print(f"   Flat Market Position Size: ${flat_position:.2f}")

    # Test with high volatility
    volatile_prices = np.random.normal(50000, 5000, 200)
    volatile_series = pd.Series(volatile_prices)
    volatile_position = vol_target_position_size(
        price_series=volatile_series,
        max_capital_at_risk=10000,
        target_ann_vol=0.25,
        ewm_span=100
    )
    print(f"   High Volatility Position Size: ${volatile_position:.2f}")

    print("\n✅ VOLATILITY TARGETING TESTS COMPLETED")
    print("=" * 50)

if __name__ == "__main__":
    test_volatility_targeting()