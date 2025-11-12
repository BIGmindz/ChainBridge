"""
Unit tests for should_release_now() - Smart Settlements release decision logic.

Tests the risk-based payment release strategy:
- LOW risk (0.0-0.33): IMMEDIATE for all events
- MEDIUM risk (0.33-0.67): IMMEDIATE for POD_CONFIRMED, DELAYED for others
- HIGH risk (0.67-1.0): MANUAL_REVIEW for POD/CLAIM, PENDING for PICKUP
"""

from app.payment_rails import should_release_now, ReleaseStrategy


class TestLowRiskReleaseBehavior:
    """Test should_release_now() for LOW-risk scores (0.0-0.33)."""

    def test_low_risk_pickup_confirmed_immediate(self):
        """LOW-risk PICKUP_CONFIRMED should release IMMEDIATE."""
        result = should_release_now(0.15, "PICKUP_CONFIRMED")
        assert result == ReleaseStrategy.IMMEDIATE

    def test_low_risk_pod_confirmed_immediate(self):
        """LOW-risk POD_CONFIRMED should release IMMEDIATE."""
        result = should_release_now(0.15, "POD_CONFIRMED")
        assert result == ReleaseStrategy.IMMEDIATE

    def test_low_risk_claim_window_closed_immediate(self):
        """LOW-risk CLAIM_WINDOW_CLOSED should release IMMEDIATE."""
        result = should_release_now(0.15, "CLAIM_WINDOW_CLOSED")
        assert result == ReleaseStrategy.IMMEDIATE

    def test_low_risk_boundary_zero(self):
        """LOW-risk boundary at 0.0 should release IMMEDIATE."""
        result = should_release_now(0.0, "POD_CONFIRMED")
        assert result == ReleaseStrategy.IMMEDIATE

    def test_low_risk_boundary_just_below_medium(self):
        """LOW-risk just below MEDIUM boundary (0.33) should release IMMEDIATE."""
        result = should_release_now(0.32, "PICKUP_CONFIRMED")
        assert result == ReleaseStrategy.IMMEDIATE


class TestMediumRiskReleaseBehavior:
    """Test should_release_now() for MEDIUM-risk scores (0.33-0.67)."""

    def test_medium_risk_pickup_confirmed_delayed(self):
        """MEDIUM-risk PICKUP_CONFIRMED should be DELAYED."""
        result = should_release_now(0.50, "PICKUP_CONFIRMED")
        assert result == ReleaseStrategy.DELAYED

    def test_medium_risk_pod_confirmed_immediate(self):
        """MEDIUM-risk POD_CONFIRMED should release IMMEDIATE."""
        result = should_release_now(0.50, "POD_CONFIRMED")
        assert result == ReleaseStrategy.IMMEDIATE

    def test_medium_risk_claim_window_closed_delayed(self):
        """MEDIUM-risk CLAIM_WINDOW_CLOSED should be DELAYED."""
        result = should_release_now(0.50, "CLAIM_WINDOW_CLOSED")
        assert result == ReleaseStrategy.DELAYED

    def test_medium_risk_boundary_at_low_threshold(self):
        """MEDIUM-risk at LOW boundary (0.33) should be DELAYED for non-POD."""
        result = should_release_now(0.33, "PICKUP_CONFIRMED")
        assert result == ReleaseStrategy.DELAYED

    def test_medium_risk_boundary_below_high_threshold(self):
        """MEDIUM-risk just below HIGH boundary (0.67) should be DELAYED for non-POD."""
        result = should_release_now(0.66, "CLAIM_WINDOW_CLOSED")
        assert result == ReleaseStrategy.DELAYED

    def test_medium_risk_pod_confirmed_boundary(self):
        """MEDIUM-risk POD_CONFIRMED at boundary (0.33) should be IMMEDIATE."""
        result = should_release_now(0.33, "POD_CONFIRMED")
        assert result == ReleaseStrategy.IMMEDIATE


