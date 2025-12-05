"""Preset feedback and reinforcement models for ChainIQ.

These models capture per-preset feedback events, aggregated behavior
statistics, and per-profile weight vectors for the AI preset
recommender. They deliberately live in a small, focused module to keep
behavioral reinforcement concerns isolated from core risk models.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class PresetFeedbackEvent(Base):
    """Single feedback signal for a preset recommendation.

    Stores both implicit and explicit feedback for auditability.
    """

    __tablename__ = "preset_feedback_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    preset_id = Column(String, index=True, nullable=False)
    profile = Column(String, index=True, nullable=False)
    rank = Column(Integer, nullable=True)
    chosen = Column(Boolean, nullable=False, default=False)

    # "up", "down" or "none"; stored as a simple string for now
    explicit_feedback = Column(String, nullable=True)

    session_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)


class PresetBehaviorStats(Base):
    """Aggregated behavior statistics per preset.

    One row per (profile, preset_id) pair.
    """

    __tablename__ = "preset_behavior_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)

    preset_id = Column(String, index=True, nullable=False)
    profile = Column(String, index=True, nullable=False)

    positive_clicks = Column(Integer, nullable=False, default=0)
    negative_clicks = Column(Integer, nullable=False, default=0)
    explicit_upvotes = Column(Integer, nullable=False, default=0)
    explicit_downvotes = Column(Integer, nullable=False, default=0)

    posterior_mean = Column(Float, nullable=False, default=0.5)

    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PresetProfileWeights(Base):
    """Per-profile weight vectors for preset recommendation components."""

    __tablename__ = "preset_profile_weights"

    id = Column(Integer, primary_key=True, autoincrement=True)

    profile = Column(String, nullable=False)

    # Optional scoping fields for multi-tenant / multi-console usage.
    # When both are NULL, the row is considered "global" for the profile.
    tenant_id = Column(String, nullable=True, index=True)
    console_id = Column(String, nullable=True, index=True)

    __table_args__ = (UniqueConstraint("profile", "tenant_id", "console_id", name="uq_profile_tenant_console"),)

    usage_weight = Column(Float, nullable=False, default=0.4)
    recency_weight = Column(Float, nullable=False, default=0.2)
    tags_weight = Column(Float, nullable=False, default=0.2)
    category_weight = Column(Float, nullable=False, default=0.2)

    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PresetAnalyticsSnapshot(Base):
    """High-level analytics snapshots for preset recommendations.

    Stores roll-up KPIs from the frontend's weightSync export so that
    dashboards and badges can query backend-verified metrics.
    """

    __tablename__ = "preset_analytics_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    profile = Column(String, nullable=False, index=True)

    ctr = Column(Float, nullable=False)
    hit_at_1 = Column(Float, nullable=False)
    hit_at_3 = Column(Float, nullable=False)
    avg_time_to_preset_ms = Column(Float, nullable=True)
    interaction_count = Column(Integer, nullable=True)

    tenant_id = Column(String, nullable=True, index=True)
    console_id = Column(String, nullable=True, index=True)
