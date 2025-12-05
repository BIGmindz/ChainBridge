"""Simpful-inspired fuzzy engine for payout confidence."""

from __future__ import annotations


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def get_payout_confidence(delta_temp_c: float, duration_mins: float) -> float:
    """Return a confidence score 0–100 based on temp delta and breach duration.

    The logic mirrors a small fuzzy system with linguistic buckets:
    - Temperature deviation: Minor / Moderate / Critical
    - Duration: Flash / Sustained / Prolonged
    - Output: Reject / Partial / Full
    """
    dt = _clamp(delta_temp_c, 0.0, 10.0)
    dur = _clamp(duration_mins, 0.0, 300.0)

    # Temperature membership (soft buckets)
    temp_minor = max(0.0, 1 - dt / 4.0)
    temp_moderate = max(0.0, 1 - abs(dt - 5.0) / 3.0)
    temp_critical = max(0.0, (dt - 6.0) / 4.0)

    # Duration membership
    flash = max(0.0, 1 - dur / 40.0)
    sustained = max(0.0, 1 - abs(dur - 120.0) / 120.0)
    prolonged = max(0.0, (dur - 150.0) / 150.0)

    # Rule aggregation (Full / Partial / Reject)
    full_score = max(
        temp_minor * flash,
        temp_minor * sustained * 0.8,
        temp_moderate * flash * 0.8,
    )
    partial_score = max(
        temp_moderate * sustained,
        temp_minor * prolonged * 0.6,
        temp_critical * flash * 0.4,
    )
    reject_score = max(
        temp_critical * sustained,
        temp_critical * prolonged,
        temp_moderate * prolonged * 0.6,
        temp_moderate * sustained * 0.5,
    )

    # Defuzzify to a percentage
    numerator = full_score * 100 + partial_score * 65 + reject_score * 0
    denominator = full_score + partial_score + reject_score or 1
    score = numerator / denominator
    return _clamp(score, 0.0, 100.0)
