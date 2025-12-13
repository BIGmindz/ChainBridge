"""
ChainIQ ML Preprocessing & Feature Engineering

Pure-Python feature engineering utilities for training ML models.
Provides sklearn-compatible interfaces WITHOUT requiring sklearn at module import time.

Key Functions:
- extract_feature_vector: Convert ShipmentFeaturesV0 → numeric array
- build_risk_feature_matrix: Batch extract features + labels for risk model training
- build_anomaly_feature_matrix: Batch extract features for anomaly model training

Safety: sklearn imports are GUARDED (only imported inside functions when needed).
This keeps FastAPI startup fast even if sklearn isn't installed.
"""

from __future__ import annotations

from typing import Any, Sequence

from app.ml.datasets import ShipmentTrainingRow
from app.models.features import ShipmentFeaturesV0

# Feature group definitions (for documentation and feature selection)
CORE_NUMERIC_FEATURES = [
    "planned_transit_hours",
    "actual_transit_hours",
    "eta_deviation_hours",
    "num_route_deviations",
    "max_route_deviation_km",
    "total_dwell_hours",
    "max_single_dwell_hours",
    "handoff_count",
    "max_custody_gap_hours",
]

MONOTONE_FEATURES = [
    # These must increase risk (or decrease if negative sign)
    "delay_flag",  # +risk
    "prior_losses_flag",  # +risk
    "missing_required_docs",  # +risk
    "shipper_on_time_pct_90d",  # -risk (inverse)
    "carrier_on_time_pct_90d",  # -risk (inverse)
]

SENTIMENT_FEATURES = [
    "lane_sentiment_score",
    "macro_logistics_sentiment_score",
    "sentiment_trend_7d",
    "sentiment_volatility_30d",
]

IOT_FEATURES = [
    "temp_mean",
    "temp_std",
    "temp_out_of_range_pct",
    "sensor_uptime_pct",
]

CATEGORICAL_FEATURES = [
    "mode",
    "commodity_category",
    "financing_type",
    "counterparty_risk_bucket",
    "collateral_value_bucket",
]

# Combined feature list (ordered for consistency)
ALL_FEATURE_NAMES = (
    CORE_NUMERIC_FEATURES
    + MONOTONE_FEATURES
    + SENTIMENT_FEATURES
    + IOT_FEATURES
    # Categorical features handled separately (need encoding)
)


def extract_feature_vector(
    features: ShipmentFeaturesV0,
    *,
    include_categorical: bool = False,
) -> list[float]:
    """
    Extract a numeric feature vector from ShipmentFeaturesV0.

    Converts Pydantic model → list of floats for ML model input.

    Args:
        features: ShipmentFeaturesV0 instance
        include_categorical: If True, include one-hot encoded categoricals

    Returns:
        List of floats (length = len(ALL_FEATURE_NAMES) + categorical dims)

    Example:
        >>> vector = extract_feature_vector(some_features)
        >>> print(f"Feature vector length: {len(vector)}")
    """
    vector = []

    # Extract numeric features in order
    for feat_name in ALL_FEATURE_NAMES:
        value = getattr(features, feat_name, 0.0)
        vector.append(float(value))

    # TODO: Add categorical encoding if include_categorical=True
    # For v0.2, we'll skip categoricals (risk/anomaly models can work without them)

    return vector


def build_risk_feature_matrix(
    rows: Sequence[ShipmentTrainingRow],
) -> tuple[list[list[float]], list[int]]:
    """
    Build (X, y) matrices for risk model training.

    Args:
        rows: Sequence of ShipmentTrainingRow instances

    Returns:
        Tuple of (X, y) where:
        - X: list of feature vectors (each row is a list of floats)
        - y: list of binary labels (1 = bad_outcome, 0 = clean)

    Example:
        >>> X, y = build_risk_feature_matrix(training_rows)
        >>> print(f"X shape: {len(X)} x {len(X[0])}")
        >>> print(f"y shape: {len(y)}, positive rate: {sum(y)/len(y):.2%}")
    """
    X = []
    y = []

    for row in rows:
        feature_vector = extract_feature_vector(row.features)
        label = 1 if row.bad_outcome else 0

        X.append(feature_vector)
        y.append(label)

    return X, y


def build_anomaly_feature_matrix(
    rows: Sequence[ShipmentTrainingRow],
) -> list[list[float]]:
    """
    Build feature matrix for anomaly model training (unsupervised).

    For unsupervised anomaly detection, we only need X (no labels).

    Args:
        rows: Sequence of ShipmentTrainingRow instances

    Returns:
        X: list of feature vectors (each row is a list of floats)

    Example:
        >>> X = build_anomaly_feature_matrix(training_rows)
        >>> print(f"X shape: {len(X)} x {len(X[0])}")
    """
    X = []

    for row in rows:
        feature_vector = extract_feature_vector(row.features)
        X.append(feature_vector)

    return X


