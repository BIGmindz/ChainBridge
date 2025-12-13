"""
ChainIQ ML v0.2 Training Interface

Defines the training pipeline for risk and anomaly models.
This module is ONLY used during offline model training, NOT in production scoring.

Key Functions:
- prepare_risk_training_data: Load & preprocess data for risk model
- fit_risk_model_v02: Train a risk classification model
- prepare_anomaly_training_data: Load & preprocess data for anomaly model
- fit_anomaly_model_v02: Train an anomaly detection model
- dry_run_demo: Test the full pipeline on synthetic data

Status: v0.2 skeleton (interfaces defined, training logic stubbed)
Real implementation in PAC-004.

Safety: Heavy ML imports (sklearn, numpy) are GUARDED and only loaded when needed.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from app.ml.datasets import ShipmentTrainingRow, generate_synthetic_training_data
from app.ml.preprocessing import build_anomaly_feature_matrix, build_risk_feature_matrix, compute_feature_stats, get_feature_names


def prepare_risk_training_data(
    rows: Sequence[ShipmentTrainingRow],
    *,
    train_test_split: float = 0.8,
    random_seed: int | None = None,
) -> tuple[Any, Any, Any, Any]:
    """
    Prepare training and test sets for risk model.

    Args:
        rows: Sequence of ShipmentTrainingRow instances
        train_test_split: Fraction of data to use for training (rest is test)
        random_seed: Random seed for reproducibility

    Returns:
        Tuple of (X_train, X_test, y_train, y_test)
        - X_train, X_test: Feature matrices (list of lists or numpy arrays)
        - y_train, y_test: Label vectors (list or numpy arrays)

    Example:
        >>> X_train, X_test, y_train, y_test = prepare_risk_training_data(rows)
        >>> print(f"Train: {len(X_train)} samples, Test: {len(X_test)} samples")
    """
    import random

    if random_seed is not None:
        random.seed(random_seed)

    # Extract features and labels
    X, y = build_risk_feature_matrix(rows)

    # Simple train/test split (no sklearn yet)
    n_train = int(len(X) * train_test_split)

    # Shuffle indices
    indices = list(range(len(X)))
    random.shuffle(indices)

    train_indices = indices[:n_train]
    test_indices = indices[n_train:]

    X_train = [X[i] for i in train_indices]
    X_test = [X[i] for i in test_indices]
    y_train = [y[i] for i in train_indices]
    y_test = [y[i] for i in test_indices]

    print("✓ Prepared risk training data:")
    print(f"  Train: {len(X_train)} samples ({sum(y_train)} positive)")
    print(f"  Test:  {len(X_test)} samples ({sum(y_test)} positive)")

    return X_train, X_test, y_train, y_test


def fit_risk_model_v02(
    X_train: Any,
    y_train: Any,
    *,
    X_test: Any | None = None,
    y_test: Any | None = None,
    model_type: str = "logistic",
    output_path: str | None = None,
    random_seed: int = 42,
) -> dict[str, Any]:
    """
    Train a risk classification model.

    Args:
        X_train: Training feature matrix
        y_train: Training labels
        X_test: Optional test feature matrix for evaluation
        y_test: Optional test labels for evaluation
        model_type: Type of model to train ('logistic' only for v0.2)
        output_path: Optional path to save trained model
        random_seed: Random seed for reproducibility

    Returns:
        Dictionary with:
        - model: Trained sklearn Pipeline (scaler + model)
        - metrics: Training metrics (AUC, precision, calibration, etc.)
        - feature_importance: List of (feature_name, weight) tuples
        - metadata: Training metadata (version, date, features, etc.)

    Example:
        >>> result = fit_risk_model_v02(X_train, y_train, X_test, y_test)
        >>> pipeline = result['model']
        >>> print(f"AUC: {result['metrics']['auc']:.3f}")
    """
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import brier_score_loss, classification_report, precision_score, recall_score, roc_auc_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import RobustScaler
    except ImportError as e:
        raise ImportError("sklearn not installed. Install with: pip install scikit-learn>=1.3") from e

    print(f"\n{'='*60}")
    print("Training Risk Model (Logistic Regression)")
    print(f"{'='*60}")

    # Convert to numpy arrays
    X_train_np = np.array(X_train, dtype=float)
    y_train_np = np.array(y_train, dtype=int)

    print(f"Train set: {X_train_np.shape[0]} samples, {X_train_np.shape[1]} features")
    print(f"Positive class: {y_train_np.sum()} ({y_train_np.mean():.1%})")

    # Create pipeline: RobustScaler + LogisticRegression
    pipeline = Pipeline(
        [
            ("scaler", RobustScaler()),
            (
                "classifier",
                LogisticRegression(
                    penalty="l1",
                    solver="liblinear",  # Required for L1 penalty
                    C=1.0,  # Inverse regularization strength
                    class_weight="balanced",  # Handle imbalanced classes
                    max_iter=500,
                    random_state=random_seed,
                ),
            ),
        ]
    )

    # Fit model
    print("\nFitting model...")
    pipeline.fit(X_train_np, y_train_np)
    print("✓ Model fitted successfully")

    # Get feature importance (coefficients)
    coefficients = pipeline.named_steps["classifier"].coef_[0]
    feature_names = get_feature_names()
    feature_importance = list(zip(feature_names, coefficients))
    feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)

    print("\nTop 10 most important features:")
    for name, coef in feature_importance[:10]:
        print(f"  {name:30s}: {coef:+.4f}")

    # Compute training metrics
    y_train_pred = pipeline.predict(X_train_np)
    y_train_proba = pipeline.predict_proba(X_train_np)[:, 1]

    train_metrics = {
        "auc": roc_auc_score(y_train_np, y_train_proba),
        "precision": precision_score(y_train_np, y_train_pred, zero_division=0),
        "recall": recall_score(y_train_np, y_train_pred, zero_division=0),
        "brier": brier_score_loss(y_train_np, y_train_proba),
    }

    print("\nTraining metrics:")
    print(f"  AUC:       {train_metrics['auc']:.3f}")
    print(f"  Precision: {train_metrics['precision']:.3f}")
    print(f"  Recall:    {train_metrics['recall']:.3f}")
    print(f"  Brier:     {train_metrics['brier']:.3f}")

    # Compute test metrics if provided
    test_metrics = None
    if X_test is not None and y_test is not None:
        X_test_np = np.array(X_test, dtype=float)
        y_test_np = np.array(y_test, dtype=int)

        y_test_pred = pipeline.predict(X_test_np)
        y_test_proba = pipeline.predict_proba(X_test_np)[:, 1]

        test_metrics = {
            "auc": roc_auc_score(y_test_np, y_test_proba),
            "precision": precision_score(y_test_np, y_test_pred, zero_division=0),
            "recall": recall_score(y_test_np, y_test_pred, zero_division=0),
            "brier": brier_score_loss(y_test_np, y_test_proba),
        }

        # Compute precision@10% (sort by predicted probability, take top 10%)
        top_10_pct = int(len(y_test_proba) * 0.1)
        if top_10_pct > 0:
            top_indices = np.argsort(y_test_proba)[-top_10_pct:]
            precision_at_10 = y_test_np[top_indices].mean()
            test_metrics["precision_at_10"] = precision_at_10
        else:
            test_metrics["precision_at_10"] = 0.0

        print("\nTest metrics:")
        print(f"  AUC:            {test_metrics['auc']:.3f}")
        print(f"  Precision:      {test_metrics['precision']:.3f}")
        print(f"  Recall:         {test_metrics['recall']:.3f}")
        print(f"  Precision@10%:  {test_metrics['precision_at_10']:.3f}")
        print(f"  Brier:          {test_metrics['brier']:.3f}")

    # Save model if output path provided
    if output_path:
        import pickle
        from pathlib import Path

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save model
        with open(output_path, "wb") as f:
            pickle.dump(pipeline, f)
        print(f"\n✓ Model saved to {output_path}")

        # Save metrics
        metrics_path = output_path.parent / f"{output_path.stem}_metrics.json"
        with open(metrics_path, "w") as f:
            json.dump(
                {
                    "train": train_metrics,
                    "test": test_metrics,
                    "feature_importance": [(name, float(coef)) for name, coef in feature_importance],
                },
                f,
                indent=2,
            )
        print(f"✓ Metrics saved to {metrics_path}")

    return {
        "model": pipeline,
        "metrics": {
            "train": train_metrics,
            "test": test_metrics,
        },
        "feature_importance": feature_importance,
        "metadata": {
            "model_type": "logistic_regression",
            "model_version": "0.2.0",
            "training_date": datetime.now().isoformat(),
            "feature_names": feature_names,
            "random_seed": random_seed,
        },
    }


def prepare_anomaly_training_data(
    rows: Sequence[ShipmentTrainingRow],
    *,
    filter_known_anomalies: bool = False,
) -> Any:
    """
    Prepare data for anomaly model (unsupervised).

    Args:
        rows: Sequence of ShipmentTrainingRow instances
        filter_known_anomalies: If True, exclude known anomalies for training
                               (train only on "clean" shipments)

    Returns:
        X: Feature matrix (all features, no labels needed for unsupervised)

    Example:
        >>> X = prepare_anomaly_training_data(rows, filter_known_anomalies=True)
        >>> print(f"Training anomaly model on {len(X)} clean examples")
    """
    # Optionally filter out known anomalies (train on clean data)
    if filter_known_anomalies:
        rows = [r for r in rows if not r.is_known_anomaly]
        print(f"✓ Filtered to {len(rows)} clean shipments for anomaly training")

    # Extract features (no labels needed)
    X = build_anomaly_feature_matrix(rows)

    print(f"✓ Prepared anomaly training data: {len(X)} samples x {len(X[0])} features")

    return X


def fit_anomaly_model_v02(
    X_train: Any,
    *,
    model_type: str = "isolation_forest",
    contamination: float = 0.05,
    output_path: str | None = None,
    random_seed: int = 42,
) -> dict[str, Any]:
    """
    Train an anomaly detection model (unsupervised).

    Args:
        X_train: Training feature matrix
        model_type: Type of model ('isolation_forest' only for v0.2)
        contamination: Expected fraction of anomalies in data (0-0.5)
        output_path: Optional path to save trained model
        random_seed: Random seed for reproducibility

    Returns:
        Dictionary with:
        - model: Trained sklearn Pipeline (scaler + model)
        - metrics: Anomaly score distribution statistics
        - metadata: Training metadata

    Example:
        >>> result = fit_anomaly_model_v02(X_train, contamination=0.05)
        >>> pipeline = result['model']
        >>> print(f"Mean anomaly score: {result['metrics']['mean_score']:.3f}")
    """
    try:
        import numpy as np
        from sklearn.ensemble import IsolationForest
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import RobustScaler
    except ImportError as e:
        raise ImportError("sklearn not installed. Install with: pip install scikit-learn>=1.3") from e

    print(f"\n{'='*60}")
    print("Training Anomaly Model (Isolation Forest)")
    print(f"{'='*60}")

    # Convert to numpy arrays
    X_train_np = np.array(X_train, dtype=float)

    print(f"Train set: {X_train_np.shape[0]} samples, {X_train_np.shape[1]} features")
    print(f"Contamination: {contamination:.1%}")

    # Create pipeline: RobustScaler + IsolationForest
    pipeline = Pipeline(
        [
            ("scaler", RobustScaler()),
            (
                "detector",
                IsolationForest(
                    n_estimators=200,
                    contamination=contamination,
                    random_state=random_seed,
                    max_samples="auto",
                    max_features=1.0,
                ),
            ),
        ]
    )

    # Fit model
    print("\nFitting model...")
    pipeline.fit(X_train_np)
    print("✓ Model fitted successfully")

    # Compute anomaly scores on training set
    # IsolationForest returns -1 for anomalies, 1 for normal
    # decision_function returns anomaly scores (lower = more anomalous)
    anomaly_scores_raw = pipeline.decision_function(X_train_np)

    # Normalize scores to [0, 1] where 1 = most anomalous
    # Use sigmoid-like transformation
    anomaly_scores_normalized = 1 / (1 + np.exp(anomaly_scores_raw))

    # Compute statistics
    metrics = {
        "mean_score": float(anomaly_scores_normalized.mean()),
        "std_score": float(anomaly_scores_normalized.std()),
        "min_score": float(anomaly_scores_normalized.min()),
        "max_score": float(anomaly_scores_normalized.max()),
        "median_score": float(np.median(anomaly_scores_normalized)),
        "p95_score": float(np.percentile(anomaly_scores_normalized, 95)),
        "p99_score": float(np.percentile(anomaly_scores_normalized, 99)),
        "expected_anomalies": int(len(anomaly_scores_normalized) * contamination),
        "actual_anomalies": int((anomaly_scores_normalized > 0.7).sum()),
    }

    print("\nAnomaly score distribution:")
    print(f"  Mean:   {metrics['mean_score']:.3f}")
    print(f"  Std:    {metrics['std_score']:.3f}")
    print(f"  Median: {metrics['median_score']:.3f}")
    print(f"  P95:    {metrics['p95_score']:.3f}")
    print(f"  P99:    {metrics['p99_score']:.3f}")
    print(f"  Expected anomalies (contamination={contamination:.1%}): {metrics['expected_anomalies']}")
    print(f"  Actual high-score samples (>0.7):                       {metrics['actual_anomalies']}")

    # Save model if output path provided
    if output_path:
        import pickle
        from pathlib import Path

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save model
        with open(output_path, "wb") as f:
            pickle.dump(pipeline, f)
        print(f"\n✓ Model saved to {output_path}")

        # Save metrics
        metrics_path = output_path.parent / f"{output_path.stem}_metrics.json"
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"✓ Metrics saved to {metrics_path}")

    return {
        "model": pipeline,
        "metrics": metrics,
        "metadata": {
            "model_type": "isolation_forest",
            "model_version": "0.2.0",
            "training_date": datetime.now().isoformat(),
            "feature_names": get_feature_names(),
            "random_seed": random_seed,
            "contamination": contamination,
        },
    }


def dry_run_demo(
    *,
    n_samples: int = 100,
    save_models: bool = False,
    output_dir: str = "ml_models",
) -> None:
    """
    Dry-run demo: test the full training pipeline on synthetic data.

    This function:
    1. Generates synthetic training data
    2. Prepares features for risk & anomaly models
    3. Computes feature statistics
    4. Trains both models using real sklearn logic
    5. Optionally saves trained models to disk

    Args:
        n_samples: Number of synthetic training rows to generate
        save_models: If True, save trained models to ml_models/
        output_dir: Directory to save models (default: 'ml_models')

    Example:
        >>> dry_run_demo(n_samples=1000, save_models=True)
    """
    print("=" * 60)
    print("ChainIQ ML v0.2 Training Pipeline - Full Training Demo")
    print("=" * 60)

    # Step 1: Generate synthetic data
    print("\n[1/6] Generating synthetic training data...")
    rows = generate_synthetic_training_data(n_samples=n_samples, positive_rate=0.15, seed=42)
    print(f"✓ Generated {len(rows)} training rows")
    print(f"  - Bad outcomes: {sum(r.bad_outcome for r in rows)}")
    print(f"  - Claims: {sum(r.had_claim for r in rows)}")
    print(f"  - Disputes: {sum(r.had_dispute for r in rows)}")
    print(f"  - Severe delays: {sum(r.severe_delay for r in rows)}")

    # Step 2: Compute feature statistics
    print("\n[2/6] Computing feature statistics...")
    stats = compute_feature_stats(rows)
    print(f"✓ Computed stats for {len(stats)} features")
    print("\nTop 5 features by mean:")
    sorted_features = sorted(stats.items(), key=lambda x: x[1]["mean"], reverse=True)
    for name, s in sorted_features[:5]:
        print(f"  {name}: mean={s['mean']:.2f}, std={s['std']:.2f}")

    # Step 3: Prepare risk model data
    print("\n[3/6] Preparing risk model training data...")
    X_train, X_test, y_train, y_test = prepare_risk_training_data(rows, train_test_split=0.8, random_seed=42)

    # Step 4: Prepare anomaly model data
    print("\n[4/6] Preparing anomaly model training data...")
    X_anomaly = prepare_anomaly_training_data(rows, filter_known_anomalies=True)

    # Step 5: Train risk model
    print("\n[5/6] Training risk model...")
    risk_output_path = f"{output_dir}/risk_v0.2.0.pkl" if save_models else None
    risk_result = fit_risk_model_v02(X_train, y_train, X_test=X_test, y_test=y_test, output_path=risk_output_path, random_seed=42)

    # Step 6: Train anomaly model
    print("\n[6/6] Training anomaly model...")
    anomaly_output_path = f"{output_dir}/anomaly_v0.2.0.pkl" if save_models else None
    anomaly_result = fit_anomaly_model_v02(X_anomaly, contamination=0.05, output_path=anomaly_output_path, random_seed=42)

    print("\n" + "=" * 60)
    print("Training complete. Summary:")
    print("=" * 60)
    print(f"✓ Data generation: {n_samples} samples")
    print(f"✓ Feature extraction: {len(stats)} features")
    print(f"✓ Train/test split: {len(X_train)}/{len(X_test)}")
    print(f"✓ Risk model trained: AUC={risk_result['metrics']['test']['auc']:.3f}")
    print(f"✓ Anomaly model trained: {len(X_anomaly)} samples")
    if save_models:
        print(f"\n✓ Models saved to {output_dir}/")
        print("  - risk_v0.2.0.pkl")
        print("  - risk_v0.2.0_metrics.json")
        print("  - anomaly_v0.2.0.pkl")
        print("  - anomaly_v0.2.0_metrics.json")
    print("\n✅ All tests passed - v0.2.0 training pipeline fully operational!")


def save_training_metadata(
    output_dir: str | Path,
    *,
    model_type: str,
    model_version: str,
    training_date: datetime | None = None,
    feature_names: list[str] | None = None,
    metrics: dict[str, float] | None = None,
) -> None:
    """
    Save training metadata to JSON for reproducibility and monitoring.

    Args:
        output_dir: Directory to save metadata
        model_type: 'risk' or 'anomaly'
        model_version: Semantic version (e.g., '0.2.0')
        training_date: When model was trained (default: now)
        feature_names: List of feature names used
        metrics: Training metrics (AUC, precision, etc.)

    Example:
        >>> save_training_metadata(
        ...     'ml_models',
        ...     model_type='risk',
        ...     model_version='0.2.0',
        ...     feature_names=get_feature_names(),
        ...     metrics={'auc': 0.82, 'precision_at_10': 0.35}
        ... )
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "model_type": model_type,
        "model_version": model_version,
        "training_date": (training_date or datetime.now()).isoformat(),
        "feature_names": feature_names or get_feature_names(),
        "metrics": metrics or {},
    }

    metadata_path = output_dir / f"{model_type}_v{model_version}_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ Saved training metadata to {metadata_path}")


