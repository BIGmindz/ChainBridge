#!/usr/bin/env python3
"""
INTEGRATE CHAINALYSIS ADOPTION TRACKER WITH MULTI-SIGNAL BOT

This script demonstrates how to integrate the Chainalysis Adoption Tracker
with the existing multi-signal decision bot framework.
"""

import json
import os
import sys
from datetime import datetime

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the AdoptionTrackerModule
from modules.adoption_tracker_module import AdoptionTrackerModule


def integrate_adoption_tracker():
    """
    Integrate the Chainalysis Adoption Tracker module
    with the multi-signal bot framework
    """
    print(
        """
    ╔═════════════════════════════════════════════════════════════╗
    ║  CHAINALYSIS ADOPTION TRACKER INTEGRATION                   ║
    ║                                                             ║
    ║  - Tracks Global Crypto Adoption Index by region/country    ║
    ║  - Generates BUY signals when adoption growth > 40% YoY     ║
    ║  - Forward-looking indicator for future crypto demand       ║
    ╚═════════════════════════════════════════════════════════════╝
    """
    )

    # Initialize the Adoption Tracker
    adoption_tracker = AdoptionTrackerModule()

    # Process data and get signals
    result = adoption_tracker.process()

    # Display the results
    print(f"\n📊 SIGNAL: {result['signal']} (Confidence: {result['confidence'] * 100:.1f}%)")
    print(f"📝 REASONING: {result['reasoning']}")

    # Identify high-growth regions
    print("\n🌍 HIGH-GROWTH REGIONS (>40% YoY):")
    for region, growth in result.get("high_growth_regions", {}).items():
        print(f"  • {region.replace('_', ' ')}: {growth * 100:.1f}% growth")

    # Show how this integrates with the multi-signal framework
    print("\n🔄 INTEGRATION WITH MULTI-SIGNAL BOT:")

    # Define the complete signal portfolio with the new module
    signal_portfolio = {
        "technical_signals": [
            {"name": "RSI", "correlation": 0.70, "weight": 0.05},
            {"name": "MACD", "correlation": 0.65, "weight": 0.05},
            {"name": "Bollinger", "correlation": 0.60, "weight": 0.05},
            {"name": "Volume", "correlation": 0.50, "weight": 0.05},
        ],
        "macro_signals": [
            {"name": "Inflation_Crisis", "correlation": 0.03, "weight": 0.15},
            {"name": "Regulatory_Flow", "correlation": 0.04, "weight": 0.05},
            {"name": "Global_Macro", "correlation": 0.02, "weight": 0.15},
        ],
        "adoption_signals": [
            {"name": "Chainalysis_Adoption", "correlation": 0.04, "weight": 0.15},
            {"name": "Regional_Growth", "correlation": 0.05, "weight": 0.10},
            {"name": "Institutional_Adoption", "correlation": 0.10, "weight": 0.10},
        ],
        "sentiment_signals": [
            {"name": "Social_Media", "correlation": 0.30, "weight": 0.05},
            {"name": "News_Sentiment", "correlation": 0.25, "weight": 0.05},
        ],
    }

    # Calculate the average correlation of each signal category
    category_correlations = {}
    category_weights = {}

    for category, signals in signal_portfolio.items():
        category_correlations[category] = sum(s["correlation"] for s in signals) / len(signals)  # type: ignore
        category_weights[category] = sum(s["weight"] for s in signals)  # type: ignore

    # Print the portfolio metrics
    print("\nSignal Portfolio Analysis:")
    print("  -------------------------")
    for category, correlation in category_correlations.items():
        print(f"  • {category.replace('_', ' ')}: {correlation:.2f} correlation, {category_weights[category] * 100:.0f}% weight")

    # Calculate the weighted average correlation
    total_weight = sum(category_weights.values())  # type: ignore
    weighted_correlation = sum(corr * category_weights[cat] / total_weight for cat, corr in category_correlations.items())  # type: ignore

    # Calculate diversification score (lower correlation = higher diversification)
    diversification_score = max(0, 1 - weighted_correlation)

    # Print the summary metrics
    print("\nPortfolio Summary:")
    print(f"  • Weighted Average Correlation: {weighted_correlation:.2f}")
    print(f"  • Diversification Score: {diversification_score:.2f}")

    # Rate the diversification
    if diversification_score > 0.8:
        rating = "EXCELLENT"
    elif diversification_score > 0.6:
        rating = "GOOD"
    elif diversification_score > 0.4:
        rating = "FAIR"
    else:
        rating = "POOR"

    print(f"  • Diversification Rating: {rating}")

    # Save the portfolio configuration
    config_dir = "config"
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, "signal_portfolio_with_adoption.json")

    with open(config_file, "w") as f:
        portfolio_data = {
            "signal_portfolio": signal_portfolio,
            "metrics": {
                "category_correlations": category_correlations,
                "category_weights": category_weights,
                "weighted_correlation": weighted_correlation,
                "diversification_score": diversification_score,
                "diversification_rating": rating,
            },
            "timestamp": datetime.now().isoformat(),
            "adoption_tracker_status": "enabled",
            "adoption_signal": result["signal"],
        }
        json.dump(portfolio_data, f, indent=2)

    print(f"\n✅ Signal portfolio configuration saved to {config_file}")
    print("\nIntegration complete! The Chainalysis Adoption Tracker is now part of your multi-signal decision system.")


if __name__ == "__main__":
    integrate_adoption_tracker()