class TestHighRiskReleaseBehavior:
    """Test should_release_now() for HIGH-risk scores (0.67-1.0)."""

    def test_high_risk_pickup_confirmed_pending(self):
        """HIGH-risk PICKUP_CONFIRMED should be PENDING."""
        result = should_release_now(0.85, "PICKUP_CONFIRMED")
        assert result == ReleaseStrategy.PENDING

    def test_high_risk_pod_confirmed_manual_review(self):
        """HIGH-risk POD_CONFIRMED should require MANUAL_REVIEW."""
        result = should_release_now(0.85, "POD_CONFIRMED")
        assert result == ReleaseStrategy.MANUAL_REVIEW

    def test_high_risk_claim_window_closed_manual_review(self):
        """HIGH-risk CLAIM_WINDOW_CLOSED should require MANUAL_REVIEW."""
        result = should_release_now(0.85, "CLAIM_WINDOW_CLOSED")
        assert result == ReleaseStrategy.MANUAL_REVIEW

    def test_high_risk_boundary_at_threshold(self):
        """HIGH-risk at boundary (0.67) should require MANUAL_REVIEW for POD."""
        result = should_release_now(0.67, "POD_CONFIRMED")
        assert result == ReleaseStrategy.MANUAL_REVIEW

    def test_high_risk_boundary_maximum(self):
        """HIGH-risk at maximum (1.0) should require MANUAL_REVIEW for POD."""
        result = should_release_now(1.0, "POD_CONFIRMED")
        assert result == ReleaseStrategy.MANUAL_REVIEW

    def test_high_risk_pickup_at_boundary(self):
        """HIGH-risk PICKUP_CONFIRMED at boundary (0.67) should be PENDING."""
        result = should_release_now(0.67, "PICKUP_CONFIRMED")
        assert result == ReleaseStrategy.PENDING


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions for should_release_now()."""

    def test_exact_medium_low_boundary(self):
        """Test exact boundary between LOW and MEDIUM (0.33)."""
        # At exactly 0.33, should enter MEDIUM tier
        result = should_release_now(0.33, "PICKUP_CONFIRMED")
        assert result == ReleaseStrategy.DELAYED

    def test_exact_high_medium_boundary(self):
        """Test exact boundary between MEDIUM and HIGH (0.67)."""
        # At exactly 0.67, should enter HIGH tier
        result = should_release_now(0.67, "PICKUP_CONFIRMED")
        assert result == ReleaseStrategy.PENDING

    def test_risk_score_zero(self):
        """Test with risk_score of 0.0 (safest possible)."""
        result = should_release_now(0.0, "PICKUP_CONFIRMED")
        assert result == ReleaseStrategy.IMMEDIATE

    def test_risk_score_one(self):
        """Test with risk_score of 1.0 (riskiest possible)."""
        result = should_release_now(1.0, "CLAIM_WINDOW_CLOSED")
        assert result == ReleaseStrategy.MANUAL_REVIEW

    def test_risk_score_midpoint(self):
        """Test with risk_score at midpoint (0.5)."""
        result = should_release_now(0.5, "POD_CONFIRMED")
        assert result == ReleaseStrategy.IMMEDIATE


class TestEventTypeConsistency:
    """Test that event_type matching is case-insensitive and consistent."""

    def test_uppercase_event_types(self):
        """Test uppercase event type names."""
        assert should_release_now(0.15, "PICKUP_CONFIRMED") == ReleaseStrategy.IMMEDIATE
        assert should_release_now(0.15, "POD_CONFIRMED") == ReleaseStrategy.IMMEDIATE
        assert should_release_now(0.15, "CLAIM_WINDOW_CLOSED") == ReleaseStrategy.IMMEDIATE

    def test_medium_risk_pod_uppercase(self):
        """Test MEDIUM-risk with uppercase POD_CONFIRMED."""
        result = should_release_now(0.50, "POD_CONFIRMED")
        assert result == ReleaseStrategy.IMMEDIATE

    def test_high_risk_events_uppercase(self):
        """Test HIGH-risk with uppercase event types."""
        assert should_release_now(0.85, "PICKUP_CONFIRMED") == ReleaseStrategy.PENDING
        assert should_release_now(0.85, "POD_CONFIRMED") == ReleaseStrategy.MANUAL_REVIEW
        assert should_release_now(0.85, "CLAIM_WINDOW_CLOSED") == ReleaseStrategy.MANUAL_REVIEW


class TestRegressionAndCrossScenarios:
    """Cross-scenario regression tests to catch unexpected behavior."""

    def test_all_low_risk_events_consistent(self):
        """All LOW-risk events should consistently release IMMEDIATE."""
        risk_score = 0.1
        events = ["PICKUP_CONFIRMED", "POD_CONFIRMED", "CLAIM_WINDOW_CLOSED"]
        for event in events:
            result = should_release_now(risk_score, event)
            assert result == ReleaseStrategy.IMMEDIATE, f"Failed for event {event}"

    def test_all_high_risk_non_pickup_consistent(self):
        """All HIGH-risk non-PICKUP events should consistently require MANUAL_REVIEW."""
        risk_score = 0.9
        events = ["POD_CONFIRMED", "CLAIM_WINDOW_CLOSED"]
        for event in events:
            result = should_release_now(risk_score, event)
            assert result == ReleaseStrategy.MANUAL_REVIEW, f"Failed for event {event}"

    def test_multiple_calls_same_result(self):
        """Multiple calls with same parameters should return same result (deterministic)."""
        risk_score = 0.45
        event = "PICKUP_CONFIRMED"
        result1 = should_release_now(risk_score, event)
        result2 = should_release_now(risk_score, event)
        result3 = should_release_now(risk_score, event)
        assert result1 == result2 == result3 == ReleaseStrategy.DELAYED
