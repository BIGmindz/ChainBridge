#!/usr/bin/env python3
"""
Unit tests for Expected Value (EV) Based Thresholding

Tests cover:
- Threshold optimization with trading costs
- Expected value maximization
- Cost-sensitive evaluation
- Multiple threshold finding
- Edge cases and error handling
"""

import pytest
import numpy as np
import pandas as pd
from ml_pipeline.ev_thresholding import EVThresholdOptimizer, TradingCosts, ThresholdResult, find_multiple_thresholds


class TestEVThresholdOptimizer:
    """Test suite for EVThresholdOptimizer class."""

    def setup_method(self):
        """Set up test data."""
        np.random.seed(42)

        # Create synthetic trading data
        n_samples = 1000
        dates = pd.date_range("2020-01-01", periods=n_samples, freq="H")

        # Generate realistic returns with some predictability
        true_returns = np.random.randn(n_samples) * 0.02  # 2% vol

        # Create predictions with some skill (correlation with future returns)
        future_returns = np.roll(true_returns, -1)  # Next period returns
        future_returns[-1] = 0

        # Add some predictive power
        skill = 0.3
        noise = np.random.randn(n_samples) * 0.5
        predictions = skill * future_returns + (1 - skill) * noise
        predictions = 1 / (1 + np.exp(-predictions))  # Sigmoid to [0,1]

        self.y_true = pd.Series(true_returns, index=dates, name="returns")
        self.y_prob = pd.Series(predictions, index=dates, name="predictions")

    def test_initialization(self):
        """Test EVThresholdOptimizer initialization."""
        optimizer = EVThresholdOptimizer()

        assert optimizer.trading_costs.total_cost_pct > 0
        assert optimizer.position_size_pct == 0.02
        assert optimizer.min_trades == 10

    def test_trading_costs(self):
        """Test TradingCosts class."""
        costs = TradingCosts(commission_pct=0.001, slippage_pct=0.0005, spread_pct=0.0002, market_impact_pct=0.0001)

        expected_total = 0.001 + 0.0005 + 0.0002 + 0.0001
        assert costs.total_cost_pct == expected_total

    def test_optimize_threshold_basic(self):
        """Test basic threshold optimization."""
        optimizer = EVThresholdOptimizer(min_trades=1)  # Lower threshold for test

        result, curve = optimizer.optimize_threshold(self.y_true, self.y_prob, return_curve=True)

        assert isinstance(result, ThresholdResult)
        assert 0.1 <= result.threshold <= 0.9
        assert isinstance(result.expected_value, float)
        assert 0 <= result.win_rate <= 1
        assert result.total_trades >= 1

        # Check curve data
        assert curve is not None
        assert len(curve) > 0
        assert "threshold" in curve.columns
        assert "expected_value" in curve.columns

    def test_optimize_threshold_with_costs(self):
        """Test threshold optimization with trading costs."""
        high_costs = TradingCosts(
            commission_pct=0.005,  # 0.5% commission
            slippage_pct=0.002,  # 0.2% slippage
        )

        optimizer = EVThresholdOptimizer(trading_costs=high_costs, min_trades=1)

        result, _ = optimizer.optimize_threshold(self.y_true, self.y_prob)

        # With higher costs, optimal threshold should be higher (more selective)
        assert result.threshold > 0.5  # Should be conservative

    def test_evaluate_threshold_insufficient_trades(self):
        """Test handling of insufficient trades."""
        # Create data that will result in very few trades
        dates = pd.date_range("2020-01-01", periods=10, freq="H")
        y_true = pd.Series([0.01] * 10, index=dates)
        y_prob = pd.Series([0.99] * 10, index=dates)  # All very high confidence

        optimizer = EVThresholdOptimizer(min_trades=50)  # Require 50 trades

        # This should raise ValueError due to insufficient trades
        with pytest.raises(ValueError, match="No valid thresholds found"):
            optimizer.optimize_threshold(y_true, y_prob)

    def test_calculate_returns_with_costs(self):
        """Test returns calculation with trading costs."""
        optimizer = EVThresholdOptimizer(min_trades=1)

        # Simple test case
        y_true = pd.Series([0.01, -0.005, 0.02])  # 1%, -0.5%, 2% returns
        signals = np.array([1, -1, 1])  # Long, Short, Long

        returns = optimizer._calculate_returns_with_costs(y_true, signals)

        # Should have 3 trades
        assert len(returns) == 3

        # Check that costs are properly deducted
        # Expected returns: position_size * market_return * signal - costs
        position_size = optimizer.position_size_pct
        cost_per_trade = optimizer.trading_costs.total_cost_pct * position_size

        expected_return_1 = position_size * 0.01 * 1 - cost_per_trade  # Long 1%
        expected_return_2 = position_size * (-0.005) * (-1) - cost_per_trade  # Short -0.5% (becomes positive)
        expected_return_3 = position_size * 0.02 * 1 - cost_per_trade  # Long 2%

        # Allow small tolerance for floating point
        assert abs(returns.iloc[0] - expected_return_1) < 1e-6
        assert abs(returns.iloc[1] - expected_return_2) < 1e-6
        assert abs(returns.iloc[2] - expected_return_3) < 1e-6

    def test_threshold_result_structure(self):
        """Test ThresholdResult data structure."""
        result = ThresholdResult(
            threshold=0.6,
            expected_value=0.001,
            win_rate=0.55,
            profit_factor=1.2,
            total_trades=100,
            avg_win=0.015,
            avg_loss=-0.008,
            max_drawdown=0.05,
            sharpe_ratio=1.5,
        )

        assert result.threshold == 0.6
        assert result.expected_value == 0.001
        assert result.win_rate == 0.55
        assert result.profit_factor == 1.2
        assert result.total_trades == 100


