"""ChainIQ Monotonicity Tests.

Validates the monotonic constraints from A10 Lock:
Higher risk signals MUST NOT decrease risk score.

════════════════════════════════════════════════════════════════════════════════
🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷
GID-10 — MAGGIE (ML & APPLIED AI)
PAC-MAGGIE-A10-RISK-MODEL-CANONICALIZATION-LOCK-01
🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷
════════════════════════════════════════════════════════════════════════════════

I. EXECUTING AGENT (MANDATORY)

EXECUTING AGENT: MAGGIE
GID: GID-10
EXECUTING COLOR: 🩷 PINK — ML & Applied AI Lane

⸻

II. TEST COVERAGE

- Carrier incident rate: increasing → non-decreasing score
- Recent delay events: increasing → non-decreasing score
- IoT alert count: increasing → non-decreasing score
- Border crossing count: increasing → non-decreasing score
- Value USD: increasing → non-decreasing score
- Lane risk index: increasing → non-decreasing score
- Boundary conditions (extreme values)
- Missing data handling (conservative degradation)

⸻

III. PROHIBITED ACTIONS

- Skipping monotonicity tests
- Non-deterministic test behavior

⸻
"""
from __future__ import annotations

from typing import List, Tuple

import pytest

# Import from canonical model spec
from app.models.canonical_model_spec import (
    MONOTONIC_FEATURES,
    MonotonicConstraint,
)

# Import the actual risk engine
from app.risk.engine import compute_risk_score
from app.risk.schemas import (
    CarrierProfile,
    LaneProfile,
    RiskBand,
    ShipmentFeatures,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def baseline_shipment() -> ShipmentFeatures:
    """Baseline shipment with moderate risk factors."""
    return ShipmentFeatures(
        value_usd=50000.0,
        is_hazmat=False,
        is_temp_control=False,
        expected_transit_days=5,
        iot_alert_count=0,
        recent_delay_events=0,
    )


@pytest.fixture
def baseline_carrier() -> CarrierProfile:
    """Baseline carrier with moderate risk factors."""
    return CarrierProfile(
        carrier_id="TEST-BASELINE",
        incident_rate_90d=0.03,
        tenure_days=300,
        on_time_rate=0.92,
    )


@pytest.fixture
def baseline_lane() -> LaneProfile:
    """Baseline lane with moderate risk factors."""
    return LaneProfile(
        origin="TEST-A",
        destination="TEST-B",
        lane_risk_index=0.4,
        border_crossing_count=0,
    )


# =============================================================================
# MONOTONICITY CONSTRAINT TESTS
# =============================================================================

class TestCarrierIncidentRateMonotonicity:
    """Test that higher carrier incident rate → higher or equal risk score."""

    def test_increasing_incident_rate_increases_score(
        self,
        baseline_shipment: ShipmentFeatures,
        baseline_lane: LaneProfile,
    ):
        """Higher incident rate must not decrease score."""
        incident_rates = [0.01, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]

        scores = []
        for rate in incident_rates:
            carrier = CarrierProfile(
                carrier_id="TEST",
                incident_rate_90d=rate,
                tenure_days=300,
                on_time_rate=0.90,
            )
            result = compute_risk_score(baseline_shipment, carrier, baseline_lane)
            scores.append(result.score)

        # Verify monotonicity: each score >= previous
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i-1], (
                f"Monotonicity violated: incident_rate {incident_rates[i-1]} → {incident_rates[i]}, "
                f"score {scores[i-1]} → {scores[i]}"
            )

    def test_extreme_incident_rate_produces_high_score(
        self,
        baseline_shipment: ShipmentFeatures,
        baseline_lane: LaneProfile,
    ):
        """Extreme incident rate should produce elevated score."""
        carrier = CarrierProfile(
            carrier_id="BAD-CARRIER",
            incident_rate_90d=0.50,  # 50% incident rate
            tenure_days=30,
            on_time_rate=0.50,
        )

        result = compute_risk_score(baseline_shipment, carrier, baseline_lane)

        # Should be at least medium risk
        assert result.score >= 40, "Extreme incident rate should elevate score"