def create_sklearn_preprocessor(
    *,
    use_robust_scaling: bool = True,
) -> Any:
    """
    Create sklearn ColumnTransformer for feature preprocessing.

    IMPORTANT: This function imports sklearn. Only call during training,
    NOT during FastAPI app startup or request handling.

    Args:
        use_robust_scaling: If True, use RobustScaler (resistant to outliers).
                           If False, use StandardScaler (faster but sensitive).

    Returns:
        sklearn ColumnTransformer (or similar pipeline)

    Raises:
        ImportError: If sklearn is not installed

    Example:
        >>> preprocessor = create_sklearn_preprocessor()
        >>> X_transformed = preprocessor.fit_transform(X_train)

    TODO (PAC-004): Implement full sklearn pipeline with:
        - Numeric scaling (RobustScaler or StandardScaler)
        - Monotone feature pass-through (no scaling for delay_flag, etc.)
        - Categorical encoding (target encoding or one-hot)
        - Missing value imputation (if needed)
    """
    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.preprocessing import RobustScaler, StandardScaler
    except ImportError as e:
        raise ImportError("sklearn not installed. Install with: pip install scikit-learn>=1.3") from e

    # Determine which features to scale
    numeric_indices = list(range(len(CORE_NUMERIC_FEATURES)))
    monotone_indices = list(
        range(
            len(CORE_NUMERIC_FEATURES),
            len(CORE_NUMERIC_FEATURES) + len(MONOTONE_FEATURES),
        )
    )
    sentiment_indices = list(
        range(
            len(CORE_NUMERIC_FEATURES) + len(MONOTONE_FEATURES),
            len(CORE_NUMERIC_FEATURES) + len(MONOTONE_FEATURES) + len(SENTIMENT_FEATURES),
        )
    )

    # Build sklearn pipeline
    scaler = RobustScaler() if use_robust_scaling else StandardScaler()

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", scaler, numeric_indices + sentiment_indices),
            ("monotone", "passthrough", monotone_indices),  # Don't scale flags
        ],
        remainder="drop",  # Drop any extra features
    )

    return preprocessor


def get_feature_names() -> list[str]:
    """
    Get ordered list of feature names (for model explainability).

    Returns:
        List of feature names in the same order as extract_feature_vector()

    Example:
        >>> names = get_feature_names()
        >>> print(f"Using {len(names)} features: {names[:5]}...")
    """
    return ALL_FEATURE_NAMES.copy()


def compute_feature_stats(rows: Sequence[ShipmentTrainingRow]) -> dict[str, dict]:
    """
    Compute basic statistics for each feature (for validation and monitoring).

    Args:
        rows: Training data

    Returns:
        Dictionary mapping feature_name → {mean, std, min, max, missing_count}

    Example:
        >>> stats = compute_feature_stats(training_rows)
        >>> print(f"delay_flag mean: {stats['delay_flag']['mean']:.2%}")
    """
    feature_names = get_feature_names()
    X, _ = build_risk_feature_matrix(rows)

    stats = {}
    for i, name in enumerate(feature_names):
        values = [row[i] for row in X]

        stats[name] = {
            "mean": sum(values) / len(values),
            "std": (sum((x - sum(values) / len(values)) ** 2 for x in values) / len(values)) ** 0.5,
            "min": min(values),
            "max": max(values),
            "missing_count": sum(1 for v in values if v == 0.0),  # Simple heuristic
        }

    return stats


# Example usage for testing
if __name__ == "__main__":
    from app.ml.datasets import generate_synthetic_training_data

    print("Generating synthetic data...")
    rows = generate_synthetic_training_data(n_samples=100, seed=42)

    print("\nExtracting features...")
    X, y = build_risk_feature_matrix(rows)

    print(f"X shape: {len(X)} rows x {len(X[0])} features")
    print(f"y shape: {len(y)} labels")
    print(f"Positive rate: {sum(y)/len(y):.2%}")

    print("\nFeature names:")
    for i, name in enumerate(get_feature_names()[:10]):
        print(f"  {i}: {name}")

    print("\nFeature statistics (first 5):")
    stats = compute_feature_stats(rows)
    for name in list(stats.keys())[:5]:
        s = stats[name]
        print(f"  {name}: mean={s['mean']:.2f}, std={s['std']:.2f}, min={s['min']:.2f}, max={s['max']:.2f}")

    print("\nTrying to create sklearn preprocessor...")
    try:
        preprocessor = create_sklearn_preprocessor()
        print(f"✓ Preprocessor created: {type(preprocessor)}")
    except ImportError as e:
        print(f"✗ sklearn not installed: {e}")
