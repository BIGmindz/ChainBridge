#!/usr/bin/env python3
"""
Market Regime Analysis Tool

This script analyzes the performance of the market regime detection system
and provides insights on how to improve it.
"""

import json
import os
import numpy as np
from datetime import datetime
from typing import Dict, List
import sys

# Conditionally import matplotlib
has_matplotlib = False
try:
    import matplotlib.pyplot as plt
    has_matplotlib = True
except ImportError:
    pass

def load_regime_stats(file_path: str) -> Dict:
    """Load market regime statistics from JSON file"""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        return {}
        
    with open(file_path, 'r') as f:
        return json.load(f)

def analyze_regime_distribution(stats: Dict) -> None:
    """Analyze how trades are distributed across market regimes"""
    regime_performance = stats.get('regime_performance', {})
    
    if not regime_performance:
        print("No regime performance data found")
        return
        
    print("\n=== MARKET REGIME DISTRIBUTION ===")
    
    total_trades = 0
    regime_trades = []
    regime_names = []
    regime_win_rates = []
    
    for regime, data in regime_performance.items():
        trades = data.get('trades', 0)
        total_trades += trades
        regime_trades.append(trades)
        regime_names.append(regime)
        win_rate = data.get('win_rate', 0)
        regime_win_rates.append(win_rate)
        
        print(f"{regime.upper()}: {trades} trades ({trades/max(total_trades, 1)*100:.1f}%), "
              f"Win rate: {win_rate:.2f}%, PnL: {data.get('pnl', 0):.2f}")
    
    print(f"\nTotal trades: {total_trades}")
    
    # Plot regime distribution
    if regime_trades and sum(regime_trades) > 0:
        plt.figure(figsize=(12, 6))
        
        # Regime distribution
        plt.subplot(1, 2, 1)
        plt.pie(regime_trades, labels=regime_names, autopct='%1.1f%%', 
                textprops={'fontsize': 9})
        plt.title('Trade Distribution by Market Regime')
        
        # Win rate by regime
        plt.subplot(1, 2, 2)
        bars = plt.bar(regime_names, regime_win_rates)
        plt.title('Win Rate by Market Regime')
        plt.ylabel('Win Rate %')
        
        # Add values on top of bars
        for bar, win_rate in zip(bars, regime_win_rates):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{win_rate:.1f}%',
                    ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig('regime_distribution_analysis.png')
        plt.close()
        print("Distribution chart saved as 'regime_distribution_analysis.png'")

def analyze_weight_optimization(stats: Dict) -> None:
    """Analyze how signal weights are optimized for different regimes"""
    market_regime = stats.get('market_regime', {})
    optimized_categories = market_regime.get('optimized_categories', {})
    
    if not optimized_categories:
        print("No optimized category data found")
        return
    
    print("\n=== SIGNAL CATEGORY OPTIMIZATION ===")
    for category, weight in optimized_categories.items():
        print(f"{category}: {weight:.2f}x weight multiplier")
    
    weight_changes = stats.get('weight_changes', {})
    print("\n=== ML WEIGHT ADAPTATION ===")
    
    # Sort signals by absolute percentage change
    sorted_signals = sorted(
        weight_changes.items(), 
        key=lambda x: abs(x[1].get('pct_change', 0)), 
        reverse=True
    )
    
    print("Signals sorted by adaptation magnitude:")
    for signal, data in sorted_signals:
        pct_change = data.get('pct_change', 0)
        direction = "↑" if pct_change > 0 else "↓"
        print(f"{signal}: {direction} {abs(pct_change):.2f}% " 
              f"({data.get('initial', 0):.4f} → {data.get('current', 0):.4f})")

def analyze_regime_confidence(stats: Dict) -> None:
    """Analyze the confidence in regime detection"""
    market_regime = stats.get('market_regime', {})
    regime = market_regime.get('regime', 'unknown')
    confidence = market_regime.get('confidence', 0)
    
    print(f"\n=== REGIME DETECTION CONFIDENCE ===")
    print(f"Current regime: {regime}")
    print(f"Confidence: {confidence:.2f}")
    
    # Provide recommendations based on confidence
    if confidence < 0.5:
        print("LOW CONFIDENCE: Consider reducing the impact of regime detection")
        print("Recommendation: Lower the regime-specific adjustments by 50%")
    elif confidence < 0.7:
        print("MODERATE CONFIDENCE: Current settings are appropriate")
        print("Recommendation: Continue with current regime adaptation strength")
    else:
        print("HIGH CONFIDENCE: Regime detection is reliable")
        print("Recommendation: Consider increasing regime-specific adjustments")

def provide_improvement_recommendations(stats: Dict) -> None:
    """Provide recommendations for improving the market regime detection"""
    # Analyze trade distribution
    regime_performance = stats.get('regime_performance', {})
    regimes = list(regime_performance.keys())
    
    print("\n=== IMPROVEMENT RECOMMENDATIONS ===")
    
    # Check for regime detection balance
    if len(regimes) <= 1:
        print("ISSUE: Only one market regime detected")
        print("Recommendation: Decrease trend_threshold to make detection more sensitive")
        print("  - Change self.trend_threshold = 0.10 to 0.08")
    
    if 'bull' not in regimes and 'bear' not in regimes:
        print("ISSUE: No bull or bear markets detected")
        print("Recommendation: Lower trend threshold and increase lookback period")
        print("  - Change lookback_period from 14 to 20")
    
    # Check win rate
    win_rates = [data.get('win_rate', 0) for data in regime_performance.values()]
    if win_rates and max(win_rates) < 30:
        print("ISSUE: Low win rates across all regimes")
        print("Recommendation: Adjust trading thresholds and position sizing")
        print("  - Review buy/sell thresholds in make_ml_decision method")
        print("  - Consider adding trailing stops for better exit timing")
    
    # Check overall ML adaptation
    ml_adaptation = stats.get('ml_adaptation', 0)
    if ml_adaptation < 0.1:
        print("ISSUE: Low ML adaptation rate")
        print("Recommendation: Increase learning rates or reset initial weights")
        print("  - Increase base_learning_rate from 0.15 to 0.25")
    
    # Check regime-specific performance
    for regime, data in regime_performance.items():
        trades = data.get('trades', 0)
        win_rate = data.get('win_rate', 0)
        pnl = data.get('pnl', 0)
        
        if trades > 50 and win_rate < 15:
            print(f"ISSUE: Poor performance in {regime} regime")
            print(f"Recommendation: Review signal weights for {regime} regime")

def main():
    """Main function to analyze market regime detection results"""
    # Get the stats file
    if len(sys.argv) > 1:
        stats_file = sys.argv[1]
    else:
        stats_file = 'market_regime_stats.json'
    
    print(f"Analyzing market regime stats from: {stats_file}")
    stats = load_regime_stats(stats_file)
    
    if not stats:
        print("No stats data found. Please run the market regime demo first.")
        return
    
    # Run analysis functions
    analyze_regime_distribution(stats)
    analyze_weight_optimization(stats)
    analyze_regime_confidence(stats)
    provide_improvement_recommendations(stats)
    
    print("\nAnalysis complete. Use these insights to improve market regime detection.")

if __name__ == "__main__":
    main()