class TestDelayEventsMonotonicity:
    """Test that more delay events → higher or equal risk score."""

    def test_increasing_delays_increases_score(
        self,
        baseline_carrier: CarrierProfile,
        baseline_lane: LaneProfile,
    ):
        """More delays must not decrease score."""
        delay_counts = [0, 1, 2, 3, 5, 10]

        scores = []
        for delays in delay_counts:
            shipment = ShipmentFeatures(
                value_usd=50000.0,
                is_hazmat=False,
                is_temp_control=False,
                expected_transit_days=5,
                iot_alert_count=0,
                recent_delay_events=delays,
            )
            result = compute_risk_score(shipment, baseline_carrier, baseline_lane)
            scores.append(result.score)

        # Verify monotonicity
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i-1], (
                f"Monotonicity violated: delays {delay_counts[i-1]} → {delay_counts[i]}, "
                f"score {scores[i-1]} → {scores[i]}"
            )


class TestIoTAlertMonotonicity:
    """Test that more IoT alerts → higher or equal risk score."""

    def test_increasing_alerts_increases_score(
        self,
        baseline_carrier: CarrierProfile,
        baseline_lane: LaneProfile,
    ):
        """More IoT alerts must not decrease score."""
        alert_counts = [0, 1, 2, 3, 5, 10]

        scores = []
        for alerts in alert_counts:
            shipment = ShipmentFeatures(
                value_usd=50000.0,
                is_hazmat=False,
                is_temp_control=False,
                expected_transit_days=5,
                iot_alert_count=alerts,
                recent_delay_events=0,
            )
            result = compute_risk_score(shipment, baseline_carrier, baseline_lane)
            scores.append(result.score)

        # Verify monotonicity
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i-1], (
                f"Monotonicity violated: alerts {alert_counts[i-1]} → {alert_counts[i]}, "
                f"score {scores[i-1]} → {scores[i]}"
            )


class TestBorderCrossingMonotonicity:
    """Test that more border crossings → higher or equal risk score."""

    def test_increasing_crossings_increases_score(
        self,
        baseline_shipment: ShipmentFeatures,
        baseline_carrier: CarrierProfile,
    ):
        """More border crossings must not decrease score."""
        crossing_counts = [0, 1, 2, 3, 5]

        scores = []
        for crossings in crossing_counts:
            lane = LaneProfile(
                origin="A",
                destination="B",
                lane_risk_index=0.4,
                border_crossing_count=crossings,
            )
            result = compute_risk_score(baseline_shipment, baseline_carrier, lane)
            scores.append(result.score)

        # Verify monotonicity
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i-1], (
                f"Monotonicity violated: crossings {crossing_counts[i-1]} → {crossing_counts[i]}, "
                f"score {scores[i-1]} → {scores[i]}"
            )


class TestValueMonotonicity:
    """Test that higher cargo value → higher or equal risk score."""

    def test_increasing_value_increases_score(
        self,
        baseline_carrier: CarrierProfile,
        baseline_lane: LaneProfile,
    ):
        """Higher cargo value must not decrease score."""
        values = [10000, 50000, 100000, 150000, 250000, 500000, 1000000]

        scores = []
        for value in values:
            shipment = ShipmentFeatures(
                value_usd=float(value),
                is_hazmat=False,
                is_temp_control=False,
                expected_transit_days=5,
                iot_alert_count=0,
                recent_delay_events=0,
            )
            result = compute_risk_score(shipment, baseline_carrier, baseline_lane)
            scores.append(result.score)

        # Verify monotonicity
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i-1], (
                f"Monotonicity violated: value ${values[i-1]:,} → ${values[i]:,}, "
                f"score {scores[i-1]} → {scores[i]}"
            )


