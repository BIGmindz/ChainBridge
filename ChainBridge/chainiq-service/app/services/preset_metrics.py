"""Preset metrics computation for AI recommendations.

Provides glass-box CTR and Hit@N metrics over feedback events.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models_preset import PresetFeedbackEvent


@dataclass
class PresetMetrics:
    ctr: float
    hit_at_1: float
    hit_at_3: float
    total_sessions: int
    total_ai_sessions: int


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def compute_preset_metrics(
    db: Session,
    since: Optional[datetime] = None,
    profile: Optional[str] = None,
) -> PresetMetrics:
    """Compute CTR and Hit@N metrics from PresetFeedbackEvent.

    - ctr: ai_chosen_sessions / total_ai_sessions
    - hit_at_1: sessions where chosen rank == 1 / total_ai_sessions
    - hit_at_3: sessions where chosen rank <= 3 / total_ai_sessions
    """

    if since is None:
        since = _now_utc() - timedelta(days=7)

    filters = [PresetFeedbackEvent.created_at >= since]
    if profile:
        filters.append(PresetFeedbackEvent.profile == profile)

    # Fallback: when session_id is null, treat each row as its own session.
    # This keeps metrics defined even before full session wiring.
    base_query = db.query(
        PresetFeedbackEvent.session_id,
        PresetFeedbackEvent.chosen,
        PresetFeedbackEvent.rank,
    ).filter(and_(*filters))

    rows = base_query.all()

    if not rows:
        return PresetMetrics(
            ctr=0.0,
            hit_at_1=0.0,
            hit_at_3=0.0,
            total_sessions=0,
            total_ai_sessions=0,
        )

    # Group by session_id (or by pseudo-session index when missing)
    sessions = {}
    next_pseudo_id = 0
    for session_id, chosen, rank in rows:
        key = session_id
        if key is None:
            key = f"__row__{next_pseudo_id}"
            next_pseudo_id += 1
        bucket = sessions.setdefault(key, [])
        bucket.append((chosen, rank))

    total_sessions = len(sessions)

    total_ai_sessions = 0
    ai_chosen_sessions = 0
    hit1_sessions = 0
    hit3_sessions = 0

    for events in sessions.values():
        # AI is considered shown if any event has a rank
        ai_shown = any(rank is not None for _, rank in events)
        if not ai_shown:
            continue
        total_ai_sessions += 1

        chosen_ranks = [rank for chosen, rank in events if chosen and rank is not None]
        if chosen_ranks:
            ai_chosen_sessions += 1
            best_rank = min(chosen_ranks)
            if best_rank is not None and best_rank <= 1:
                hit1_sessions += 1
            if best_rank is not None and best_rank <= 3:
                hit3_sessions += 1

    if total_ai_sessions == 0:
        return PresetMetrics(
            ctr=0.0,
            hit_at_1=0.0,
            hit_at_3=0.0,
            total_sessions=total_sessions,
            total_ai_sessions=0,
        )

    ctr = ai_chosen_sessions / total_ai_sessions
    hit_at_1 = hit1_sessions / total_ai_sessions
    hit_at_3 = hit3_sessions / total_ai_sessions

    return PresetMetrics(
        ctr=ctr,
        hit_at_1=hit_at_1,
        hit_at_3=hit_at_3,
        total_sessions=total_sessions,
        total_ai_sessions=total_ai_sessions,
    )
