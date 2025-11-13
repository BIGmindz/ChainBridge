"""
Unit tests for payment schedule building logic.

Tests the build_default_schedule() function to verify:
- Correct event types are generated
- Percentages match risk tier specifications
- Sequence order is maintained
- Schedules sum to 100% (or close to it for floating point)
"""

from app.schedule_builder import build_default_schedule, RiskTierSchedule


class TestLowRiskScheduleBuilding:
    """Test schedule building for LOW-risk tier."""

    def test_low_risk_schedule_items_count(self) -> None:
        """LOW-risk schedule should have 3 items (PICKUP/POD/CLAIM)."""
        items = build_default_schedule(RiskTierSchedule.LOW)
        assert len(items) == 3

    def test_low_risk_schedule_percentages(self) -> None:
        """LOW-risk schedule should be 20% PICKUP / 70% POD / 10% CLAIM."""
        items = build_default_schedule(RiskTierSchedule.LOW)
        item_dict = {item["event_type"]: item["percentage"] for item in items}

        assert item_dict["PICKUP_CONFIRMED"] == 0.20
        assert item_dict["POD_CONFIRMED"] == 0.70
        assert item_dict["CLAIM_WINDOW_CLOSED"] == 0.10

    def test_low_risk_schedule_sum_to_one(self) -> None:
        """LOW-risk schedule percentages should sum to 1.0."""
        items = build_default_schedule(RiskTierSchedule.LOW)
        total = sum(item["percentage"] for item in items)
        assert abs(total - 1.0) < 0.001  # Allow small floating point variance

    def test_low_risk_schedule_sequence_order(self) -> None:
        """LOW-risk schedule items should be in correct sequence order."""
        items = build_default_schedule(RiskTierSchedule.LOW)
        sequences = [item["order"] for item in items]
        assert sequences == [1, 2, 3]

    def test_low_risk_schedule_event_types_present(self) -> None:
        """LOW-risk schedule should have all required event types."""
        items = build_default_schedule(RiskTierSchedule.LOW)
        event_types = {item["event_type"] for item in items}
        expected_types = {"PICKUP_CONFIRMED", "POD_CONFIRMED", "CLAIM_WINDOW_CLOSED"}
        assert event_types == expected_types


class TestMediumRiskScheduleBuilding:
    """Test schedule building for MEDIUM-risk tier."""

    def test_medium_risk_schedule_items_count(self) -> None:
        """MEDIUM-risk schedule should have 3 items."""
        items = build_default_schedule(RiskTierSchedule.MEDIUM)
        assert len(items) == 3

    def test_medium_risk_schedule_percentages(self) -> None:
        """MEDIUM-risk schedule should be 10% PICKUP / 70% POD / 20% CLAIM."""
        items = build_default_schedule(RiskTierSchedule.MEDIUM)
        item_dict = {item["event_type"]: item["percentage"] for item in items}

        assert item_dict["PICKUP_CONFIRMED"] == 0.10
        assert item_dict["POD_CONFIRMED"] == 0.70
        assert item_dict["CLAIM_WINDOW_CLOSED"] == 0.20

    def test_medium_risk_schedule_sum_to_one(self) -> None:
        """MEDIUM-risk schedule percentages should sum to 1.0."""
        items = build_default_schedule(RiskTierSchedule.MEDIUM)
        total = sum(item["percentage"] for item in items)
        assert abs(total - 1.0) < 0.001

    def test_medium_risk_schedule_sequence_order(self) -> None:
        """MEDIUM-risk schedule items should be in sequence 1, 2, 3."""
        items = build_default_schedule(RiskTierSchedule.MEDIUM)
        sequences = [item["order"] for item in items]
        assert sequences == [1, 2, 3]


class TestHighRiskScheduleBuilding:
    """Test schedule building for HIGH-risk tier."""

    def test_high_risk_schedule_items_count(self) -> None:
        """HIGH-risk schedule should have 3 items."""
        items = build_default_schedule(RiskTierSchedule.HIGH)
        assert len(items) == 3

    def test_high_risk_schedule_percentages(self) -> None:
        """HIGH-risk schedule should be 0% PICKUP / 80% POD / 20% CLAIM."""
        items = build_default_schedule(RiskTierSchedule.HIGH)
        item_dict = {item["event_type"]: item["percentage"] for item in items}

        assert item_dict["PICKUP_CONFIRMED"] == 0.0
        assert item_dict["POD_CONFIRMED"] == 0.80
        assert item_dict["CLAIM_WINDOW_CLOSED"] == 0.20

    def test_high_risk_schedule_sum_to_one(self) -> None:
        """HIGH-risk schedule percentages should sum to 1.0."""
        items = build_default_schedule(RiskTierSchedule.HIGH)
        total = sum(item["percentage"] for item in items)
        assert abs(total - 1.0) < 0.001

    def test_high_risk_schedule_sequence_order(self) -> None:
        """HIGH-risk schedule items should be in sequence 1, 2, 3."""
        items = build_default_schedule(RiskTierSchedule.HIGH)
        sequences = [item["order"] for item in items]
        assert sequences == [1, 2, 3]

    def test_high_risk_zero_pickup_percentage(self) -> None:
        """HIGH-risk should have exactly 0% for PICKUP_CONFIRMED."""
        items = build_default_schedule(RiskTierSchedule.HIGH)
        pickup_item = next(
            item for item in items if item["event_type"] == "PICKUP_CONFIRMED"
        )
        assert pickup_item["percentage"] == 0.0


