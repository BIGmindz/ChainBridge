#!/usr/bin/env python3
"""
Unit Tests for Triple Barrier Labeling System

Tests triple barrier labeling with synthetic data to ensure:
- Correct barrier hits (profit-taking, stop-loss, max-holding)
- Proper label distribution
- Edge cases handling
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_pipeline.triple_barrier_labeling import (
    TripleBarrierLabeler,
    create_synthetic_labels,
    analyze_label_distribution
)

class TestTripleBarrierLabeling(unittest.TestCase):
    """Test cases for triple barrier labeling system."""

    def setUp(self):
        """Set up test data."""
        # Create synthetic price series with known patterns
        dates = pd.date_range('2024-01-01', periods=100, freq='H')
        np.random.seed(42)

        # Create a trending upward series
        base_price = 100.0
        prices = []
        for i in range(100):
            # Add trend + noise
            trend = i * 0.1
            noise = np.random.normal(0, 1)
            price = base_price + trend + noise
            prices.append(max(price, 1.0))  # Ensure positive prices

        self.price_series = pd.Series(prices, index=dates)

    def test_profit_taking_barrier_long(self):
        """Test profit-taking barrier hit for long position."""
        labeler = TripleBarrierLabeler(pt=0.05, sl=-0.02, max_h=10)

        # Create a series that hits profit target quickly
        test_prices = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.1])  # 5.1% gain

        label, exit_idx = labeler.label_series(test_prices, 0, side=1)

        self.assertEqual(label, 1)  # Profit-taking
        self.assertEqual(exit_idx, 5)  # Index where PT was hit

    def test_stop_loss_barrier_long(self):
        """Test stop-loss barrier hit for long position."""
        labeler = TripleBarrierLabeler(pt=0.05, sl=-0.02, max_h=10)

        # Create a series that hits stop loss
        test_prices = pd.Series([100.0, 99.0, 98.5, 98.0, 97.9])  # -2.1% loss

        label, exit_idx = labeler.label_series(test_prices, 0, side=1)

        self.assertEqual(label, -1)  # Stop-loss
        self.assertEqual(exit_idx, 3)  # Index where SL was hit

    def test_max_holding_barrier(self):
        """Test max holding period barrier."""
        labeler = TripleBarrierLabeler(pt=0.10, sl=-0.10, max_h=3, min_h=1)

        # Create a series that doesn't hit PT or SL within max_h
        test_prices = pd.Series([100.0, 100.5, 101.0, 100.8, 101.2])  # Small movements

        label, exit_idx = labeler.label_series(test_prices, 0, side=1)

        self.assertEqual(label, 0)  # Max holding
        self.assertEqual(exit_idx, 3)  # max_h periods later

    def test_short_position_profit_taking(self):
        """Test profit-taking for short position."""
        labeler = TripleBarrierLabeler(pt=0.03, sl=-0.02, max_h=10)

        # Create a series that goes down (good for short)
        test_prices = pd.Series([100.0, 99.0, 98.0, 96.9])  # -3.1% drop

        label, exit_idx = labeler.label_series(test_prices, 0, side=-1)

        self.assertEqual(label, 1)  # Profit-taking for short
        self.assertEqual(exit_idx, 3)  # Index where PT was hit

    def test_short_position_stop_loss(self):
        """Test stop-loss for short position."""
        labeler = TripleBarrierLabeler(pt=0.05, sl=-0.02, max_h=10)

        # Create a series that goes up (bad for short)
        test_prices = pd.Series([100.0, 101.0, 102.1])  # +2.1% gain

        label, exit_idx = labeler.label_series(test_prices, 0, side=-1)

        self.assertEqual(label, -1)  # Stop-loss for short
        self.assertEqual(exit_idx, 2)  # Index where SL was hit

    def test_insufficient_data(self):
        """Test handling of insufficient data for labeling."""
        labeler = TripleBarrierLabeler(pt=0.05, sl=-0.02, max_h=10, min_h=2)

        # Series too short for minimum holding period
        test_prices = pd.Series([100.0, 101.0])

        label, exit_idx = labeler.label_series(test_prices, 0, side=1)

        self.assertEqual(label, 0)  # No valid label
        self.assertIsNone(exit_idx)

    def test_synthetic_labels_creation(self):
        """Test creation of synthetic labels."""
        labels_df = create_synthetic_labels(self.price_series, entry_probability=0.2, seed=42)

        # Check that we have some labels
        self.assertGreater(len(labels_df), 0)

        # Check that all labels are valid (-1, 0, 1)
        valid_labels = labels_df['label'].isin([-1, 0, 1]).all()
        self.assertTrue(valid_labels)

        # Check that sides are valid (-1, 1)
        valid_sides = labels_df['side'].isin([-1, 1]).all()
        self.assertTrue(valid_sides)

    def test_label_distribution_analysis(self):
        """Test analysis of label distribution."""
        # Create synthetic labels
        labels_df = create_synthetic_labels(self.price_series, entry_probability=0.3, seed=123)

        # Analyze distribution
        distribution = analyze_label_distribution(labels_df)

        # Check that we have all required keys
        required_keys = [
            'total_samples', 'profit_taking', 'stop_loss', 'max_holding',
            'profit_taking_pct', 'stop_loss_pct', 'max_holding_pct'
        ]

        for key in required_keys:
            self.assertIn(key, distribution)

        # Check that percentages sum to 100 (approximately)
        pct_sum = (distribution['profit_taking_pct'] +
                  distribution['stop_loss_pct'] +
                  distribution['max_holding_pct'])

        self.assertAlmostEqual(pct_sum, 100.0, places=1)

    def test_apply_labels_multiple_entries(self):
        """Test applying labels to multiple entry points."""
        labeler = TripleBarrierLabeler(pt=0.03, sl=-0.02, max_h=5)

        # Create entry points
        entry_points = pd.Series([False] * len(self.price_series), index=self.price_series.index)
        entry_points.iloc[10] = True
        entry_points.iloc[30] = True
        entry_points.iloc[50] = True

        # Create sides
        sides = pd.Series([1] * len(self.price_series), index=self.price_series.index)
        sides.iloc[30] = -1  # Short position

        # Apply labels
        labels_df = labeler.apply_labels(self.price_series, entry_points, sides)

        # Check that we have labels for all entry points
        self.assertEqual(len(labels_df), 3)

        # Check that labels are valid
        valid_labels = labels_df['label'].isin([-1, 0, 1]).all()
        self.assertTrue(valid_labels)

if __name__ == '__main__':
    unittest.main()