"""Tests for ContextLedgerRiskModel."""

from __future__ import annotations

import math

import pandas as pd

from ml_engine.feature_store.context_ledger_features import (
    TARGET_COLUMN,
    derive_context_feature_frame,
)
from ml_engine.models.context_ledger_risk_model import ContextLedgerRiskModel


RAW_ROWS = [
    {
        "corridor": "COR-1",
        "amount": 1000.0,
        "risk_score": 85.0,
        "corridor_risk_rating": 0.8,
        "user_velocity_24h": 5,
        "role": "admin",
        "recent_alert_count": 2,
        "reason_codes": ["HIGH_AMOUNT", "MANUAL_OVERRIDE"],
        "policies_applied": ["P-STRICT-KYC", "P-HIGH_VALUE"],
        "token_velocity": 12.0,
        "anomaly_density": 0.9,
        "decision_status": "ESCALATED",
        "label": 1,
    },
    {
        "corridor": "COR-1",
        "amount": 100.0,
        "risk_score": 10.0,
        "corridor_risk_rating": 0.2,
        "user_velocity_24h": 0,
        "role": "standard",
        "recent_alert_count": 0,
        "reason_codes": [],
        "policies_applied": ["P-BASELINE"],
        "token_velocity": 1.0,
        "anomaly_density": 0.1,
        "decision_status": "APPROVED",
        "label": 0,
    },
    {
        "corridor": "COR-2",
        "amount": 200.0,
        "risk_score": 75.0,
        "corridor_risk_rating": 0.4,
        "user_velocity_24h": 8,
        "role": "compliance",
        "recent_alert_count": 5,
        "reason_codes": ["MULTIPLE_ALERTS"],
        "policies_applied": ["P-STRICT-KYC"],
        "token_velocity": 8.0,
        "anomaly_density": 0.7,
        "decision_status": "HOLD",
        "label": 1,
    },
]


def _build_dataset() -> pd.DataFrame:
    df = pd.DataFrame(RAW_ROWS)
    features = derive_context_feature_frame(df)
    features[TARGET_COLUMN] = df["label"]
    return features


def test_model_trains_and_predicts_probabilities() -> None:
    dataset = _build_dataset()
    model = ContextLedgerRiskModel(epochs=200)
    model.train(dataset)

    sample = dataset.iloc[[0]].drop(columns=[TARGET_COLUMN])
    output = model.predict(sample)

    assert 0.0 <= output["risk_probability"] <= 1.0
    assert output["risk_bucket"] in {"LOW", "MEDIUM", "HIGH"}
    assert 0.0 <= output["confidence"] <= 1.0
    assert len(output["top_signals"]) == 3


def test_model_requires_training_before_prediction() -> None:
    model = ContextLedgerRiskModel()
    sample = pd.DataFrame([{col: 0.1 for col in model.feature_columns}])
    try:
        model.predict(sample)
    except RuntimeError:
        return
    raise AssertionError("predict should require prior training")


def test_training_fails_for_missing_features() -> None:
    # Drop a required feature column and confirm the model rejects the dataset.
    # NOTE: the feature name must match DEFAULT_FEATURE_COLUMNS ("amount_log").
    dataset = _build_dataset().drop(columns=["amount_log"])
    model = ContextLedgerRiskModel()
    try:
        model.train(dataset)
    except ValueError as exc:
        assert "Missing feature columns" in str(exc)
        return
    raise AssertionError("Expected ValueError for missing feature columns")
