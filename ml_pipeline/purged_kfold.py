#!/usr/bin/env python3
"""
Purged K-Fold Cross-Validation for Time Series

Implements purged K-fold CV with embargo to prevent data leakage in financial ML.
Base    # Check embargo violations (train data too close to test)
    if len(train_times) > 0 and len(test_times) > 0:
        time_diff = test_start - train_end
        # Convert to hours for comparison
        hours_diff = time_diff.total_seconds() / 3600
        embargo_violation = hours_diff < 1  # Less than 1 hour gap
    else:
        embargo_violation = FalseAdvances in Financial Machine Learning" by Marcos Lopez de Prado.

Features:
- Purged train/test splits (no overlap)
- Embargo buffers around test sets
- Time series aware splitting
- Leakage detection and reporting
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
from sklearn.model_selection import KFold
import logging

logger = logging.getLogger(__name__)

class PurgedKFold:
    """
    Purged K-Fold cross-validation for time series data.

    Prevents data leakage by:
    1. Purging overlapping observations between train/test
    2. Adding embargo buffers around test sets
    3. Ensuring temporal ordering
    """

    def __init__(self,
                 n_splits: int = 5,
                 purge_pct: float = 0.01,
                 embargo_pct: float = 0.01,
                 shuffle: bool = False):
        """
        Initialize purged K-fold CV.

        Args:
            n_splits: Number of CV folds
            purge_pct: Percentage of data to purge around test sets
            embargo_pct: Percentage of data to embargo after test sets
            shuffle: Whether to shuffle (NOT recommended for time series)
        """
        self.n_splits = n_splits
        self.purge_pct = purge_pct
        self.embargo_pct = embargo_pct
        self.shuffle = shuffle

        if shuffle:
            logger.warning("Shuffle=True is not recommended for time series data")

    def split(self,
              X: pd.DataFrame,
              y: Optional[pd.Series] = None,
              groups: Optional[np.ndarray] = None) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Generate purged K-fold splits with proper time ordering and embargo.

        Args:
            X: Feature matrix (must have datetime index)
            y: Target vector (optional)
            groups: Group labels (optional)

        Returns:
            List of (train_indices, test_indices) tuples
        """
        if not isinstance(X.index, pd.DatetimeIndex):
            raise ValueError("X must have a DatetimeIndex for time series CV")

        n_samples = len(X)
        indices = np.arange(n_samples)

        # Create time-ordered splits with proper embargo
        splits = []
        fold_size = n_samples // self.n_splits

        for i in range(self.n_splits):
            # Test set: later portion of the data
            test_start = (i + 1) * fold_size if i < self.n_splits - 1 else i * fold_size
            test_end = min(n_samples, (i + 2) * fold_size if i < self.n_splits - 1 else n_samples)

            test_idx = indices[test_start:test_end]

            # Train set: data before test, but respect embargo from previous folds
            if i == 0:
                # First fold: train on all data before test
                train_idx = indices[:test_start]
            else:
                # Subsequent folds: train up to embargo point before test
                embargo_size = max(1, int(n_samples * self.embargo_pct))
                train_end = max(0, test_start - embargo_size)
                train_idx = indices[:train_end]

            # Apply purging within this fold
            purged_train_idx, purged_test_idx = self._apply_purging_embargo(
                indices, train_idx, test_idx, n_samples
            )

            splits.append((purged_train_idx, purged_test_idx))

        return splits

    def _apply_purging_embargo(self,
                              indices: np.ndarray,
                              train_idx: np.ndarray,
                              test_idx: np.ndarray,
                              n_samples: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply purging and embargo to train/test indices.

        Args:
            indices: Full array of indices
            train_idx: Original train indices
            test_idx: Original test indices
            n_samples: Total number of samples

        Returns:
            Tuple of (purged_train_idx, purged_test_idx)
        """
        # Sort indices to ensure temporal order
        train_idx = np.sort(train_idx)
        test_idx = np.sort(test_idx)

        # Calculate purge and embargo sizes
        purge_size = max(1, int(n_samples * self.purge_pct))
        embargo_size = max(1, int(n_samples * self.embargo_pct))

        # Get test period boundaries
        test_start = test_idx[0]
        test_end = test_idx[-1]

        # Apply purging: remove observations too close to test set
        purge_start = max(0, test_start - purge_size)
        purge_end = min(n_samples, test_end + purge_size)

        # Remove purged observations from train set
        purged_train_mask = (train_idx < purge_start) | (train_idx > purge_end)
        purged_train_idx = train_idx[purged_train_mask]

        # Apply embargo: remove observations immediately after test set
        embargo_end = min(n_samples, test_end + embargo_size)
        embargo_mask = indices <= embargo_end
        embargoed_test_idx = test_idx[embargo_mask[test_idx]]

        return purged_train_idx, embargoed_test_idx

def detect_leakage(train_idx: np.ndarray,
                   test_idx: np.ndarray,
                   timestamps: pd.DatetimeIndex) -> dict:
    """
    Detect potential data leakage between train and test sets.

    Args:
        train_idx: Training set indices
        test_idx: Test set indices
        timestamps: Datetime index for all data

    Returns:
        Dictionary with leakage analysis
    """
    train_times = timestamps[train_idx]
    test_times = timestamps[test_idx]

    # Check for temporal overlap
    train_start, train_end = train_times.min(), train_times.max()
    test_start, test_end = test_times.min(), test_times.max()

    # Check for index overlap
    overlap = np.intersect1d(train_idx, test_idx)
    has_overlap = len(overlap) > 0

    # Check temporal ordering
    temporal_leakage = train_end >= test_start

    # Calculate embargo violations (train data too close to test)
    if len(train_times) > 0 and len(test_times) > 0:
        time_diff = test_start - train_end
        embargo_violation = time_diff < pd.Timedelta(hours=1)  # Example threshold
    else:
        embargo_violation = False

    return {
        'has_index_overlap': has_overlap,
        'has_temporal_leakage': temporal_leakage,
        'embargo_violation': embargo_violation,
        'train_period': (train_start, train_end),
        'test_period': (test_start, test_end),
        'overlap_indices': overlap.tolist(),
        'is_leakage_free': not (has_overlap or temporal_leakage or embargo_violation)
    }

def generate_leakage_report(cv_splits: List[Tuple[np.ndarray, np.ndarray]],
                           timestamps: pd.DatetimeIndex) -> dict:
    """
    Generate comprehensive leakage report for all CV folds.

    Args:
        cv_splits: List of (train_idx, test_idx) tuples
        timestamps: Datetime index for all data

    Returns:
        Dictionary with leakage analysis for all folds
    """
    report = {
        'total_folds': len(cv_splits),
        'folds_with_leakage': 0,
        'leakage_details': [],
        'overall_status': 'PASS'
    }

    for i, (train_idx, test_idx) in enumerate(cv_splits):
        fold_leakage = detect_leakage(train_idx, test_idx, timestamps)

        if not fold_leakage['is_leakage_free']:
            report['folds_with_leakage'] += 1
            report['overall_status'] = 'FAIL'

        fold_report = {
            'fold': i + 1,
            'status': 'PASS' if fold_leakage['is_leakage_free'] else 'FAIL',
            'train_samples': len(train_idx),
            'test_samples': len(test_idx),
            'leakage_info': fold_leakage
        }

        report['leakage_details'].append(fold_report)

    return report

def walk_forward_split(X: pd.DataFrame,
                      train_pct: float = 0.7,
                      val_pct: float = 0.15,
                      test_pct: float = 0.15,
                      embargo_pct: float = 0.01) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Create walk-forward train/validation/test split.

    Args:
        X: Feature matrix with datetime index
        train_pct: Percentage for training
        val_pct: Percentage for validation
        test_pct: Percentage for testing
        embargo_pct: Embargo percentage between sets

    Returns:
        Tuple of (train_idx, val_idx, test_idx)
    """
    n_samples = len(X)
    embargo_size = max(1, int(n_samples * embargo_pct))

    # Calculate split points
    train_end = int(n_samples * train_pct)
    val_end = train_end + int(n_samples * val_pct)

    # Apply embargo
    val_start = train_end + embargo_size
    test_start = val_end + embargo_size

    train_idx = np.arange(0, train_end)
    val_idx = np.arange(val_start, val_end)
    test_idx = np.arange(test_start, n_samples)

    return train_idx, val_idx, test_idx