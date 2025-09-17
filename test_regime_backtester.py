#!/usr/bin/env python3
"""Test script for the RegimeBacktester"""

import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the backtester
from src.backtesting.regime_backtester import RegimeBacktester

def test_backtester():
    """Run basic tests for the RegimeBacktester"""
    # Create test data with 100 points
    print("Creating test data...")
    price_data = np.linspace(100, 200, 100)
    
    # Create regime data with different regimes
    regime_data = np.zeros(100)
    regime_data[30:60] = 1  # Bullish regime
    regime_data[60:90] = 2  # Bearish regime
    
    # Define regime labels
    regime_labels = ["Sideways", "Bullish", "Bearish"]
    
    print(f"Created test data with {len(price_data)} price points")
    print(f"Created {len(np.unique(regime_data))} different regimes")
    
    # Create backtester
    print("Initializing RegimeBacktester...")
    backtester = RegimeBacktester(price_data, regime_data, regime_labels)
    print("RegimeBacktester initialized successfully")
    
    # Define a simple strategy for testing
    def simple_strategy(prices, params):
        threshold = params.get("threshold", 0.5)
        signals = np.zeros_like(prices)
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1] * (1 + threshold/100):
                signals[i] = 1  # Buy
            elif prices[i] < prices[i-1] * (1 - threshold/100):
                signals[i] = -1  # Sell
        return signals
    
    # Define strategy parameters
    default_params = {"threshold": 0.5}
    regime_specific_params = {
        "Bullish": {"threshold": 0.7},
        "Bearish": {"threshold": 0.3}
    }
    
    # Run the backtest
    print("Running backtest...")
    results = backtester.run_backtest(simple_strategy, default_params, regime_specific_params)
    print("Backtest completed successfully")
    
    # Verify results
    if "Overall" not in results:
        print("ERROR: Overall results not found")
        return False
    
    for regime_label in regime_labels:
        if regime_label not in results:
            print(f"ERROR: Results for {regime_label} regime not found")
            return False
        
        if "metrics" not in results[regime_label]:
            print(f"ERROR: Metrics for {regime_label} regime not found")
            return False
            
        metrics = results[regime_label]["metrics"]
        required_metrics = ["total_return", "sharpe_ratio", "max_drawdown", "win_rate"]
        for metric in required_metrics:
            if metric not in metrics:
                print(f"ERROR: Metric {metric} not found for {regime_label} regime")
                return False
    
    print("All basic result validations passed")
    
    # Test parameter optimization
    print("Testing parameter optimization...")
    param_grid = {
        "threshold": [0.3, 0.5, 0.7]
    }
    
    best_params = backtester.get_best_parameters_by_regime(simple_strategy, param_grid)
    print("Parameter optimization completed successfully")
    
    # Verify optimization results
    for regime_label in regime_labels:
        if regime_label not in best_params:
            print(f"WARNING: Best parameters for {regime_label} regime not found")
            continue
            
        params = best_params[regime_label]
        if "threshold" not in params:
            print(f"ERROR: Threshold parameter not found in best parameters for {regime_label} regime")
            return False
    
    print("All parameter optimization validations passed")
    print("All tests passed successfully!")
    return True

if __name__ == "__main__":
    if test_backtester():
        print("\n✅ RegimeBacktester validation successful")
    else:
        print("\n❌ RegimeBacktester validation failed")
        sys.exit(1)
