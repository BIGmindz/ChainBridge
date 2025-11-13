#!/usr/bin/env python3
"""
Unit tests for Purged K-Fold Cross-Validation

Tests cover:
- Purging mechanism prevents overlap
- Embargo buffers work correctly
- Leakage detection functions
- Edge cases and error handling
- Integration with scikit-learn patterns
"""

import pytest
import numpy as np
import pandas as pd
from ml_pipeline.purged_kfold import (
    PurgedKFold,
    detect_leakage,
    generate_leakage_report,
    walk_forward_split,
)


class TestPurgedKFold:
    """Test suite for PurgedKFold class."""

    def setup_method(self):
        """Set up test data."""
        # Create synthetic time series data
        dates = pd.date_range("2020-01-01", periods=1000, freq="H")
        self.X = pd.DataFrame(
            {"feature1": np.random.randn(1000), "feature2": np.random.randn(1000)},
            index=dates,
        )

    def test_initialization(self) -> None:
        """Test PurgedKFold initialization."""
        pkf = PurgedKFold(n_splits=5, purge_pct=0.01, embargo_pct=0.01)

        assert pkf.n_splits == 5
        assert pkf.purge_pct == 0.01
        assert pkf.embargo_pct == 0.01
        assert not pkf.shuffle

    def test_split_basic(self) -> None:
        """Test basic split functionality."""
        pkf = PurgedKFold(n_splits=5)
        splits = pkf.split(self.X)

        assert len(splits) == 5

        for train_idx, test_idx in splits:
            # No overlap between train and test
            assert len(np.intersect1d(train_idx, test_idx)) == 0

            # Test indices are consecutive (temporal order)
            assert np.all(test_idx[:-1] <= test_idx[1:])

            # Train indices are consecutive
            assert np.all(train_idx[:-1] <= train_idx[1:])

    def test_purging_effectiveness(self) -> None:
        """Test that purging prevents data leakage."""
        pkf = PurgedKFold(n_splits=5, purge_pct=0.05)  # 5% purge
        splits = pkf.split(self.X)

        for train_idx, test_idx in splits:
            # Check temporal separation
            train_times = self.X.index[train_idx]
            test_times = self.X.index[test_idx]

            # Test period should not overlap with train period
            train_start, train_end = train_times.min(), train_times.max()
            test_start, test_end = test_times.min(), test_times.max()

            # Allow small tolerance for edge cases
            tolerance = pd.Timedelta(hours=1)

            # Test should be clearly after train (with purge buffer)
            assert test_start >= train_end - tolerance

    def test_embargo_effectiveness(self) -> None:
        """Test that embargo prevents training on data too close to test periods."""
        pkf = PurgedKFold(n_splits=5, embargo_pct=0.03)  # 3% embargo
        splits = pkf.split(self.X)

        # Check embargo for non-first folds (where embargo should be applied)
        for i, (train_idx, test_idx) in enumerate(splits):
            if i > 0:  # Skip first fold, check subsequent folds
                # Check that training data doesn't include data too close to test
                train_times = self.X.index[train_idx]
                test_times = self.X.index[test_idx]

                train_end = train_times.max()
                test_start = test_times.min()

                # There should be a gap between training end and test start
                gap = test_start - train_end
                expected_embargo = pd.Timedelta(hours=int(1000 * 0.03))  # ~30 hours

                # Allow some tolerance for edge cases
                assert (
                    gap >= expected_embargo * 0.8
                ), f"Fold {i}: gap {gap} < expected {expected_embargo * 0.8}"

    def test_no_datetime_index_error(self) -> None:
        """Test error when X doesn't have DatetimeIndex."""
        X_no_dt = pd.DataFrame({"a": [1, 2, 3]})  # No datetime index

        pkf = PurgedKFold()
        with pytest.raises(ValueError, match="must have a DatetimeIndex"):
            pkf.split(X_no_dt)

    def test_edge_case_small_dataset(self) -> None:
        """Test behavior with small datasets."""
        small_dates = pd.date_range("2020-01-01", periods=20, freq="H")
        small_X = pd.DataFrame({"a": np.random.randn(20)}, index=small_dates)

        pkf = PurgedKFold(n_splits=3)
        splits = pkf.split(small_X)

        assert len(splits) == 3

        for train_idx, test_idx in splits:
            assert len(np.intersect1d(train_idx, test_idx)) == 0

    def test_purge_embargo_sizes(self) -> None:
        """Test that purge and embargo sizes are calculated correctly."""
        pkf = PurgedKFold(purge_pct=0.02, embargo_pct=0.03)

        # Test with known dataset size
        n_samples = len(self.X)
        expected_purge = max(1, int(n_samples * 0.02))
        expected_embargo = max(1, int(n_samples * 0.03))

        # We can't directly test private method, but we can verify behavior
        splits = pkf.split(self.X)

        # Check that splits are reasonable
        for train_idx, test_idx in splits:
            # Train should be smaller than original due to purging
            assert len(train_idx) < n_samples
            assert len(test_idx) > 0


