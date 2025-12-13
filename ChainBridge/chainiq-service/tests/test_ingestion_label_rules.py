"""
Unit tests for ChainIQ ML label derivation rules.

Tests cover:
- derive_had_claim
- derive_had_dispute
- derive_severe_delay
- derive_loss_amount
- derive_is_known_anomaly
"""

from datetime import datetime


from app.ml.event_parsing import EventType, ParsedEvent
from app.ml.ingestion import derive_had_claim, derive_had_dispute, derive_is_known_anomaly, derive_loss_amount, derive_severe_delay


def test_derive_had_claim_true():
    """Test that had_claim is True when CLAIM_FILED event exists."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1), {}),
        ParsedEvent("e2", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 5), {}),
    ]

    assert derive_had_claim(events) is True


def test_derive_had_claim_false():
    """Test that had_claim is False when no CLAIM_FILED event."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1), {}),
        ParsedEvent("e2", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 3), {}),
    ]

    assert derive_had_claim(events) is False


def test_derive_had_claim_multiple_claims():
    """Test that had_claim is True even with multiple CLAIM_FILED events."""
    events = [
        ParsedEvent("e1", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 5), {}),
        ParsedEvent("e2", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 6), {}),
    ]

    assert derive_had_claim(events) is True


def test_derive_had_dispute_true():
    """Test that had_dispute is True when DISPUTE_OPENED event exists."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1), {}),
        ParsedEvent("e2", "shp1", EventType.DISPUTE_OPENED, datetime(2024, 1, 10), {}),
    ]

    assert derive_had_dispute(events) is True


def test_derive_had_dispute_false():
    """Test that had_dispute is False when no DISPUTE_OPENED event."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1), {}),
        ParsedEvent("e2", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 5), {}),
    ]

    assert derive_had_dispute(events) is False


def test_derive_severe_delay_true_late_delivery():
    """Test severe_delay when delivered >48h after ETA."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1, 0, 0), {"eta": "2024-01-03T00:00:00Z"}),
        ParsedEvent("e2", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 6, 0, 0), {}),  # 72 hours late
    ]

    assert derive_severe_delay(events) is True


def test_derive_severe_delay_false_on_time():
    """Test severe_delay is False for on-time delivery."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1, 0, 0), {"eta": "2024-01-03T00:00:00Z"}),
        ParsedEvent("e2", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 3, 0, 0), {}),  # On time
    ]

    assert derive_severe_delay(events) is False


def test_derive_severe_delay_false_minor_delay():
    """Test severe_delay is False for minor delay (<48h)."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1, 0, 0), {"eta": "2024-01-03T00:00:00Z"}),
        ParsedEvent("e2", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 4, 0, 0), {}),  # 24 hours late (minor)
    ]

    assert derive_severe_delay(events) is False


def test_derive_severe_delay_true_no_delivery():
    """Test severe_delay is True when shipment never delivered (lost)."""
    from datetime import timezone

    events = [
        ParsedEvent(
            "e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc), {"eta": "2024-01-03T00:00:00Z"}
        ),
        # No delivery event
    ]

    assert derive_severe_delay(events) is True


def test_derive_loss_amount_from_approved_claim():
    """Test extracting loss amount from CLAIM_APPROVED event."""
    events = [
        ParsedEvent("e1", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 5), {"claim_amount": 500.0}),
        ParsedEvent("e2", "shp1", EventType.CLAIM_APPROVED, datetime(2024, 1, 10), {"approved_amount": 450.0}),  # Approved for less
    ]

    # Should use approved amount (actual payout)
    assert derive_loss_amount(events) == 450.0


def test_derive_loss_amount_from_filed_claim():
    """Test extracting loss amount from CLAIM_FILED when no approval yet."""
    events = [
        ParsedEvent("e1", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 5), {"claim_amount": 750.0}),
        # No approval yet
    ]

    # Should use claimed amount
    assert derive_loss_amount(events) == 750.0


def test_derive_loss_amount_zero():
    """Test that loss amount is 0.0 when no claims."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1), {}),
        ParsedEvent("e2", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 3), {}),
    ]

    assert derive_loss_amount(events) == 0.0


