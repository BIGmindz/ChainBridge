"""Tests for ChainFreight ingestion service."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from api.schemas.chainfreight import (
    IngestionBatchCreate,
    ShipmentEventCreate,
    ReconciliationRequest,
)
from api.services.chainfreight_processor import ChainFreightProcessor


class TestChainFreightProcessor:
    """Test the ChainFreightProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.processor = ChainFreightProcessor(self.mock_db)

    def test_process_edi_214_success(self):
        """Test successful processing of EDI 214 record."""
        raw_record = {
            "pro_number": "PRO123456",
            "scac": "UPSN",
            "status_code": "AF",
            "status_description": "Arrived at facility",
            "city": "Chicago",
            "state": "IL",
            "country": "US",
            "date": "20251126",
            "time": "1430",
            "equipment_id": "TRAILER123",
        }

        result = self.processor.process_edi_214(raw_record)

        assert result["shipment_reference"] == "PRO123456"
        assert result["carrier_code"] == "UPSN"
        assert result["status_code"] == "AF"
        assert result["location"]["city"] == "Chicago"
        assert result["equipment_id"] == "TRAILER123"

    def test_process_edi_214_with_events(self):
        """Test EDI 214 processing with status segments."""
        raw_record = {
            "pro_number": "PRO123456",
            "status_segments": [
                {
                    "status_code": "NS",
                    "status_description": "Not started",
                    "date": "20251125",
                    "time": "0800",
                    "location_code": "CHIIL",
                },
                {
                    "status_code": "AF",
                    "status_description": "Arrived at facility",
                    "date": "20251126",
                    "time": "1430",
                    "location_code": "DETML",
                },
            ],
        }

        result = self.processor.process_edi_214(raw_record)

        assert "events" in result
        assert len(result["events"]) == 2
        assert result["events"][0]["event_code"] == "NS"
        assert result["events"][0]["event_type"] == "PICKUP"
        assert result["events"][1]["event_code"] == "AF"
        assert result["events"][1]["event_type"] == "ARRIVED_FACILITY"

    def test_process_edi_210_success(self):
        """Test successful processing of EDI 210 record."""
        raw_record = {
            "pro_number": "PRO123456",
            "invoice_number": "INV789",
            "total_charges": 1250.00,
            "currency": "USD",
            "line_items": [
                {"description": "Freight charges", "amount": 1000.00},
                {"description": "Fuel surcharge", "amount": 250.00},
            ],
            "due_date": "2025-12-15",
        }

        result = self.processor.process_edi_210(raw_record)

        assert result["shipment_reference"] == "PRO123456"
        assert result["invoice_number"] == "INV789"
        assert result["total_charges"] == 1250.00
        assert result["currency"] == "USD"
        assert len(result["line_items"]) == 2

    def test_process_telematics_success(self):
        """Test successful processing of telematics data."""
        raw_record = {
            "vehicle_id": "TRUCK001",
            "lat": 41.8781,
            "lng": -87.6298,
            "timestamp": "2025-11-26T14:30:00Z",
            "speed": 65,
            "heading": 90,
            "fuel_level": 75,
            "driver_id": "DRIVER123",
            "status": "DRIVING",
        }

        result = self.processor.process_telematics(raw_record)

        assert result["equipment_id"] == "TRUCK001"
        assert result["location"]["latitude"] == 41.8781
        assert result["location"]["longitude"] == -87.6298
        assert result["speed"] == 65
        assert result["driver_id"] == "DRIVER123"

    def test_parse_edi_timestamp_yymmdd_format(self):
        """Test parsing EDI timestamps in YYMMDD format."""
        result = self.processor._parse_edi_timestamp("251126", "1430")
        expected = "2025-11-26T14:30:00"
        assert result == expected

    def test_parse_edi_timestamp_yyyymmdd_format(self):
        """Test parsing EDI timestamps in YYYYMMDD format."""
        result = self.processor._parse_edi_timestamp("20251126", "143045")
        expected = "2025-11-26T14:30:45"
        assert result == expected

    def test_parse_edi_timestamp_date_only(self):
        """Test parsing EDI timestamp with date only."""
        result = self.processor._parse_edi_timestamp("251126", None)
        expected = "2025-11-26T00:00:00"
        assert result == expected

    def test_parse_edi_timestamp_invalid_format(self):
        """Test parsing invalid EDI timestamp returns None."""
        result = self.processor._parse_edi_timestamp("invalid", "1430")
        assert result is None

    def test_map_edi_status_to_event_type(self):
        """Test mapping EDI status codes to event types."""
        test_cases = [
            ("AF", "ARRIVED_FACILITY"),
            ("AG", "DEPARTED_FACILITY"),
            ("D1", "DELIVERY"),
            ("I1", "IN_TRANSIT"),
            ("NS", "PICKUP"),
            ("X1", "EXCEPTION"),
            ("UNKNOWN", "UNKNOWN"),
            (None, "UNKNOWN"),
        ]

        for status_code, expected_event_type in test_cases:
            result = self.processor._map_edi_status_to_event_type(status_code)
            assert result == expected_event_type


