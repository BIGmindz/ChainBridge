"""
GlassBox Model Training Pipeline

Reproducible training for interpretable ML models using EBM (Explainable Boosting Machine).

Key Properties:
- REPRODUCIBLE: Fixed seeds, deterministic splitting
- VERSIONED: All artifacts tagged with version + timestamp
- AUDITABLE: Full metrics, feature importance, training metadata saved

CLI Usage:
    python -m app.ml.glassbox_training train-risk --seed 42 --output ml_models/
    python -m app.ml.glassbox_training train-anomaly --seed 42 --output ml_models/
    python -m app.ml.glassbox_training evaluate --model ml_models/risk_glassbox_v1.0.0.pkl
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Sequence

from app.ml.datasets import ShipmentTrainingRow, generate_synthetic_training_data
from app.ml.preprocessing import build_risk_feature_matrix, get_feature_names

logger = logging.getLogger(__name__)

# Model version - increment on each training run modification
MODEL_VERSION = "1.0.0"


def compute_robust_feature_stats(rows: Sequence[ShipmentTrainingRow]) -> Dict[str, Dict[str, float]]:
    """
    Compute robust statistics (median, MAD) for each feature.

    MAD (Median Absolute Deviation) is robust to outliers.

    Args:
        rows: Training data

    Returns:
        Dictionary mapping feature_name → {median, mad, min, max}
    """
    import numpy as np

    feature_names = get_feature_names()
    X, _ = build_risk_feature_matrix(rows)
    X_np = np.array(X, dtype=float)

    stats = {}
    for i, name in enumerate(feature_names):
        values = X_np[:, i]

        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))

        stats[name] = {
            "median": median,
            "mad": mad if mad > 0 else 1e-6,  # Avoid division by zero
            "min": float(np.min(values)),
            "max": float(np.max(values)),
        }

    return stats


def train_glassbox_risk_model(
    rows: Sequence[ShipmentTrainingRow],
    *,
    output_dir: str | Path = "ml_models",
    model_version: str = MODEL_VERSION,
    random_seed: int = 42,
    test_split: float = 0.2,
    max_bins: int = 256,
    interactions: int = 10,
) -> Dict[str, Any]:
    """
    Train GlassBox risk model using Explainable Boosting Machine.

    REPRODUCIBILITY GUARANTEES:
    - Fixed random_seed for train/test split
    - Fixed random_state in EBM
    - Deterministic feature preprocessing

    Args:
        rows: Training data (ShipmentTrainingRow instances)
        output_dir: Directory for model artifacts
        model_version: Semantic version string
        random_seed: Random seed for reproducibility
        test_split: Fraction of data for test set
        max_bins: EBM parameter (more bins = more precision)
        interactions: Max number of pairwise interactions to detect

    Returns:
        Dictionary with:
        - model: Trained EBM classifier
        - metrics: Training + test metrics
        - feature_importance: Global feature importance
        - metadata: Training metadata
    """
    try:
        import numpy as np
        from interpret.glassbox import ExplainableBoostingClassifier
        from sklearn.metrics import brier_score_loss, f1_score, precision_score, recall_score, roc_auc_score
    except ImportError as e:
        raise ImportError("Required packages not installed. Run: pip install interpret scikit-learn") from e

    print(f"\n{'='*60}")
    print("Training GlassBox Risk Model (EBM)")
    print(f"{'='*60}")

    # Build feature matrix
    X, y = build_risk_feature_matrix(rows)
    feature_names = get_feature_names()

    # Convert to numpy
    X_np = np.array(X, dtype=float)
    y_np = np.array(y, dtype=int)

    print(f"Dataset: {len(X_np)} samples, {X_np.shape[1]} features")
    print(f"Positive class: {y_np.sum()} ({y_np.mean():.1%})")

    # Reproducible train/test split
    rng = np.random.RandomState(random_seed)
    indices = np.arange(len(X_np))
    rng.shuffle(indices)

    n_test = int(len(X_np) * test_split)
    test_indices = indices[:n_test]
    train_indices = indices[n_test:]

    X_train, X_test = X_np[train_indices], X_np[test_indices]
    y_train, y_test = y_np[train_indices], y_np[test_indices]

    print(f"Train: {len(X_train)} samples ({y_train.mean():.1%} positive)")
    print(f"Test:  {len(X_test)} samples ({y_test.mean():.1%} positive)")

    # Train EBM
    print("\nTraining EBM classifier...")
    ebm = ExplainableBoostingClassifier(
        feature_names=feature_names,
        random_state=random_seed,
        max_bins=max_bins,
        interactions=interactions,
        outer_bags=8,
        inner_bags=0,
        learning_rate=0.01,
        validation_size=0.15,
        early_stopping_rounds=50,
        n_jobs=-1,
    )

    ebm.fit(X_train, y_train)
    print("✓ EBM trained successfully")

    # Compute metrics
    y_train_pred = ebm.predict(X_train)
    y_train_proba = ebm.predict_proba(X_train)[:, 1]

    y_test_pred = ebm.predict(X_test)
    y_test_proba = ebm.predict_proba(X_test)[:, 1]

    train_metrics = {
        "auc": float(roc_auc_score(y_train, y_train_proba)),
        "precision": float(precision_score(y_train, y_train_pred, zero_division=0)),
        "recall": float(recall_score(y_train, y_train_pred, zero_division=0)),
        "f1": float(f1_score(y_train, y_train_pred, zero_division=0)),
        "brier": float(brier_score_loss(y_train, y_train_proba)),
    }

    test_metrics = {
        "auc": float(roc_auc_score(y_test, y_test_proba)),
        "precision": float(precision_score(y_test, y_test_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_test_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_test_pred, zero_division=0)),
        "brier": float(brier_score_loss(y_test, y_test_proba)),
    }

    # Precision@10%
    top_10_pct = int(len(y_test_proba) * 0.1)
    if top_10_pct > 0:
        top_indices = np.argsort(y_test_proba)[-top_10_pct:]
        test_metrics["precision_at_10"] = float(y_test[top_indices].mean())

    print("\nTraining metrics:")
    print(f"  AUC:       {train_metrics['auc']:.3f}")
    print(f"  Precision: {train_metrics['precision']:.3f}")
    print(f"  Recall:    {train_metrics['recall']:.3f}")
    print(f"  F1:        {train_metrics['f1']:.3f}")

    print("\nTest metrics:")
    print(f"  AUC:            {test_metrics['auc']:.3f}")
    print(f"  Precision:      {test_metrics['precision']:.3f}")
    print(f"  Recall:         {test_metrics['recall']:.3f}")
    print(f"  F1:             {test_metrics['f1']:.3f}")
    print(f"  Precision@10%:  {test_metrics.get('precision_at_10', 0):.3f}")

    # Extract feature importance
    global_exp = ebm.explain_global()
    importance_names = global_exp._internal_obj["overall"]["names"]
    importance_scores = global_exp._internal_obj["overall"]["scores"]
    feature_importance = list(zip(importance_names, [float(s) for s in importance_scores]))
    feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)

    print("\nTop 10 most important features:")
    for name, score in feature_importance[:10]:
        print(f"  {name:35s}: {score:.4f}")

    # Save artifacts
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_filename = f"risk_glassbox_v{model_version}.pkl"
    model_path = output_dir / model_filename

    import pickle

    with open(model_path, "wb") as f:
        pickle.dump(ebm, f)
    print(f"\n✓ Model saved to {model_path}")

    # Save metadata
    metadata = {
        "model_id": "risk_glassbox",
        "model_version": model_version,
        "model_type": "ExplainableBoostingClassifier",
        "training_date": datetime.now(timezone.utc).isoformat(),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "n_features": X_np.shape[1],
        "feature_names": feature_names,
        "hyperparameters": {
            "max_bins": max_bins,
            "interactions": interactions,
            "random_seed": random_seed,
        },
        "train_metrics": train_metrics,
        "test_metrics": test_metrics,
        "feature_importance": feature_importance,
    }

    metadata_path = output_dir / f"risk_glassbox_v{model_version}_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata saved to {metadata_path}")

    return {
        "model": ebm,
        "model_path": str(model_path),
        "metrics": {"train": train_metrics, "test": test_metrics},
        "feature_importance": feature_importance,
        "metadata": metadata,
    }


def train_glassbox_anomaly_model(
    rows: Sequence[ShipmentTrainingRow],
    *,
    output_dir: str | Path = "ml_models",
    model_version: str = MODEL_VERSION,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """
    Train GlassBox anomaly model using learned feature statistics.

    Uses robust statistics (median, MAD) that are resistant to outliers.
    Anomaly score = how far features deviate from learned norms.

    Args:
        rows: Training data (treat as "normal" examples)
        output_dir: Directory for model artifacts
        model_version: Semantic version string
        random_seed: Random seed for reproducibility

    Returns:
        Dictionary with model stats and metadata
    """

    print(f"\n{'='*60}")
    print("Training GlassBox Anomaly Model (Statistics-based)")
    print(f"{'='*60}")

    # Compute robust statistics for each feature
    stats = compute_robust_feature_stats(rows)

    print(f"Learned statistics for {len(stats)} features")
    print("\nSample feature statistics:")
    for name in list(stats.keys())[:5]:
        s = stats[name]
        print(f"  {name}: median={s['median']:.3f}, MAD={s['mad']:.3f}")

    # Save stats as model
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_filename = f"anomaly_glassbox_v{model_version}.pkl"
    model_path = output_dir / model_filename

    import pickle

    with open(model_path, "wb") as f:
        pickle.dump(stats, f)
    print(f"\n✓ Model saved to {model_path}")

    # Save metadata
    metadata = {
        "model_id": "anomaly_glassbox",
        "model_version": model_version,
        "model_type": "RobustStatisticsAnomalyDetector",
        "training_date": datetime.now(timezone.utc).isoformat(),
        "training_samples": len(rows),
        "n_features": len(stats),
        "feature_stats_summary": {name: {"median": s["median"], "mad": s["mad"]} for name, s in list(stats.items())[:10]},
        "hyperparameters": {
            "random_seed": random_seed,
        },
    }

    metadata_path = output_dir / f"anomaly_glassbox_v{model_version}_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata saved to {metadata_path}")

    return {
        "stats": stats,
        "model_path": str(model_path),
        "metadata": metadata,
    }


def evaluate_model(model_path: str, rows: Sequence[ShipmentTrainingRow]) -> Dict[str, Any]:
    """
    Evaluate a trained GlassBox model on new data.

    Args:
        model_path: Path to trained model
        rows: Evaluation data

    Returns:
        Evaluation metrics
    """
    import pickle

    import numpy as np
    from sklearn.metrics import precision_score, recall_score, roc_auc_score

    print(f"\nEvaluating model: {model_path}")

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    X, y = build_risk_feature_matrix(rows)
    X_np = np.array(X, dtype=float)
    y_np = np.array(y, dtype=int)

    y_pred = model.predict(X_np)
    y_proba = model.predict_proba(X_np)[:, 1]

    metrics = {
        "auc": float(roc_auc_score(y_np, y_proba)),
        "precision": float(precision_score(y_np, y_pred, zero_division=0)),
        "recall": float(recall_score(y_np, y_pred, zero_division=0)),
    }

    print(f"\nEvaluation results ({len(X_np)} samples):")
    print(f"  AUC:       {metrics['auc']:.3f}")
    print(f"  Precision: {metrics['precision']:.3f}")
    print(f"  Recall:    {metrics['recall']:.3f}")

    return metrics


# CLI entrypoint
if __name__ == "__main__":
    import sys

    def print_usage():
        print("GlassBox ML Training Pipeline")
        print("=" * 60)
        print("\nUsage:")
        print("  python -m app.ml.glassbox_training <command> [options]")
        print("\nCommands:")
        print("  train-risk    --seed N --output DIR --samples N")
        print("  train-anomaly --seed N --output DIR --samples N")
        print("  train-all     --seed N --output DIR --samples N")
        print("  evaluate      --model PATH --samples N")
        print("\nExamples:")
        print("  python -m app.ml.glassbox_training train-risk --seed 42")
        print("  python -m app.ml.glassbox_training train-all --samples 5000")

    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    command = sys.argv[1]

    # Parse args
    args = {}
    i = 2
    while i < len(sys.argv):
        if sys.argv[i].startswith("--"):
            key = sys.argv[i][2:]
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                args[key] = sys.argv[i + 1]
                i += 2
            else:
                args[key] = True
                i += 1
        else:
            i += 1

    seed = int(args.get("seed", 42))
    output = args.get("output", "ml_models")
    n_samples = int(args.get("samples", 3000))

    if command == "train-risk":
        print(f"Generating {n_samples} synthetic samples...")
        rows = generate_synthetic_training_data(n_samples=n_samples, positive_rate=0.15, seed=seed)
        train_glassbox_risk_model(rows, output_dir=output, random_seed=seed)

    elif command == "train-anomaly":
        print(f"Generating {n_samples} synthetic samples...")
        rows = generate_synthetic_training_data(n_samples=n_samples, positive_rate=0.15, seed=seed)
        train_glassbox_anomaly_model(rows, output_dir=output, random_seed=seed)

    elif command == "train-all":
        print(f"Generating {n_samples} synthetic samples...")
        rows = generate_synthetic_training_data(n_samples=n_samples, positive_rate=0.15, seed=seed)
        train_glassbox_risk_model(rows, output_dir=output, random_seed=seed)
        train_glassbox_anomaly_model(rows, output_dir=output, random_seed=seed)

    elif command == "evaluate":
        model_path = args.get("model")
        if not model_path:
            print("Error: --model PATH required")
            sys.exit(1)
        rows = generate_synthetic_training_data(n_samples=n_samples, positive_rate=0.15, seed=seed + 1)
        evaluate_model(model_path, rows)

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)