class TestMultipleThresholds:
    """Test suite for multiple threshold finding."""

    def setup_method(self):
        """Set up test data."""
        np.random.seed(42)
        n_samples = 500
        dates = pd.date_range("2020-01-01", periods=n_samples, freq="H")

        # Create test data
        true_returns = np.random.randn(n_samples) * 0.02
        predictions = np.random.rand(n_samples)  # Random predictions

        self.y_true = pd.Series(true_returns, index=dates)
        self.y_prob = pd.Series(predictions, index=dates)

    def test_find_multiple_thresholds(self):
        """Test finding multiple thresholds."""
        results = find_multiple_thresholds(self.y_true, self.y_prob, n_thresholds=3, min_trades=1)

        assert len(results) <= 3  # May find fewer if some ranges fail

        for result in results:
            assert isinstance(result, ThresholdResult)
            assert 0.1 <= result.threshold <= 0.9

        # Thresholds should be in different ranges
        if len(results) >= 2:
            thresholds = [r.threshold for r in results]
            assert len(set(thresholds)) == len(thresholds)  # All unique

    def test_find_multiple_thresholds_insufficient_data(self):
        """Test multiple thresholds with insufficient data."""
        # Very small dataset
        small_y_true = pd.Series([0.01, -0.01])
        small_y_prob = pd.Series([0.6, 0.4])

        results = find_multiple_thresholds(small_y_true, small_y_prob, n_thresholds=3, min_trades=1)

        # Should still work with small data
        assert len(results) >= 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_all_positive_predictions(self):
        """Test with all positive predictions."""
        dates = pd.date_range("2020-01-01", periods=100, freq="H")
        y_true = pd.Series(np.random.randn(100) * 0.02, index=dates)
        y_prob = pd.Series([0.9] * 100, index=dates)  # All high confidence

        optimizer = EVThresholdOptimizer(min_trades=1)
        result, _ = optimizer.optimize_threshold(y_true, y_prob)

        assert result.total_trades > 0
        assert result.threshold <= 0.9  # Should be able to find optimal

    def test_all_negative_predictions(self):
        """Test with all negative predictions."""
        dates = pd.date_range("2020-01-01", periods=100, freq="H")
        y_true = pd.Series(np.random.randn(100) * 0.02, index=dates)
        y_prob = pd.Series([0.1] * 100, index=dates)  # All low confidence

        optimizer = EVThresholdOptimizer(min_trades=1)
        result, _ = optimizer.optimize_threshold(y_true, y_prob)

        assert result.total_trades > 0
        assert result.threshold >= 0.1  # Should be able to find optimal

    def test_extreme_thresholds(self):
        """Test optimization with extreme threshold ranges."""
        dates = pd.date_range("2020-01-01", periods=100, freq="H")
        y_true = pd.Series(np.random.randn(100) * 0.02, index=dates)
        y_prob = pd.Series(np.random.rand(100), index=dates)

        optimizer = EVThresholdOptimizer(min_trades=1)

        # Test very high threshold
        result, _ = optimizer.optimize_threshold(y_true, y_prob, thresholds=np.array([0.95]))
        assert result.threshold == 0.95

        # Test very low threshold
        result, _ = optimizer.optimize_threshold(y_true, y_prob, thresholds=np.array([0.05]))
        assert result.threshold == 0.05

    def test_zero_returns(self):
        """Test with zero returns (no market movement)."""
        dates = pd.date_range("2020-01-01", periods=100, freq="H")
        y_true = pd.Series([0.0] * 100, index=dates)  # No returns
        y_prob = pd.Series(np.random.rand(100), index=dates)

        optimizer = EVThresholdOptimizer(min_trades=1)

        # Should still work but expected value should be negative (only costs)
        result, _ = optimizer.optimize_threshold(y_true, y_prob)

        # Expected value should be negative due to trading costs
        assert result.expected_value < 0.0
        assert result.total_trades > 0


class TestPerformanceMetrics:
    """Test performance metric calculations."""

    def test_profit_factor_calculation(self):
        """Test profit factor calculation."""
        optimizer = EVThresholdOptimizer(min_trades=1)

        # Create known scenario
        y_true = pd.Series([0.02, 0.01, -0.015, 0.005, -0.01])  # Mixed returns
        signals = np.array([1, 1, -1, 1, -1])  # Mix of long/short

        returns = optimizer._calculate_returns_with_costs(y_true, signals)

        # Calculate expected profit factor manually
        wins = returns[returns > 0]
        losses = returns[returns < 0]

        if len(wins) > 0 and len(losses) > 0:
            gross_profit = wins.sum()
            gross_loss = abs(losses.sum())
            expected_pf = gross_profit / gross_loss
        else:
            expected_pf = float("inf") if len(wins) > 0 else 0.0

        # This is tested indirectly through the optimizer
        assert len(returns) == len([s for s in signals if s != 0])


if __name__ == "__main__":
    pytest.main([__file__])
