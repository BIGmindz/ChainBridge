"""Business logic for the ChainPay settlement API."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from sqlalchemy.orm import Session

from ..models_context_ledger import ContextLedgerEntry
from ..schemas_settlement import (
    OnchainStatus,
    RiskBand,
    SettleOnchainRequest,
    SettleOnchainResponse,
    SettlementAckRequest,
    SettlementAckResponse,
    SettlementDetailResponse,
    SettlementStatus,
)
from .xrpl_stub_adapter import XRPLSettlementAdapter

SETTLEMENT_KEY = "settlement"
ACK_KEY = "acks"


class SettlementNotFoundError(Exception):
    """Raised when the requested settlement cannot be located."""


class SettlementConflictError(Exception):
    """Raised when the settlement is in an invalid state for the requested action."""


class SettlementAPIService:
    """Reads and mutates settlement metadata stored in the context ledger."""

    def __init__(self, session: Session, *, xrpl_adapter: XRPLSettlementAdapter | None = None) -> None:
        self.session = session
        self.xrpl_adapter = xrpl_adapter or XRPLSettlementAdapter()

    def trigger_onchain_settlement(self, payload: SettleOnchainRequest) -> SettleOnchainResponse:
        entry, metadata, block = self._locate_settlement(payload.settlement_id)
        self._validate_amount(block, payload.amount)
        block.setdefault("amount", float(payload.amount))
        block["asset"] = payload.asset
        block["carrier_wallet"] = payload.carrier_wallet
        block["risk_band"] = payload.risk_band.value
        block["risk_trace_id"] = payload.trace_id
        block["memo"] = payload.memo
        block.setdefault("status", SettlementStatus.RELEASED.value)

        adapter_result = self.xrpl_adapter.submit_payment(
            settlement_id=payload.settlement_id,
            amount=payload.amount,
            asset=payload.asset,
            carrier_wallet=payload.carrier_wallet,
            memo=payload.memo,
        )
        block["onchain_status"] = adapter_result["status"].value
        block["tx_hash"] = adapter_result["tx_hash"]
        block["xrpl_timestamp"] = adapter_result["xrpl_timestamp"]
        block["last_submitted_at"] = _now_iso()
        block["status"] = (
            SettlementStatus.ONCHAIN_CONFIRMED.value
            if adapter_result["status"] == OnchainStatus.CONFIRMED
            else SettlementStatus.RELEASED.value
        )

        self._persist_metadata(entry, metadata)
        return SettleOnchainResponse(
            settlement_id=payload.settlement_id,
            tx_hash=adapter_result["tx_hash"],
            xrpl_timestamp=adapter_result["xrpl_timestamp"],
            status=adapter_result["status"],
        )

    def get_settlement_detail(self, settlement_id: str) -> SettlementDetailResponse:
        entry, metadata, block = self._locate_settlement(settlement_id)
        ack_list = metadata.get(ACK_KEY)
        return SettlementDetailResponse(
            settlement_id=settlement_id,
            status=_coerce_enum(SettlementStatus, block.get("status"), SettlementStatus.PENDING),
            amount=float(block.get("amount", entry.amount)),
            asset=str(block.get("asset") or entry.currency or "USD"),
            carrier_wallet=block.get("carrier_wallet"),
            risk_band=_coerce_enum_value(block.get("risk_band")),
            risk_trace_id=block.get("risk_trace_id"),
            memo=block.get("memo"),
            tx_hash=block.get("tx_hash"),
            xrpl_timestamp=block.get("xrpl_timestamp"),
            onchain_status=_coerce_enum(OnchainStatus, block.get("onchain_status")),
            ack_count=len(ack_list) if isinstance(ack_list, list) else 0,
        )

    def record_acknowledgement(self, settlement_id: str, payload: SettlementAckRequest) -> SettlementAckResponse:
        entry, metadata, block = self._locate_settlement(settlement_id)
        ack_list = metadata.setdefault(ACK_KEY, [])
        if not isinstance(ack_list, list):
            ack_list = []
            metadata[ACK_KEY] = ack_list

        record = {
            "trace_id": payload.trace_id,
            "consumer_id": payload.consumer_id,
            "notes": payload.notes,
            "acknowledged_at": _now_iso(),
        }
        if payload.trace_id and payload.consumer_id:
            for existing in ack_list:
                if (
                    existing.get("trace_id") == payload.trace_id
                    and existing.get("consumer_id") == payload.consumer_id
                ):
                    existing.update(record)
                    break
            else:
                ack_list.append(record)
        else:
            ack_list.append(record)

        # Keep settlement status stable unless explicitly moved elsewhere.
        block.setdefault("status", SettlementStatus.RELEASED.value)
        self._persist_metadata(entry, metadata)
        return SettlementAckResponse(ok=True, settlement_id=settlement_id, ack_count=len(ack_list))

    def _locate_settlement(self, settlement_id: str) -> Tuple[ContextLedgerEntry, Dict[str, Any], Dict[str, Any]]:
        pattern = f'"settlement_id": "{settlement_id}"'
        entry = (
            self.session.query(ContextLedgerEntry)
            .filter(ContextLedgerEntry.metadata_json.isnot(None))
            .filter(ContextLedgerEntry.metadata_json.contains(pattern))
            .order_by(ContextLedgerEntry.created_at.desc(), ContextLedgerEntry.id.desc())
            .first()
        )
        if not entry:
            raise SettlementNotFoundError(f"Settlement {settlement_id} not found")

        metadata = _deserialize(entry.metadata_json)
        block = metadata.get(SETTLEMENT_KEY)
        if not isinstance(block, dict) or block.get("settlement_id") != settlement_id:
            raise SettlementNotFoundError(f"Settlement {settlement_id} not found")
        metadata[SETTLEMENT_KEY] = block
        return entry, metadata, block

    def _validate_amount(self, block: Dict[str, Any], requested_amount: float) -> None:
        stored_amount = block.get("amount")
        if stored_amount is None:
            return
        if not math.isclose(float(stored_amount), float(requested_amount), rel_tol=1e-6, abs_tol=1e-6):
            raise SettlementConflictError("Settlement amount does not match ledger value")

    def _persist_metadata(self, entry: ContextLedgerEntry, metadata: Dict[str, Any]) -> None:
        entry.metadata_json = json.dumps(metadata)
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)


def _deserialize(raw: str | None) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _coerce_enum(enum_cls, value: Any, default: Any | None = None):
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            return default
    return default


def _coerce_enum_value(value: Any):
    if isinstance(value, RiskBand):
        return value
    if isinstance(value, str):
        try:
            return RiskBand(value)
        except ValueError:
            return None
    return None


__all__ = [
    "SettlementAPIService",
    "SettlementNotFoundError",
    "SettlementConflictError",
]
