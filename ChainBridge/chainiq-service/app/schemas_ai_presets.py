from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PresetAnalyticsPreset(BaseModel):
    preset_id: str = Field(..., alias="presetId")
    posterior: float
    clicks: int
    votes: Dict[str, int]


class PresetAnalyticsKpis(BaseModel):
    ctr: float
    hit_at_1: float = Field(..., alias="hitAt1")
    hit_at_3: float = Field(..., alias="hitAt3")
    avg_time_to_preset_ms: float = Field(..., alias="avgTimeToPresetMs")

    class Config:
        populate_by_name = True


class PresetAnalyticsPayload(BaseModel):
    generated_at: datetime = Field(..., alias="generatedAt")
    profile: str
    kpis: PresetAnalyticsKpis
    stats: Dict[str, Any]

    class Config:
        populate_by_name = True


class PresetAnalyticsSummary(BaseModel):
    profile: str
    window_days: int
    ctr: float
    hit_at_1: float
    hit_at_3: float
    avg_time_to_preset_ms: Optional[float]
    snapshots: int


# =============================================================================
# PAC-005 — AI Benefit Score Response
# =============================================================================


class AIBenefitResponse(BaseModel):
    """Response schema for AI benefit score computation.

    All scores are glass-box interpretable:

    - ai_benefit_score: Net benefit in [-1.0, 1.0].
      Positive = AI is helping operators. Negative = AI may be hurting.

    - speed_gain: How much faster AI makes preset selection vs baseline.
      +0.2 means 20% faster. -0.1 means 10% slower.

    - precision_lift: Change in Hit@3 rate vs baseline.
      +0.15 means 15 percentage points more top-3 hits.

    - adoption_intensity: Fraction of recent activity.
      High values mean users are actively engaging with AI.

    - stability_score: How consistent metrics are across time.
      High values (>0.7) mean stable, reliable benefit.
    """

    profile: str = Field(..., description="Profile name (conservative/moderate/aggressive)")
    window_days: int = Field(..., description="Lookback window in days")
    ai_benefit_score: float = Field(..., ge=-1.0, le=1.0, description="Net AI benefit score in [-1, 1]. Positive = AI helping.")
    speed_gain: float = Field(..., ge=-1.0, le=1.0, description="Speed improvement vs baseline. Positive = faster.")
    precision_lift: float = Field(..., ge=-1.0, le=1.0, description="Hit@3 improvement vs baseline. Positive = more accurate.")
    adoption_intensity: float = Field(..., ge=0.0, le=1.0, description="Fraction of recent activity in the window.")
    stability_score: float = Field(..., ge=0.0, le=1.0, description="Metric consistency. High = stable, low = volatile.")


# =============================================================================
# MetricsResponse schema for /metrics endpoint
# =============================================================================


class MetricsResponse(BaseModel):
    ctr: float
    hit_at_1: float
    hit_at_3: float
    total_sessions: int
    total_ai_sessions: int