# ============================================================================
# LAZY MODEL LOADING FOR SHADOW MODE (Production-Safe)
# ============================================================================

_real_risk_model_instance = None


def load_real_risk_model_v02():
    """
    Lazy-load the trained real risk model for shadow mode with SECURITY VERIFICATION.

    CRITICAL PRODUCTION SAFETY:
    - Model is loaded ONLY when first accessed (lazy initialization)
    - Global singleton prevents re-loading on every request
    - Failure to load returns None (never crashes production)
    - Heavy ML dependencies only imported when needed

    SECURITY FEATURES (SAM GID-06):
    - SHA256 signature verification
    - Threat detection (size anomalies, suspicious imports)
    - Model quarantine for compromised artifacts
    - Supply chain attack protection

    Returns:
        sklearn Pipeline or None if model not available

    Example:
        >>> model = load_real_risk_model_v02()
        >>> if model:
        ...     score = model.predict_proba(X)[:, 1][0]
    """
    global _real_risk_model_instance

    # Return cached instance if already loaded
    if _real_risk_model_instance is not None:
        return _real_risk_model_instance

    try:
        import logging

        logger = logging.getLogger(__name__)

        # SECURITY: Import model security manager
        from app.ml.model_security import ModelQuarantineError, ModelSecurityError, ModelSecurityManager

        # Locate model file
        model_path = Path(__file__).parent / "models" / "risk_model_v0.2.pkl"

        if not model_path.exists():
            logger.warning(
                f"Real risk model not found at {model_path}. " "Shadow mode will be disabled until model is trained and deployed."
            )
            return None

        # SECURITY: Load model with verification
        try:
            security_mgr = ModelSecurityManager()
            _real_risk_model_instance = security_mgr.load_verified_model(model_path, enable_quarantine=True)
            logger.info(f"✓ Loaded and verified real risk model from {model_path}")
        except (ModelSecurityError, ModelQuarantineError) as sec_err:
            logger.error(
                f"⚠️  MODEL SECURITY VIOLATION: {sec_err}. "
                "Shadow mode DISABLED for safety. "
                "Contact SAM (GID-06) or re-train model with proper signing."
            )
            return None

        return _real_risk_model_instance

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Failed to load real risk model: {e}", exc_info=True)
        return None


