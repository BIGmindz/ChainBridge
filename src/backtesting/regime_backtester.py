"""
Regime-specific backtesting module for trading strategies.

This module provides functionality to backtest trading strategies under different market regimes.
"""

from typing import Dict, List, Optional, Tuple, Union

import numpy as np

# Conditional import for matplotlib
try:
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class RegimeBacktester:
    """
    A backtester that evaluates trading strategies under different market regimes.

    This class allows for the evaluation of trading strategies in different market conditions
    (regimes) such as trending, ranging, or volatile markets.
    """

    def __init__(
        self,
        price_data: np.ndarray,
        regime_data: Optional[np.ndarray] = None,
        regime_labels: Optional[List[str]] = None,
    ):
        """
        Initialize the regime backtester.

        Args:
            price_data: Historical price data for backtesting.
            regime_data: Optional array identifying regime periods. If None, regime detection will be performed.
            regime_labels: Optional labels for the regimes. If None, numeric indices will be used.
        """
        self.price_data = price_data
        self.regime_data = regime_data
        self.regime_labels = regime_labels or []
        self.results: Dict[str, Dict] = {}

        # Detect regimes if not provided
        if self.regime_data is None:
            self._detect_regimes()

    def _detect_regimes(self) -> None:
        """
        Detect market regimes based on price behavior.

        This is a simple implementation that can be extended with more sophisticated methods.
        """
        # Simple regime detection based on volatility and trend
        returns = np.diff(self.price_data) / self.price_data[:-1]

        # Classify regimes
        self.regime_data = np.zeros(len(self.price_data))

        # Use volatility and trend to set regime data
        # This is a simplified implementation that you can expand
        for i in range(len(self.regime_data)):
            if i < 50:  # Not enough data for initial periods
                self.regime_data[i] = 0  # Default to ranging
            else:
                segment = returns[max(0, i - 50) : i]
                vol_i = np.std(np.abs(segment))
                trend_i = np.mean(segment)

                # High volatility threshold (can be adjusted)
                high_vol = vol_i > 0.015

                # Determine regime based on volatility and trend
                if abs(trend_i) < 0.001:  # Low trend
                    self.regime_data[i] = 3 if high_vol else 0  # Choppy or Ranging
                elif trend_i > 0:  # Positive trend
                    self.regime_data[i] = (
                        4 if high_vol else 1
                    )  # Bullish Volatile or Bullish
                else:  # Negative trend
                    self.regime_data[i] = (
                        5 if high_vol else 2
                    )  # Bearish Volatile or Bearish
        # Regime 0: Low volatility, no trend (ranging)
        # Regime 1: Low volatility, positive trend (bullish)
        # Regime 2: Low volatility, negative trend (bearish)
        # Regime 3: High volatility, no trend (choppy)
        # Regime 4: High volatility, positive trend (bullish volatile)
        # Regime 5: High volatility, negative trend (bearish volatile)

        # Default regime labels if not provided
        if not self.regime_labels:
            self.regime_labels = [
                "Ranging",
                "Bullish",
                "Bearish",
                "Choppy",
                "Bullish Volatile",
                "Bearish Volatile",
            ]

    def run_backtest(
        self,
        strategy_fn: callable,
        params: Dict[str, Union[float, int, str]],
        regime_specific_params: Optional[
            Dict[str, Dict[str, Union[float, int, str]]]
        ] = None,
    ) -> Dict[str, Dict]:
        """
        Run a backtest across all regimes.

        Args:
            strategy_fn: Function that generates trading signals based on price data and parameters.
            params: Default parameters for the strategy.
            regime_specific_params: Optional parameters specific to each regime.

        Returns:
            Dictionary containing backtest results for each regime.
        """
        self.results = {}
        unique_regimes = np.unique(self.regime_data)

        for regime in unique_regimes:
            regime_idx = self.regime_data == regime
            regime_prices = self.price_data[regime_idx]

            if len(regime_prices) < 2:
                continue

            # Use regime-specific parameters if available
            regime_params = params.copy()
            regime_label = (
                self.regime_labels[int(regime)]
                if int(regime) < len(self.regime_labels)
                else f"Regime {regime}"
            )

            if regime_specific_params and regime_label in regime_specific_params:
                regime_params.update(regime_specific_params[regime_label])

            # Generate signals
            signals = strategy_fn(regime_prices, regime_params)

            # Calculate performance
            returns = self._calculate_returns(regime_prices, signals)
            performance_metrics = self._calculate_metrics(returns)

            self.results[regime_label] = {
                "returns": returns,
                "metrics": performance_metrics,
                "signals": signals,
                "prices": regime_prices,
            }

        # Calculate overall performance
        overall_returns = self._calculate_returns(
            self.price_data, strategy_fn(self.price_data, params)
        )
        overall_metrics = self._calculate_metrics(overall_returns)
        self.results["Overall"] = {
            "returns": overall_returns,
            "metrics": overall_metrics,
        }

        return self.results

    def _calculate_returns(self, prices: np.ndarray, signals: np.ndarray) -> np.ndarray:
        """Calculate strategy returns based on prices and signals."""
        # Simple return calculation: signal * next period's return
        price_returns = np.diff(prices) / prices[:-1]
        strategy_returns = signals[:-1] * price_returns
        return strategy_returns

    def _calculate_metrics(self, returns: np.ndarray) -> Dict[str, float]:
        """Calculate performance metrics from returns."""
        if len(returns) == 0:
            return {
                "total_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
            }

        # Calculate metrics
        total_return = np.cumprod(1 + returns)[-1] - 1
        sharpe_ratio = (
            returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        )
        cumulative_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (running_max - cumulative_returns) / running_max
        max_drawdown = drawdowns.max()
        win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0

        return {
            "total_return": float(total_return),
            "sharpe_ratio": float(sharpe_ratio),
            "max_drawdown": float(max_drawdown),
            "win_rate": float(win_rate),
        }

    def plot_results(self, figsize: Tuple[int, int] = (12, 8)) -> None:
        """
        Plot backtest results by regime.

        Args:
            figsize: Figure size for the plot.
        """
        if not MATPLOTLIB_AVAILABLE:
            print("Matplotlib is not available. Plotting is disabled.")
            return

        if not self.results:
            print("No backtest results to plot. Run a backtest first.")
            return

        # Create figure and axes
        fig, axs = plt.subplots(2, 1, figsize=figsize)

        # Plot cumulative returns by regime
        for regime, result in self.results.items():
            if regime != "Overall" and "returns" in result:
                cumulative_returns = np.cumprod(1 + result["returns"])
                axs[0].plot(cumulative_returns, label=regime)

        # Plot overall returns
        if "Overall" in self.results and "returns" in self.results["Overall"]:
            overall_returns = np.cumprod(1 + self.results["Overall"]["returns"])
            axs[0].plot(overall_returns, label="Overall", linewidth=2, color="black")

        axs[0].set_title("Cumulative Returns by Regime")
        axs[0].set_ylabel("Cumulative Return")
        axs[0].legend()
        axs[0].grid(True)

        # Plot regime distribution
        if self.regime_data is not None and len(self.regime_labels) > 0:
            unique_regimes, counts = np.unique(self.regime_data, return_counts=True)
            labels = [
                (
                    self.regime_labels[int(r)]
                    if int(r) < len(self.regime_labels)
                    else f"Regime {r}"
                )
                for r in unique_regimes
            ]
            axs[1].bar(labels, counts / len(self.regime_data) * 100)
            axs[1].set_title("Regime Distribution")
            axs[1].set_ylabel("% of Time")
            axs[1].grid(True)

        plt.tight_layout()
        plt.show()

    def get_best_parameters_by_regime(
        self,
        strategy_fn: callable,
        param_grid: Dict[str, List],
        metric: str = "sharpe_ratio",
    ) -> Dict[str, Dict]:
        """
        Find the best parameters for each regime using grid search.

        Args:
            strategy_fn: Function that generates trading signals based on price data and parameters.
            param_grid: Dictionary of parameter names and lists of values to try.
            metric: Performance metric to optimize.

        Returns:
            Dictionary of best parameters for each regime.
        """
        unique_regimes = np.unique(self.regime_data)
        best_params = {}

        from itertools import product

        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(product(*param_values))

        for regime in unique_regimes:
            regime_idx = self.regime_data == regime
            regime_prices = self.price_data[regime_idx]

            if len(regime_prices) < 2:
                continue

            regime_label = (
                self.regime_labels[int(regime)]
                if int(regime) < len(self.regime_labels)
                else f"Regime {regime}"
            )
            best_metric_value = -np.inf
            best_regime_params = None

            # Grid search
            for combo in param_combinations:
                params = dict(zip(param_names, combo))

                # Generate signals
                signals = strategy_fn(regime_prices, params)

                # Calculate performance
                returns = self._calculate_returns(regime_prices, signals)
                performance = self._calculate_metrics(returns)

                # Update if better
                if performance[metric] > best_metric_value:
                    best_metric_value = performance[metric]
                    best_regime_params = params

            best_params[regime_label] = best_regime_params

        return best_params
