"""Feature engineering helpers for the context ledger risk model."""

from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd

# Corridors that historically create more investigative churn.
_HIGH_RISK_CORRIDORS = {"LATAM-USD", "AFRICA-USD", "APAC-CRYPTO"}

DEFAULT_FEATURE_COLUMNS: List[str] = [
    "amount_log",
    "risk_score",
    "reason_code_intensity",
    "policy_stack_depth",
    "corridor_risk_factor",
    "velocity_score",
    "anomaly_indicator",
    "role_tier_weight",
]

TARGET_COLUMN = "requires_manual_review"


def _normalize_series(series: pd.Series) -> pd.Series:
    mean = series.mean()
    std = series.std()
    if std == 0 or np.isnan(std):
        std = 1.0
    return (series - mean) / std


def _corridor_factor(corridor: str | float | None) -> float:
    if not corridor or not isinstance(corridor, str):
        return 0.0
    corridor = corridor.upper()
    if corridor in _HIGH_RISK_CORRIDORS:
        return 1.0
    if "STABLE" in corridor:
        return -0.3
    return 0.2


def _ensure_list(value: object) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, (tuple, set)):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def derive_context_feature_frame(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Return a feature matrix the risk model can ingest."""

    df = raw_df.copy()

    df["amount"] = df["amount"].astype(float)
    df["risk_score"] = df["risk_score"].astype(float)

    # role_tier may be missing entirely in synthetic/test data; default to 3
    if "role_tier" not in df:
        df["role_tier"] = 3.0
    else:
        df["role_tier"] = df["role_tier"].fillna(3).astype(float)

    df["amount_log"] = np.log1p(df["amount"].clip(lower=0))
    df["reason_codes"] = df.get("reason_codes", []).apply(_ensure_list)
    df["policies_applied"] = df.get("policies_applied", []).apply(_ensure_list)

    df["reason_code_intensity"] = df["reason_codes"].apply(len).astype(float)
    df["policy_stack_depth"] = df["policies_applied"].apply(len).astype(float)
    df["corridor_risk_factor"] = df.get("corridor", "").apply(_corridor_factor)

    velocity = df.get("token_velocity", 0.0)
    if not isinstance(velocity, pd.Series):
        velocity = pd.Series([velocity] * len(df), index=df.index)
    velocity = velocity.astype(float).fillna(0.0)
    df["velocity_score"] = _normalize_series(velocity)

    anomaly = df.get("anomaly_density", 0.0)
    if not isinstance(anomaly, pd.Series):
        anomaly = pd.Series([anomaly] * len(df), index=df.index)
    anomaly = anomaly.astype(float).fillna(0.0)
    df["anomaly_indicator"] = (anomaly > anomaly.median()).astype(float)

    df["role_tier_weight"] = 1.0 / df["role_tier"].clip(lower=1.0)

    statuses = df.get("decision_status", "").astype(str).str.upper()
    df[TARGET_COLUMN] = ((df["risk_score"] >= 70) | statuses.isin(["REJECTED", "ESCALATED", "HOLD"])).astype(int)

    feature_frame = df[DEFAULT_FEATURE_COLUMNS + [TARGET_COLUMN]].copy()
    return feature_frame


__all__ = [
    "DEFAULT_FEATURE_COLUMNS",
    "TARGET_COLUMN",
    "derive_context_feature_frame",
]
