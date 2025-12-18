# tests/risk/test_feature_extractors.py
"""
Unit tests for TRI feature extractors.

Validates:
- Bounds checking (all outputs in [0.0, 1.0])
- Monotonicity (worse inputs → higher scores)
- Null handling
- Decay functions
- Saturation behavior

Author: MAGGIE (GID-10) — PAC-MAGGIE-RISK-IMPL-01
"""

from datetime import datetime, timedelta

import pytest

from core.risk.feature_extractors import (  # Helpers; GI extractors; OD extractors; SD extractors; Constants
    DECAY_SCOPE_VIOLATION_HALFLIFE,
    SATURATION_SCOPE_VIOLATIONS,
    exponential_decay,
    extract_gi_artifact_failures,
    extract_gi_denial_rate,
    extract_gi_forbidden_verbs,
    extract_gi_scope_violations,
    extract_gi_tool_denials,
    extract_od_diggi_corrections,
    extract_od_drcp_rate,
    extract_od_envelope_violations,
    extract_od_escalation_recoveries,
    extract_od_replay_denials,
    extract_sd_boot_failures,
    extract_sd_drift_count,
    extract_sd_fingerprint_changes,
    extract_sd_freshness_violation,
    extract_sd_manifest_deltas,
    hours_since,
    rate_to_score,
    saturating_score,
)
from core.risk.types import FeatureID


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_exponential_decay_at_zero(self) -> None:
        """Decay at t=0 should be 1.0."""
        assert exponential_decay(0, 168) == pytest.approx(1.0)

    def test_exponential_decay_at_halflife(self) -> None:
        """Decay at t=half_life should be 0.5."""
        assert exponential_decay(168, 168) == pytest.approx(0.5)

    def test_exponential_decay_at_double_halflife(self) -> None:
        """Decay at t=2*half_life should be 0.25."""
        assert exponential_decay(336, 168) == pytest.approx(0.25)

    def test_saturating_score_zero(self) -> None:
        """Count=0 should produce score=0."""
        assert saturating_score(0, 10) == 0.0

    def test_saturating_score_monotonic(self) -> None:
        """Higher counts should produce higher scores."""
        scores = [saturating_score(i, 10) for i in range(20)]
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i - 1]

    def test_saturating_score_bounded(self) -> None:
        """Scores should never exceed 1.0."""
        # At very high counts, approaches 1.0 asymptotically
        assert saturating_score(1000, 10) <= 1.0
        assert saturating_score(1000, 10) > 0.99

    def test_rate_to_score_zero_denominator(self) -> None:
        """Zero denominator should return None."""
        assert rate_to_score(5, 0) is None

    def test_rate_to_score_valid(self) -> None:
        """Valid rate should produce correct score."""
        assert rate_to_score(10, 100) == pytest.approx(0.1)
        assert rate_to_score(50, 100) == pytest.approx(0.5)

    def test_rate_to_score_capped(self) -> None:
        """Rate > 1.0 should be capped at 1.0."""
        assert rate_to_score(150, 100) == 1.0

    def test_hours_since_none(self) -> None:
        """None timestamp should return infinity."""
        assert hours_since(None, datetime.utcnow()) == float("inf")

    def test_hours_since_valid(self) -> None:
        """Valid timestamp should return correct hours."""
        now = datetime.utcnow()
        past = now - timedelta(hours=5)
        assert hours_since(past, now) == pytest.approx(5.0)


