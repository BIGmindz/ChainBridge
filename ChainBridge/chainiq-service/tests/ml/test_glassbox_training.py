"""
Tests for GlassBox ML Training Pipeline

Tests training reproducibility and artifact generation.
Uses synthetic data for fast, deterministic tests.

Run with:
    pytest tests/ml/test_glassbox_training.py -v
"""

import json
import pickle
import tempfile
from pathlib import Path

import pytest

from app.ml.datasets import generate_synthetic_training_data

# Check if interpret is available
try:
    import interpret.glassbox  # noqa: F401

    INTERPRET_AVAILABLE = True
except ImportError:
    INTERPRET_AVAILABLE = False


class TestTrainingReproducibility:
    """Tests that training is reproducible with fixed seeds."""

    def test_synthetic_data_determinism(self):
        """Same seed produces same synthetic data."""
        rows1 = generate_synthetic_training_data(n_samples=100, positive_rate=0.2, seed=42)
        rows2 = generate_synthetic_training_data(n_samples=100, positive_rate=0.2, seed=42)

        # Same labels
        labels1 = [r.bad_outcome for r in rows1]
        labels2 = [r.bad_outcome for r in rows2]
        assert labels1 == labels2

        # Same corridor distribution
        corridors1 = [r.features.corridor for r in rows1]
        corridors2 = [r.features.corridor for r in rows2]
        assert corridors1 == corridors2

    def test_different_seeds_produce_different_labels(self):
        """Different seeds produce different label distributions."""
        rows1 = generate_synthetic_training_data(n_samples=100, positive_rate=0.2, seed=42)
        rows2 = generate_synthetic_training_data(n_samples=100, positive_rate=0.2, seed=123)

        labels1 = [r.bad_outcome for r in rows1]
        labels2 = [r.bad_outcome for r in rows2]

        # Should have different label distributions
        assert labels1 != labels2

    def test_prepare_risk_training_data_reproducibility(self):
        """Train/test split is reproducible."""
        from app.ml.training_v02 import prepare_risk_training_data

        rows = generate_synthetic_training_data(n_samples=200, seed=42)

        X1_train, X1_test, y1_train, y1_test = prepare_risk_training_data(rows, random_seed=42)
        X2_train, X2_test, y2_train, y2_test = prepare_risk_training_data(rows, random_seed=42)

        # Same split
        assert X1_train == X2_train
        assert X1_test == X2_test
        assert y1_train == y2_train
        assert y1_test == y2_test


@pytest.mark.skipif(not INTERPRET_AVAILABLE, reason="interpret package not installed")
class TestGlassBoxRiskTraining:
    """Tests for GlassBox risk model training."""

    @pytest.mark.slow
    def test_train_saves_model_and_metadata(self):
        """Training saves model pickle and metadata JSON."""
        from app.ml.glassbox_training import train_glassbox_risk_model

        rows = generate_synthetic_training_data(n_samples=500, positive_rate=0.2, seed=42)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = train_glassbox_risk_model(
                rows,
                output_dir=tmpdir,
                model_version="test",
                random_seed=42,
            )

            # Check model file exists
            model_path = Path(result["model_path"])
            assert model_path.exists()
            assert model_path.suffix == ".pkl"

            # Check metadata file exists
            metadata_path = Path(tmpdir) / "risk_glassbox_vtest_metadata.json"
            assert metadata_path.exists()

            # Load and verify metadata
            with open(metadata_path) as f:
                metadata = json.load(f)

            assert metadata["model_id"] == "risk_glassbox"
            assert metadata["model_version"] == "test"
            assert "train_metrics" in metadata
            assert "test_metrics" in metadata
            assert "feature_importance" in metadata

    @pytest.mark.slow
    def test_train_produces_valid_metrics(self):
        """Training produces valid AUC, precision, recall."""
        from app.ml.glassbox_training import train_glassbox_risk_model

        rows = generate_synthetic_training_data(n_samples=500, positive_rate=0.2, seed=42)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = train_glassbox_risk_model(
                rows,
                output_dir=tmpdir,
                random_seed=42,
            )

            metrics = result["metrics"]

            # Train metrics should be valid
            assert 0.0 <= metrics["train"]["auc"] <= 1.0
            assert 0.0 <= metrics["train"]["precision"] <= 1.0
            assert 0.0 <= metrics["train"]["recall"] <= 1.0

            # Test metrics should be valid
            assert 0.0 <= metrics["test"]["auc"] <= 1.0
            assert 0.0 <= metrics["test"]["precision"] <= 1.0
            assert 0.0 <= metrics["test"]["recall"] <= 1.0

    @pytest.mark.slow
    def test_trained_model_can_predict(self):
        """Trained model can make predictions."""
        import numpy as np

        from app.ml.glassbox_training import train_glassbox_risk_model
        from app.ml.preprocessing import build_risk_feature_matrix

        rows = generate_synthetic_training_data(n_samples=500, positive_rate=0.2, seed=42)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = train_glassbox_risk_model(
                rows,
                output_dir=tmpdir,
                random_seed=42,
            )

            model = result["model"]

            # Get some test features
            X, _ = build_risk_feature_matrix(rows[:10])
            X_np = np.array(X, dtype=float)

            # Predict
            proba = model.predict_proba(X_np)

            assert proba.shape == (10, 2)
            assert all(0.0 <= p <= 1.0 for p in proba[:, 1])


class TestGlassBoxAnomalyTraining:
    """Tests for GlassBox anomaly model training."""

    def test_train_saves_stats(self):
        """Training saves feature statistics."""
        from app.ml.glassbox_training import train_glassbox_anomaly_model

        rows = generate_synthetic_training_data(n_samples=500, seed=42)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = train_glassbox_anomaly_model(
                rows,
                output_dir=tmpdir,
                model_version="test",
            )

            # Check model file exists
            model_path = Path(result["model_path"])
            assert model_path.exists()

            # Load and verify stats
            with open(model_path, "rb") as f:
                stats = pickle.load(f)

            # Should have median and MAD for each feature
            for name, s in stats.items():
                assert "median" in s
                assert "mad" in s
                assert isinstance(s["median"], float)
                assert isinstance(s["mad"], float)
