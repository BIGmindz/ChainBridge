"""
ChainIQ v0.1 - Models

Baseline risk prediction models with glass-box explainability.

Author: Maggie (GID-10) - ML & Applied AI Lead
"""

import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

import numpy as np

# Conditional imports for ML libraries
try:
    import xgboost as xgb

    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    xgb = None

try:
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from .features import MODEL_FEATURE_NAMES

# =============================================================================
# CONFIGURATION
# =============================================================================


@dataclass
class ModelConfig:
    """Configuration for ChainIQ risk models."""

    # XGBoost parameters (primary model)
    xgb_n_estimators: int = 200
    xgb_max_depth: int = 6
    xgb_learning_rate: float = 0.05
    xgb_min_child_weight: int = 10
    xgb_subsample: float = 0.8
    xgb_colsample_bytree: float = 0.8
    xgb_reg_alpha: float = 0.1
    xgb_reg_lambda: float = 1.0

    # Logistic regression parameters (interpretable fallback)
    lr_penalty: str = "l2"
    lr_C: float = 1.0
    lr_max_iter: int = 1000

    # Calibration
    calibration_method: str = "isotonic"
    calibration_cv: int = 5

    # Feature names
    feature_names: list = field(default_factory=lambda: MODEL_FEATURE_NAMES.copy())

    # Random state for reproducibility
    random_state: int = 42


# =============================================================================
# BASE MODEL INTERFACE
# =============================================================================


class BaseRiskModel:
    """Abstract base class for ChainIQ risk models."""

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()
        self.model = None
        self.scaler = None
        self.is_fitted = False
        self.version = "chainiq-v0.1"

    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaseRiskModel":
        """Train the model on labeled data."""
        raise NotImplementedError

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probability of bad outcome."""
        raise NotImplementedError

    def get_feature_importance(self) -> dict[str, float]:
        """Get feature importance scores."""
        raise NotImplementedError

    def save(self, path: Path) -> None:
        """Save model to disk."""
        raise NotImplementedError

    @classmethod
    def load(cls, path: Path) -> "BaseRiskModel":
        """Load model from disk."""
        raise NotImplementedError


# =============================================================================
# XGBOOST MODEL (PRIMARY)
# =============================================================================


class XGBoostRiskModel(BaseRiskModel):
    """
    Gradient Boosted Tree model for risk prediction.

    Primary model for ChainIQ v0.1 - good balance of performance and
    explainability via SHAP values.
    """

    def __init__(self, config: Optional[ModelConfig] = None):
        super().__init__(config)
        if not HAS_XGBOOST:
            raise ImportError("xgboost is required for XGBoostRiskModel")

    def fit(self, X: np.ndarray, y: np.ndarray) -> "XGBoostRiskModel":
        """Train XGBoost classifier."""
        self.model = xgb.XGBClassifier(
            n_estimators=self.config.xgb_n_estimators,
            max_depth=self.config.xgb_max_depth,
            learning_rate=self.config.xgb_learning_rate,
            min_child_weight=self.config.xgb_min_child_weight,
            subsample=self.config.xgb_subsample,
            colsample_bytree=self.config.xgb_colsample_bytree,
            reg_alpha=self.config.xgb_reg_alpha,
            reg_lambda=self.config.xgb_reg_lambda,
            random_state=self.config.random_state,
            use_label_encoder=False,
            eval_metric="logloss",
        )

        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probability of bad outcome (class 1)."""
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        # Ensure 2D
        if X.ndim == 1:
            X = X.reshape(1, -1)

        # Return probability of positive class
        proba = self.model.predict_proba(X)
        return proba[:, 1]

    def get_feature_importance(self) -> dict[str, float]:
        """Get gain-based feature importance."""
        if not self.is_fitted:
            return {}

        importance = self.model.feature_importances_
        return {name: float(imp) for name, imp in zip(self.config.feature_names, importance)}

    def get_shap_values(self, X: np.ndarray) -> np.ndarray:
        """
        Get SHAP values for explainability.

        Returns array of shape (n_samples, n_features) with SHAP contributions.
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted.")

        try:
            import shap

            explainer = shap.TreeExplainer(self.model)
            if X.ndim == 1:
                X = X.reshape(1, -1)
            shap_values = explainer.shap_values(X)
            return shap_values
        except ImportError:
            # Fallback to feature importance-based pseudo-SHAP
            return self._pseudo_shap(X)

    def _pseudo_shap(self, X: np.ndarray) -> np.ndarray:
        """
        Fallback when SHAP library not available.
        Uses feature importance * feature value as approximation.
        """
        importance = self.model.feature_importances_
        if X.ndim == 1:
            X = X.reshape(1, -1)

        # Scale features and multiply by importance
        X_scaled = X / (np.abs(X).max(axis=0, keepdims=True) + 1e-8)
        return X_scaled * importance

    def save(self, path: Path) -> None:
        """Save model to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        save_dict = {
            "model": self.model,
            "config": self.config,
            "version": self.version,
            "is_fitted": self.is_fitted,
        }

        with open(path, "wb") as f:
            pickle.dump(save_dict, f)

    @classmethod
    def load(cls, path: Path) -> "XGBoostRiskModel":
        """Load model from disk."""
        with open(path, "rb") as f:
            save_dict = pickle.load(f)

        instance = cls(config=save_dict["config"])
        instance.model = save_dict["model"]
        instance.version = save_dict["version"]
        instance.is_fitted = save_dict["is_fitted"]
        return instance


