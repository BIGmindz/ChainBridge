"""
Data Processing Core for Benson

This module handles data normalization, validation, and transformation
for the Benson multi-signal decision system.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Union

import pandas as pd


class DataProcessor:
    """Core data processing and normalization engine."""

    def __init__(self):
        self.processed_count = 0
        self.error_count = 0

    def normalize_timestamp(self, timestamp: Union[str, int, datetime]) -> str:
        """Normalize various timestamp formats to ISO string."""
        try:
            if isinstance(timestamp, str):
                # Try parsing various string formats
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except Exception:
                    # Try pandas parser for flexible parsing
                    dt = pd.to_datetime(timestamp)  # type: ignore
            elif isinstance(timestamp, (int, float)):
                # Unix timestamp
                dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            elif isinstance(timestamp, datetime):
                dt = timestamp
            else:
                raise ValueError(f"Unsupported timestamp type: {type(timestamp)}")

            # Ensure timezone awareness
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt.isoformat()

        except Exception as e:
            raise ValueError(f"Failed to normalize timestamp {timestamp}: {str(e)}")

    def normalize_price_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize price/financial data to standard format."""
        normalized = {
            "timestamp": None,
            "symbol": None,
            "price": None,
            "volume": None,
            "source": "unknown",
        }

        # Map common field variations
        field_mappings = {
            "timestamp": ["timestamp", "time", "ts", "datetime", "date"],
            "symbol": ["symbol", "pair", "market", "instrument"],
            "price": ["price", "close", "last", "value"],
            "volume": ["volume", "vol", "amount"],
            "source": ["source", "exchange", "provider"],
        }

        for standard_field, variations in field_mappings.items():
            for variation in variations:
                if variation in data:
                    if standard_field == "timestamp":
                        normalized[standard_field] = self.normalize_timestamp(data[variation])
                    elif standard_field in ["price", "volume"]:
                        normalized[standard_field] = float(data[variation]) if data[variation] is not None else None  # type: ignore
                    else:
                        normalized[standard_field] = str(data[variation])
                    break

        return normalized

    def normalize_signal_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize trading signals to standard format."""
        normalized = {
            "timestamp": None,
            "symbol": None,
            "signal": None,
            "confidence": None,
            "source": "unknown",
            "metadata": {},
        }

        # Extract timestamp
        if "timestamp" in data:
            normalized["timestamp"] = self.normalize_timestamp(data["timestamp"])
        else:
            normalized["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Extract other fields
        if "symbol" in data:
            normalized["symbol"] = str(data["symbol"])
        if "signal" in data:
            signal_value = str(data["signal"]).upper()
            if signal_value in ["BUY", "SELL", "HOLD"]:
                normalized["signal"] = signal_value
            else:
                raise ValueError(f"Invalid signal value: {signal_value}")

        if "confidence" in data:
            normalized["confidence"] = float(data["confidence"])  # type: ignore

        if "source" in data:
            normalized["source"] = str(data["source"])

        # Store additional fields in metadata
        excluded_fields = {"timestamp", "symbol", "signal", "confidence", "source"}
        for key, value in data.items():
            if key not in excluded_fields:
                normalized["metadata"][key] = value

        return normalized

    def validate_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data quality and return quality metrics."""
        quality_report = {
            "valid": True,
            "issues": [],
            "completeness_score": 0.0,
            "field_count": len(data),
        }

        # Check for null/empty values
        null_fields = []
        total_fields = len(data)
        non_null_fields = 0

        for key, value in data.items():
            if value is None or value == "" or (isinstance(value, str) and value.strip() == ""):
                null_fields.append(key)  # type: ignore
            else:
                non_null_fields += 1

        if null_fields:
            quality_report["issues"].append(f"Null/empty fields: {null_fields}")  # type: ignore

        # Calculate completeness score
        quality_report["completeness_score"] = non_null_fields / total_fields if total_fields > 0 else 0.0

        # Mark as invalid if completeness is too low
        if quality_report["completeness_score"] < 0.5:
            quality_report["valid"] = False
            quality_report["issues"].append("Data completeness below 50%")  # type: ignore

        return quality_report

    def process_batch(self, data_list: List[Dict[str, Any]], data_type: str = "generic") -> Dict[str, Any]:
        """Process a batch of data records."""
        results = {
            "processed": [],
            "errors": [],
            "summary": {
                "total": len(data_list),
                "successful": 0,
                "failed": 0,
                "start_time": datetime.now(timezone.utc).isoformat(),
            },
        }

        for i, record in enumerate(data_list):
            try:
                # Apply appropriate normalization based on data type
                if data_type == "price":
                    normalized = self.normalize_price_data(record)
                elif data_type == "signal":
                    normalized = self.normalize_signal_data(record)
                else:
                    normalized = record  # Generic pass-through

                # Validate quality
                quality = self.validate_data_quality(normalized)
                normalized["_quality"] = quality

                results["processed"].append(normalized)  # type: ignore
                results["summary"]["successful"] += 1
                self.processed_count += 1

            except Exception as e:
                error_info = {"index": i, "error": str(e), "data": record}
                results["errors"].append(error_info)  # type: ignore
                results["summary"]["failed"] += 1
                self.error_count += 1

        results["summary"]["end_time"] = datetime.now(timezone.utc).isoformat()
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "total_processed": self.processed_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / max(self.processed_count + self.error_count, 1),
        }
