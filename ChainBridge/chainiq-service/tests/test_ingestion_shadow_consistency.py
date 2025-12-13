"""
Ingestion → Shadow Mode Consistency Tests

Validates that data flows correctly from ingestion pipeline to shadow mode logging,
ensuring perfect feature parity between ML training and shadow validation.

PAC-CODY-026: Shadow Mode + Ingestion Alignment Patch
"""

from datetime import datetime, timezone

from app.ml.datasets import ShipmentTrainingRow
from app.ml.event_parsing import EventType, ParsedEvent
from app.ml.ingestion import build_training_rows_from_events, derive_loss_amount, derive_severe_delay, extract_features_from_events
from app.models.features import ShipmentFeaturesV0


class TestIngestionShadowFeatureParity:
    """
    Test that features extracted by ingestion match the schema expected by shadow mode.
    """

    def test_features_have_all_required_shadow_fields(self):
        """Verify ShipmentFeaturesV0 has all fields needed for shadow mode scoring."""
        required_fields = [
            "shipment_id",
            "corridor",
            "origin_country",
            "destination_country",
            "mode",
            "planned_transit_hours",
            "actual_transit_hours",
            "eta_deviation_hours",
            "num_route_deviations",
            "max_route_deviation_km",
            "total_dwell_hours",
            "max_single_dwell_hours",
            "handoff_count",
            "max_custody_gap_hours",
            "delay_flag",
            "has_iot_telemetry",
            "temp_mean",
            "carrier_on_time_pct_90d",
            "shipper_on_time_pct_90d",
            "lane_sentiment_score",
        ]

        # Check that all required fields exist in schema
        model_fields = ShipmentFeaturesV0.model_fields.keys()
        for field in required_fields:
            assert field in model_fields, f"Missing required field: {field}"

    def test_ingestion_produces_valid_features_for_shadow(self):
        """Test that ingestion output is valid input for shadow mode."""
        events = [
            ParsedEvent(
                "e1",
                "shp_test",
                EventType.SHIPMENT_CREATED,
                datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
                {"eta": "2024-01-03T00:00:00Z"},
            ),
            ParsedEvent("e2", "shp_test", EventType.SHIPMENT_PICKED_UP, datetime(2024, 1, 1, 6, 0, tzinfo=timezone.utc), {}),
            ParsedEvent("e3", "shp_test", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 4, 6, 0, tzinfo=timezone.utc), {}),
        ]

        features = extract_features_from_events("shp_test", events)

        # Verify all critical numeric features are not None
        assert features["planned_transit_hours"] is not None
        assert features["actual_transit_hours"] is not None
        assert features["eta_deviation_hours"] is not None

        # Verify values are valid for ML model input
        assert 0 <= features["planned_transit_hours"] <= 1000
        assert 0 <= features["actual_transit_hours"] <= 1000
        assert -500 <= features["eta_deviation_hours"] <= 500

    def test_training_row_can_be_used_for_shadow_scoring(self):
        """Test that ShipmentTrainingRow features are compatible with shadow mode."""
        event_records = [
            {
                "event_id": "e1",
                "shipment_id": "shp_shadow_test",
                "event_type": "SHIPMENT_CREATED",
                "timestamp": "2024-01-01T00:00:00Z",
                "payload": {"eta": "2024-01-03T00:00:00Z"},
            },
            {
                "event_id": "e2",
                "shipment_id": "shp_shadow_test",
                "event_type": "SHIPMENT_DELIVERED",
                "timestamp": "2024-01-03T00:00:00Z",
                "payload": {},
            },
        ]

        rows = build_training_rows_from_events(event_records)
        assert len(rows) == 1

        row = rows[0]

        # Verify the row has all required attributes for shadow mode
        assert hasattr(row, "features")
        assert isinstance(row.features, ShipmentFeaturesV0)

        # Verify convenience properties work
        assert row.shipment_id == "shp_shadow_test"
        assert row.planned_transit_hours == 48.0
        assert row.eta_deviation_hours == 0.0  # On-time delivery


