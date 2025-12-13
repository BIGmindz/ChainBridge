# app/risk/tests/test_glassbox_sanity.py
"""
ChainIQ Glass-Box Sanity Tests

Author: MAGGIE (GID-10) - ML & Applied AI Lead

Purpose:
    Protect the "glass-box-only final scoring" doctrine with minimal,
    deterministic invariant tests. These tests ensure:

    1. Score bounds: All scores are within [0, 100]
    2. Missing fields: No crashes on incomplete input
    3. Monotonic risk ordering: Higher risk inputs yield >= scores than low-risk

Design Principles:
    - Deterministic: Same input → Same output (no randomness)
    - Glass-box: Only test interpretable, rule-based models
    - Minimal: Focus on invariants, not implementation details
"""
from __future__ import annotations

import pytest

from app.risk.engine import compute_risk_score
from app.risk.glassbox_model_v0 import score_shipment_risk
from app.risk.schemas import CarrierProfile, LaneProfile, ShipmentFeatures

# =============================================================================
# TEST FIXTURES: LOW/HIGH RISK SYNTHETIC INPUTS
# =============================================================================


@pytest.fixture
def low_risk_shipment_v0() -> dict:
    """Minimal risk shipment for glassbox v0."""
    return {
        "origin_country": "US",
        "destination_country": "CA",
        "amount": 5000,  # Small amount
    }


@pytest.fixture
def high_risk_shipment_v0() -> dict:
    """Maximum risk shipment for glassbox v0."""
    return {
        "origin_country": "XYZ",  # High-risk country
        "destination_country": "XYZ",
        "amount": 500000,  # Large amount
    }


@pytest.fixture
def low_risk_context() -> dict:
    """Clean history context."""
    return {
        "has_disputes": False,
        "has_late_deliveries": False,
    }


@pytest.fixture
def high_risk_context() -> dict:
    """Bad history context."""
    return {
        "has_disputes": True,
        "has_late_deliveries": True,
    }


@pytest.fixture
def low_risk_shipment_v1() -> ShipmentFeatures:
    """Minimal risk shipment for v1 engine."""
    return ShipmentFeatures(
        value_usd=5000,
        is_hazmat=False,
        is_temp_control=False,
        expected_transit_days=3,
        iot_alert_count=0,
        recent_delay_events=0,
    )


@pytest.fixture
def high_risk_shipment_v1() -> ShipmentFeatures:
    """Maximum risk shipment for v1 engine."""
    return ShipmentFeatures(
        value_usd=500000,
        is_hazmat=True,
        is_temp_control=True,
        expected_transit_days=15,
        iot_alert_count=5,
        recent_delay_events=3,
    )


@pytest.fixture
def trusted_carrier() -> CarrierProfile:
    """Low-risk carrier profile."""
    return CarrierProfile(
        carrier_id="TRUSTED-001",
        incident_rate_90d=0.005,
        tenure_days=730,
        on_time_rate=0.98,
    )


@pytest.fixture
def risky_carrier() -> CarrierProfile:
    """High-risk carrier profile."""
    return CarrierProfile(
        carrier_id="RISKY-999",
        incident_rate_90d=0.15,
        tenure_days=30,
        on_time_rate=0.70,
    )


@pytest.fixture
def safe_lane() -> LaneProfile:
    """Low-risk lane profile."""
    return LaneProfile(
        origin="US",
        destination="CA",
        lane_risk_index=0.1,
        border_crossing_count=1,
    )


@pytest.fixture
def dangerous_lane() -> LaneProfile:
    """High-risk lane profile."""
    return LaneProfile(
        origin="CONFLICT_ZONE",
        destination="SANCTIONS_COUNTRY",
        lane_risk_index=0.9,
        border_crossing_count=5,
    )


# =============================================================================
# GLASSBOX V0 SANITY TESTS
# =============================================================================


