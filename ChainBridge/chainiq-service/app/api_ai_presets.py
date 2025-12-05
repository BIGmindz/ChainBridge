"""AI Preset feedback and profile APIs for ChainIQ.

These endpoints allow the ChainBoard UI to record behavioral feedback
(implicit clicks and explicit votes) and to retrieve current profile
weights used by the preset recommender.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


from app.database import get_db
from app.models_preset import PresetFeedbackEvent, PresetProfileWeights
from app.services.preset_reinforcement import (
    ProfileWeights,
    upsert_behavior_stats,
    update_profile_weights,
)
from app.services.preset_metrics import PresetMetrics, compute_preset_metrics
from app.schemas_ai_presets import (
    PresetAnalyticsPayload,
    PresetAnalyticsSummary,
    MetricsResponse,
    AIBenefitResponse,
)
from app.services.preset_analytics import (
    ingest_preset_analytics,
    get_preset_analytics_summary,
    get_ai_benefit,
)

router = APIRouter(prefix="/api/ai/presets", tags=["ai-presets"])


class PresetFeedbackRequest(BaseModel):
    preset_id: str = Field(..., description="Preset identifier from UI")
    profile: str = Field(..., description="Profile name (e.g., moderate)")
    rank: Optional[int] = Field(
        None,
        description="Rank of the preset in the recommendation list (1 = top)",
    )
    chosen: bool = Field(..., description="Whether the preset was chosen")
    explicit: Optional[Literal["up", "down", "none"]] = Field(
        None,
        description="Explicit feedback from user (thumbs up/down/none)",
    )
    session_id: Optional[str] = Field(None, description="Optional session identifier for future analysis")
    user_id: Optional[str] = Field(None, description="Optional user identifier for future analysis")
    component_scores: Optional[Dict[str, float]] = Field(
        None,
        description=("Optional per-component scores from frontend (usage, recency, " "tags, category) used to nudge profile weights."),
    )
    tenant_id: Optional[str] = Field(
        None,
        description="Optional tenant identifier for scoping profile weights",
    )
    console_id: Optional[str] = Field(
        None,
        description="Optional console identifier for scoping profile weights",
    )


class PresetFeedbackResponse(BaseModel):
    ok: bool
    preset_id: str
    profile: str
    posterior: float
    updated_weights: Optional[Dict[str, float]] = None


class ProfileWeightsResponseItem(BaseModel):
    profile: str
    weights: Dict[str, float]
    updated_at: str


class ProfilesResponse(BaseModel):
    profiles: list[ProfileWeightsResponseItem]


@router.post("/feedback", response_model=PresetFeedbackResponse)
async def record_preset_feedback(payload: PresetFeedbackRequest, db: Session = Depends(get_db)) -> PresetFeedbackResponse:
    """Record preset feedback and optionally update profile weights."""

    event = PresetFeedbackEvent(
        preset_id=payload.preset_id,
        profile=payload.profile,
        rank=payload.rank,
        chosen=payload.chosen,
        explicit_feedback=payload.explicit,
        session_id=payload.session_id,
        user_id=payload.user_id,
    )
    db.add(event)

    positive_delta = 0
    negative_delta = 0
    upvote_delta = 0
    downvote_delta = 0

    if payload.rank is not None:
        if payload.chosen:
            positive_delta += 1
        else:
            negative_delta += 1

    if payload.explicit == "up":
        upvote_delta += 1
    elif payload.explicit == "down":
        downvote_delta += 1

    stats = upsert_behavior_stats(
        db,
        preset_id=payload.preset_id,
        profile=payload.profile,
        positive_delta=positive_delta,
        negative_delta=negative_delta,
        upvote_delta=upvote_delta,
        downvote_delta=downvote_delta,
    )

    updated_weights: Optional[ProfileWeights] = None

    if payload.component_scores:
        direction = 0
        if payload.chosen or payload.explicit == "up":
            direction = 1
        elif payload.explicit == "down" or (not payload.chosen and payload.rank is not None):
            direction = -1

        if direction != 0:
            updated_weights = update_profile_weights(
                db,
                payload.profile,
                payload.component_scores,
                direction,
                tenant_id=payload.tenant_id,
                console_id=payload.console_id,
            )

    # Commit all changes
    db.commit()

    weights_dict: Optional[Dict[str, float]] = None
    if updated_weights:
        weights_dict = {
            "usage": updated_weights.usage,
            "recency": updated_weights.recency,
            "tags": updated_weights.tags,
            "category": updated_weights.category,
        }

    return PresetFeedbackResponse(
        ok=True,
        preset_id=payload.preset_id,
        profile=payload.profile,
        posterior=stats.posterior_mean,
        updated_weights=weights_dict,
    )


@router.get("/profiles", response_model=ProfilesResponse)
async def get_profiles(
    tenant_id: Optional[str] = None,
    console_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ProfilesResponse:
    """Return current weight vectors for all profiles."""

    query = db.query(PresetProfileWeights)

    if tenant_id is not None:
        query = query.filter(PresetProfileWeights.tenant_id == tenant_id)
    if console_id is not None:
        query = query.filter(PresetProfileWeights.console_id == console_id)

    rows = query.all()

    items: list[ProfileWeightsResponseItem] = []
    for row in rows:
        items.append(
            ProfileWeightsResponseItem(
                profile=row.profile,
                weights={
                    "usage": row.usage_weight,
                    "recency": row.recency_weight,
                    "tags": row.tags_weight,
                    "category": row.category_weight,
                },
                updated_at=row.updated_at.isoformat(),
            )
        )

    return ProfilesResponse(profiles=items)


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    since_days: int = 7,
    profile: Optional[str] = None,
    db: Session = Depends(get_db),
) -> MetricsResponse:
    """Return CTR and Hit@N metrics for presets.

    - `since_days`: lookback window (days) from now in UTC.
    - `profile`: optional profile filter; when omitted, aggregates across profiles.
    """

    if since_days <= 0:
        raise HTTPException(status_code=400, detail="since_days must be positive")

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=since_days)

    metrics: PresetMetrics = compute_preset_metrics(
        db=db,
        since=since,
        profile=profile,
    )

    return MetricsResponse(
        ctr=metrics.ctr,
        hit_at_1=metrics.hit_at_1,
        hit_at_3=metrics.hit_at_3,
        total_sessions=metrics.total_sessions,
        total_ai_sessions=metrics.total_ai_sessions,
    )


@router.post("/analytics/ingest", status_code=204)
async def ingest_analytics(
    payload: PresetAnalyticsPayload,
    db: Session = Depends(get_db),
) -> Response:
    """Ingest a frontend analytics export snapshot.

    Sonny's weightSync backend hook can POST payloads here. We persist
    only high-level KPIs; per-preset details remain in other stores.
    """

    ingest_preset_analytics(db, payload)
    return Response(status_code=204)


@router.get("/analytics/summary", response_model=PresetAnalyticsSummary)
async def get_analytics_summary(
    profile: str,
    window_days: int = 7,
    db: Session = Depends(get_db),
) -> PresetAnalyticsSummary:
    """Return a roll-up summary of recent analytics snapshots."""

    return get_preset_analytics_summary(db, profile=profile, window_days=window_days)


# =============================================================================
# PAC-005 — AI Benefit Score Endpoint
# =============================================================================


@router.get("/analytics/benefit", response_model=AIBenefitResponse)
async def get_ai_benefit_view(
    profile: str,
    window_days: int = 28,
    buckets: int = 7,
    db: Session = Depends(get_db),
) -> AIBenefitResponse:
    """Compute AI benefit score for a profile.

    This endpoint answers the question: "Is AI actually helping operators
    with this profile over the specified time window?"

    Args:
        profile: Profile name (conservative/moderate/aggressive)
        window_days: Lookback window in days (default 28)
        buckets: Number of time buckets for trend analysis (default 7)

    Returns:
        AIBenefitResponse with:
        - ai_benefit_score: Net benefit in [-1, 1]. Positive = AI helping.
        - speed_gain: Time improvement vs baseline.
        - precision_lift: Hit@3 improvement vs baseline.
        - adoption_intensity: Recent engagement level.
        - stability_score: Metric consistency over time.

    Interpretation:
        - ai_benefit_score > 0.3: AI is clearly helping
        - ai_benefit_score in [-0.1, 0.1]: Neutral / insufficient data
        - ai_benefit_score < -0.3: AI may be hurting performance
    """
    result = get_ai_benefit(
        db=db,
        profile=profile,
        window_days=window_days,
        buckets=buckets,
    )

    return AIBenefitResponse(
        profile=result.profile,
        window_days=result.window_days,
        ai_benefit_score=result.ai_benefit_score,
        speed_gain=result.speed_gain,
        precision_lift=result.precision_lift,
        adoption_intensity=result.adoption_intensity,
        stability_score=result.stability_score,
    )