class TestIngestionShadowLabelConsistency:
    """
    Test that labels derived by ingestion are consistent with shadow mode expectations.
    """

    def test_severe_delay_threshold_consistency(self):
        """Verify 48-hour severe delay threshold is enforced consistently."""
        # Exactly at threshold (not severe)
        events_at_threshold = [
            ParsedEvent(
                "e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc), {"eta": "2024-01-03T00:00:00Z"}
            ),
            ParsedEvent(
                "e2", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 5, 0, 0, tzinfo=timezone.utc), {}
            ),  # Exactly 48h late
        ]
        assert derive_severe_delay(events_at_threshold) is False

        # Just over threshold (severe)
        events_over_threshold = [
            ParsedEvent(
                "e1", "shp2", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc), {"eta": "2024-01-03T00:00:00Z"}
            ),
            ParsedEvent("e2", "shp2", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 5, 0, 1, tzinfo=timezone.utc), {}),  # 48h + 1min late
        ]
        assert derive_severe_delay(events_over_threshold) is True

    def test_loss_amount_aggregation_for_multi_claim(self):
        """Verify multi-claim shipments sum all approved amounts."""
        events = [
            ParsedEvent("e1", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 5, tzinfo=timezone.utc), {"claim_amount": 1000.0}),
            ParsedEvent("e2", "shp1", EventType.CLAIM_APPROVED, datetime(2024, 1, 10, tzinfo=timezone.utc), {"approved_amount": 800.0}),
            ParsedEvent("e3", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 15, tzinfo=timezone.utc), {"claim_amount": 500.0}),
            ParsedEvent("e4", "shp1", EventType.CLAIM_APPROVED, datetime(2024, 1, 20, tzinfo=timezone.utc), {"approved_amount": 450.0}),
        ]

        # Should SUM all approved amounts: 800 + 450 = 1250
        total_loss = derive_loss_amount(events)
        assert total_loss == 1250.0, f"Expected 1250.0, got {total_loss}"

    def test_training_row_bad_outcome_consistency(self):
        """Verify bad_outcome label consistency between ingestion and shadow."""
        event_records = [
            {
                "event_id": "e1",
                "shipment_id": "shp1",
                "event_type": "SHIPMENT_CREATED",
                "timestamp": "2024-01-01T00:00:00Z",
                "payload": {"eta": "2024-01-03T00:00:00Z"},
            },
            {
                "event_id": "e2",
                "shipment_id": "shp1",
                "event_type": "SHIPMENT_DELIVERED",
                "timestamp": "2024-01-06T00:00:00Z",  # 72h late (severe)
                "payload": {},
            },
            {
                "event_id": "e3",
                "shipment_id": "shp1",
                "event_type": "CLAIM_FILED",
                "timestamp": "2024-01-07T00:00:00Z",
                "payload": {"claim_amount": 500.0},
            },
        ]

        rows = build_training_rows_from_events(event_records)
        assert len(rows) == 1

        row = rows[0]

        # Verify label consistency
        assert row.had_claim is True
        assert row.severe_delay is True
        assert row.bad_outcome is True  # Composite of claim OR dispute OR severe_delay


