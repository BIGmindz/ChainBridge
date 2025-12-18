# tests/risk/test_types.py
"""
Unit tests for TRI type definitions.

Validates:
- Immutability
- Bounds checking
- Serialization
- Risk tier mapping

Author: MAGGIE (GID-10) — PAC-MAGGIE-RISK-IMPL-01
"""

from datetime import datetime

import pytest

from core.risk.types import (
    DOMAIN_WEIGHTS,
    FEATURE_DOMAINS,
    FEATURE_WEIGHTS,
    RISK_TIERS,
    ConfidenceBand,
    ContributionRow,
    DomainScore,
    FeatureID,
    FeatureValue,
    RiskDomain,
    TRIResult,
    TrustWeights,
    get_risk_tier,
)


class TestFeatureValue:
    """Tests for FeatureValue dataclass."""

    def test_valid_feature_value(self) -> None:
        """Valid feature values should be accepted."""
        fv = FeatureValue(
            feature_id=FeatureID.GI_DENIAL_RATE,
            value=0.5,
            window="24h",
            sample_count=100,
            last_seen=datetime.utcnow(),
        )
        assert fv.value == 0.5
        assert fv.window == "24h"

    def test_null_value_allowed(self) -> None:
        """Null feature values should be allowed."""
        fv = FeatureValue(
            feature_id=FeatureID.GI_DENIAL_RATE,
            value=None,
            window="24h",
            sample_count=0,
            last_seen=None,
        )
        assert fv.value is None

    def test_value_below_zero_rejected(self) -> None:
        """Values below 0.0 should be rejected."""
        with pytest.raises(ValueError, match="must be in"):
            FeatureValue(
                feature_id=FeatureID.GI_DENIAL_RATE,
                value=-0.1,
                window="24h",
                sample_count=100,
                last_seen=None,
            )

    def test_value_above_one_rejected(self) -> None:
        """Values above 1.0 should be rejected."""
        with pytest.raises(ValueError, match="must be in"):
            FeatureValue(
                feature_id=FeatureID.GI_DENIAL_RATE,
                value=1.1,
                window="24h",
                sample_count=100,
                last_seen=None,
            )

    def test_boundary_values_accepted(self) -> None:
        """Boundary values 0.0 and 1.0 should be accepted."""
        fv_zero = FeatureValue(
            feature_id=FeatureID.GI_DENIAL_RATE,
            value=0.0,
            window="24h",
            sample_count=100,
            last_seen=None,
        )
        assert fv_zero.value == 0.0

        fv_one = FeatureValue(
            feature_id=FeatureID.GI_SCOPE_VIOLATIONS,
            value=1.0,
            window="24h",
            sample_count=100,
            last_seen=None,
        )
        assert fv_one.value == 1.0


class TestConfidenceBand:
    """Tests for ConfidenceBand dataclass."""

    def test_valid_band(self) -> None:
        """Valid confidence bands should be accepted."""
        band = ConfidenceBand(lower=0.2, upper=0.4)
        assert band.lower == 0.2
        assert band.upper == 0.4
        assert band.width == pytest.approx(0.2)

    def test_lower_above_upper_rejected(self) -> None:
        """Lower bound above upper should be rejected."""
        with pytest.raises(ValueError, match="Invalid confidence band"):
            ConfidenceBand(lower=0.5, upper=0.3)

    def test_out_of_bounds_rejected(self) -> None:
        """Values outside [0, 1] should be rejected."""
        with pytest.raises(ValueError):
            ConfidenceBand(lower=-0.1, upper=0.5)

        with pytest.raises(ValueError):
            ConfidenceBand(lower=0.5, upper=1.1)


class TestTrustWeights:
    """Tests for TrustWeights dataclass."""

    def test_valid_weights(self) -> None:
        """Valid trust weights should be accepted."""
        tw = TrustWeights(
            freshness=1.0,
            gameday=1.2,
            evidence=1.5,
            density=2.0,
        )
        assert tw.freshness == 1.0
        assert tw.gameday == 1.2

    def test_composite_geometric_mean(self) -> None:
        """Composite should be geometric mean of all weights."""
        tw = TrustWeights(
            freshness=1.0,
            gameday=1.0,
            evidence=1.0,
            density=1.0,
        )
        assert tw.composite == pytest.approx(1.0)

        tw2 = TrustWeights(
            freshness=2.0,
            gameday=2.0,
            evidence=2.0,
            density=2.0,
        )
        assert tw2.composite == pytest.approx(2.0)

    def test_weight_below_one_rejected(self) -> None:
        """Weights below 1.0 should be rejected."""
        with pytest.raises(ValueError, match="must be in"):
            TrustWeights(
                freshness=0.9,
                gameday=1.0,
                evidence=1.0,
                density=1.0,
            )

    def test_weight_above_two_rejected(self) -> None:
        """Weights above 2.0 should be rejected."""
        with pytest.raises(ValueError, match="must be in"):
            TrustWeights(
                freshness=1.0,
                gameday=2.1,
                evidence=1.0,
                density=1.0,
            )