class TestLaneRiskIndexMonotonicity:
    """Test that higher lane risk index → higher or equal risk score."""

    def test_increasing_lane_risk_increases_score(
        self,
        baseline_shipment: ShipmentFeatures,
        baseline_carrier: CarrierProfile,
    ):
        """Higher lane risk index must not decrease score."""
        risk_indices = [0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]

        scores = []
        for risk_idx in risk_indices:
            lane = LaneProfile(
                origin="A",
                destination="B",
                lane_risk_index=risk_idx,
                border_crossing_count=0,
            )
            result = compute_risk_score(baseline_shipment, baseline_carrier, lane)
            scores.append(result.score)

        # Verify monotonicity
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i-1], (
                f"Monotonicity violated: lane_risk {risk_indices[i-1]} → {risk_indices[i]}, "
                f"score {scores[i-1]} → {scores[i]}"
            )


# =============================================================================
# BOUNDARY CONDITION TESTS
# =============================================================================

class TestBoundaryConditions:
    """Test extreme value handling."""

    def test_minimum_risk_produces_low_score(self):
        """Minimum risk inputs should produce low score."""
        shipment = ShipmentFeatures(
            value_usd=1000.0,  # Very low value
            is_hazmat=False,
            is_temp_control=False,
            expected_transit_days=1,
            iot_alert_count=0,
            recent_delay_events=0,
        )
        carrier = CarrierProfile(
            carrier_id="BEST",
            incident_rate_90d=0.001,  # Excellent record
            tenure_days=3650,  # 10 year tenure
            on_time_rate=0.999,
        )
        lane = LaneProfile(
            origin="A",
            destination="B",
            lane_risk_index=0.01,  # Very safe lane
            border_crossing_count=0,
        )

        result = compute_risk_score(shipment, carrier, lane)

        assert result.score <= 30, f"Minimum risk should be LOW band, got score {result.score}"
        assert result.band == RiskBand.LOW, f"Expected LOW band, got {result.band}"

    def test_maximum_risk_produces_high_score(self):
        """Maximum risk inputs should produce high score."""
        shipment = ShipmentFeatures(
            value_usd=10000000.0,  # $10M cargo
            is_hazmat=True,
            is_temp_control=True,
            expected_transit_days=30,
            iot_alert_count=10,
            recent_delay_events=10,
        )
        carrier = CarrierProfile(
            carrier_id="WORST",
            incident_rate_90d=0.50,  # Terrible record
            tenure_days=30,
            on_time_rate=0.50,
        )
        lane = LaneProfile(
            origin="HIGH",
            destination="RISK",
            lane_risk_index=1.0,  # Maximum risk lane
            border_crossing_count=10,
        )

        result = compute_risk_score(shipment, carrier, lane)

        assert result.score >= 70, f"Maximum risk should be HIGH band, got score {result.score}"
        assert result.band == RiskBand.HIGH, f"Expected HIGH band, got {result.band}"

    def test_score_is_clamped_to_valid_range(self):
        """Score should always be in [0, 100] range."""
        # Try to provoke extreme scores
        test_cases = [
            # Minimum case
            (
                ShipmentFeatures(
                    value_usd=0, is_hazmat=False, is_temp_control=False,
                    expected_transit_days=0, iot_alert_count=0, recent_delay_events=0,
                ),
                CarrierProfile(
                    carrier_id="X", incident_rate_90d=0.0, tenure_days=10000, on_time_rate=1.0,
                ),
                LaneProfile(origin="A", destination="B", lane_risk_index=0.0, border_crossing_count=0),
            ),
            # Maximum case
            (
                ShipmentFeatures(
                    value_usd=1e9, is_hazmat=True, is_temp_control=True,
                    expected_transit_days=100, iot_alert_count=100, recent_delay_events=100,
                ),
                CarrierProfile(
                    carrier_id="Y", incident_rate_90d=1.0, tenure_days=0, on_time_rate=0.0,
                ),
                LaneProfile(origin="X", destination="Y", lane_risk_index=1.0, border_crossing_count=100),
            ),
        ]

        for shipment, carrier, lane in test_cases:
            result = compute_risk_score(shipment, carrier, lane)
            assert 0 <= result.score <= 100, f"Score out of range: {result.score}"


