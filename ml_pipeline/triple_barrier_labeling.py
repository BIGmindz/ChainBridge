#!/usr/bin/env python3
"""
Triple Barrier Labeling System for BensonBot

Implements event-based labels using triple-barrier method:
- Profit-taking barrier (pt)
- Stop-loss barrier (sl)
- Maximum holding barrier (max_h)

Outputs: y ∈ {-1, 0, 1} (SELL, HOLD, BUY)
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class TripleBarrierLabeler:
    """
    Triple-barrier labeling for financial time series.

    Based on "Advances in Financial Machine Learning" by Marcos Lopez de Prado.
    """

    def __init__(self,
                 pt: float = 0.02,      # Profit-taking barrier (2%)
                 sl: float = -0.01,     # Stop-loss barrier (-1%)
                 max_h: int = 24,       # Maximum holding period (hours)
                 min_h: int = 1):       # Minimum holding period
        """
        Initialize triple barrier labeler.

        Args:
            pt: Profit-taking barrier as fraction (e.g., 0.02 = 2%)
            sl: Stop-loss barrier as fraction (e.g., -0.01 = -1%)
            max_h: Maximum holding period in periods
            min_h: Minimum holding period in periods
        """
        self.pt = pt
        self.sl = sl
        self.max_h = max_h
        self.min_h = min_h

    def label_series(self,
                    price_series: pd.Series,
                    entry_idx: int,
                    side: int = 1) -> Tuple[int, Optional[int]]:
        """
        Label a single entry point using triple barrier method.

        Args:
            price_series: Price series to analyze
            entry_idx: Entry point index
            side: Trade direction (1 = long, -1 = short)

        Returns:
            Tuple of (label, exit_index)
            label: -1 (stop-loss), 0 (max holding), 1 (profit-taking)
            exit_index: Index where barrier was hit, None if no exit
        """
        if entry_idx >= len(price_series) - self.min_h:
            return 0, None  # No valid holding period

        entry_price = price_series.iloc[entry_idx]

        # Calculate barriers
        # For long positions: PT above entry, SL below entry
        # For short positions: PT below entry, SL above entry
        if side == 1:  # Long
            pt_barrier = entry_price * (1 + self.pt)
            sl_barrier = entry_price * (1 + self.sl)
        else:  # Short
            pt_barrier = entry_price * (1 - self.pt)  # Price needs to go down
            sl_barrier = entry_price * (1 - self.sl)  # Price going up is bad

        # Look ahead for barrier hits
        max_lookahead = min(entry_idx + self.max_h + 1, len(price_series))  # +1 to include the max_h index

        for i in range(entry_idx + self.min_h, max_lookahead):
            current_price = price_series.iloc[i]

            # Check profit-taking barrier
            if side == 1 and current_price >= pt_barrier:
                return 1, i
            elif side == -1 and current_price <= pt_barrier:
                return 1, i

            # Check stop-loss barrier
            if side == 1 and current_price <= sl_barrier:
                return -1, i
            elif side == -1 and current_price >= sl_barrier:
                return -1, i

        # Max holding period reached
        return 0, max_lookahead - 1

    def apply_labels(self,
                    price_series: pd.Series,
                    entry_points: pd.Series,
                    sides: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        Apply triple barrier labeling to multiple entry points.

        Args:
            price_series: Price series to analyze
            entry_points: Boolean series indicating entry points
            sides: Trade directions (1=long, -1=short), defaults to long

        Returns:
            DataFrame with labels and exit indices
        """
        if sides is None:
            sides = pd.Series(1, index=price_series.index)

        labels = []
        exit_indices = []

        entry_indices = price_series.index[entry_points]

        for entry_idx in entry_indices:
            if entry_idx not in sides.index:
                continue

            side = sides.loc[entry_idx]
            label, exit_idx = self.label_series(price_series, price_series.index.get_loc(entry_idx), side)

            labels.append(label)
            exit_indices.append(exit_idx)

        # Create result DataFrame
        result = pd.DataFrame({
            'entry_idx': entry_indices,
            'label': labels,
            'exit_idx': exit_indices,
            'side': [sides.loc[idx] for idx in entry_indices if idx in sides.index]
        })

        return result

def create_synthetic_labels(price_series: pd.Series,
                          entry_probability: float = 0.1,
                          seed: int = 42) -> pd.DataFrame:
    """
    Create synthetic entry points for testing triple barrier labeling.

    Args:
        price_series: Price series to analyze
        entry_probability: Probability of entry at each point
        seed: Random seed for reproducibility

    Returns:
        DataFrame with synthetic entry points and labels
    """
    np.random.seed(seed)

    # Create random entry points
    entry_points = pd.Series(
        np.random.random(len(price_series)) < entry_probability,
        index=price_series.index
    )

    # Random sides (long/short)
    sides = pd.Series(
        np.random.choice([-1, 1], len(price_series)),
        index=price_series.index
    )

    # Apply triple barrier labeling
    labeler = TripleBarrierLabeler(pt=0.02, sl=-0.01, max_h=24)
    labels_df = labeler.apply_labels(price_series, entry_points, sides)

    return labels_df

def analyze_label_distribution(labels_df: pd.DataFrame) -> dict:
    """
    Analyze the distribution of triple barrier labels.

    Args:
        labels_df: DataFrame with labels from triple barrier method

    Returns:
        Dictionary with label distribution statistics
    """
    total_labels = len(labels_df)
    label_counts = labels_df['label'].value_counts()

    distribution = {
        'total_samples': total_labels,
        'profit_taking': label_counts.get(1, 0),
        'stop_loss': label_counts.get(-1, 0),
        'max_holding': label_counts.get(0, 0),
        'profit_taking_pct': label_counts.get(1, 0) / total_labels * 100,
        'stop_loss_pct': label_counts.get(-1, 0) / total_labels * 100,
        'max_holding_pct': label_counts.get(0, 0) / total_labels * 100,
    }

    return distribution