"""Simple tests for ChainFreight processor without full app context."""

from unittest.mock import Mock

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from api.services.chainfreight_processor import ChainFreightProcessor


def test_edi_214_processing():
    """Test EDI 214 processing without database dependencies."""
    mock_db = Mock()
    processor = ChainFreightProcessor(mock_db)

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

    result = processor.process_edi_214(raw_record)

    assert result["shipment_reference"] == "PRO123456"
    assert result["carrier_code"] == "UPSN"
    assert result["status_code"] == "AF"
    assert result["location"]["city"] == "Chicago"
    assert result["equipment_id"] == "TRAILER123"
    print("✅ EDI 214 processing test passed")


def test_edi_210_processing():
    """Test EDI 210 processing."""
    mock_db = Mock()
    processor = ChainFreightProcessor(mock_db)

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

    result = processor.process_edi_210(raw_record)

    assert result["shipment_reference"] == "PRO123456"
    assert result["invoice_number"] == "INV789"
    assert result["total_charges"] == 1250.00
    assert result["currency"] == "USD"
    assert len(result["line_items"]) == 2
    print("✅ EDI 210 processing test passed")


def test_telematics_processing():
    """Test telematics data processing."""
    mock_db = Mock()
    processor = ChainFreightProcessor(mock_db)

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

    result = processor.process_telematics(raw_record)

    assert result["equipment_id"] == "TRUCK001"
    assert result["location"]["latitude"] == 41.8781
    assert result["location"]["longitude"] == -87.6298
    assert result["speed"] == 65
    assert result["driver_id"] == "DRIVER123"
    print("✅ Telematics processing test passed")


def test_edi_timestamp_parsing():
    """Test EDI timestamp parsing."""
    mock_db = Mock()
    processor = ChainFreightProcessor(mock_db)

    # Test YYMMDD format
    result = processor._parse_edi_timestamp("251126", "1430")
    expected = "2025-11-26T14:30:00"
    assert result == expected

    # Test YYYYMMDD format
    result = processor._parse_edi_timestamp("20251126", "143045")
    expected = "2025-11-26T14:30:45"
    assert result == expected

    # Test date only
    result = processor._parse_edi_timestamp("251126", None)
    expected = "2025-11-26T00:00:00"
    assert result == expected

    # Test invalid format
    result = processor._parse_edi_timestamp("invalid", "1430")
    assert result is None

    print("✅ EDI timestamp parsing tests passed")


def test_edi_status_mapping():
    """Test EDI status code mapping."""
    mock_db = Mock()
    processor = ChainFreightProcessor(mock_db)

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
        result = processor._map_edi_status_to_event_type(status_code)
        assert result == expected_event_type

    print("✅ EDI status mapping tests passed")


if __name__ == "__main__":
    print("Running ChainFreight processor tests...")
    test_edi_214_processing()
    test_edi_210_processing()
    test_telematics_processing()
    test_edi_timestamp_parsing()
    test_edi_status_mapping()
    print("✅ All ChainFreight processor tests passed!")