class TestRiskTiers:
    """Tests for risk tier mapping."""

    def test_tier_boundaries(self) -> None:
        """Test tier assignment at boundaries."""
        assert get_risk_tier(0.0) == "MINIMAL"
        assert get_risk_tier(0.19) == "MINIMAL"
        assert get_risk_tier(0.20) == "LOW"
        assert get_risk_tier(0.39) == "LOW"
        assert get_risk_tier(0.40) == "MODERATE"
        assert get_risk_tier(0.59) == "MODERATE"
        assert get_risk_tier(0.60) == "HIGH"
        assert get_risk_tier(0.79) == "HIGH"
        assert get_risk_tier(0.80) == "CRITICAL"
        assert get_risk_tier(1.0) == "CRITICAL"

    def test_no_safe_tier(self) -> None:
        """Verify no tier is called 'safe' (per governance contract)."""
        all_tiers = [tier for _, tier in RISK_TIERS]
        assert "SAFE" not in all_tiers
        assert "safe" not in [t.lower() for t in all_tiers]


class TestTRIResult:
    """Tests for TRIResult dataclass."""

    def test_advisory_only_enforced(self) -> None:
        """advisory_only must always be True."""
        now = datetime.utcnow()
        domain_score = DomainScore(
            domain=RiskDomain.GOVERNANCE_INTEGRITY,
            score=0.3,
            weight=0.4,
            features=(),
            null_count=0,
        )

        # Should work with advisory_only=True (default)
        result = TRIResult(
            tri=0.3,
            confidence=ConfidenceBand(lower=0.2, upper=0.4),
            tier="LOW",
            domains={RiskDomain.GOVERNANCE_INTEGRITY.value: domain_score},
            trust_weights=TrustWeights(freshness=1.0, gameday=1.0, evidence=1.0, density=1.0),
            computed_at=now,
            window="24h",
            event_count=100,
            feature_count=15,
            null_features=[],
        )
        assert result.advisory_only is True

    def test_to_dict_serialization(self) -> None:
        """to_dict should produce valid JSON-serializable dict."""
        now = datetime.utcnow()
        domain_score = DomainScore(
            domain=RiskDomain.GOVERNANCE_INTEGRITY,
            score=0.3,
            weight=0.4,
            features=(),
            null_count=0,
        )

        result = TRIResult(
            tri=0.3,
            confidence=ConfidenceBand(lower=0.2, upper=0.4),
            tier="LOW",
            domains={RiskDomain.GOVERNANCE_INTEGRITY.value: domain_score},
            trust_weights=TrustWeights(freshness=1.0, gameday=1.0, evidence=1.0, density=1.0),
            computed_at=now,
            window="24h",
            event_count=100,
            feature_count=15,
            null_features=[],
        )

        d = result.to_dict()
        assert d["tri"] == 0.3
        assert d["tier"] == "LOW"
        assert d["advisory_only"] is True
        assert "confidence" in d
        assert "domains" in d
        assert "trust_weights" in d


class TestFeatureDomainMapping:
    """Tests for feature-domain relationships."""

    def test_all_features_have_domain(self) -> None:
        """Every feature ID should map to a domain."""
        for feature_id in FeatureID:
            assert feature_id in FEATURE_DOMAINS

    def test_all_features_have_weight(self) -> None:
        """Every feature ID should have a weight."""
        for feature_id in FeatureID:
            assert feature_id in FEATURE_WEIGHTS

    def test_domain_weights_sum_to_one(self) -> None:
        """Domain weights should sum to 1.0."""
        total = sum(DOMAIN_WEIGHTS.values())
        assert total == pytest.approx(1.0)

    def test_feature_weights_per_domain_sum_correctly(self) -> None:
        """Feature weights within each domain should sum to 1.0."""
        for domain in RiskDomain:
            domain_features = [fid for fid, d in FEATURE_DOMAINS.items() if d == domain]
            total_weight = sum(FEATURE_WEIGHTS[fid] for fid in domain_features)
            assert total_weight == pytest.approx(1.0), f"Domain {domain.value}"

    def test_fifteen_features_total(self) -> None:
        """Should have exactly 15 features."""
        assert len(FeatureID) == 15

    def test_five_features_per_domain(self) -> None:
        """Each domain should have exactly 5 features."""
        for domain in RiskDomain:
            count = sum(1 for d in FEATURE_DOMAINS.values() if d == domain)
            assert count == 5, f"Domain {domain.value} has {count} features"
