"""
Performance Dashboard for Market Regime Analysis

This module provides tools for visualizing trading performance
across different market regimes.
"""

import numpy as np
import json
import os
from typing import Dict
from datetime import datetime, timedelta

# Conditional import for visualization libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.gridspec import GridSpec
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: Matplotlib is not available. Visualization features will be disabled.")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: Pandas is not available. Some features will be disabled.")

# Optional seaborn for enhanced visualizations
try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
    # Set seaborn style
    sns.set_style("whitegrid")
    plt.rcParams['axes.facecolor'] = 'white'
except ImportError:
    SEABORN_AVAILABLE = False


class RegimePerformanceDashboard:
    """
    Dashboard for visualizing trading performance across different market regimes.
    """
    
    def __init__(
        self,
        results: Dict[str, Dict],
        figsize: Tuple[int, int] = (16, 10),
        output_dir: str = "reports",
    ):
        """
        Initialize the performance dashboard.
        
        Args:
            results: Dictionary of backtest results by regime.
            figsize: Figure size for the dashboard.
            output_dir: Directory to save the dashboard output files.
        """
        self.results = results
        self.figsize = figsize
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Check if visualization is available
        if not MATPLOTLIB_AVAILABLE:
            print("Warning: Matplotlib is not available. Only text reports will be generated.")
    
    def generate_dashboard(self, title: str = "Regime Performance Dashboard") -> None:
        """
        Generate the complete performance dashboard.
        
        Args:
            title: Title for the dashboard.
        """
        if not MATPLOTLIB_AVAILABLE:
            print("Cannot generate visual dashboard: Matplotlib is not available.")
            self._generate_text_report()
            return
        
        # Create the main figure
        fig = plt.figure(figsize=self.figsize, facecolor='white')
        gs = GridSpec(3, 3, figure=fig)
        
        # Add title
        fig.suptitle(title, fontsize=16, y=0.98)
        
        # Plot the performance overview
        self._plot_performance_overview(fig.add_subplot(gs[0, :]))
        
        # Plot metrics comparison
        self._plot_metrics_comparison(fig.add_subplot(gs[1, 0:2]))
        
        # Plot regime distribution
        self._plot_regime_distribution(fig.add_subplot(gs[1, 2]))
        
        # Plot trade analysis
        self._plot_trade_analysis(fig.add_subplot(gs[2, 0:2]))
        
        # Plot risk metrics
        self._plot_risk_metrics(fig.add_subplot(gs[2, 2]))
        
        # Adjust layout
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        # Save the dashboard
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.output_dir, f"regime_dashboard_{timestamp}.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Dashboard saved to {output_path}")
        
        # Generate text report too
        self._generate_text_report()
    
    def _plot_performance_overview(self, ax) -> None:
        """Plot the performance overview chart."""
        # Plot cumulative returns for each regime
        for regime, result in self.results.items():
            if regime != "Overall" and "returns" in result:
                returns = result.get("returns", [])
                
                if len(returns) > 0:
                    cumulative_returns = np.cumprod(1 + returns) - 1
                    ax.plot(cumulative_returns, label=regime)
        
        # Plot overall returns
        if "Overall" in self.results and "returns" in self.results["Overall"]:
            overall_returns = self.results["Overall"]["returns"]
            if len(overall_returns) > 0:
                cumulative_overall = np.cumprod(1 + overall_returns) - 1
                ax.plot(cumulative_overall, label="Overall", linewidth=2.5, color='black')
        
        ax.set_title("Cumulative Returns by Regime", fontsize=12)
        ax.set_ylabel("Cumulative Return (%)")
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)
        
        # Format y-axis as percentage
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1%}'))
        
        # Add horizontal line at y=0
        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
    
    def _plot_metrics_comparison(self, ax) -> None:
        """Plot the metrics comparison chart."""
        regimes = [r for r in self.results.keys() if r != "Overall"]
        metrics = ["total_return", "sharpe_ratio", "max_drawdown", "win_rate"]
        metric_labels = ["Total Return", "Sharpe Ratio", "Max Drawdown", "Win Rate"]
        
        # Prepare data
        data = []
        for regime in regimes:
            if "metrics" in self.results[regime]:
                regime_metrics = self.results[regime]["metrics"]
                row = [regime]
                for metric in metrics:
                    value = regime_metrics.get(metric, 0)
                    row.append(value)
                data.append(row)
        
        # Convert to numpy array for easier manipulation
        data_array = np.array([[r[0]] + [float(x) for x in r[1:]] for r in data])
        
        if len(data_array) == 0:
            ax.text(0.5, 0.5, "No metrics data available", 
                   horizontalalignment='center', verticalalignment='center')
            return
            
        # Create the table
        column_labels = ["Regime"] + metric_labels
        ax.axis('tight')
        ax.axis('off')
        
        # Format the data for display
        display_data = []
        for row in data_array:
            regime = row[0]
            formatted_row = [
                f"{float(row[1]):.2%}",  # Total Return
                f"{float(row[2]):.2f}",  # Sharpe Ratio
                f"{float(row[3]):.2%}",  # Max Drawdown
                f"{float(row[4]):.2%}"   # Win Rate
            ]
            display_data.append([regime] + formatted_row)
        
        table = ax.table(
            cellText=display_data,
            colLabels=column_labels,
            loc='center',
            cellLoc='center'
        )
        
        # Adjust table appearance
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.5)
        
        # Color code the cells based on performance
        for i, row in enumerate(data_array):
            # Total Return (higher is better)
            cell = table[(i+1, 1)]
            value = float(row[1])
            if value > 0.1:
                cell.set_facecolor('#c6efce')  # Light green
            elif value < 0:
                cell.set_facecolor('#ffc7ce')  # Light red
                
            # Sharpe Ratio (higher is better)
            cell = table[(i+1, 2)]
            value = float(row[2])
            if value > 1.0:
                cell.set_facecolor('#c6efce')
            elif value < 0:
                cell.set_facecolor('#ffc7ce')
                
            # Max Drawdown (lower is better)
            cell = table[(i+1, 3)]
            value = float(row[3])
            if value < 0.1:
                cell.set_facecolor('#c6efce')
            elif value > 0.2:
                cell.set_facecolor('#ffc7ce')
                
            # Win Rate (higher is better)
            cell = table[(i+1, 4)]
            value = float(row[4])
            if value > 0.6:
                cell.set_facecolor('#c6efce')
            elif value < 0.4:
                cell.set_facecolor('#ffc7ce')
    
    def _plot_regime_distribution(self, ax) -> None:
        """Plot the regime distribution chart."""
        # Get regime counts from the results
        regime_counts = {}
        total_periods = 0
        
        for regime, data in self.results.items():
            if regime != "Overall" and "returns" in data:
                count = len(data["returns"])
                regime_counts[regime] = count
                total_periods += count
        
        if total_periods == 0:
            ax.text(0.5, 0.5, "No regime data available", 
                   horizontalalignment='center', verticalalignment='center')
            return
        
        # Convert to percentages
        labels = list(regime_counts.keys())
        sizes = [count / total_periods * 100 for count in regime_counts.values()]
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=None,
            autopct='%1.1f%%',
            startangle=90,
            colors=plt.cm.tab10.colors[:len(labels)]
        )
        
        # Customize text appearance
        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_color('white')
        
        ax.set_title("Regime Distribution", fontsize=12)
        ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(0.9, 0.5))
        ax.axis('equal')  # Equal aspect ratio ensures pie is drawn as a circle
    
    def _plot_trade_analysis(self, ax) -> None:
        """Plot trade analysis."""
        regimes = [r for r in self.results.keys() if r != "Overall"]
        
        # Check if signals data is available
        has_signals = all(
            "signals" in self.results[regime] 
            for regime in regimes
        )
        
        if not has_signals:
            ax.text(0.5, 0.5, "No trade data available", 
                   horizontalalignment='center', verticalalignment='center')
            return
        
        # Count trades by type and regime
        buy_counts = []
        sell_counts = []
        hold_counts = []
        
        for regime in regimes:
            signals = self.results[regime].get("signals", [])
            
            buy_count = np.sum(signals == 1)
            sell_count = np.sum(signals == -1)
            hold_count = np.sum(signals == 0)
            
            buy_counts.append(buy_count)
            sell_counts.append(sell_count)
            hold_counts.append(hold_count)
        
        # Create bar chart
        x = np.arange(len(regimes))
        width = 0.25
        
        ax.bar(x - width, buy_counts, width, label='Buy', color='green', alpha=0.7)
        ax.bar(x, sell_counts, width, label='Sell', color='red', alpha=0.7)
        ax.bar(x + width, hold_counts, width, label='Hold', color='gray', alpha=0.7)
        
        ax.set_title("Trading Activity by Regime", fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(regimes)
        ax.set_ylabel("Number of Signals")
        ax.legend()
        ax.grid(True, axis='y', alpha=0.3)
    
    def _plot_risk_metrics(self, ax) -> None:
        """Plot risk metrics."""
        regimes = [r for r in self.results.keys() if r != "Overall"]
        
        # Calculate volatility for each regime
        volatilities = []
        max_drawdowns = []
        
        for regime in regimes:
            returns = self.results[regime].get("returns", [])
            
            if len(returns) > 0:
                volatility = np.std(returns) * np.sqrt(252)  # Annualized
                volatilities.append(volatility)
                
                # Max drawdown is already in the metrics
                max_drawdown = self.results[regime].get("metrics", {}).get("max_drawdown", 0)
                max_drawdowns.append(max_drawdown)
            else:
                volatilities.append(0)
                max_drawdowns.append(0)
        
        # Create horizontal bar chart
        y_pos = np.arange(len(regimes))
        
        # Plot volatility bars
        ax.barh(y_pos - 0.2, volatilities, 0.4, label='Volatility (Ann.)', color='blue', alpha=0.7)
        
        # Plot max drawdown bars
        ax.barh(y_pos + 0.2, max_drawdowns, 0.4, label='Max Drawdown', color='red', alpha=0.7)
        
        ax.set_title("Risk Metrics by Regime", fontsize=12)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(regimes)
        ax.set_xlabel("Value")
        ax.legend(loc="upper right")
        ax.grid(True, axis='x', alpha=0.3)
        
        # Format x-axis as percentage
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.1%}'))
    
    def _generate_text_report(self) -> None:
        """Generate a text report of the results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.output_dir, f"regime_report_{timestamp}.txt")
        
        with open(report_path, 'w') as f:
            f.write("=== REGIME PERFORMANCE REPORT ===\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("-- Performance Metrics by Regime --\n")
            f.write("\n{:<15} {:<15} {:<15} {:<15} {:<15}\n".format(
                "Regime", "Total Return", "Sharpe Ratio", "Max Drawdown", "Win Rate"
            ))
            f.write("-" * 75 + "\n")
            
            for regime, data in self.results.items():
                if "metrics" in data:
                    metrics = data["metrics"]
                    f.write("{:<15} {:<15.2%} {:<15.2f} {:<15.2%} {:<15.2%}\n".format(
                        regime,
                        metrics.get("total_return", 0),
                        metrics.get("sharpe_ratio", 0),
                        metrics.get("max_drawdown", 0),
                        metrics.get("win_rate", 0)
                    ))
            
            f.write("\n-- Regime Distribution --\n")
            total_periods = sum(
                len(data.get("returns", [])) 
                for regime, data in self.results.items() 
                if regime != "Overall"
            )
            
            if total_periods > 0:
                f.write("\n{:<15} {:<15} {:<15}\n".format("Regime", "Periods", "Percentage"))
                f.write("-" * 45 + "\n")
                
                for regime, data in self.results.items():
                    if regime != "Overall" and "returns" in data:
                        periods = len(data["returns"])
                        percentage = periods / total_periods * 100
                        f.write("{:<15} {:<15} {:<15.2f}%\n".format(regime, periods, percentage))
            
            # Save trade analysis if signals data is available
            has_signals = all(
                "signals" in self.results[regime] 
                for regime in self.results 
                if regime != "Overall"
            )
            
            if has_signals:
                f.write("\n-- Trade Analysis --\n")
                f.write("\n{:<15} {:<15} {:<15} {:<15}\n".format(
                    "Regime", "Buy Signals", "Sell Signals", "Hold Signals"
                ))
                f.write("-" * 60 + "\n")
                
                for regime, data in self.results.items():
                    if regime != "Overall" and "signals" in data:
                        signals = data["signals"]
                        buy_count = np.sum(signals == 1)
                        sell_count = np.sum(signals == -1)
                        hold_count = np.sum(signals == 0)
                        
                        f.write("{:<15} {:<15} {:<15} {:<15}\n".format(
                            regime, buy_count, sell_count, hold_count
                        ))
        
        # Also save results as JSON for further analysis
        json_path = os.path.join(self.output_dir, f"regime_results_{timestamp}.json")
        with open(json_path, 'w') as f:
            # Convert numpy arrays to lists for JSON serialization
            serializable_results = {}
            for regime, data in self.results.items():
                serializable_data = {}
                for key, value in data.items():
                    if isinstance(value, np.ndarray):
                        serializable_data[key] = value.tolist()
                    else:
                        serializable_data[key] = value
                serializable_results[regime] = serializable_data
            
            json.dump(serializable_results, f, indent=2)
        
        print(f"Text report saved to {report_path}")
        print(f"JSON data saved to {json_path}")


def create_dashboard(
    results: Dict[str, Dict],
    title: str = "Regime Performance Dashboard",
    output_dir: str = "reports",
    show_plot: bool = True
) -> None:
    """
    Create and display a performance dashboard.
    
    Args:
        results: Dictionary of backtest results by regime.
        title: Title for the dashboard.
        output_dir: Directory to save the dashboard output files.
        show_plot: Whether to show the plot interactively.
    """
    dashboard = RegimePerformanceDashboard(results, output_dir=output_dir)
    dashboard.generate_dashboard(title)
    
    if show_plot and MATPLOTLIB_AVAILABLE:
        plt.show()