class TestIngestionBatchValidation:
    """Test validation of ingestion batch creation."""

    def test_valid_ingestion_batch_create(self):
        """Test valid ingestion batch creation."""
        batch_data = {
            "source_system": "SEEBURGER",
            "batch_type": "EDI_214",
            "records": [
                {"pro_number": "PRO123", "status_code": "AF"},
                {"pro_number": "PRO456", "status_code": "D1"},
            ],
        }

        batch = IngestionBatchCreate(**batch_data)
        assert batch.source_system == "SEEBURGER"
        assert batch.batch_type == "EDI_214"
        assert len(batch.records) == 2

    def test_invalid_source_system(self):
        """Test validation fails for invalid source system."""
        batch_data = {
            "source_system": "INVALID_SYSTEM",
            "batch_type": "EDI_214",
            "records": [{"pro_number": "PRO123"}],
        }

        with pytest.raises(ValueError, match="source_system must be one of"):
            IngestionBatchCreate(**batch_data)

    def test_invalid_batch_type(self):
        """Test validation fails for invalid batch type."""
        batch_data = {
            "source_system": "SEEBURGER",
            "batch_type": "INVALID_TYPE",
            "records": [{"pro_number": "PRO123"}],
        }

        with pytest.raises(ValueError, match="batch_type must be one of"):
            IngestionBatchCreate(**batch_data)


class TestShipmentEventValidation:
    """Test validation of shipment event creation."""

    def test_valid_shipment_event_create(self):
        """Test valid shipment event creation."""
        event_data = {
            "shipment_id": "SHIP123",
            "event_type": "PICKUP",
            "event_timestamp": datetime.now(),
            "location_code": "CHIIL",
            "carrier_code": "UPSN",
        }

        event = ShipmentEventCreate(**event_data)
        assert event.shipment_id == "SHIP123"
        assert event.event_type == "PICKUP"
        assert event.location_code == "CHIIL"

    def test_invalid_event_type(self):
        """Test validation fails for invalid event type."""
        event_data = {
            "shipment_id": "SHIP123",
            "event_type": "INVALID_EVENT",
            "event_timestamp": datetime.now(),
        }

        with pytest.raises(ValueError, match="event_type must be one of"):
            ShipmentEventCreate(**event_data)

    def test_confidence_score_validation(self):
        """Test confidence score must be between 0 and 1."""
        # Valid score
        event_data = {
            "shipment_id": "SHIP123",
            "event_type": "PICKUP",
            "event_timestamp": datetime.now(),
            "confidence_score": 0.85,
        }
        event = ShipmentEventCreate(**event_data)
        assert event.confidence_score == 0.85

        # Invalid score - too high
        event_data["confidence_score"] = 1.5
        with pytest.raises(ValueError):
            ShipmentEventCreate(**event_data)

        # Invalid score - negative
        event_data["confidence_score"] = -0.1
        with pytest.raises(ValueError):
            ShipmentEventCreate(**event_data)


class TestReconciliationValidation:
    """Test validation of reconciliation requests."""

    def test_valid_reconciliation_request(self):
        """Test valid reconciliation request."""
        req_data = {
            "batch_id": "BATCH123",
            "shipment_references": ["PRO123", "PRO456"],
            "force_reprocess": True,
        }

        req = ReconciliationRequest(**req_data)
        assert req.batch_id == "BATCH123"
        assert len(req.shipment_references) == 2
        assert req.force_reprocess is True

    def test_optional_fields_reconciliation_request(self):
        """Test reconciliation request with optional fields."""
        req_data = {"force_reprocess": False}

        req = ReconciliationRequest(**req_data)
        assert req.batch_id is None
        assert req.shipment_references is None
        assert req.force_reprocess is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