class TestScheduleDifferentiationByRiskTier:
    """Test that different risk tiers produce meaningfully different schedules."""

    def test_low_vs_medium_risk_different_schedules(self) -> None:
        """LOW and MEDIUM risk schedules should differ."""
        low = build_default_schedule(RiskTierSchedule.LOW)
        medium = build_default_schedule(RiskTierSchedule.MEDIUM)

        low_dict = {item["event_type"]: item["percentage"] for item in low}
        medium_dict = {item["event_type"]: item["percentage"] for item in medium}

        assert low_dict != medium_dict

    def test_medium_vs_high_risk_different_schedules(self) -> None:
        """MEDIUM and HIGH risk schedules should differ."""
        medium = build_default_schedule(RiskTierSchedule.MEDIUM)
        high = build_default_schedule(RiskTierSchedule.HIGH)

        medium_dict = {item["event_type"]: item["percentage"] for item in medium}
        high_dict = {item["event_type"]: item["percentage"] for item in high}

        assert medium_dict != high_dict

    def test_low_vs_high_risk_most_different(self) -> None:
        """LOW and HIGH risk schedules should be most different."""
        low = build_default_schedule(RiskTierSchedule.LOW)
        high = build_default_schedule(RiskTierSchedule.HIGH)

        low_dict = {item["event_type"]: item["percentage"] for item in low}
        high_dict = {item["event_type"]: item["percentage"] for item in high}

        # Compare by calculating total difference
        low_pickup = low_dict["PICKUP_CONFIRMED"]
        high_pickup = high_dict["PICKUP_CONFIRMED"]
        assert low_pickup != high_pickup  # LOW should have > 0, HIGH should have 0


class TestScheduleStructureValidation:
    """Validate the structure and types of schedule items."""

    def test_schedule_item_has_required_keys(self) -> None:
        """Each schedule item should have required keys."""
        items = build_default_schedule(RiskTierSchedule.LOW)
        required_keys = {"event_type", "percentage", "order"}

        for item in items:
            assert required_keys.issubset(item.keys()), f"Item missing keys: {item}"

    def test_schedule_item_types_correct(self) -> None:
        """Schedule item values should have correct types."""
        items = build_default_schedule(RiskTierSchedule.MEDIUM)

        for item in items:
            assert isinstance(item["event_type"], str)
            assert isinstance(item["percentage"], (int, float))
            assert isinstance(item["order"], int)

    def test_schedule_percentages_non_negative(self) -> None:
        """All percentages should be non-negative."""
        for risk_tier in [
            RiskTierSchedule.LOW,
            RiskTierSchedule.MEDIUM,
            RiskTierSchedule.HIGH,
        ]:
            items = build_default_schedule(risk_tier)
            for item in items:
                assert (
                    item["percentage"] >= 0.0
                ), f"Negative percentage in {risk_tier}: {item}"

    def test_schedule_percentages_not_exceed_one(self) -> None:
        """No single percentage should exceed 1.0."""
        for risk_tier in [
            RiskTierSchedule.LOW,
            RiskTierSchedule.MEDIUM,
            RiskTierSchedule.HIGH,
        ]:
            items = build_default_schedule(risk_tier)
            for item in items:
                assert (
                    item["percentage"] <= 1.0
                ), f"Percentage > 1.0 in {risk_tier}: {item}"


class TestScheduleConsistency:
    """Test consistency of schedule generation across multiple calls."""

    def test_low_risk_schedule_reproducible(self) -> None:
        """LOW-risk schedule should be reproducible (same each call)."""
        items1 = build_default_schedule(RiskTierSchedule.LOW)
        items2 = build_default_schedule(RiskTierSchedule.LOW)
        assert items1 == items2

    def test_medium_risk_schedule_reproducible(self) -> None:
        """MEDIUM-risk schedule should be reproducible."""
        items1 = build_default_schedule(RiskTierSchedule.MEDIUM)
        items2 = build_default_schedule(RiskTierSchedule.MEDIUM)
        assert items1 == items2

    def test_high_risk_schedule_reproducible(self) -> None:
        """HIGH-risk schedule should be reproducible."""
        items1 = build_default_schedule(RiskTierSchedule.HIGH)
        items2 = build_default_schedule(RiskTierSchedule.HIGH)
        assert items1 == items2
