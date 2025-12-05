"""Risk scoring wrapper for ChainPay context ledger events (PINK-01)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import log1p
from typing import Dict, List, Sequence

import pandas as pd

from ml_engine.feature_store.context_ledger_features import (
    DEFAULT_FEATURE_COLUMNS,
    TARGET_COLUMN,
)
from ml_engine.models.context_ledger_risk_model import ContextLedgerRiskModel

from app.schemas_context_risk import ContextLedgerEvent, RiskScoreResponse


@dataclass(frozen=True)
class _ScalarInputs:
    amount: float
    route_notional: float
    counterparty_notional: float
    recent_events: float
    recent_failed: float
    is_reversal: float
    is_night: float
    is_xrpl: float
    is_onchain: float


# Corridors with persistent investigative load from Maggie's intel briefs.
_HIGH_RISK_CORRIDORS = {"US-BR", "LATAM-USD", "AFRICA-USD", "APAC-CRYPTO"}

_ROLE_TIERS = {
    "anchor": 1,
    "carrier": 2,
    "broker": 2,
    "buyer": 3,
    "seller": 3,
}


def _extract_scalar_inputs(event: ContextLedgerEvent) -> _ScalarInputs:
    amount = float(max(event.amount, 0.0))
    route_notional = float(event.route_notional_7d_usd or 0.0)
    counterparty_notional = float(event.counterparty_notional_30d_usd or 0.0)
    recent_events = float(event.recent_event_count_24h or 0.0)
    recent_failed = float(event.recent_failed_count_7d or 0.0)
    settlement = (event.settlement_channel or "").upper()
    event_type = (event.event_type or "").upper()
    hour = event.timestamp.hour

    return _ScalarInputs(
        amount=amount,
        route_notional=route_notional,
        counterparty_notional=counterparty_notional,
        recent_events=recent_events,
        recent_failed=recent_failed,
        is_reversal=1.0 if event_type == "REVERSAL" else 0.0,
        is_night=1.0 if hour < 6 or hour >= 22 else 0.0,
        is_xrpl=1.0 if settlement == "XRPL" else 0.0,
        is_onchain=1.0 if settlement == "ONCHAIN_TOKEN" else 0.0,
    )


def _corridor_factor(corridor_id: str) -> float:
    if not corridor_id:
        return 0.0
    corridor = corridor_id.upper()
    if corridor in _HIGH_RISK_CORRIDORS:
        return 1.0
    if "STABLE" in corridor:
        return -0.3
    return 0.2


def _role_tier_weight(role: str) -> float:
    tier = _ROLE_TIERS.get(role.lower(), 3)
    return 1.0 / float(max(tier, 1))


def _event_to_features(event: ContextLedgerEvent) -> Dict[str, float]:
    scalars = _extract_scalar_inputs(event)

    base_risk = (
        0.25 * scalars.amount / 100_000.0
        + 0.2 * scalars.route_notional / 1_000_000.0
        + 0.15 * scalars.counterparty_notional / 1_000_000.0
        + 0.05 * scalars.recent_events
        + 0.8 * scalars.is_reversal
        + 0.3 * scalars.is_night
        + 0.4 * (scalars.is_xrpl + scalars.is_onchain)
        + 0.1 * scalars.recent_failed
    )
    risk_score = max(0.0, min(100.0, base_risk * 100.0))

    features: Dict[str, float] = {
        "amount_log": log1p(scalars.amount),
        "risk_score": risk_score,
        "reason_code_intensity": scalars.recent_failed + (2.0 * scalars.is_reversal),
        "policy_stack_depth": 1.0 + scalars.is_onchain + scalars.is_xrpl,
        "corridor_risk_factor": _corridor_factor(event.corridor_id),
        "velocity_score": min(3.0, scalars.recent_events / 4.0),
        "anomaly_indicator": 1.0 if scalars.is_reversal or scalars.is_night or scalars.recent_failed >= 5 else 0.0,
        "role_tier_weight": _role_tier_weight(event.counterparty_role),
        "is_reversal_flag": scalars.is_reversal,
        "is_night_flag": scalars.is_night,
        "is_xrpl_flag": scalars.is_xrpl,
        "is_onchain_flag": scalars.is_onchain,
        "recent_failed": scalars.recent_failed,
        "recent_events": scalars.recent_events,
        "route_notional_usd": scalars.route_notional,
        "counterparty_notional_usd": scalars.counterparty_notional,
    }
    return features


def _reason_codes(features: Dict[str, float]) -> List[str]:
    """Derive stable, operator-friendly reason codes for the risk strip.

    This is the closed vocabulary for PINK-01 v1.1. Codes are ordered by
    salience and truncated to a small list so operators see at most
    3–5 concise factors.
    """

    codes: List[str] = []

    if features.get("is_reversal_flag"):
        codes.append("REPEATED_REVERSALS_ON_ROUTE")
    if features.get("recent_failed", 0.0) >= 5:
        codes.append("REPEATED_SETTLEMENT_FAILURES")
    if features.get("corridor_risk_factor", 0.0) > 0.5:
        codes.append("HIGH_RISK_CORRIDOR")
    if features.get("route_notional_usd", 0.0) >= 1_000_000:
        codes.append("ELEVATED_ROUTE_NOTIONAL")
    if features.get("counterparty_notional_usd", 0.0) >= 2_000_000:
        codes.append("CONCENTRATED_COUNTERPARTY_EXPOSURE")
    if features.get("is_night_flag"):
        codes.append("AFTER_HOURS_ACTIVITY")
    if features.get("is_xrpl_flag"):
        codes.append("XRPL_SETTLEMENT_CHANNEL")
    if features.get("is_onchain_flag") and "XRPL_SETTLEMENT_CHANNEL" not in codes:
        codes.append("ONCHAIN_TOKEN_CHANNEL")

    if not codes:
        codes.append("BASELINE_MONITORING")

    # Cap to the top 5 factors to avoid overloading operators.
    return codes[:5]


def _bootstrap_probability(features: Dict[str, float]) -> float:
    """Lightweight fallback probability when the ML model is unavailable.

    Uses a bounded linear blend of interpretable feature hints to return a
    0–1 probability suitable for downstream band mapping.
    """

    risk_score_component = 0.3 * min(1.0, features.get("risk_score", 0.0) / 100.0)
    anomaly_component = 0.2 * min(1.0, features.get("anomaly_indicator", 0.0))
    velocity_component = 0.2 * min(1.0, features.get("velocity_score", 0.0) / 3.0)
    failure_component = 0.1 * min(1.0, features.get("recent_failed", 0.0) / 10.0)
    corridor_component = 0.2 * max(0.0, features.get("corridor_risk_factor", 0.0) / 1.5)

    probability = risk_score_component + anomaly_component + velocity_component
    probability += failure_component + corridor_component
    return float(min(1.0, max(0.0, probability)))


def _anomaly_score(features: Dict[str, float], risk_probability: float) -> float:
    base = 0.4 * risk_probability
    base += 0.2 * (1.0 if features.get("is_night_flag") else 0.0)
    base += 0.2 * min(1.0, features.get("recent_failed", 0.0) / 10.0)
    base += 0.2 * min(1.0, features.get("recent_events", 0.0) / 50.0)
    return float(min(1.0, max(0.0, base)))


def _map_score_to_band(probability: float) -> str:
    """Map a 0–1 risk score into ChainPay bands.

    PINK-01 v1.1 calibration for ChainPay v1:
    - 0.00–0.34 → LOW
    - 0.35–0.64 → MEDIUM
    - 0.65–0.79 → HIGH
    - 0.80–1.00 → CRITICAL
    """

    if probability >= 0.80:
        return "CRITICAL"
    if probability >= 0.65:
        return "HIGH"
    if probability >= 0.35:
        return "MEDIUM"
    return "LOW"


def score_context_event(event: ContextLedgerEvent) -> RiskScoreResponse:
    model = _get_model()
    features = _event_to_features(event)
    vector = {col: features.get(col, 0.0) for col in model.feature_columns}
    output = model.predict(vector)

    risk_probability = float(output["risk_probability"])
    risk_band = _map_score_to_band(risk_probability)
    response = RiskScoreResponse(
        risk_score=risk_probability,
        anomaly_score=_anomaly_score(features, risk_probability),
        risk_band=risk_band,
        top_features=list(output["top_signals"]),
        reason_codes=_reason_codes(features),
        trace_id=event.event_id,
    )
    return response


__all__ = [
    "_bootstrap_probability",
    "score_context_event",
]


_REFERENCE_EVENTS: Sequence[tuple[ContextLedgerEvent, int]] = (
    (
        ContextLedgerEvent(
            event_id="seed-low-1",
            timestamp=datetime(2025, 1, 1, 15, tzinfo=timezone.utc),
            amount=8_000.0,
            currency="USD",
            corridor_id="US-CA",
            counterparty_id="cp-low",
            counterparty_role="buyer",
            settlement_channel="BANK",
            event_type="SETTLED",
            recent_event_count_24h=4,
            recent_failed_count_7d=0,
            route_notional_7d_usd=50_000.0,
            counterparty_notional_30d_usd=120_000.0,
        ),
        0,
    ),
    (
        ContextLedgerEvent(
            event_id="seed-med-1",
            timestamp=datetime(2025, 1, 3, 19, tzinfo=timezone.utc),
            amount=45_000.0,
            currency="USD",
            corridor_id="US-MX",
            counterparty_id="cp-med",
            counterparty_role="carrier",
            settlement_channel="BANK",
            event_type="SETTLED",
            recent_event_count_24h=18,
            recent_failed_count_7d=2,
            route_notional_7d_usd=420_000.0,
            counterparty_notional_30d_usd=650_000.0,
        ),
        0,
    ),
    (
        ContextLedgerEvent(
            event_id="seed-high-1",
            timestamp=datetime(2025, 1, 5, 2, tzinfo=timezone.utc),
            amount=275_000.0,
            currency="USD",
            corridor_id="US-BR",
            counterparty_id="cp-high",
            counterparty_role="seller",
            settlement_channel="XRPL",
            event_type="REVERSAL",
            recent_event_count_24h=42,
            recent_failed_count_7d=6,
            route_notional_7d_usd=1_700_000.0,
            counterparty_notional_30d_usd=2_800_000.0,
        ),
        1,
    ),
    (
        ContextLedgerEvent(
            event_id="seed-critical-1",
            timestamp=datetime(2025, 1, 6, 0, tzinfo=timezone.utc),
            amount=380_000.0,
            currency="USD",
            corridor_id="APAC-CRYPTO",
            counterparty_id="cp-critical",
            counterparty_role="broker",
            settlement_channel="ONCHAIN_TOKEN",
            event_type="REVERSAL",
            recent_event_count_24h=60,
            recent_failed_count_7d=9,
            route_notional_7d_usd=2_500_000.0,
            counterparty_notional_30d_usd=4_100_000.0,
        ),
        1,
    ),
)

_REFERENCE_DATASET = pd.DataFrame(
    [
        {
            **{col: 0.0 for col in DEFAULT_FEATURE_COLUMNS},
            **{
                col: _event_to_features(event).get(col, 0.0)
                for col in DEFAULT_FEATURE_COLUMNS
            },
            TARGET_COLUMN: float(label),
        }
        for event, label in _REFERENCE_EVENTS
    ]
)

_model: ContextLedgerRiskModel | None = None


def _get_model() -> ContextLedgerRiskModel:
    global _model
    if _model is None:
        if _REFERENCE_DATASET.empty:
            raise RuntimeError("Reference dataset for ContextLedgerRiskModel is empty")
        model = ContextLedgerRiskModel()
        # Some test environments inject a stub model without train(); guard accordingly.
        train_fn = getattr(model, "train", None)
        if callable(train_fn):
            train_fn(_REFERENCE_DATASET)
        _model = model
    return _model