class TestGlassboxV0Bounds:
    """Score bound invariants for glassbox_model_v0."""

    def test_score_within_0_100_low_risk(self, low_risk_shipment_v0, low_risk_context):
        """Score must be in [0, 100] for low-risk input."""
        result = score_shipment_risk(low_risk_shipment_v0, low_risk_context)
        assert 0 <= result["risk_score"] <= 100, f"Score {result['risk_score']} out of bounds"

    def test_score_within_0_100_high_risk(self, high_risk_shipment_v0, high_risk_context):
        """Score must be in [0, 100] for high-risk input."""
        result = score_shipment_risk(high_risk_shipment_v0, high_risk_context)
        assert 0 <= result["risk_score"] <= 100, f"Score {result['risk_score']} out of bounds"

    def test_risk_band_is_valid(self, low_risk_shipment_v0, low_risk_context):
        """Risk band must be one of the valid values."""
        result = score_shipment_risk(low_risk_shipment_v0, low_risk_context)
        assert result["risk_band"] in {"LOW", "MEDIUM", "HIGH"}, f"Invalid band: {result['risk_band']}"


class TestGlassboxV0MissingFields:
    """Missing field handling for glassbox_model_v0."""

    def test_empty_shipment_no_crash(self):
        """Empty shipment dict should not crash."""
        result = score_shipment_risk({}, {})
        assert 0 <= result["risk_score"] <= 100
        assert result["risk_band"] in {"LOW", "MEDIUM", "HIGH"}

    def test_missing_amount_no_crash(self):
        """Missing amount should not crash."""
        shipment = {"origin_country": "US", "destination_country": "CA"}
        result = score_shipment_risk(shipment, {})
        assert 0 <= result["risk_score"] <= 100

    def test_none_context_values_no_crash(self):
        """None values in context should not crash."""
        shipment = {"amount": 10000}
        context = {"has_disputes": None, "has_late_deliveries": None}
        result = score_shipment_risk(shipment, context)
        assert 0 <= result["risk_score"] <= 100


class TestGlassboxV0Monotonicity:
    """Monotonic risk ordering for glassbox_model_v0."""

    def test_high_risk_shipment_scores_higher(self, low_risk_shipment_v0, high_risk_shipment_v0, low_risk_context):
        """High-risk shipment should score >= low-risk shipment."""
        low_result = score_shipment_risk(low_risk_shipment_v0, low_risk_context)
        high_result = score_shipment_risk(high_risk_shipment_v0, low_risk_context)
        assert high_result["risk_score"] >= low_result["risk_score"], (
            f"Monotonicity violation: high_risk={high_result['risk_score']} < " f"low_risk={low_result['risk_score']}"
        )

    def test_bad_history_scores_higher(self, low_risk_shipment_v0, low_risk_context, high_risk_context):
        """Bad history context should score >= clean history."""
        clean_result = score_shipment_risk(low_risk_shipment_v0, low_risk_context)
        bad_result = score_shipment_risk(low_risk_shipment_v0, high_risk_context)
        assert bad_result["risk_score"] >= clean_result["risk_score"], (
            f"Monotonicity violation: bad_history={bad_result['risk_score']} < " f"clean_history={clean_result['risk_score']}"
        )

    def test_disputes_increase_score(self, low_risk_shipment_v0):
        """Adding disputes should increase or maintain score."""
        no_disputes = score_shipment_risk(low_risk_shipment_v0, {"has_disputes": False})
        with_disputes = score_shipment_risk(low_risk_shipment_v0, {"has_disputes": True})
        assert with_disputes["risk_score"] >= no_disputes["risk_score"]


# =============================================================================
# V1 ENGINE SANITY TESTS
# =============================================================================


