# tests/risk/test_tri_engine.py
"""
Unit tests for TRI Engine.

Validates:
- Deterministic output (same inputs → same output)
- Bounded output [0.0, 1.0]
- All 15 features computed or null
- Confidence band always present
- Advisory-only flag enforced
- No governance imports in risk code

Author: MAGGIE (GID-10) — PAC-MAGGIE-RISK-IMPL-01
"""

from datetime import datetime, timedelta

import pytest

from core.risk.tri_engine import EventSummary, TRIEngine, create_empty_event_summary, demo_tri_computation
from core.risk.types import FeatureID, RiskDomain, TRIResult


class TestTRIEngineDeterminism:
    """Tests for deterministic computation."""

    def test_same_inputs_same_output(self) -> None:
        """Identical inputs should produce identical outputs."""
        now = datetime(2025, 12, 17, 12, 0, 0)
        window_start = now - timedelta(hours=24)

        events = EventSummary(
            window_start=window_start,
            window_end=now,
            total_decisions=100,
            denied_decisions=5,
            last_event_time=now,
            gameday_passing=130,
            gameday_total=133,
        )

        engine = TRIEngine()
        result1 = engine.compute(events, now)
        result2 = engine.compute(events, now)

        assert result1.tri == result2.tri
        assert result1.confidence.lower == result2.confidence.lower
        assert result1.confidence.upper == result2.confidence.upper
        assert result1.tier == result2.tier

    def test_bit_stable_across_calls(self) -> None:
        """TRI should be bit-stable across multiple calls."""
        now = datetime(2025, 12, 17, 12, 0, 0)
        events = create_empty_event_summary(24, now)
        events = EventSummary(
            window_start=events.window_start,
            window_end=events.window_end,
            total_decisions=50,
            denied_decisions=3,
            last_event_time=now - timedelta(hours=1),
        )

        engine = TRIEngine()
        results = [engine.compute(events, now) for _ in range(10)]

        first_tri = results[0].tri
        for r in results[1:]:
            assert r.tri == first_tri


class TestTRIEngineBounds:
    """Tests for output bounds."""

    def test_tri_bounded_zero_to_one(self) -> None:
        """TRI should always be in [0.0, 1.0]."""
        now = datetime.utcnow()
        engine = TRIEngine()

        # Test with various extreme inputs
        test_cases = [
            # Empty events (baseline)
            create_empty_event_summary(24, now),
            # High denial rate
            EventSummary(
                window_start=now - timedelta(hours=24),
                window_end=now,
                total_decisions=100,
                denied_decisions=100,
                last_event_time=now,
            ),
            # Many violations
            EventSummary(
                window_start=now - timedelta(hours=24),
                window_end=now,
                scope_violations=[{"timestamp": now} for _ in range(50)],
                last_event_time=now,
            ),
        ]

        for events in test_cases:
            result = engine.compute(events, now)
            assert 0.0 <= result.tri <= 1.0, f"TRI out of bounds: {result.tri}"

    def test_confidence_band_bounded(self) -> None:
        """Confidence band should always be in [0.0, 1.0]."""
        now = datetime.utcnow()
        engine = TRIEngine()
        events = create_empty_event_summary(24, now)
        result = engine.compute(events, now)

        assert 0.0 <= result.confidence.lower <= result.confidence.upper <= 1.0


class TestTRIEngineFeatures:
    """Tests for feature computation."""

    def test_all_fifteen_features(self) -> None:
        """Should attempt to compute all 15 features."""
        now = datetime.utcnow()
        engine = TRIEngine()
        events = EventSummary(
            window_start=now - timedelta(hours=24),
            window_end=now,
            total_decisions=100,
            denied_decisions=5,
            total_operations=50,
            drcp_triggers=2,
            last_event_time=now,
        )
        result = engine.compute(events, now)

        # Count total features (computed + null)
        total_features = result.feature_count + len(result.null_features)
        assert total_features == 15

    def test_null_features_tracked(self) -> None:
        """Null features should be tracked in result."""
        now = datetime.utcnow()
        engine = TRIEngine()
        events = EventSummary(
            window_start=now - timedelta(hours=24),
            window_end=now,
            # Escalation recoveries requires escalations > 0
            escalations=0,
            escalation_recoveries=0,
            last_event_time=now,
        )
        result = engine.compute(events, now)

        # od_escalation_recoveries should be null
        assert FeatureID.OD_ESCALATION_RECOVERIES.value in result.null_features