class TestIngestionShadowTimezoneConsistency:
    """
    Test that timezone handling is consistent between ingestion and shadow mode.
    """

    def test_utc_normalization_for_transit_times(self):
        """Verify that transit times are calculated correctly with UTC normalization."""
        # Mix of naive and aware timestamps
        events = [
            ParsedEvent(
                "e1",
                "shp1",
                EventType.SHIPMENT_CREATED,
                datetime(2024, 1, 1, 0, 0),  # Naive (treated as UTC)
                {"eta": "2024-01-03T00:00:00Z"},
            ),  # Aware (explicit UTC)
            ParsedEvent("e2", "shp1", EventType.SHIPMENT_PICKED_UP, datetime(2024, 1, 1, 6, 0, tzinfo=timezone.utc), {}),  # Aware
            ParsedEvent("e3", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 4, 6, 0), {}),  # Naive (treated as UTC)
        ]

        features = extract_features_from_events("shp1", events)

        # Verify calculations are correct despite mixed timezone-awareness
        assert features["planned_transit_hours"] == 48.0  # Created to ETA
        assert features["actual_transit_hours"] == 72.0  # Pickup to delivery
        assert features["eta_deviation_hours"] == 30.0  # Delivered 30h after ETA

    def test_severe_delay_handles_mixed_timezones(self):
        """Verify severe_delay correctly handles mixed timezone inputs."""
        # Naive timestamp for created, aware ETA
        events = [
            ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1, 0, 0), {"eta": "2024-01-03T00:00:00Z"}),
            ParsedEvent("e2", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 6, 0, 0), {}),  # 72h late (severe)
        ]

        # Should correctly determine severe delay
        assert derive_severe_delay(events) is True


class TestIngestionShadowDataFlow:
    """
    Test the complete data flow from ingestion to shadow mode.
    """

    def test_end_to_end_ingestion_to_shadow_features(self):
        """Test complete pipeline: raw events → features → shadow-compatible row."""
        # Raw event records (as they would come from ChainBridge logs)
        event_records = [
            {
                "event_id": "evt_001",
                "shipment_id": "SH-2024-12345",
                "event_type": "SHIPMENT_CREATED",
                "timestamp": "2024-01-01T10:00:00Z",
                "payload": {"eta": "2024-01-05T10:00:00Z"},  # 4 day transit
            },
            {
                "event_id": "evt_002",
                "shipment_id": "SH-2024-12345",
                "event_type": "SHIPMENT_PICKED_UP",
                "timestamp": "2024-01-01T14:00:00Z",
                "payload": {},
            },
            {
                "event_id": "evt_003",
                "shipment_id": "SH-2024-12345",
                "event_type": "ROUTE_DEVIATION",
                "timestamp": "2024-01-02T08:00:00Z",
                "payload": {"deviation_km": 15.5},
            },
            {
                "event_id": "evt_004",
                "shipment_id": "SH-2024-12345",
                "event_type": "SENSOR_READING",
                "timestamp": "2024-01-03T12:00:00Z",
                "payload": {"temperature": 22.5},
            },
            {
                "event_id": "evt_005",
                "shipment_id": "SH-2024-12345",
                "event_type": "SHIPMENT_DELIVERED",
                "timestamp": "2024-01-05T08:00:00Z",  # 2h early!
                "payload": {},
            },
        ]

        # Step 1: Build training rows from events
        rows = build_training_rows_from_events(event_records)

        assert len(rows) == 1
        row = rows[0]

        # Step 2: Verify the ShipmentTrainingRow has correct structure
        assert isinstance(row, ShipmentTrainingRow)
        assert isinstance(row.features, ShipmentFeaturesV0)

        # Step 3: Verify computed features
        assert row.shipment_id == "SH-2024-12345"
        assert row.planned_transit_hours == 96.0  # 4 days
        assert row.num_route_deviations == 1
        assert row.max_route_deviation_km == 15.5
        assert row.temp_mean == 22.5  # Single sensor reading

        # Step 4: Verify labels
        assert row.had_claim is False  # No claim filed
        assert row.severe_delay is False  # Delivered early
        assert row.bad_outcome is False  # No bad outcome

        # Step 5: Verify the features can be serialized for shadow mode
        features_dict = row.features.model_dump()
        assert "shipment_id" in features_dict
        assert "corridor" in features_dict
        assert "planned_transit_hours" in features_dict

        # Step 6: Verify all numeric features are valid (no NaN, no None in required fields)
        assert features_dict["planned_transit_hours"] is not None
        assert features_dict["actual_transit_hours"] is not None
        assert features_dict["eta_deviation_hours"] is not None