class TestEngineV1Bounds:
    """Score bound invariants for v1 engine."""

    def test_score_within_0_100_low_risk(self, low_risk_shipment_v1, trusted_carrier, safe_lane):
        """Score must be in [0, 100] for low-risk input."""
        result = compute_risk_score(low_risk_shipment_v1, trusted_carrier, safe_lane)
        assert 0 <= result.score <= 100, f"Score {result.score} out of bounds"

    def test_score_within_0_100_high_risk(self, high_risk_shipment_v1, risky_carrier, dangerous_lane):
        """Score must be in [0, 100] for high-risk input."""
        result = compute_risk_score(high_risk_shipment_v1, risky_carrier, dangerous_lane)
        assert 0 <= result.score <= 100, f"Score {result.score} out of bounds"

    def test_risk_band_is_valid(self, low_risk_shipment_v1, trusted_carrier, safe_lane):
        """Risk band must be a valid RiskBand enum."""
        from app.risk.schemas import RiskBand

        result = compute_risk_score(low_risk_shipment_v1, trusted_carrier, safe_lane)
        assert result.band in RiskBand, f"Invalid band: {result.band}"


class TestEngineV1Monotonicity:
    """Monotonic risk ordering for v1 engine."""

    def test_high_risk_shipment_scores_higher(
        self,
        low_risk_shipment_v1,
        high_risk_shipment_v1,
        trusted_carrier,
        safe_lane,
    ):
        """High-risk shipment should score >= low-risk shipment."""
        low_result = compute_risk_score(low_risk_shipment_v1, trusted_carrier, safe_lane)
        high_result = compute_risk_score(high_risk_shipment_v1, trusted_carrier, safe_lane)
        assert high_result.score >= low_result.score, f"Monotonicity violation: high_risk={high_result.score} < low_risk={low_result.score}"

    def test_risky_carrier_scores_higher(
        self,
        low_risk_shipment_v1,
        trusted_carrier,
        risky_carrier,
        safe_lane,
    ):
        """Risky carrier should score >= trusted carrier."""
        trusted_result = compute_risk_score(low_risk_shipment_v1, trusted_carrier, safe_lane)
        risky_result = compute_risk_score(low_risk_shipment_v1, risky_carrier, safe_lane)
        assert risky_result.score >= trusted_result.score, (
            f"Monotonicity violation: risky_carrier={risky_result.score} < " f"trusted_carrier={trusted_result.score}"
        )

    def test_dangerous_lane_scores_higher(
        self,
        low_risk_shipment_v1,
        trusted_carrier,
        safe_lane,
        dangerous_lane,
    ):
        """Dangerous lane should score >= safe lane."""
        safe_result = compute_risk_score(low_risk_shipment_v1, trusted_carrier, safe_lane)
        dangerous_result = compute_risk_score(low_risk_shipment_v1, trusted_carrier, dangerous_lane)
        assert dangerous_result.score >= safe_result.score, (
            f"Monotonicity violation: dangerous_lane={dangerous_result.score} < " f"safe_lane={safe_result.score}"
        )


class TestEngineV1ModelVersion:
    """Model version traceability for v1 engine."""

    def test_model_version_is_set(self, low_risk_shipment_v1, trusted_carrier, safe_lane):
        """Model version must be populated for audit trail."""
        result = compute_risk_score(low_risk_shipment_v1, trusted_carrier, safe_lane)
        assert result.model_version is not None, "Model version must be set"
        assert len(result.model_version) > 0, "Model version must not be empty"


class TestEngineV1Determinism:
    """Deterministic output for v1 engine."""

    def test_same_input_same_output(self, low_risk_shipment_v1, trusted_carrier, safe_lane):
        """Same input must produce identical output."""
        r1 = compute_risk_score(low_risk_shipment_v1, trusted_carrier, safe_lane)
        r2 = compute_risk_score(low_risk_shipment_v1, trusted_carrier, safe_lane)
        assert r1.score == r2.score, f"Non-deterministic: {r1.score} != {r2.score}"
        assert r1.band == r2.band
        assert r1.reasons == r2.reasons