class TestTRIEngineDomains:
    """Tests for domain score computation."""

    def test_all_three_domains(self) -> None:
        """Should compute scores for all three domains."""
        now = datetime.utcnow()
        engine = TRIEngine()
        events = create_empty_event_summary(24, now)
        result = engine.compute(events, now)

        assert len(result.domains) == 3
        assert RiskDomain.GOVERNANCE_INTEGRITY.value in result.domains
        assert RiskDomain.OPERATIONAL_DISCIPLINE.value in result.domains
        assert RiskDomain.SYSTEM_DRIFT.value in result.domains

    def test_domain_weights_applied(self) -> None:
        """Domain weights should be applied correctly."""
        now = datetime.utcnow()
        engine = TRIEngine()
        events = create_empty_event_summary(24, now)
        result = engine.compute(events, now)

        gi_domain = result.domains[RiskDomain.GOVERNANCE_INTEGRITY.value]
        od_domain = result.domains[RiskDomain.OPERATIONAL_DISCIPLINE.value]
        sd_domain = result.domains[RiskDomain.SYSTEM_DRIFT.value]

        assert gi_domain.weight == pytest.approx(0.40)
        assert od_domain.weight == pytest.approx(0.35)
        assert sd_domain.weight == pytest.approx(0.25)


class TestTRIEngineAdvisoryOnly:
    """Tests for advisory-only enforcement."""

    def test_advisory_only_always_true(self) -> None:
        """advisory_only flag should always be True."""
        now = datetime.utcnow()
        engine = TRIEngine()
        events = create_empty_event_summary(24, now)
        result = engine.compute(events, now)

        assert result.advisory_only is True

    def test_to_dict_includes_advisory_only(self) -> None:
        """Serialized output should include advisory_only."""
        now = datetime.utcnow()
        engine = TRIEngine()
        events = create_empty_event_summary(24, now)
        result = engine.compute(events, now)

        d = result.to_dict()
        assert "advisory_only" in d
        assert d["advisory_only"] is True


class TestTRIEngineConfidence:
    """Tests for confidence band computation."""

    def test_confidence_band_present(self) -> None:
        """Confidence band should always be present."""
        now = datetime.utcnow()
        engine = TRIEngine()
        events = create_empty_event_summary(24, now)
        result = engine.compute(events, now)

        assert result.confidence is not None
        assert result.confidence.lower is not None
        assert result.confidence.upper is not None

    def test_sparse_data_wide_band(self) -> None:
        """Sparse data should produce wide confidence band."""
        now = datetime.utcnow()
        engine = TRIEngine()
        events = EventSummary(
            window_start=now - timedelta(hours=24),
            window_end=now,
            total_decisions=5,
            last_event_time=now,
        )
        result = engine.compute(events, now)

        # Sparse data → wide band
        assert result.confidence.width > 0.2

    def test_rich_data_narrow_band(self) -> None:
        """Rich data should produce narrower confidence band."""
        now = datetime.utcnow()
        engine = TRIEngine()
        events = EventSummary(
            window_start=now - timedelta(hours=24),
            window_end=now,
            total_decisions=500,
            denied_decisions=25,
            total_operations=300,
            drcp_triggers=10,
            last_event_time=now,
            gameday_passing=133,
            gameday_total=133,
            bound_executions=200,
            total_executions=200,
        )
        result = engine.compute(events, now)

        # Rich data → narrower band
        assert result.confidence.width < 0.3


