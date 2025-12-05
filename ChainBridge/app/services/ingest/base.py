"""Abstract ingestion adapter interface."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict

from app.schemas.normalized_logistics import StandardShipment


class BaseIngestor(ABC):
    """Base interface for all ingestion sources."""

    source_name: str = "UNKNOWN"

    @staticmethod
    def _coerce_payload(raw_payload: dict | str) -> Dict[str, Any]:
        if isinstance(raw_payload, dict):
            return raw_payload
        if isinstance(raw_payload, str):
            try:
                return json.loads(raw_payload)
            except Exception:
                return {"raw": raw_payload}
        raise ValueError("Unsupported payload type; expected dict or str")

    @staticmethod
    def _hash(raw_payload: Any) -> str:
        return StandardShipment.compute_hash(raw_payload)

    @abstractmethod
    def parse(self, raw_payload: dict | str) -> StandardShipment: ...