# =============================================================================
# LOGISTIC REGRESSION MODEL (INTERPRETABLE FALLBACK)
# =============================================================================


class LogisticRiskModel(BaseRiskModel):
    """
    Logistic Regression model for fully interpretable risk prediction.

    Use when explainability is paramount or for sparse-data tenants.
    """

    def __init__(self, config: Optional[ModelConfig] = None):
        super().__init__(config)
        if not HAS_SKLEARN:
            raise ImportError("scikit-learn is required for LogisticRiskModel")
        self.scaler = StandardScaler()

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogisticRiskModel":
        """Train logistic regression with scaling."""
        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Fit logistic regression
        self.model = LogisticRegression(
            penalty=self.config.lr_penalty,
            C=self.config.lr_C,
            max_iter=self.config.lr_max_iter,
            random_state=self.config.random_state,
        )
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probability of bad outcome."""
        if not self.is_fitted:
            raise RuntimeError("Model not fitted.")

        if X.ndim == 1:
            X = X.reshape(1, -1)

        X_scaled = self.scaler.transform(X)
        proba = self.model.predict_proba(X_scaled)
        return proba[:, 1]

    def get_feature_importance(self) -> dict[str, float]:
        """Get coefficient-based feature importance."""
        if not self.is_fitted:
            return {}

        coef = np.abs(self.model.coef_[0])
        return {name: float(c) for name, c in zip(self.config.feature_names, coef)}

    def get_coefficients(self) -> dict[str, float]:
        """Get raw coefficients for interpretation."""
        if not self.is_fitted:
            return {}

        return {name: float(c) for name, c in zip(self.config.feature_names, self.model.coef_[0])}

    def get_shap_values(self, X: np.ndarray) -> np.ndarray:
        """
        For logistic regression, SHAP values are simply coef * scaled_feature.
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted.")

        if X.ndim == 1:
            X = X.reshape(1, -1)

        X_scaled = self.scaler.transform(X)
        return X_scaled * self.model.coef_[0]

    def save(self, path: Path) -> None:
        """Save model and scaler to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        save_dict = {
            "model": self.model,
            "scaler": self.scaler,
            "config": self.config,
            "version": self.version,
            "is_fitted": self.is_fitted,
        }

        with open(path, "wb") as f:
            pickle.dump(save_dict, f)

    @classmethod
    def load(cls, path: Path) -> "LogisticRiskModel":
        """Load model from disk."""
        with open(path, "rb") as f:
            save_dict = pickle.load(f)

        instance = cls(config=save_dict["config"])
        instance.model = save_dict["model"]
        instance.scaler = save_dict["scaler"]
        instance.version = save_dict["version"]
        instance.is_fitted = save_dict["is_fitted"]
        return instance


# =============================================================================
# HEURISTIC MODEL (NO-ML FALLBACK)
# =============================================================================


class HeuristicRiskModel(BaseRiskModel):
    """
    Rule-based risk model for when ML models are unavailable.

    Uses domain knowledge heuristics. Always available, requires no training.
    """

    def __init__(self, config: Optional[ModelConfig] = None):
        super().__init__(config)
        self.is_fitted = True  # Heuristic always "fitted"
        self.version = "chainiq-v0.1-heuristic"

    def fit(self, X: np.ndarray, y: np.ndarray) -> "HeuristicRiskModel":
        """No-op for heuristic model."""
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Compute risk score using weighted heuristics.
        """
        if X.ndim == 1:
            X = X.reshape(1, -1)

        feature_idx = {name: i for i, name in enumerate(self.config.feature_names)}

        scores = []
        for row in X:
            risk = 0.0

            # Lane risk (30% weight)
            lane_rate = row[feature_idx.get("lane_historical_delay_rate", 0)]
            risk += 0.30 * min(1.0, lane_rate * 5)  # 20% delay rate → 100% contribution

            # Carrier risk (20% weight)
            carrier_rate = row[feature_idx.get("carrier_historical_delay_rate", 0)]
            risk += 0.20 * min(1.0, carrier_rate * 5)

            # Seasonal risk (15% weight)
            is_peak = row[feature_idx.get("is_peak_season", 0)]
            risk += 0.15 * is_peak

            # Event risk (20% weight)
            events_score = 0.0
            if row[feature_idx.get("has_customs_hold", 0)]:
                events_score += 0.4
            if row[feature_idx.get("has_port_congestion", 0)]:
                events_score += 0.3
            if row[feature_idx.get("has_temperature_alarm", 0)]:
                events_score += 0.3
            risk += 0.20 * min(1.0, events_score)

            # Departure delay (10% weight)
            delay_hours = row[feature_idx.get("departure_delay_hours", 0)]
            delay_risk = min(1.0, max(0, delay_hours) / 48)  # 48h delay → 100%
            risk += 0.10 * delay_risk

            # Data quality penalty (5% weight)
            data_quality = row[feature_idx.get("data_completeness_score", 0)]
            risk += 0.05 * (1 - data_quality)

            scores.append(min(1.0, max(0.0, risk)))

        return np.array(scores)

    def get_feature_importance(self) -> dict[str, float]:
        """Return heuristic weights as importance."""
        return {
            "lane_historical_delay_rate": 0.30,
            "carrier_historical_delay_rate": 0.20,
            "is_peak_season": 0.15,
            "has_customs_hold": 0.08,
            "has_port_congestion": 0.06,
            "has_temperature_alarm": 0.06,
            "departure_delay_hours": 0.10,
            "data_completeness_score": 0.05,
        }

    def get_shap_values(self, X: np.ndarray) -> np.ndarray:
        """
        Return weighted contributions as pseudo-SHAP values.
        """
        if X.ndim == 1:
            X = X.reshape(1, -1)

        importance = self.get_feature_importance()
        shap = np.zeros_like(X, dtype=np.float32)

        for i, name in enumerate(self.config.feature_names):
            weight = importance.get(name, 0.0)
            shap[:, i] = X[:, i] * weight

        return shap

    def save(self, path: Path) -> None:
        """Save config to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        save_dict = {
            "config": self.config,
            "version": self.version,
        }

        with open(path, "wb") as f:
            pickle.dump(save_dict, f)

    @classmethod
    def load(cls, path: Path) -> "HeuristicRiskModel":
        """Load from disk."""
        with open(path, "rb") as f:
            save_dict = pickle.load(f)

        instance = cls(config=save_dict["config"])
        instance.version = save_dict["version"]
        return instance


# =============================================================================
# MODEL FACTORY
# =============================================================================


def get_model(
    model_type: Literal["xgboost", "logistic", "heuristic"] = "heuristic",
    config: Optional[ModelConfig] = None,
) -> BaseRiskModel:
    """
    Factory function to get appropriate model.

    Falls back gracefully if ML libraries unavailable.
    """
    if model_type == "xgboost":
        if HAS_XGBOOST:
            return XGBoostRiskModel(config)
        else:
            print("Warning: xgboost not available, falling back to heuristic")
            return HeuristicRiskModel(config)

    elif model_type == "logistic":
        if HAS_SKLEARN:
            return LogisticRiskModel(config)
        else:
            print("Warning: scikit-learn not available, falling back to heuristic")
            return HeuristicRiskModel(config)

    else:
        return HeuristicRiskModel(config)


def load_model(path: Path) -> BaseRiskModel:
    """
    Load a model from disk, auto-detecting type.
    """
    with open(path, "rb") as f:
        save_dict = pickle.load(f)

    version = save_dict.get("version", "")

    if "heuristic" in version:
        return HeuristicRiskModel.load(path)
    elif "model" in save_dict and hasattr(save_dict["model"], "feature_importances_"):
        return XGBoostRiskModel.load(path)
    else:
        return LogisticRiskModel.load(path)
