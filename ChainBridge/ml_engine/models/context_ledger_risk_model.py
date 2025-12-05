"""Lightweight logistic model for context ledger risk scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, MutableMapping, TypedDict

import numpy as np
import pandas as pd

from ..feature_store.context_ledger_features import DEFAULT_FEATURE_COLUMNS, TARGET_COLUMN


class ContextLedgerRiskOutput(TypedDict):
    risk_probability: float
    risk_bucket: str
    confidence: float
    top_signals: List[str]


@dataclass
class _Scaler:
    mean: np.ndarray
    std: np.ndarray

    def transform(self, values: np.ndarray) -> np.ndarray:
        return (values - self.mean) / np.where(self.std == 0, 1.0, self.std)


class ContextLedgerRiskModel:
    """Minimal logistic regression trained with gradient descent."""

    def __init__(
        self,
        *,
        feature_columns: Iterable[str] | None = None,
        learning_rate: float = 0.1,
        epochs: int = 300,
    ) -> None:
        self.feature_columns = list(feature_columns or DEFAULT_FEATURE_COLUMNS)
        self.learning_rate = learning_rate
        self.epochs = epochs
        self._scaler: _Scaler | None = None
        self._weights: np.ndarray | None = None
        self._bias: float = 0.0

    def train(self, dataset: pd.DataFrame) -> None:
        if dataset.empty:
            raise ValueError("ContextLedgerRiskModel requires non-empty training data")
        missing = [c for c in self.feature_columns if c not in dataset]
        if missing:
            raise ValueError(f"Missing feature columns: {missing}")
        if TARGET_COLUMN not in dataset:
            raise ValueError(f"Training data missing target column '{TARGET_COLUMN}'")

        X = dataset[self.feature_columns].astype(float).to_numpy()
        y = dataset[TARGET_COLUMN].astype(float).to_numpy()

        mean = X.mean(axis=0)
        std = X.std(axis=0)
        std[std == 0] = 1.0
        self._scaler = _Scaler(mean=mean, std=std)
        X_norm = self._scaler.transform(X)

        self._weights = np.zeros(X_norm.shape[1])
        self._bias = 0.0

        for _ in range(self.epochs):
            logits = X_norm @ self._weights + self._bias
            preds = 1.0 / (1.0 + np.exp(-logits))
            error = preds - y
            grad_w = X_norm.T @ error / len(X_norm)
            grad_b = float(error.mean())
            self._weights -= self.learning_rate * grad_w
            self._bias -= self.learning_rate * grad_b

    def predict(self, features: Mapping[str, float] | pd.Series | pd.DataFrame) -> ContextLedgerRiskOutput:
        if self._weights is None or self._scaler is None:
            raise RuntimeError("Model must be trained before calling predict()")

        vector = self._extract_feature_vector(features)
        norm_vector = self._scaler.transform(vector)
        logit = float(norm_vector @ self._weights + self._bias)
        prob = float(1.0 / (1.0 + np.exp(-logit)))
        bucket = self._bucketize(prob)
        confidence = 1.0 - abs(0.5 - prob) * 2
        top_signals = self._top_features(vector)

        return ContextLedgerRiskOutput(
            risk_probability=prob,
            risk_bucket=bucket,
            confidence=max(0.0, min(1.0, confidence)),
            top_signals=top_signals,
        )

    def _extract_feature_vector(self, features: Mapping[str, float] | pd.Series | pd.DataFrame) -> np.ndarray:
        if isinstance(features, pd.DataFrame):
            if len(features) != 1:
                raise ValueError("Predict expects a single row when passing a DataFrame")
            row = features.iloc[0]
        elif isinstance(features, pd.Series):
            row = features
        else:
            row = pd.Series(features)

        usable = []
        for column in self.feature_columns:
            if column in row:
                usable.append(row[column])
            else:
                usable.append(0.0)
        return np.array(usable, dtype=float)

    def _bucketize(self, probability: float) -> str:
        # Core banding is calibrated for PINK-01 v1.1 and
        # expressed in terms of the underlying model probability.
        # The final CRITICAL promotion rule is applied in the
        # ChainPay wrapper to keep this model reusable.
        if probability >= 0.65:
            return "HIGH"
        if probability >= 0.35:
            return "MEDIUM"
        return "LOW"

    def _top_features(self, vector: np.ndarray) -> List[str]:
        assert self._weights is not None
        contributions = np.abs(self._weights * vector)
        ranking = np.argsort(-contributions)
        top_indices = ranking[:3]
        return [self.feature_columns[i] for i in top_indices]


__all__ = [
    "ContextLedgerRiskModel",
    "ContextLedgerRiskOutput",
]