def test_derive_loss_amount_multiple_claims():
    """Test loss amount with multiple claims (should SUM all approved amounts)."""
    events = [
        ParsedEvent("e1", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 5), {"claim_amount": 200.0}),
        ParsedEvent("e2", "shp1", EventType.CLAIM_APPROVED, datetime(2024, 1, 10), {"approved_amount": 180.0}),
        ParsedEvent("e3", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 12), {"claim_amount": 300.0}),
        ParsedEvent("e4", "shp1", EventType.CLAIM_APPROVED, datetime(2024, 1, 15), {"approved_amount": 280.0}),
    ]

    # Should SUM all approved amounts (multi-claim shipment)
    # 180.0 + 280.0 = 460.0
    assert derive_loss_amount(events) == 460.0


def test_derive_is_known_anomaly_route_deviations():
    """Test known anomaly for multiple route deviations (>3)."""
    events = [
        ParsedEvent("e1", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 1), {}),
        ParsedEvent("e2", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 2), {}),
        ParsedEvent("e3", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 3), {}),
        ParsedEvent("e4", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 4), {}),
    ]

    assert derive_is_known_anomaly(events) is True


def test_derive_is_known_anomaly_custody_gap():
    """Test known anomaly for custody gap."""
    events = [
        ParsedEvent("e1", "shp1", EventType.CUSTODY_GAP, datetime(2024, 1, 2), {}),
    ]

    assert derive_is_known_anomaly(events) is True


def test_derive_is_known_anomaly_temperature_violation():
    """Test known anomaly for temperature violation."""
    events = [
        ParsedEvent("e1", "shp1", EventType.TEMPERATURE_VIOLATION, datetime(2024, 1, 2), {}),
    ]

    assert derive_is_known_anomaly(events) is True


def test_derive_is_known_anomaly_sensor_offline():
    """Test known anomaly for sensor offline."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SENSOR_OFFLINE, datetime(2024, 1, 2), {}),
    ]

    assert derive_is_known_anomaly(events) is True


def test_derive_is_known_anomaly_cancelled_shipment():
    """Test known anomaly for cancelled shipment."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CANCELLED, datetime(2024, 1, 2), {}),
    ]

    assert derive_is_known_anomaly(events) is True


def test_derive_is_known_anomaly_false_normal_shipment():
    """Test that normal shipment is not flagged as anomaly."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1), {}),
        ParsedEvent("e2", "shp1", EventType.SHIPMENT_PICKED_UP, datetime(2024, 1, 1, 6, 0), {}),
        ParsedEvent("e3", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 3, 6, 0), {}),
    ]

    assert derive_is_known_anomaly(events) is False


def test_derive_is_known_anomaly_false_minor_deviations():
    """Test that minor route deviations (≤3) don't trigger anomaly flag."""
    events = [
        ParsedEvent("e1", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 1), {}),
        ParsedEvent("e2", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 2), {}),
        ParsedEvent("e3", "shp1", EventType.ROUTE_DEVIATION, datetime(2024, 1, 3), {}),
    ]

    assert derive_is_known_anomaly(events) is False


def test_label_edge_case_empty_events():
    """Test all label functions with empty event list."""
    events = []

    assert derive_had_claim(events) is False
    assert derive_had_dispute(events) is False
    # severe_delay will be True (no delivery = severely delayed)
    assert derive_severe_delay(events) is True
    assert derive_loss_amount(events) == 0.0
    assert derive_is_known_anomaly(events) is False


def test_label_consistency_bad_outcome():
    """Test that labels are consistent for a 'bad outcome' shipment."""
    events = [
        ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1, 0, 0), {"eta": "2024-01-03T00:00:00Z"}),
        ParsedEvent("e2", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 6, 0, 0), {}),  # 72 hours late
        ParsedEvent("e3", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 7), {"claim_amount": 1000.0}),
        ParsedEvent("e4", "shp1", EventType.DISPUTE_OPENED, datetime(2024, 1, 10), {}),
    ]

    # All labels should be True for this problematic shipment
    assert derive_had_claim(events) is True
    assert derive_had_dispute(events) is True
    assert derive_severe_delay(events) is True
    assert derive_loss_amount(events) == 1000.0
