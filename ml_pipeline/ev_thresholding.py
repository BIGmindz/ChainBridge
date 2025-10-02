#!/usr/bin/env python3
"""
Expected Value (EV) Based Thresholding for Financial ML

Implements cost-sensitive threshold optimization that maximizes expected value
considering trading costs, slippage, and position sizing. Based on "Advances in
Financial Machine Learning" principles for P&L-focused model evaluation.

Features:
- Cost-sensitive threshold search
- Expected value maximization
- Trading cost incorporation (fees, slippage)
- Position sizing integration
- Backtest simulation for threshold validation
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TradingCosts:
    """Trading cost parameters."""

    commission_pct: float = 0.001  # 0.1% commission
    slippage_pct: float = 0.0005  # 0.05% slippage
    spread_pct: float = 0.0002  # 0.02% spread
    market_impact_pct: float = 0.0001  # 0.01% market impact

    @property
    def total_cost_pct(self) -> float:
        """Total trading cost as percentage."""
        return self.commission_pct + self.slippage_pct + self.spread_pct + self.market_impact_pct


@dataclass
class ThresholdResult:
    """Results from threshold optimization."""

    threshold: float
    expected_value: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_win: float
    avg_loss: float
    max_drawdown: float
    sharpe_ratio: float


class EVThresholdOptimizer:
    """
    Expected Value based threshold optimizer for financial ML models.

    Optimizes prediction thresholds to maximize expected P&L considering
    trading costs and position sizing.
    """

    def __init__(
        self,
        trading_costs: Optional[TradingCosts] = None,
        position_size_pct: float = 0.02,  # 2% of capital per trade
        min_trades: int = 10,
    ):
        """
        Initialize EV threshold optimizer.

        Args:
            trading_costs: Trading cost parameters
            position_size_pct: Position size as percentage of capital
            min_trades: Minimum trades required for valid threshold
        """
        self.trading_costs = trading_costs or TradingCosts()
        self.position_size_pct = position_size_pct
        self.min_trades = min_trades

    def optimize_threshold(
        self, y_true: pd.Series, y_prob: pd.Series, thresholds: Optional[np.ndarray] = None, return_curve: bool = False
    ) -> Tuple[ThresholdResult, Optional[pd.DataFrame]]:
        """
        Find optimal threshold that maximizes expected value.

        Args:
            y_true: True labels (returns)
            y_prob: Predicted probabilities
            thresholds: Thresholds to test (default: 0.1 to 0.9)
            return_curve: Whether to return threshold curve data

        Returns:
            Tuple of (optimal_result, curve_data)
        """
        if thresholds is None:
            thresholds = np.linspace(0.1, 0.9, 81)  # 0.1, 0.11, ..., 0.9

        results = []

        for threshold in thresholds:
            result = self._evaluate_threshold(y_true, y_prob, threshold)
            if result and result.total_trades >= self.min_trades:
                results.append(result)  # type: ignore

        if not results:
            raise ValueError(f"No valid thresholds found with minimum {self.min_trades} trades")

        # Find optimal threshold
        optimal_result = max(results, key=lambda x: x.expected_value)

        curve_data = None
        if return_curve:
            curve_data = pd.DataFrame(
                [
                    {
                        "threshold": r.threshold,
                        "expected_value": r.expected_value,
                        "win_rate": r.win_rate,
                        "profit_factor": r.profit_factor,
                        "total_trades": r.total_trades,
                    }
                    for r in results
                ]
            )

        return optimal_result, curve_data

    def _evaluate_threshold(self, y_true: pd.Series, y_prob: pd.Series, threshold: float) -> Optional[ThresholdResult]:
        """
        Evaluate a single threshold's performance.

        Args:
            y_true: True returns
            y_prob: Predicted probabilities
            threshold: Classification threshold

        Returns:
            ThresholdResult or None if insufficient trades
        """
        # Generate predictions
        y_pred = (y_prob >= threshold).astype(int)  # type: ignore

        # Map to long/short signals (-1, 0, 1)
        # Assume positive predictions = long, negative true values = short
        signals = np.where(y_pred == 1, 1, np.where(y_true < 0, -1, 0))

        # Calculate returns with costs
        returns_with_costs = self._calculate_returns_with_costs(y_true, signals)

        if len(returns_with_costs) < self.min_trades:
            return None

        # Calculate performance metrics
        total_return = returns_with_costs.sum()  # type: ignore
        win_trades = returns_with_costs[returns_with_costs > 0]
        loss_trades = returns_with_costs[returns_with_costs < 0]

        win_rate = len(win_trades) / len(returns_with_costs) if len(returns_with_costs) > 0 else 0
        avg_win = win_trades.mean() if len(win_trades) > 0 else 0
        avg_loss = loss_trades.mean() if len(loss_trades) > 0 else 0

        # Profit factor
        gross_profit = win_trades.sum() if len(win_trades) > 0 else 0  # type: ignore
        gross_loss = abs(loss_trades.sum()) if len(loss_trades) > 0 else 0  # type: ignore
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")  # type: ignore

        # Expected value per trade
        expected_value = returns_with_costs.mean()

        # Calculate drawdown and Sharpe ratio
        cumulative = returns_with_costs.cumsum()  # type: ignore
        peak = cumulative.expanding().max()
        drawdown = cumulative - peak
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0

        # Sharpe ratio (annualized, assuming daily returns)
        if len(returns_with_costs) > 1:
            sharpe_ratio = returns_with_costs.mean() / returns_with_costs.std() * np.sqrt(252)
        else:
            sharpe_ratio = 0

        return ThresholdResult(
            threshold=threshold,
            expected_value=expected_value,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(returns_with_costs),
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
        )

    def _calculate_returns_with_costs(self, y_true: pd.Series, signals: np.ndarray) -> pd.Series:
        """
        Calculate returns after accounting for trading costs.

        Args:
            y_true: True returns
            signals: Trading signals (-1, 0, 1)

        Returns:
            Returns with costs deducted
        """
        # Only consider trades (non-zero signals)
        trade_mask = signals != 0
        if not trade_mask.any():
            return pd.Series([], dtype=float)

        returns = y_true.copy()
        signals = pd.Series(signals, index=y_true.index)

        # Apply position sizing
        position_size = self.position_size_pct

        # Calculate trading costs for each trade
        # Charge a fixed cost for every trade (simplified model)
        trading_costs = pd.Series(self.trading_costs.total_cost_pct * position_size, index=returns.index)
        trading_costs = trading_costs * trade_mask  # Only charge for actual trades

        # Apply costs to returns
        net_returns = returns * signals * position_size - trading_costs

        return net_returns[trade_mask]


def find_multiple_thresholds(y_true: pd.Series, y_prob: pd.Series, n_thresholds: int = 3, **kwargs) -> List[ThresholdResult]:
    """
    Find multiple optimal thresholds for different risk levels.

    Args:
        y_true: True labels
        y_prob: Predicted probabilities
        n_thresholds: Number of thresholds to find
        **kwargs: Arguments for EVThresholdOptimizer

    Returns:
        List of optimal thresholds
    """
    optimizer = EVThresholdOptimizer(**kwargs)

    # Search different threshold ranges for different risk levels
    threshold_ranges = [
        (0.1, 0.4),  # Conservative (higher threshold)
        (0.4, 0.7),  # Moderate
        (0.7, 0.9),  # Aggressive (lower threshold)
    ][:n_thresholds]

    results = []
    for i, (min_thresh, max_thresh) in enumerate(threshold_ranges):
        thresholds = np.linspace(min_thresh, max_thresh, 31)
        try:
            result, _ = optimizer.optimize_threshold(y_true, y_prob, thresholds)
            results.append(result)  # type: ignore
        except ValueError:
            logger.warning(f"Could not find valid threshold in range {min_thresh}-{max_thresh}")
            continue

    return results


def plot_threshold_curve(curve_data: pd.DataFrame, optimal_threshold: float, save_path: Optional[str] = None):
    """
    Plot threshold optimization curve.

    Args:
        curve_data: DataFrame with threshold curve data
        optimal_threshold: Optimal threshold value
        save_path: Path to save plot (optional)
    """
    try:
        import matplotlib.pyplot as plt

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

        # Expected Value curve
        ax1.plot(curve_data["threshold"], curve_data["expected_value"], "b-", linewidth=2)
        ax1.axvline(x=optimal_threshold, color="r", linestyle="--", alpha=0.7, label=f"Optimal: {optimal_threshold:.3f}")
        ax1.set_xlabel("Threshold")
        ax1.set_ylabel("Expected Value")
        ax1.set_title("Expected Value vs Threshold")
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Win Rate curve
        ax2.plot(curve_data["threshold"], curve_data["win_rate"], "g-", linewidth=2)
        ax2.axvline(x=optimal_threshold, color="r", linestyle="--", alpha=0.7)
        ax2.set_xlabel("Threshold")
        ax2.set_ylabel("Win Rate")
        ax2.set_title("Win Rate vs Threshold")
        ax2.grid(True, alpha=0.3)

        # Profit Factor curve
        ax3.plot(curve_data["threshold"], curve_data["profit_factor"], "orange", linewidth=2)
        ax3.axvline(x=optimal_threshold, color="r", linestyle="--", alpha=0.7)
        ax3.set_xlabel("Threshold")
        ax3.set_ylabel("Profit Factor")
        ax3.set_title("Profit Factor vs Threshold")
        ax3.grid(True, alpha=0.3)

        # Trade Count curve
        ax4.plot(curve_data["threshold"], curve_data["total_trades"], "purple", linewidth=2)
        ax4.axvline(x=optimal_threshold, color="r", linestyle="--", alpha=0.7)
        ax4.set_xlabel("Threshold")
        ax4.set_ylabel("Total Trades")
        ax4.set_title("Trade Count vs Threshold")
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"📈 Threshold curve saved to {save_path}")

        return fig

    except ImportError:
        logger.warning("matplotlib not available for plotting")
        return None
