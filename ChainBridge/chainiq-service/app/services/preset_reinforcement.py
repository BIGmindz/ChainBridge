"""Behavioral reinforcement helpers for preset recommendations.

Implements glass-box Bayesian posteriors and profile weight updates
without any ML frameworks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models_preset import PresetBehaviorStats, PresetProfileWeights


def compute_posterior_score(positive: int, negative: int) -> float:
    """Compute a smoothed preference probability using Beta(1, 1) prior.

    posterior = (positive + 1) / (positive + negative + 2)
    """

    total = positive + negative
    return (positive + 1.0) / (total + 2.0)


@dataclass
class ProfileWeights:
    usage: float
    recency: float
    tags: float
    category: float


def _load_profile_weights(
    db: Session,
    profile: str,
    tenant_id: Optional[str] = None,
    console_id: Optional[str] = None,
) -> PresetProfileWeights:
    query = db.query(PresetProfileWeights).filter(
        PresetProfileWeights.profile == profile,
    )

    if tenant_id is None:
        query = query.filter(PresetProfileWeights.tenant_id.is_(None))
    else:
        query = query.filter(PresetProfileWeights.tenant_id == tenant_id)

    if console_id is None:
        query = query.filter(PresetProfileWeights.console_id.is_(None))
    else:
        query = query.filter(PresetProfileWeights.console_id == console_id)

    weights = query.one_or_none()
    if weights is None:
        # Bootstrap with simple moderate defaults
        weights = PresetProfileWeights(
            profile=profile,
            tenant_id=tenant_id,
            console_id=console_id,
            usage_weight=0.4,
            recency_weight=0.2,
            tags_weight=0.2,
            category_weight=0.2,
        )
        db.add(weights)
        db.flush()
    return weights


def update_profile_weights(
    db: Session,
    profile: str,
    component_scores: Dict[str, float],
    direction: int,
    step: float = 0.01,
    tenant_id: Optional[str] = None,
    console_id: Optional[str] = None,
) -> ProfileWeights:
    """Update and persist profile weights based on component scores.

    direction: +1 for positive reinforcement, -1 for negative.
    """

    weights_row = _load_profile_weights(db, profile, tenant_id=tenant_id, console_id=console_id)

    current = {
        "usage": weights_row.usage_weight,
        "recency": weights_row.recency_weight,
        "tags": weights_row.tags_weight,
        "category": weights_row.category_weight,
    }

    updated = {}
    for key in ["usage", "recency", "tags", "category"]:
        base = current.get(key, 0.0)
        score = component_scores.get(key, 0.0)
        delta = direction * score * step
        value = max(0.0, min(1.0, base + delta))
        updated[key] = value

    total = sum(updated.values())
    if total <= 0.0:
        # Fallback to equal weights
        for key in updated:
            updated[key] = 0.25
        total = 1.0

    for key in updated:
        updated[key] = updated[key] / total

    weights_row.usage_weight = updated["usage"]
    weights_row.recency_weight = updated["recency"]
    weights_row.tags_weight = updated["tags"]
    weights_row.category_weight = updated["category"]
    weights_row.updated_at = datetime.utcnow()

    db.add(weights_row)

    return ProfileWeights(**updated)


def upsert_behavior_stats(
    db: Session,
    preset_id: str,
    profile: str,
    *,
    positive_delta: int = 0,
    negative_delta: int = 0,
    upvote_delta: int = 0,
    downvote_delta: int = 0,
) -> PresetBehaviorStats:
    """Update or insert aggregate behavior stats for a preset/profile pair."""

    stats = (
        db.query(PresetBehaviorStats)
        .filter(
            PresetBehaviorStats.preset_id == preset_id,
            PresetBehaviorStats.profile == profile,
        )
        .one_or_none()
    )

    if stats is None:
        stats = PresetBehaviorStats(
            preset_id=preset_id,
            profile=profile,
            positive_clicks=0,
            negative_clicks=0,
            explicit_upvotes=0,
            explicit_downvotes=0,
            posterior_mean=0.5,
        )
        db.add(stats)
        db.flush()

    stats.positive_clicks += positive_delta
    stats.negative_clicks += negative_delta
    stats.explicit_upvotes += upvote_delta
    stats.explicit_downvotes += downvote_delta

    stats.positive_clicks = max(0, stats.positive_clicks)
    stats.negative_clicks = max(0, stats.negative_clicks)

    stats.posterior_mean = compute_posterior_score(stats.positive_clicks, stats.negative_clicks)
    stats.updated_at = datetime.utcnow()

    db.add(stats)

    return stats