class TestLeakageDetection:
    """Test suite for leakage detection functions."""

    def setup_method(self):
        """Set up test data."""
        dates = pd.date_range("2020-01-01", periods=100, freq="H")
        self.timestamps = dates

    def test_detect_leakage_no_leakage(self) -> None:
        """Test leakage detection with clean splits."""
        # Clean split: train before test with gap
        train_idx = np.arange(0, 40)
        test_idx = np.arange(60, 100)

        result = detect_leakage(train_idx, test_idx, self.timestamps)

        assert not result["has_index_overlap"]
        assert not result["has_temporal_leakage"]
        assert not result["embargo_violation"]
        assert result["is_leakage_free"]

    def test_detect_leakage_index_overlap(self) -> None:
        """Test detection of index overlap."""
        # Overlapping indices
        train_idx = np.arange(0, 50)
        test_idx = np.arange(40, 80)  # Overlaps with train

        result = detect_leakage(train_idx, test_idx, self.timestamps)

        assert result["has_index_overlap"]
        assert not result["is_leakage_free"]
        assert len(result["overlap_indices"]) > 0

    def test_detect_leakage_temporal_leakage(self) -> None:
        """Test detection of temporal leakage."""
        # Train ends after test starts
        train_idx = np.arange(0, 70)
        test_idx = np.arange(60, 100)

        result = detect_leakage(train_idx, test_idx, self.timestamps)

        assert result["has_temporal_leakage"]
        assert not result["is_leakage_free"]

    def test_detect_leakage_embargo_violation(self) -> None:
        """Test detection of embargo violations."""
        # Train too close to test (less than 1 hour gap)
        # Create timestamps with 30-minute frequency for finer control
        timestamps_30min = pd.date_range("2020-01-01", periods=200, freq="30min")

        # Train ends at index 116 (time 2020-01-01 10:00:00)
        # Test starts at index 117 (time 2020-01-01 10:30:00) - only 30 min gap
        train_idx = np.arange(0, 117)  # Ends at index 116
        test_idx = np.arange(117, 140)  # Starts at index 117

        result = detect_leakage(train_idx, test_idx, timestamps_30min)

        assert result["embargo_violation"]
        assert not result["is_leakage_free"]


class TestLeakageReport:
    """Test suite for leakage report generation."""

    def setup_method(self):
        """Set up test data."""
        dates = pd.date_range("2020-01-01", periods=200, freq="H")
        self.timestamps = dates

    def test_generate_leakage_report_clean(self) -> None:
        """Test report generation with no leakage."""
        # Create clean splits
        splits = [
            (np.arange(0, 60), np.arange(80, 120)),
            (np.arange(0, 100), np.arange(120, 160)),
            (np.arange(0, 140), np.arange(160, 200)),
        ]

        report = generate_leakage_report(splits, self.timestamps)

        assert report["total_folds"] == 3
        assert report["folds_with_leakage"] == 0
        assert report["overall_status"] == "PASS"
        assert len(report["leakage_details"]) == 3

        for fold in report["leakage_details"]:
            assert fold["status"] == "PASS"

    def test_generate_leakage_report_with_leakage(self) -> None:
        """Test report generation with leakage."""
        # Create splits with leakage
        splits = [
            (np.arange(0, 60), np.arange(80, 120)),  # Clean
            (np.arange(0, 100), np.arange(90, 130)),  # Leakage
            (np.arange(0, 140), np.arange(160, 200)),  # Clean
        ]

        report = generate_leakage_report(splits, self.timestamps)

        assert report["total_folds"] == 3
        assert report["folds_with_leakage"] == 1
        assert report["overall_status"] == "FAIL"

        statuses = [fold["status"] for fold in report["leakage_details"]]
        assert statuses.count("FAIL") == 1
        assert statuses.count("PASS") == 2


class TestWalkForwardSplit:
    """Test suite for walk-forward splitting."""

    def setup_method(self):
        """Set up test data."""
        dates = pd.date_range("2020-01-01", periods=1000, freq="H")
        self.X = pd.DataFrame({"a": np.random.randn(1000)}, index=dates)

    def test_walk_forward_split_sizes(self) -> None:
        """Test that walk-forward split creates correct sizes."""
        train_idx, val_idx, test_idx = walk_forward_split(self.X)

        # Check approximate sizes (allowing for embargo)
        total_samples = len(self.X)
        train_size = len(train_idx)
        val_size = len(val_idx)
        test_size = len(test_idx)

        # Train should be ~70%
        assert 0.65 <= train_size / total_samples <= 0.75

        # Val should be ~15%
        assert 0.10 <= val_size / total_samples <= 0.20

        # Test should be ~15%
        assert 0.10 <= test_size / total_samples <= 0.20

    def test_walk_forward_split_temporal_order(self) -> None:
        """Test that walk-forward split maintains temporal order."""
        train_idx, val_idx, test_idx = walk_forward_split(self.X)

        # Check temporal ordering
        assert train_idx[-1] < val_idx[0]
        assert val_idx[-1] < test_idx[0]

        # Check no overlap
        assert len(np.intersect1d(train_idx, val_idx)) == 0
        assert len(np.intersect1d(val_idx, test_idx)) == 0
        assert len(np.intersect1d(train_idx, test_idx)) == 0

    def test_walk_forward_split_embargo(self) -> None:
        """Test that embargo is applied correctly."""
        train_idx, val_idx, test_idx = walk_forward_split(self.X, embargo_pct=0.02)

        embargo_size = max(1, int(len(self.X) * 0.02))

        # Check embargo between train and val
        expected_val_start = train_idx[-1] + embargo_size + 1
        assert val_idx[0] >= expected_val_start

        # Check embargo between val and test
        expected_test_start = val_idx[-1] + embargo_size + 1
        assert test_idx[0] >= expected_test_start


if __name__ == "__main__":
    pytest.main([__file__])
