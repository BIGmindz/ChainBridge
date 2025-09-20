"""
CSV Data Ingestion Module

This module handles CSV file ingestion and data normalization
as an example of a simple data ingestion module.
"""

import os
from typing import Any, Dict

import pandas as pd

from core.module_manager import Module


class CSVIngestionModule(Module):
    """CSV data ingestion and processing module."""

    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.supported_formats = ["csv", "tsv"]

    def get_schema(self) -> Dict[str, Any]:
        return {
            "input": {
                "file_path": "string",
                "delimiter": 'string (optional, default: ",")',
                "header_row": "integer (optional, default: 0)",
                "columns_map": "dict (optional, column name mapping)",
            },
            "output": {
                "data": "list of dictionaries",
                "metadata": {
                    "row_count": "integer",
                    "column_count": "integer",
                    "file_size_bytes": "integer",
                    "columns": "list of strings",
                },
            },
        }

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process CSV file and return structured data."""
        file_path = data.get("file_path")
        if not file_path:
            raise ValueError("file_path is required")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Configuration options
        delimiter = data.get("delimiter", ",")
        header_row = data.get("header_row", 0)
        columns_map = data.get("columns_map", {})

        try:
            # Read CSV file
            df = pd.read_csv(file_path, delimiter=delimiter, header=header_row)

            # Apply column mapping if provided
            if columns_map:
                df = df.rename(columns=columns_map)

            # Convert to list of dictionaries
            records = df.to_dict("records")

            # Get file metadata
            file_stats = os.stat(file_path)

            result = {
                "data": records,
                "metadata": {
                    "row_count": len(records),
                    "column_count": len(df.columns),
                    "file_size_bytes": file_stats.st_size,
                    "columns": list(df.columns),
                    "file_path": file_path,
                },
                "module_info": {
                    "name": self.name,
                    "version": self.version,
                    "processing_timestamp": pd.Timestamp.now().isoformat(),
                },
            }

            return result

        except Exception as e:
            raise RuntimeError(f"Failed to process CSV file {file_path}: {str(e)}")

    def validate_csv_structure(self, file_path: str) -> Dict[str, Any]:
        """Validate CSV file structure and return analysis."""
        if not os.path.exists(file_path):
            return {"valid": False, "error": "File not found"}

        try:
            # Quick analysis using pandas
            sample_df = pd.read_csv(file_path, nrows=5)  # Read first 5 rows

            analysis = {
                "valid": True,
                "columns": list(sample_df.columns),
                "column_count": len(sample_df.columns),
                "sample_data_types": sample_df.dtypes.to_dict(),
                "has_header": True,  # Assuming header by default
                "estimated_rows": None,  # Could implement row counting
            }

            # Check for common issues
            issues = []

            # Check for unnamed columns
            unnamed_cols = [col for col in sample_df.columns if col.startswith("Unnamed")]
            if unnamed_cols:
                issues.append(f"Unnamed columns detected: {unnamed_cols}")

            # Check for completely empty columns
            empty_cols = sample_df.columns[sample_df.isnull().all()].tolist()
            if empty_cols:
                issues.append(f"Empty columns detected: {empty_cols}")

            analysis["issues"] = issues
            return analysis

        except Exception as e:
            return {"valid": False, "error": f"Failed to analyze CSV: {str(e)}"}
