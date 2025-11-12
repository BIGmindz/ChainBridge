#!/usr/bin/env python3
"""
Test script for the updated strategy engine with symbol-specific models.
"""

import os
import sys
import logging

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from strategy_engine import get_strategy_for_regime_and_symbol

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)


def test_strategy_selection():
    """Test the symbol-specific strategy selection logic."""

    print("🧪 Testing Symbol-Specific Strategy Selection")
    print("=" * 50)

    # Test cases: (regime, symbol) -> expected behavior
    test_cases = [
        ("bull", "BTC/USD"),
        ("bear", "ETH/USD"),
        ("sideways", "SOL/USD"),
        ("bull", "DOGE/USD"),
        ("bear", "AVAX/USD"),
    ]

    for regime, symbol in test_cases:
        print(f"\n📊 Testing: {regime.upper()} regime with {symbol}")

        strategy = get_strategy_for_regime_and_symbol(regime, symbol)

        print(f"   Description: {strategy['description']}")
        print(f"   Config: {strategy['config_path']}")
        print(f"   Model: {strategy['model_path']}")
        print(f"   Scaler: {strategy['scaler_path']}")

        # Check if files exist
        model_exists = os.path.exists(strategy["model_path"])
        scaler_exists = strategy["scaler_path"] and os.path.exists(
            strategy["scaler_path"]
        )
        config_exists = os.path.exists(strategy["config_path"])

        print(f"   Model exists: {'✅' if model_exists else '❌'}")
        print(f"   Scaler exists: {'✅' if scaler_exists else '❌'}")
        print(f"   Config exists: {'✅' if config_exists else '❌'}")


if __name__ == "__main__":
    test_strategy_selection()