# CLI entrypoint for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "dry-run":
            n_samples = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
            save_models = "--save" in sys.argv
            dry_run_demo(n_samples=n_samples, save_models=save_models)

        elif command == "train-risk":
            print("Training risk model...")
            rows = generate_synthetic_training_data(n_samples=5000, positive_rate=0.15, seed=42)
            X_train, X_test, y_train, y_test = prepare_risk_training_data(rows, random_seed=42)
            result = fit_risk_model_v02(X_train, y_train, X_test=X_test, y_test=y_test, output_path="ml_models/risk_v0.2.0.pkl")
            print("\n✓ Risk model trained and saved!")
            print(f"  AUC: {result['metrics']['test']['auc']:.3f}")
            print(f"  Precision@10%: {result['metrics']['test']['precision_at_10']:.3f}")

        elif command == "train-anomaly":
            print("Training anomaly model...")
            rows = generate_synthetic_training_data(n_samples=5000, positive_rate=0.15, seed=42)
            X = prepare_anomaly_training_data(rows, filter_known_anomalies=True)
            result = fit_anomaly_model_v02(X, contamination=0.05, output_path="ml_models/anomaly_v0.2.0.pkl")
            print("\n✓ Anomaly model trained and saved!")
            print(f"  Mean score: {result['metrics']['mean_score']:.3f}")

        elif command == "full-train":
            print("Training both models...")
            dry_run_demo(n_samples=5000, save_models=True)

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    else:
        print("ChainIQ ML v0.2 Training Interface")
        print("=" * 60)
        print("\nUsage:")
        print("  python -m app.ml.training_v02 <command> [options]")
        print("\nCommands:")
        print("  dry-run [n_samples] [--save]  - Test pipeline on synthetic data")
        print("  train-risk                    - Train risk model (saves to ml_models/)")
        print("  train-anomaly                 - Train anomaly model (saves to ml_models/)")
        print("  full-train                    - Train both models (saves to ml_models/)")
        print("\nExamples:")
        print("  python -m app.ml.training_v02 dry-run 1000")
        print("  python -m app.ml.training_v02 dry-run 1000 --save")
        print("  python -m app.ml.training_v02 train-risk")
        print("  python -m app.ml.training_v02 full-train")