class TestGIExtractors:
    """Tests for Governance Integrity extractors."""

    def test_gi_denial_rate_zero(self) -> None:
        """Zero denials should produce score=0."""
        fv = extract_gi_denial_rate(0, 100, "24h", None)
        assert fv.value == 0.0
        assert fv.feature_id == FeatureID.GI_DENIAL_RATE

    def test_gi_denial_rate_full(self) -> None:
        """100% denial rate should produce score=1.0."""
        now = datetime.utcnow()
        fv = extract_gi_denial_rate(100, 100, "24h", now)
        assert fv.value == 1.0

    def test_gi_denial_rate_no_decisions(self) -> None:
        """No decisions should produce null score."""
        fv = extract_gi_denial_rate(0, 0, "24h", None)
        assert fv.value is None

    def test_gi_scope_violations_empty(self) -> None:
        """No violations should produce score=0."""
        fv = extract_gi_scope_violations([], "24h", datetime.utcnow())
        assert fv.value == 0.0

    def test_gi_scope_violations_decay(self) -> None:
        """Recent violations should score higher than old ones."""
        now = datetime.utcnow()
        # Use multiple violations to get non-zero scores
        recent = [{"timestamp": now - timedelta(hours=1)} for _ in range(5)]
        old = [{"timestamp": now - timedelta(days=7)} for _ in range(5)]

        fv_recent = extract_gi_scope_violations(recent, "7d", now)
        fv_old = extract_gi_scope_violations(old, "7d", now)

        # Recent violations should produce higher weighted score
        assert fv_recent.value > fv_old.value

    def test_gi_forbidden_verbs_monotonic(self) -> None:
        """More attempts should produce higher scores."""
        fv1 = extract_gi_forbidden_verbs(1, "24h", None)
        fv5 = extract_gi_forbidden_verbs(5, "24h", None)
        fv10 = extract_gi_forbidden_verbs(10, "24h", None)

        assert fv1.value < fv5.value < fv10.value

    def test_gi_tool_denials_rate_mode(self) -> None:
        """With enough data, should use rate calculation."""
        fv = extract_gi_tool_denials(5, 50, "24h", None)
        assert fv.value == pytest.approx(0.1)

    def test_gi_tool_denials_count_mode(self) -> None:
        """With sparse data, should use saturation."""
        fv = extract_gi_tool_denials(5, 5, "24h", None)
        # Count mode uses saturation, not rate
        assert fv.value is not None
        assert 0 < fv.value < 1

    def test_gi_artifact_failures_zero(self) -> None:
        """Zero failures should produce low/zero score."""
        fv = extract_gi_artifact_failures(0, 20, "24h", None)
        assert fv.value == 0.0


class TestODExtractors:
    """Tests for Operational Discipline extractors."""

    def test_od_drcp_rate_zero(self) -> None:
        """Zero DRCP triggers should produce low score."""
        fv = extract_od_drcp_rate(0, 100, "24h", None)
        assert fv.value == 0.0

    def test_od_diggi_corrections_monotonic(self) -> None:
        """More corrections should produce higher scores."""
        fv1 = extract_od_diggi_corrections(1, "24h", None)
        fv5 = extract_od_diggi_corrections(5, "24h", None)
        assert fv1.value < fv5.value

    def test_od_replay_denials_serious(self) -> None:
        """Replay denials should produce significant score."""
        fv = extract_od_replay_denials(3, "24h", None)
        # Low saturation threshold means even 3 is significant
        assert fv.value > 0.3

    def test_od_envelope_violations_bounded(self) -> None:
        """All scores should be in [0, 1]."""
        for count in [0, 1, 5, 10, 50, 100]:
            fv = extract_od_envelope_violations(count, "24h", None)
            assert 0.0 <= fv.value <= 1.0

    def test_od_escalation_recoveries_inverse(self) -> None:
        """Higher recovery rate should produce LOWER risk score."""
        # High recovery = low risk
        fv_high = extract_od_escalation_recoveries(9, 10, "24h", None)
        # Low recovery = high risk
        fv_low = extract_od_escalation_recoveries(1, 10, "24h", None)

        assert fv_high.value < fv_low.value

    def test_od_escalation_recoveries_no_escalations(self) -> None:
        """No escalations should produce null (no data)."""
        fv = extract_od_escalation_recoveries(0, 0, "24h", None)
        assert fv.value is None