class TestTRIEngineRiskTiers:
    """Tests for risk tier assignment."""

    def test_tier_assigned(self) -> None:
        """Result should always have a tier."""
        now = datetime.utcnow()
        engine = TRIEngine()
        events = create_empty_event_summary(24, now)
        result = engine.compute(events, now)

        assert result.tier in ["MINIMAL", "LOW", "MODERATE", "HIGH", "CRITICAL"]

    def test_no_safe_tier(self) -> None:
        """No tier should be called 'safe'."""
        now = datetime.utcnow()
        engine = TRIEngine()

        # Test various scenarios
        for decisions in [0, 10, 50, 100]:
            for denials in range(0, decisions + 1, max(1, decisions // 4)):
                events = EventSummary(
                    window_start=now - timedelta(hours=24),
                    window_end=now,
                    total_decisions=decisions,
                    denied_decisions=denials,
                    last_event_time=now,
                )
                result = engine.compute(events, now)
                assert result.tier.lower() != "safe"


class TestTRIEngineDemo:
    """Tests for demo function."""

    def test_demo_returns_valid_dict(self) -> None:
        """Demo should return valid TRI result dict."""
        result = demo_tri_computation()

        assert isinstance(result, dict)
        assert "tri" in result
        assert "confidence" in result
        assert "tier" in result
        assert "advisory_only" in result
        assert result["advisory_only"] is True

    def test_demo_tri_in_bounds(self) -> None:
        """Demo TRI should be in valid range."""
        result = demo_tri_computation()
        assert 0.0 <= result["tri"] <= 1.0


class TestTRIEngineNoGovernanceImports:
    """Tests to verify risk module doesn't import governance."""

    def test_no_governance_in_types(self) -> None:
        """types.py should not import from core.governance."""
        import sys

        import core.risk.types as types_module

        # Check that no governance modules are in the module's namespace
        for name in dir(types_module):
            obj = getattr(types_module, name)
            if hasattr(obj, "__module__"):
                assert "governance" not in str(obj.__module__), f"{name} imports from governance"

    def test_no_governance_in_extractors(self) -> None:
        """feature_extractors.py should not import from core.governance."""
        import core.risk.feature_extractors as extractors_module

        for name in dir(extractors_module):
            obj = getattr(extractors_module, name)
            if hasattr(obj, "__module__"):
                assert "governance" not in str(obj.__module__), f"{name} imports from governance"

    def test_no_governance_in_trust_weights(self) -> None:
        """trust_weights.py should not import from core.governance."""
        import core.risk.trust_weights as tw_module

        for name in dir(tw_module):
            obj = getattr(tw_module, name)
            if hasattr(obj, "__module__"):
                assert "governance" not in str(obj.__module__), f"{name} imports from governance"


class TestContributionTable:
    """Tests for contribution table generation."""

    def test_contribution_table_generated(self) -> None:
        """Should generate contribution table."""
        now = datetime.utcnow()
        engine = TRIEngine()
        events = EventSummary(
            window_start=now - timedelta(hours=24),
            window_end=now,
            total_decisions=100,
            denied_decisions=10,
            total_operations=50,
            drcp_triggers=5,
            last_event_time=now,
        )
        result = engine.compute(events, now)
        table = result.contribution_table()

        assert len(table) == 15  # All features
        assert all(hasattr(row, "feature_name") for row in table)
        assert all(hasattr(row, "contribution") for row in table)

    def test_contribution_table_has_evidence(self) -> None:
        """Each row should have evidence description."""
        now = datetime.utcnow()
        engine = TRIEngine()
        events = EventSummary(
            window_start=now - timedelta(hours=24),
            window_end=now,
            total_decisions=100,
            denied_decisions=10,
            last_event_time=now,
        )
        result = engine.compute(events, now)
        table = result.contribution_table()

        for row in table:
            assert row.evidence is not None
            assert len(row.evidence) > 0
