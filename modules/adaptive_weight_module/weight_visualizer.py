#!/usr/bin/env python3
"""
Adaptive Weight Visualization

This module provides visualization tools for the adaptive weight model,
including market regime detection, signal weight optimization,
and performance analysis across different market conditions.
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


class AdaptiveWeightVisualizer:
    """
    Visualization tools for the adaptive weight model and market regimes
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the visualizer"""
        self.config = config or {}

        # Configure output directory
        self.output_dir = self.config.get("output_dir", "reports/adaptive_weight_viz")
        os.makedirs(self.output_dir, exist_ok=True)

        # Color scheme for different regimes
        self.regime_colors = {
            "BULL": "green",
            "BEAR": "red",
            "SIDEWAYS": "gray",
            "VOLATILE": "orange",
            "LOW_VOLATILITY": "blue",
            "UNKNOWN": "black",
        }

        # Set seaborn style
        sns.set_style("whitegrid")

    def plot_regime_history(
        self, regime_data: Dict[str, Any], title: str = "Market Regime History"
    ) -> str:
        """
        Create a visualization of market regime history

        Args:
            regime_data: Dictionary with regime history data
            title: Plot title

        Returns:
            Path to the saved visualization
        """
        # Extract data
        regimes = regime_data.get("regime_history", {}).get("regimes", [])
        timestamps = regime_data.get("regime_history", {}).get("timestamps", [])
        confidences = regime_data.get("regime_history", {}).get("confidences", [])

        if not regimes or not timestamps:
            print("No regime history data available for visualization")
            return ""

        # Convert timestamps to datetime
        try:
            dates = [datetime.fromisoformat(ts) for ts in timestamps]
        except (ValueError, TypeError):
            print("Invalid timestamp format in regime history data")
            return ""

        # Create DataFrame for plotting
        df = pd.DataFrame({"date": dates, "regime": regimes, "confidence": confidences})

        # Create plot
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [3, 1]}
        )

        # Plot regimes
        for regime, color in self.regime_colors.items():
            regime_df = df[df["regime"] == regime]
            if not regime_df.empty:
                ax1.scatter(
                    regime_df["date"],
                    [regime] * len(regime_df),
                    c=color,
                    label=regime,
                    s=50,
                )

        # Configure regime plot
        ax1.set_title(title)
        ax1.set_ylabel("Market Regime")
        ax1.legend(loc="upper right")
        ax1.set_yticks(list(self.regime_colors.keys()))

        # Plot confidence
        ax2.fill_between(df["date"], 0, df["confidence"], color="skyblue", alpha=0.6)
        ax2.set_xlabel("Date")
        ax2.set_ylabel("Confidence")
        ax2.set_ylim(0, 1)

        # Adjust layout
        plt.tight_layout()

        # Save figure
        output_path = os.path.join(self.output_dir, "regime_history.png")
        plt.savefig(output_path)

        return output_path

    def plot_regime_transitions(
        self,
        transition_matrix: Dict[str, Dict[str, float]],
        title: str = "Regime Transition Probabilities",
    ) -> str:
        """
        Plot the transition probability matrix between market regimes

        Args:
            transition_matrix: Nested dictionary of transition probabilities
            title: Plot title

        Returns:
            Path to the saved visualization
        """
        if not transition_matrix:
            print("No transition matrix data available for visualization")
            return ""

        # Convert to DataFrame
        df = pd.DataFrame(transition_matrix)

        # Create plot
        plt.figure(figsize=(10, 8))
        sns.heatmap(
            df,
            annot=True,
            cmap="YlGnBu",
            vmin=0,
            vmax=1,
            fmt=".2f",
            cbar_kws={"label": "Probability"},
        )

        plt.title(title)
        plt.xlabel("To Regime")
        plt.ylabel("From Regime")

        # Save figure
        output_path = os.path.join(self.output_dir, "regime_transitions.png")
        plt.savefig(output_path)
        plt.close()

        return output_path

    def plot_performance_by_regime(
        self,
        performance_data: Dict[str, Dict[str, float]],
        metric: str = "win_rate",
        title: str = "Trading Performance by Market Regime",
    ) -> str:
        """
        Plot performance metrics for each market regime

        Args:
            performance_data: Dictionary with performance metrics by regime
            metric: Performance metric to plot
            title: Plot title

        Returns:
            Path to the saved visualization
        """
        if not performance_data:
            print("No performance data available for visualization")
            return ""

        # Extract metric for each regime
        regimes = []
        values = []

        for regime, perf in performance_data.items():
            if metric in perf:
                regimes.append(regime)
                values.append(perf[metric])

        if not regimes:
            print(f"No {metric} data available for visualization")
            return ""

        # Create plot
        plt.figure(figsize=(10, 6))

        # Create bar colors based on regime
        colors = [self.regime_colors.get(r, "gray") for r in regimes]

        bars = plt.bar(regimes, values, color=colors)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 0.02,
                f"{height:.2f}",
                ha="center",
                va="bottom",
            )

        plt.title(f"{title}: {metric.replace('_', ' ').title()}")
        plt.ylabel(metric.replace("_", " ").title())
        plt.xlabel("Market Regime")

        # Save figure
        output_path = os.path.join(self.output_dir, f"performance_{metric}.png")
        plt.savefig(output_path)
        plt.close()

        return output_path

    def plot_weight_optimization(
        self,
        weight_history: List[Dict[str, Any]],
        title: str = "Signal Weight Optimization Over Time",
    ) -> str:
        """
        Plot how signal weights change over time

        Args:
            weight_history: List of weight optimization results with timestamps
            title: Plot title

        Returns:
            Path to the saved visualization
        """
        if not weight_history:
            print("No weight history data available for visualization")
            return ""

        # Extract data
        dates = []
        regimes = []
        weights_by_layer = {}

        for entry in weight_history:
            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(entry.get("timestamp", ""))
                dates.append(timestamp)
            except (ValueError, TypeError):
                continue

            # Get regime
            regimes.append(entry.get("market_regime", "UNKNOWN"))

            # Get weights
            weights = entry.get("optimized_weights", {})
            for layer, weight in weights.items():
                if layer not in weights_by_layer:
                    weights_by_layer[layer] = []
                weights_by_layer[layer].append(weight)

        if not dates:
            print("No valid timestamps in weight history data")
            return ""

        # Create plot
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(12, 10), gridspec_kw={"height_ratios": [1, 3]}
        )

        # Plot regimes on top subplot
        for i, regime in enumerate(regimes):
            color = self.regime_colors.get(regime, "gray")
            ax1.axvspan(dates[i], dates[i] + timedelta(hours=1), alpha=0.3, color=color)

        # Add regime legend
        regime_patches = [
            plt.Rectangle((0, 0), 1, 1, color=color, alpha=0.3)
            for color in self.regime_colors.values()
        ]
        ax1.legend(regime_patches, self.regime_colors.keys(), loc="upper right")
        ax1.set_title("Market Regimes")
        ax1.set_yticks([])

        # Plot weight changes on bottom subplot
        for layer, weights in weights_by_layer.items():
            if len(weights) == len(dates):  # Ensure matching length
                ax2.plot(dates, weights, marker="o", linestyle="-", label=layer)

        ax2.set_title(title)
        ax2.set_xlabel("Date")
        ax2.set_ylabel("Weight Multiplier")
        ax2.legend(loc="upper left")
        ax2.grid(True)

        # Adjust layout
        plt.tight_layout()

        # Save figure
        output_path = os.path.join(self.output_dir, "weight_optimization.png")
        plt.savefig(output_path)
        plt.close()

        return output_path

    def plot_signal_importance(
        self,
        signal_weights: Dict[str, float],
        title: str = "Signal Importance for Current Market Regime",
    ) -> str:
        """
        Create a visualization of signal importance based on weights

        Args:
            signal_weights: Dictionary with signal names and weights
            title: Plot title

        Returns:
            Path to the saved visualization
        """
        if not signal_weights:
            print("No signal weights available for visualization")
            return ""

        # Sort signals by weight
        sorted_signals = sorted(
            signal_weights.items(), key=lambda x: x[1], reverse=True
        )
        signals = [s[0] for s in sorted_signals]
        weights = [s[1] for s in sorted_signals]

        # Create plot
        plt.figure(figsize=(12, 6))

        # Create horizontal bar chart
        bars = plt.barh(signals, weights)

        # Add a vertical line at weight = 1.0 (neutral)
        plt.axvline(x=1.0, color="gray", linestyle="--", alpha=0.7)

        # Color bars based on whether they're above or below 1.0
        for i, bar in enumerate(bars):
            if weights[i] > 1.0:
                bar.set_color("green")
            elif weights[i] < 1.0:
                bar.set_color("red")
            else:
                bar.set_color("gray")

        # Add value labels on bars
        for i, bar in enumerate(bars):
            width = bar.get_width()
            label_x = width + 0.02 if width < 1.0 else width - 0.08
            plt.text(
                label_x,
                bar.get_y() + bar.get_height() / 2.0,
                f"{width:.2f}",
                va="center",
            )

        plt.title(title)
        plt.xlabel("Weight Multiplier")
        plt.ylabel("Signal")
        plt.grid(axis="x")
        plt.tight_layout()

        # Save figure
        output_path = os.path.join(self.output_dir, "signal_importance.png")
        plt.savefig(output_path)
        plt.close()

        return output_path

    def create_dashboard(self, all_data: Dict[str, Any]) -> str:
        """
        Create a comprehensive dashboard with multiple visualizations

        Args:
            all_data: Dictionary with all visualization data

        Returns:
            Path to the saved dashboard
        """
        # Extract data
        regime_data = all_data.get("regime_data", {})
        transition_matrix = all_data.get("transition_matrix", {})
        performance_data = all_data.get("performance_data", {})
        weight_history = all_data.get("weight_history", [])
        current_weights = all_data.get("current_weights", {})

        # Create individual visualizations
        _regime_plot = self.plot_regime_history(regime_data)
        _transition_plot = self.plot_regime_transitions(transition_matrix)
        _perf_win_rate_plot = self.plot_performance_by_regime(
            performance_data, "win_rate"
        )
        _perf_pnl_plot = self.plot_performance_by_regime(performance_data, "pnl")
        _weight_plot = self.plot_weight_optimization(weight_history)
        _importance_plot = self.plot_signal_importance(current_weights)

        # Create an HTML dashboard
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Adaptive Weight Model Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333366; }}
                .dashboard-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
                .full-width {{ grid-column: span 2; }}
                .viz-container {{ border: 1px solid #ddd; border-radius: 5px; padding: 10px; }}
                img {{ max-width: 100%; }}
            </style>
        </head>
        <body>
            <h1>Adaptive Weight Model Dashboard</h1>
            <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            
            <div class="dashboard-grid">
                <div class="viz-container full-width">
                    <h2>Market Regime History</h2>
                    <img src="regime_history.png" alt="Market Regime History">
                </div>
                
                <div class="viz-container">
                    <h2>Regime Transitions</h2>
                    <img src="regime_transitions.png" alt="Regime Transitions">
                </div>
                
                <div class="viz-container">
                    <h2>Signal Importance</h2>
                    <img src="signal_importance.png" alt="Signal Importance">
                </div>
                
                <div class="viz-container">
                    <h2>Win Rate by Regime</h2>
                    <img src="performance_win_rate.png" alt="Win Rate by Regime">
                </div>
                
                <div class="viz-container">
                    <h2>PnL by Regime</h2>
                    <img src="performance_pnl.png" alt="PnL by Regime">
                </div>
                
                <div class="viz-container full-width">
                    <h2>Weight Optimization Over Time</h2>
                    <img src="weight_optimization.png" alt="Weight Optimization">
                </div>
            </div>
        </body>
        </html>
        """

        # Save the HTML dashboard
        dashboard_path = os.path.join(self.output_dir, "dashboard.html")
        with open(dashboard_path, "w") as f:
            f.write(html_content)

        return dashboard_path
