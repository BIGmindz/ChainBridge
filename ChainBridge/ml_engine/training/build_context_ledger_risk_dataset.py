"""Dataset composer for the context ledger risk model."""

from __future__ import annotations

from typing import Iterable, List, TypedDict

import pandas as pd

from ..feature_store.context_ledger_features import (
    DEFAULT_FEATURE_COLUMNS,
    TARGET_COLUMN,
    derive_context_feature_frame,
)


class RawContextLedgerEvent(TypedDict, total=False):
    agent_id: str
    gid: str
    role_tier: int
    gid_hgp_version: str
    decision_type: str
    decision_status: str
    shipment_id: str | None
    payer_id: str | None
    payee_id: str | None
    amount: float
    currency: str
    corridor: str | None
    risk_score: int
    reason_codes: List[str]
    policies_applied: List[str]
    economic_reliability: float | None
    token_velocity: float | None
    anomaly_density: float | None
    created_at: str


def build_context_ledger_risk_dataset(events: Iterable[RawContextLedgerEvent]) -> pd.DataFrame:
    """Convert raw context ledger events into a model-ready feature matrix."""

    rows = list(events)
    if not rows:
        columns = DEFAULT_FEATURE_COLUMNS + [TARGET_COLUMN]
        return pd.DataFrame(columns=columns)

    frame = pd.DataFrame(rows)
    for col in ("reason_codes", "policies_applied"):
        if col not in frame:
            frame[col] = [[] for _ in range(len(frame))]
        else:
            frame[col] = frame[col].apply(lambda v: v if isinstance(v, list) else [])

    feature_frame = derive_context_feature_frame(frame)
    return feature_frame


__all__ = [
    "RawContextLedgerEvent",
    "build_context_ledger_risk_dataset",
]
