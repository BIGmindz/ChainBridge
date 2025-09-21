#!/usr/bin/env python3
"""
Test Script for High-Fidelity Backtesting Engine

This script tests the backtester functionality without requiring actual data or models.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_backtester_import():
    """Test that the backtester can be imported successfully"""
    try:
        from apps.backtester.backtester import run_backtest, generate_performance_report
        print("✅ Backtester import successful")
        return True
    except ImportError as e:
        print(f"❌ Backtester import failed: {e}")
        return False

def create_mock_data():
    """Create mock historical data for testing"""
    # Create sample data
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    symbols = ['BTC/USD', 'ETH/USD']

    data = []
    for symbol in symbols:
        for date in dates:
            # Generate realistic price data
            base_price = 50000 if symbol == 'BTC/USD' else 3000
            price_variation = np.random.normal(0, 0.02)  # 2% daily volatility
            price = base_price * (1 + price_variation)

            data.append({
                'timestamp': date,
                'symbol': symbol,
                'price': max(price, 100),  # Ensure positive price
                'rsi_value': np.random.uniform(30, 70),
                'volume': np.random.uniform(1000000, 10000000)
            })

    df = pd.DataFrame(data)
    df.to_csv('data/consolidated_market_data.csv', index=False)
    print(f"✅ Created mock data with {len(df)} rows")
    return df

def create_mock_strategy():
    """Create a mock strategy for testing"""
    strategy_path = 'strategies/test_strategy'
    os.makedirs(strategy_path, exist_ok=True)

    # Create mock config
    config = {
        'exchange': {
            'symbols': ['BTC/USD']
        },
        'trading': {
            'initial_capital': 10000,
            'fees': {
                'taker_bps': 25
            }
        },
        'signals': {
            'machine_learning': {
                'features': ['rsi_value', 'price']
            }
        }
    }

    import yaml
    with open(os.path.join(strategy_path, 'config.yaml'), 'w') as f:
        yaml.dump(config, f)

    print("✅ Created mock strategy configuration")
    return config

def test_backtester_structure():
    """Test that the backtester has the expected structure"""
    backtester_dir = 'apps/backtester'

    required_files = [
        'backtester.py',
        '__init__.py',
        'README.md',
        'run_backtester.sh'
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(backtester_dir, file)):
            missing_files.append(file)

    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def main():
    """Run all backtester tests"""
    print("🧪 Testing High-Fidelity Backtesting Engine")
    print("=" * 50)

    tests = [
        ("File Structure", test_backtester_structure),
        ("Import Test", test_backtester_import),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"Result: {status}")
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print("-" * 50)
    print(f"Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Backtester is ready.")
        print("\n💡 To run a full backtest:")
        print("   1. Create real historical data in data/consolidated_market_data.csv")
        print("   2. Train ML models for your strategies")
        print("   3. Run: python apps/backtester/backtester.py")
    else:
        print("⚠️  Some tests failed. Check the output above.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)