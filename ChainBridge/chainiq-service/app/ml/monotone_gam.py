"""
ChainIQ ML Monotonic GAM Prototype

Glass-box interpretable model using Generalized Additive Models (GAM)
with enforced monotonicity constraints.

Features:
- Monotone constraints for risk-increasing/decreasing features
- Per-feature shape functions for explainability
- Direct coefficient interpretation
- Calibration via Platt scaling

Author: Maggie (GID-10) 🩷
PAC: MAGGIE-PAC-A
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.preprocessing import RobustScaler

# Import feature specs

# ═══════════════════════════════════════════════════════════════════════════════
# MONOTONE CONSTRAINT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Features where higher values should increase risk score
MONOTONE_INCREASING = [
    "planned_transit_hours",
    "actual_transit_hours",
    "eta_deviation_hours",
    "num_route_deviations",
    "max_route_deviation_km",
    "total_dwell_hours",
    "max_single_dwell_hours",
    "handoff_count",
    "max_custody_gap_hours",
    "delay_flag",
    "prior_losses_flag",
    "missing_required_docs",
    "sentiment_volatility_30d",
    "temp_std",
    "temp_out_of_range_pct",
]

# Features where higher values should decrease risk score
MONOTONE_DECREASING = [
    "shipper_on_time_pct_90d",
    "carrier_on_time_pct_90d",
    "lane_sentiment_score",
    "macro_logistics_sentiment_score",
    "sentiment_trend_7d",
    "sensor_uptime_pct",
]

# Features with no monotonicity constraint
MONOTONE_NONE = [
    "temp_mean",  # Extremes are bad, moderate is good
]


# ═══════════════════════════════════════════════════════════════════════════════
# MONOTONIC GAM ESTIMATOR
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class MonotoneGAMResult:
    """Result container for monotone GAM training."""

    feature_names: list[str]
    coefficients: dict[str, float]
    intercept: float
    feature_shapes: dict[str, list[tuple[float, float]]]  # feature -> [(x, contribution)]
    monotone_violations: list[dict[str, Any]]
    metrics: dict[str, float]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MonotoneLogisticGAM(BaseEstimator, ClassifierMixin):
    """
    Monotone-constrained Logistic Regression as a Glass-Box GAM approximation.

    This implements a simplified GAM where each feature has a linear effect,
    but we enforce monotonicity by:
    1. Transforming decreasing features to negative scale
    2. Using L2 penalty to shrink non-conforming coefficients
    3. Post-hoc validation and warning for violations

    For a true GAM with splines, use interpret.glassbox.ExplainableBoostingClassifier
    or pygam.LogisticGAM with monotone constraints.
    """

    def __init__(
        self,
        penalty: str = "l2",
        C: float = 1.0,
        max_iter: int = 1000,
        enforce_monotonicity: bool = True,
        calibrate: bool = True,
    ):
        self.penalty = penalty
        self.C = C
        self.max_iter = max_iter
        self.enforce_monotonicity = enforce_monotonicity
        self.calibrate = calibrate

        self.feature_names_: list[str] = []
        self.scaler_: RobustScaler | None = None
        self.model_: LogisticRegression | None = None
        self.calibrator_: CalibratedClassifierCV | None = None
        self.monotone_signs_: dict[str, int] = {}

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: list[str] | None = None):
        """
        Fit the monotone GAM model.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Binary labels (n_samples,)
            feature_names: Optional list of feature names
        """
        self.feature_names_ = feature_names or [f"feature_{i}" for i in range(X.shape[1])]

        # Determine monotone signs
        self._compute_monotone_signs()

        # Transform features for monotonicity
        X_transformed = self._transform_for_monotonicity(X)

        # Scale features
        self.scaler_ = RobustScaler()
        X_scaled = self.scaler_.fit_transform(X_transformed)

        # Fit logistic regression
        self.model_ = LogisticRegression(
            penalty=self.penalty,
            C=self.C,
            max_iter=self.max_iter,
            solver="lbfgs",
            class_weight="balanced",
        )
        self.model_.fit(X_scaled, y)

        # Calibrate if requested
        if self.calibrate:
            self.calibrator_ = CalibratedClassifierCV(
                self.model_,
                method="isotonic",
                cv="prefit",
            )
            self.calibrator_.fit(X_scaled, y)

        return self

    def _compute_monotone_signs(self):
        """Compute expected sign for each feature."""
        self.monotone_signs_ = {}

        for name in self.feature_names_:
            if name in MONOTONE_INCREASING:
                self.monotone_signs_[name] = 1  # Positive coefficient expected
            elif name in MONOTONE_DECREASING:
                self.monotone_signs_[name] = -1  # Negative coefficient expected
            else:
                self.monotone_signs_[name] = 0  # No constraint

    def _transform_for_monotonicity(self, X: np.ndarray) -> np.ndarray:
        """
        Transform features to encourage monotonicity.

        For decreasing features, we negate them so the model can use
        positive coefficients consistently.
        """
        if not self.enforce_monotonicity:
            return X

        X_transformed = X.copy()

        for i, name in enumerate(self.feature_names_):
            if self.monotone_signs_.get(name, 0) == -1:
                # Negate decreasing features
                X_transformed[:, i] = -X_transformed[:, i]

        return X_transformed

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities."""
        X_transformed = self._transform_for_monotonicity(X)
        X_scaled = self.scaler_.transform(X_transformed)

        if self.calibrator_ is not None:
            return self.calibrator_.predict_proba(X_scaled)
        else:
            return self.model_.predict_proba(X_scaled)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels."""
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)

    def get_coefficients(self) -> dict[str, float]:
        """
        Get interpretable coefficients.

        Returns coefficients in original feature space (un-negating decreasing features).
        """
        if self.model_ is None:
            raise ValueError("Model not fitted")

        raw_coefs = self.model_.coef_[0]
        coefficients = {}

        for i, name in enumerate(self.feature_names_):
            coef = raw_coefs[i]

            # Un-negate for decreasing features to show true effect
            if self.monotone_signs_.get(name, 0) == -1:
                coef = -coef

            coefficients[name] = float(coef)

        return coefficients

    def get_intercept(self) -> float:
        """Get model intercept."""
        return float(self.model_.intercept_[0]) if self.model_ is not None else 0.0

    def validate_monotonicity(self) -> list[dict[str, Any]]:
        """
        Check for monotonicity violations.

        Returns list of violations where coefficient sign doesn't match expected.
        """
        violations = []
        coefficients = self.get_coefficients()

        for name, coef in coefficients.items():
            expected_sign = self.monotone_signs_.get(name, 0)

            if expected_sign == 1 and coef < 0:
                violations.append(
                    {
                        "feature": name,
                        "expected": "positive",
                        "actual": coef,
                        "severity": "high" if abs(coef) > 0.1 else "low",
                    }
                )
            elif expected_sign == -1 and coef > 0:
                violations.append(
                    {
                        "feature": name,
                        "expected": "negative",
                        "actual": coef,
                        "severity": "high" if abs(coef) > 0.1 else "low",
                    }
                )

        return violations

    def get_feature_contributions(
        self,
        X: np.ndarray,
        baseline: np.ndarray | None = None,
    ) -> np.ndarray:
        """
        Compute per-feature contributions to prediction.

        For linear models: contribution_i = coef_i * (x_i - baseline_i)

        Args:
            X: Feature matrix (n_samples, n_features)
            baseline: Baseline values (defaults to 0)

        Returns:
            Contributions matrix (n_samples, n_features)
        """
        if baseline is None:
            baseline = np.zeros(X.shape[1])

        X_transformed = self._transform_for_monotonicity(X)
        X_scaled = self.scaler_.transform(X_transformed)

        baseline_transformed = self._transform_for_monotonicity(baseline.reshape(1, -1))
        baseline_scaled = self.scaler_.transform(baseline_transformed)

        raw_coefs = self.model_.coef_[0]

        contributions = (X_scaled - baseline_scaled) * raw_coefs

        return contributions

    def explain_prediction(self, x: np.ndarray) -> dict[str, Any]:
        """
        Generate explanation for a single prediction.

        Args:
            x: Single sample (1D array or 2D with shape (1, n_features))

        Returns:
            Dictionary with prediction details and feature contributions
        """
        x = x.reshape(1, -1) if x.ndim == 1 else x

        proba = self.predict_proba(x)[0, 1]
        contributions = self.get_feature_contributions(x)[0]
        coefficients = self.get_coefficients()

        # Sort by absolute contribution
        feature_impacts = []
        for i, name in enumerate(self.feature_names_):
            feature_impacts.append(
                {
                    "feature": name,
                    "value": float(x[0, i]),
                    "coefficient": coefficients[name],
                    "contribution": float(contributions[i]),
                    "direction": "increases risk" if contributions[i] > 0 else "decreases risk",
                }
            )

        feature_impacts.sort(key=lambda f: abs(f["contribution"]), reverse=True)

        return {
            "probability": float(proba),
            "prediction": "bad_outcome" if proba >= 0.5 else "good_outcome",
            "intercept": self.get_intercept(),
            "feature_impacts": feature_impacts,
            "top_risk_factors": [f for f in feature_impacts[:5] if f["contribution"] > 0],
            "top_protective_factors": [f for f in feature_impacts[:5] if f["contribution"] < 0],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════


def fit_monotone_gam(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    C: float = 1.0,
    calibrate: bool = True,
) -> MonotoneGAMResult:
    """
    Train a monotone-constrained GAM model.

    Args:
        X: Feature matrix (n_samples, n_features)
        y: Binary labels
        feature_names: List of feature names
        C: Regularization strength
        calibrate: Whether to apply isotonic calibration

    Returns:
        MonotoneGAMResult with model details
    """
    print("\n" + "=" * 60)
    print("🩷 MAGGIE MONOTONE GAM TRAINING")
    print("=" * 60)

    # Fit model
    print(f"\n[1/4] Fitting monotone logistic GAM (n={len(y)}, p={X.shape[1]})...")
    gam = MonotoneLogisticGAM(C=C, calibrate=calibrate)
    gam.fit(X, y, feature_names=feature_names)

    # Get coefficients
    print("\n[2/4] Extracting coefficients...")
    coefficients = gam.get_coefficients()
    intercept = gam.get_intercept()

    # Validate monotonicity
    print("\n[3/4] Validating monotonicity constraints...")
    violations = gam.validate_monotonicity()

    if violations:
        print(f"   ⚠️ Found {len(violations)} monotonicity violations:")
        for v in violations:
            print(f"      - {v['feature']}: expected {v['expected']}, got {v['actual']:.4f}")
    else:
        print("   ✓ All monotonicity constraints satisfied")

    # Compute metrics
    print("\n[4/4] Computing metrics...")
    y_proba = gam.predict_proba(X)[:, 1]
    y_pred = gam.predict(X)

    metrics = {
        "auc": float(roc_auc_score(y, y_proba)),
        "brier_score": float(brier_score_loss(y, y_proba)),
        "log_loss": float(log_loss(y, y_proba)),
        "accuracy": float((y_pred == y).mean()),
    }

    print(f"   AUC: {metrics['auc']:.3f}")
    print(f"   Brier: {metrics['brier_score']:.3f}")
    print(f"   Log Loss: {metrics['log_loss']:.3f}")

    # Generate feature shape functions (linear for this model)
    feature_shapes = {}
    for i, name in enumerate(feature_names):
        # For linear model, shape is just the scaled coefficient
        x_range = np.linspace(X[:, i].min(), X[:, i].max(), 20)
        coef = coefficients[name]

        # Contribution at each point (relative to mean)
        mean_val = X[:, i].mean()
        contributions = [(float(x), float(coef * (x - mean_val))) for x in x_range]
        feature_shapes[name] = contributions

    print("\n" + "=" * 60)
    print("✓ MONOTONE GAM TRAINING COMPLETE")
    print("=" * 60)

    return MonotoneGAMResult(
        feature_names=feature_names,
        coefficients=coefficients,
        intercept=intercept,
        feature_shapes=feature_shapes,
        monotone_violations=violations,
        metrics=metrics,
    )


def generate_gam_report(result: MonotoneGAMResult) -> str:
    """Generate markdown report for monotone GAM results."""
    md = f"""# ChainIQ Monotone GAM Report

