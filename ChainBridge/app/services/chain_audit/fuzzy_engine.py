"""Simpful-backed payout confidence engine."""
from __future__ import annotations


try:
    from simpful import FuzzySystem, LinguisticVariable, FuzzySet, Trapezoidal_MF
except Exception:  # pragma: no cover - fallback when simpful is unavailable
    FuzzySystem = None  # type: ignore


def _fallback_confidence(delta_temp_c: float, duration_mins: float) -> float:
    """Deterministic fallback mirroring the rule set."""
    if delta_temp_c <= 2:
        return 100.0
    if delta_temp_c <= 5:
        if duration_mins <= 30:
            return 100.0
        elif duration_mins <= 120:
            return 60.0
        return 40.0
    return 0.0


def get_payout_confidence(delta_temp_c: float, duration_mins: float) -> float:
    """Return payout confidence 0-100 based on fuzzy rules."""
    delta_temp_c = max(0.0, min(delta_temp_c, 10.0))
    duration_mins = max(0.0, min(duration_mins, 300.0))

    if FuzzySystem is None:
        return _fallback_confidence(delta_temp_c, duration_mins)

    fs = FuzzySystem()

    temp_minor = FuzzySet(function=Trapezoidal_MF(0, 0, 2, 2), term="Minor")
    temp_moderate = FuzzySet(function=Trapezoidal_MF(2, 2, 5, 5), term="Moderate")
    temp_critical = FuzzySet(function=Trapezoidal_MF(5, 5.5, 10, 10), term="Critical")
    fs.add_linguistic_variable("Temp", LinguisticVariable([temp_minor, temp_moderate, temp_critical]))

    time_flash = FuzzySet(function=Trapezoidal_MF(0, 0, 20, 30), term="Flash")
    time_sustained = FuzzySet(function=Trapezoidal_MF(30, 40, 120, 140), term="Sustained")
    time_prolonged = FuzzySet(function=Trapezoidal_MF(120, 150, 300, 300), term="Prolonged")
    fs.add_linguistic_variable("Time", LinguisticVariable([time_flash, time_sustained, time_prolonged]))

    conf_full = FuzzySet(function=Trapezoidal_MF(90, 95, 100, 100), term="Full")
    conf_partial = FuzzySet(function=Trapezoidal_MF(40, 50, 80, 90), term="Partial")
    conf_reject = FuzzySet(function=Trapezoidal_MF(0, 0, 10, 20), term="Reject")
    fs.add_linguistic_variable("Confidence", LinguisticVariable([conf_full, conf_partial, conf_reject], universe_of_discourse=[0, 100]))

    fs.add_rules(
        [
            "IF (Temp IS Minor) THEN Confidence IS Full",
            "IF (Temp IS Moderate) AND (Time IS Flash) THEN Confidence IS Full",
            "IF (Temp IS Moderate) AND (Time IS Sustained) THEN Confidence IS Partial",
            "IF (Temp IS Critical) THEN Confidence IS Reject",
        ]
    )

    fs.set_variable("Temp", delta_temp_c)
    fs.set_variable("Time", duration_mins)
    try:
        result = fs.inference()
        confidence = float(result.get("Confidence", 0.0))
    except Exception:
        confidence = _fallback_confidence(delta_temp_c, duration_mins)
    return max(0.0, min(confidence, 100.0))


async def get_payout_confidence_async(delta_temp_c: float, duration_mins: float) -> float:
    """Async wrapper to ensure fuzzy evaluation does not block the event loop."""
    import asyncio

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: get_payout_confidence(delta_temp_c, duration_mins))