class TestSDExtractors:
    """Tests for System Drift extractors."""

    def test_sd_drift_count_empty(self) -> None:
        """No drift events should produce score=0."""
        fv = extract_sd_drift_count([], "7d", datetime.utcnow())
        assert fv.value == 0.0

    def test_sd_drift_count_decay(self) -> None:
        """Recent drift should score higher than old drift."""
        now = datetime.utcnow()
        # Use multiple drift events to get non-zero scores
        recent = [{"timestamp": now - timedelta(hours=1)} for _ in range(3)]
        old = [{"timestamp": now - timedelta(days=3)} for _ in range(3)]

        fv_recent = extract_sd_drift_count(recent, "7d", now)
        fv_old = extract_sd_drift_count(old, "7d", now)

        # Recent drift should produce higher weighted score
        assert fv_recent.value > fv_old.value

    def test_sd_fingerprint_changes_monotonic(self) -> None:
        """More changes should produce higher scores."""
        fv1 = extract_sd_fingerprint_changes(1, "7d", None)
        fv3 = extract_sd_fingerprint_changes(3, "7d", None)
        assert fv1.value < fv3.value

    def test_sd_boot_failures_bounded(self) -> None:
        """All scores should be in [0, 1]."""
        for failures in range(10):
            fv = extract_sd_boot_failures(failures, 10, "7d", None)
            assert 0.0 <= fv.value <= 1.0

    def test_sd_manifest_deltas_saturation(self) -> None:
        """Score should saturate for high counts."""
        fv10 = extract_sd_manifest_deltas(10, "7d", None)
        fv100 = extract_sd_manifest_deltas(100, "7d", None)
        # Both should be high (approaching saturation)
        assert fv10.value > 0.8
        assert fv100.value > 0.99
        # At saturation, difference narrows
        assert fv100.value > fv10.value  # Still monotonic

    def test_sd_freshness_violation_fresh(self) -> None:
        """Recent events should produce score=0."""
        now = datetime.utcnow()
        recent = now - timedelta(hours=1)
        fv = extract_sd_freshness_violation(recent, now)
        assert fv.value == 0.0

    def test_sd_freshness_violation_stale(self) -> None:
        """Old events should produce high score."""
        now = datetime.utcnow()
        old = now - timedelta(hours=48)
        fv = extract_sd_freshness_violation(old, now)
        assert fv.value == 1.0

    def test_sd_freshness_violation_no_events(self) -> None:
        """No events at all should produce max score."""
        fv = extract_sd_freshness_violation(None, datetime.utcnow())
        assert fv.value == 1.0


class TestMonotonicity:
    """Verify all extractors maintain monotonicity property."""

    def test_all_extractors_bounded(self) -> None:
        """All extractor outputs should be in [0.0, 1.0] or None."""
        now = datetime.utcnow()

        # Test a variety of inputs
        extractors_and_results = [
            extract_gi_denial_rate(50, 100, "24h", now),
            extract_gi_scope_violations([{"timestamp": now}], "24h", now),
            extract_gi_forbidden_verbs(5, "24h", now),
            extract_gi_tool_denials(10, 50, "24h", now),
            extract_gi_artifact_failures(2, 10, "24h", now),
            extract_od_drcp_rate(5, 100, "24h", now),
            extract_od_diggi_corrections(3, "24h", now),
            extract_od_replay_denials(2, "24h", now),
            extract_od_envelope_violations(3, "24h", now),
            extract_od_escalation_recoveries(5, 10, "24h", now),
            extract_sd_drift_count([{"timestamp": now}], "24h", now),
            extract_sd_fingerprint_changes(2, "7d", now),
            extract_sd_boot_failures(1, 5, "7d", now),
            extract_sd_manifest_deltas(3, "7d", now),
            extract_sd_freshness_violation(now - timedelta(hours=12), now),
        ]

        for fv in extractors_and_results:
            if fv.value is not None:
                assert 0.0 <= fv.value <= 1.0, f"{fv.feature_id} out of bounds"