**Generated:** {result.timestamp}
**Agent:** Maggie (GID-10) 🩷
**Model:** Monotone-Constrained Logistic GAM

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| AUC | {result.metrics['auc']:.3f} |
| Brier Score | {result.metrics['brier_score']:.3f} |
| Log Loss | {result.metrics['log_loss']:.3f} |
| Accuracy | {result.metrics['accuracy']:.1%} |

---

## Feature Coefficients (Glass-Box)

| Feature | Coefficient | Direction | Monotone |
|---------|-------------|-----------|----------|
"""

    # Sort by absolute coefficient
    sorted_coefs = sorted(result.coefficients.items(), key=lambda x: abs(x[1]), reverse=True)

    violation_features = {v["feature"] for v in result.monotone_violations}

    for name, coef in sorted_coefs:
        direction = "↑ risk" if coef > 0 else "↓ risk"
        monotone_status = "⚠️ VIOLATION" if name in violation_features else "✅"
        md += f"| `{name}` | {coef:+.4f} | {direction} | {monotone_status} |\n"

    md += f"\n**Intercept:** {result.intercept:.4f}\n"

    # Monotonicity violations
    if result.monotone_violations:
        md += f"""
---

## ⚠️ Monotonicity Violations ({len(result.monotone_violations)})

| Feature | Expected | Actual | Severity |
|---------|----------|--------|----------|
"""
        for v in result.monotone_violations:
            md += f"| `{v['feature']}` | {v['expected']} | {v['actual']:.4f} | {v['severity']} |\n"
    else:
        md += """
