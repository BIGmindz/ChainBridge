"""Seeburger ingestion adapter mapping EDI 856 into the Golden Record."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree

from app.schemas.normalized_logistics import Asset, StandardShipment, TemperatureTolerance
from app.services.ingest.base import BaseIngestor

logger = logging.getLogger(__name__)


class SeeburgerIngestor(BaseIngestor):
    source_name = "SEEBURGER"

    def _parse_xml_payload(self, raw_xml: str) -> Dict[str, Any]:
        try:
            root = ElementTree.fromstring(raw_xml)
        except ElementTree.ParseError:
            return {"raw": raw_xml}

        def _text(tag: str) -> Optional[str]:
            node = root.find(tag)
            return node.text if node is not None else None

        items: List[Dict[str, Any]] = []
        for node in root.findall(".//LineItem"):
            items.append(
                {
                    "sku": node.findtext("SKU"),
                    "description": node.findtext("Description"),
                    "quantity": float(node.findtext("Quantity") or 0),
                    "unit": node.findtext("Unit") or "EA",
                    "value": (float(node.findtext("Value")) if node.findtext("Value") is not None else None),
                }
            )

        return {
            "control_number": _text("ControlNumber"),
            "shipment_id": _text("ShipmentID"),
            "expected_arrival": _text("ExpectedArrival"),
            "carrier": _text("Carrier"),
            "line_items": items,
        }

    @staticmethod
    def _parse_expected_arrival(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        return datetime.utcnow()

    def _extract_assets(self, payload: Dict[str, Any]) -> List[Asset]:
        assets: List[Asset] = []
        for item in payload.get("line_items", []):
            try:
                assets.append(Asset(**item))
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("seeburger.asset_parse_failed", extra={"error": str(exc)})
        return assets

    def parse(self, raw_payload: dict | str) -> StandardShipment:
        payload = (
            self._parse_xml_payload(raw_payload)
            if isinstance(raw_payload, str) and raw_payload.strip().startswith("<")
            else self._coerce_payload(raw_payload)
        )
        control_number = (
            payload.get("control_number")
            or payload.get("edi_control_number")
            or payload.get("interchange", {}).get("control_number")
            or payload.get("external_id")
        )
        shipment_id = payload.get("shipment_id") or payload.get("shipment", {}).get("id") or control_number
        expected_arrival = self._parse_expected_arrival(payload.get("expected_arrival") or payload.get("eta"))
        tolerances_data = payload.get("tolerances") or payload.get("plan", {}).get("tolerances") or {}
        tolerances = None
        if tolerances_data:
            tolerances = TemperatureTolerance(
                max_celsius=tolerances_data.get("max_temp") or tolerances_data.get("max_celsius"),
                min_celsius=tolerances_data.get("min_temp") or tolerances_data.get("min_celsius"),
            )
        assets = self._extract_assets(payload)
        metadata = {
            "carrier": payload.get("carrier"),
            "document_type": payload.get("document_type", "EDI_856"),
            "raw_summary": {
                "line_item_count": len(assets),
                "has_tolerances": bool(tolerances),
            },
        }
        if "raw" in payload:
            metadata["raw"] = payload["raw"]
        return StandardShipment(
            source_system=self.source_name,
            external_id=str(control_number or "UNKNOWN"),
            shipment_id=str(shipment_id or control_number or "UNKNOWN"),
            assets=assets,
            raw_data_hash=self._hash(raw_payload),
            expected_arrival=expected_arrival,
            metadata=metadata,
            tolerances=tolerances,
        )