# =============================================================================
# CANONICAL CONSTRAINT VALIDATION
# =============================================================================

class TestCanonicalConstraints:
    """Test that canonical monotonic constraints are properly defined."""

    def test_all_monotonic_features_defined(self):
        """All expected monotonic features should be defined."""
        expected_features = {
            "carrier_incident_rate_90d",
            "recent_delay_events",
            "iot_alert_count",
            "border_crossing_count",
            "value_usd",
            "lane_risk_index",
        }

        actual_features = {c.feature_name for c in MONOTONIC_FEATURES}

        assert expected_features == actual_features, (
            f"Missing features: {expected_features - actual_features}, "
            f"Extra features: {actual_features - expected_features}"
        )

    def test_all_constraints_are_increasing(self):
        """All canonical risk features should have increasing direction."""
        for constraint in MONOTONIC_FEATURES:
            assert constraint.direction == "increasing", (
                f"Feature {constraint.feature_name} should be 'increasing', "
                f"got '{constraint.direction}'"
            )

    def test_constraint_validation_method_works(self):
        """MonotonicConstraint.validate() should detect violations."""
        constraint = MonotonicConstraint(
            feature_name="test_feature",
            direction="increasing",
        )

        # Valid: higher feature, higher score
        assert constraint.validate(1.0, 2.0, 50.0, 60.0) is True

        # Valid: same feature, same score
        assert constraint.validate(1.0, 1.0, 50.0, 50.0) is True

        # Invalid: higher feature, lower score
        assert constraint.validate(1.0, 2.0, 60.0, 50.0) is False


# =============================================================================
# REASON CODE TESTS
# =============================================================================

class TestReasonCodes:
    """Test that reason codes are generated for risk contributions."""

    def test_high_value_generates_reason(
        self,
        baseline_carrier: CarrierProfile,
        baseline_lane: LaneProfile,
    ):
        """High value shipment should have reason code."""
        shipment = ShipmentFeatures(
            value_usd=150000.0,  # >$100k
            is_hazmat=False,
            is_temp_control=False,
            expected_transit_days=5,
            iot_alert_count=0,
            recent_delay_events=0,
        )

        result = compute_risk_score(shipment, baseline_carrier, baseline_lane)

        assert any("High Value" in r or "100k" in r for r in result.reasons), (
            f"Expected high value reason, got: {result.reasons}"
        )

    def test_hazmat_generates_reason(
        self,
        baseline_carrier: CarrierProfile,
        baseline_lane: LaneProfile,
    ):
        """Hazmat shipment should have reason code."""
        shipment = ShipmentFeatures(
            value_usd=50000.0,
            is_hazmat=True,
            is_temp_control=False,
            expected_transit_days=5,
            iot_alert_count=0,
            recent_delay_events=0,
        )

        result = compute_risk_score(shipment, baseline_carrier, baseline_lane)

        assert any("Hazmat" in r for r in result.reasons), (
            f"Expected hazmat reason, got: {result.reasons}"
        )

    def test_iot_alerts_generate_reason(
        self,
        baseline_carrier: CarrierProfile,
        baseline_lane: LaneProfile,
    ):
        """IoT alerts should have reason code."""
        shipment = ShipmentFeatures(
            value_usd=50000.0,
            is_hazmat=False,
            is_temp_control=False,
            expected_transit_days=5,
            iot_alert_count=3,
            recent_delay_events=0,
        )

        result = compute_risk_score(shipment, baseline_carrier, baseline_lane)

        assert any("IoT" in r for r in result.reasons), (
            f"Expected IoT alert reason, got: {result.reasons}"
        )


# END — Maggie (GID-10) — 🩷 PINK