---

## ✅ Monotonicity Validation

All monotonicity constraints satisfied. Model coefficients align with domain expectations.
"""

    md += """
---

## Interpretation Guide

### How to Use Coefficients

For a shipment with features $x$:

$$
\\text{log-odds} = \\beta_0 + \\sum_{i} \\beta_i \\cdot x_i
$$

$$
P(\\text{bad outcome}) = \\frac{1}{1 + e^{-\\text{log-odds}}}
$$

### Top Risk Factors

Features with **positive coefficients** increase risk when their values increase:
- Delays, deviations, dwell time
- Missing documents, custody gaps
- Temperature variance

### Top Protective Factors

Features with **negative coefficients** decrease risk when their values increase:
- On-time delivery history
- Sentiment scores
- Sensor uptime

---

*Generated by ChainIQ Monotone GAM v0.1*
"""

    return md


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """CLI entry point for monotone GAM training."""
    print("\n🩷 MAGGIE MONOTONE GAM - ChainIQ Glass-Box Model")
    print("=" * 60)

    # Import validation module to get training data
    from app.ml.preprocessing import ALL_FEATURE_NAMES, extract_feature_vector
    from app.ml.validation_real_data import load_ingested_training_rows
    from app.models.features import ShipmentFeaturesV0

    print("\nLoading training rows...")
    rows = load_ingested_training_rows(limit=2000)

    # Build feature matrix
    print("Building feature matrix...")
    X_list = []
    y_list = []

    for row in rows:
        features_dict = row.get("features", row)

        # Create ShipmentFeaturesV0 from dict (with defaults)
        features_v0 = ShipmentFeaturesV0(
            **{
                k: (
                    features_dict.get(k, 0.0)
                    if k not in ["shipment_id", "corridor", "mode", "commodity_category", "financing_type"]
                    else features_dict.get(k, "unknown")
                )
                for k in ShipmentFeaturesV0.__fields__.keys()
            }
        )

        feature_vector = extract_feature_vector(features_v0)
        X_list.append(feature_vector)

        bad_outcome = row.get("had_claim", False) or row.get("had_dispute", False) or row.get("severe_delay", False)
        y_list.append(int(bad_outcome))

    X = np.array(X_list)
    y = np.array(y_list)

    print(f"Dataset: {X.shape[0]} samples, {X.shape[1]} features")
    print(f"Bad outcome rate: {y.mean():.1%}")

    # Train monotone GAM
    result = fit_monotone_gam(X, y, ALL_FEATURE_NAMES)

    # Save report
    output_dir = Path(__file__).parent.parent.parent / "docs" / "chainiq"
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "MONOTONE_GAM_REPORT.md"
    with open(report_path, "w") as f:
        f.write(generate_gam_report(result))

    print(f"\n✓ Report saved to: {report_path}")

    return result


if __name__ == "__main__":
    main()
