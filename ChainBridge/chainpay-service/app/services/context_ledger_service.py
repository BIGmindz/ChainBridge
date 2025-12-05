"""Persistence layer for the Context Ledger (settlement governance decisions)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.governance.models import AgentMeta, GovernanceDecision, SettlementContext
from app.models_context_ledger import ContextLedgerEntry
from app.payment_rails import compute_milestone_release
from app.schemas_context_risk import ContextLedgerEvent
from app.services.context_ledger_risk import (
    _bootstrap_probability,
    _event_to_features,
    _map_score_to_band,
    _reason_codes,
    score_context_event,
)

logger = logging.getLogger(__name__)


class ContextLedgerService:
    """Writes and queries Context Ledger entries."""

    _MILESTONE_EVENTS = {"pickup_confirmed", "mid_transit_verified", "settlement_released"}

    def __init__(self, session: Session, *, decision_type: str = "settlement_precheck") -> None:
        self.session = session
        self.decision_type = decision_type

    def record_decision(
        self,
        *,
        context: SettlementContext,
        decision: GovernanceDecision,
        agent_meta: AgentMeta,
        metadata: Optional[dict] = None,
    ) -> ContextLedgerEntry:
        metadata_dict: Dict[str, Any] = dict(metadata or {})
        risk_snapshot: Optional[Dict[str, Any]] = None
        risk_generated_from_empty = not bool(metadata_dict)
        risk_snapshot = self._compute_risk_snapshot(
            context=context,
            decision=decision,
            agent_meta=agent_meta,
            metadata=metadata_dict,
        )
        if risk_snapshot:
            if risk_generated_from_empty:
                risk_snapshot["auto_generated"] = True
            metadata_dict["risk"] = risk_snapshot
        payout_plan = self._build_payout_plan(
            metadata=metadata_dict,
            total_amount=float(context.amount),
            risk_score=decision.risk_score,
            corridor_id=context.corridor,
        )
        if payout_plan:
            metadata_dict["payout_plan"] = payout_plan
            if isinstance(metadata_dict.get("risk"), dict):
                metadata_dict["risk"]["payout_plan"] = dict(payout_plan)
        entry = ContextLedgerEntry(
            agent_id=agent_meta.agent_id,
            gid=agent_meta.gid,
            role_tier=agent_meta.role_tier,
            gid_hgp_version=agent_meta.gid_hgp_version,
            decision_type=self.decision_type,
            decision_status=decision.status,
            shipment_id=context.shipment_id,
            payer_id=context.payer,
            payee_id=context.payee,
            amount=float(context.amount),
            currency=context.currency,
            corridor=context.corridor,
            risk_score=decision.risk_score,
            reason_codes=json.dumps(decision.reason_codes),
            policies_applied=json.dumps(decision.policies_applied),
            economic_justification=context.economic_justification,
            metadata_json=json.dumps(metadata_dict),
        )
        self.session.add(entry)
        self.session.flush()
        self.session.refresh(entry)
        return entry

    def get_decisions_for_shipment(self, shipment_id: str) -> List[ContextLedgerEntry]:
        return (
            self.session.query(ContextLedgerEntry)
            .filter(ContextLedgerEntry.shipment_id == shipment_id)
            .order_by(ContextLedgerEntry.created_at.desc())
            .all()
        )

    def get_recent_decisions(self, limit: int = 50) -> List[ContextLedgerEntry]:
        return (
            self.session.query(ContextLedgerEntry)
            .order_by(ContextLedgerEntry.created_at.desc(), ContextLedgerEntry.id.desc())
            .limit(limit)
            .all()
        )

    def get_recent_context_ledger_events_with_risk(self, limit: int = 50) -> List[ContextLedgerEntry]:
        """Return the newest Context Ledger entries for the risk feed."""

        safe_limit = max(1, min(limit, 200))
        return (
            self.session.query(ContextLedgerEntry)
            .order_by(ContextLedgerEntry.created_at.desc(), ContextLedgerEntry.id.desc())
            .limit(safe_limit)
            .all()
        )

    def _compute_risk_snapshot(
        self,
        *,
        context: SettlementContext,
        decision: GovernanceDecision,
        agent_meta: AgentMeta,
        metadata: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        merged_metadata = self._merge_metadata(context, metadata)
        try:
            event = self._build_context_event(
                context=context,
                decision=decision,
                agent_meta=agent_meta,
                metadata=merged_metadata,
            )
        except Exception as build_err:  # pragma: no cover - defensive logging
            logger.warning("Failed to build ContextLedgerEvent for shipment %s: %s", context.shipment_id, build_err)
            return None

        try:
            response = score_context_event(event)
            return {
                "risk_score": response.risk_score,
                "risk_band": response.risk_band,
                "reason_codes": response.reason_codes,
                "top_features": response.top_features,
                "trace_id": response.trace_id,
                "engine": "ContextLedgerRiskModel",
                "version": response.version,
                "anomaly_score": response.anomaly_score,
            }
        except Exception as risk_err:  # pragma: no cover - defensive logging
            logger.warning(
                "Context ledger risk scoring failed for shipment %s: %s",
                context.shipment_id,
                risk_err,
            )
            return self._fallback_risk(decision, event)

    @staticmethod
    def _fallback_risk(decision: GovernanceDecision, event: ContextLedgerEvent) -> Dict[str, Any]:
        score = float(decision.risk_score)
        normalized = score / 100.0 if score > 1.0 else score
        normalized = max(0.0, min(1.0, normalized))

        features = _event_to_features(event)
        bootstrap_probability = _bootstrap_probability(features)
        probability = normalized if normalized > 0 else bootstrap_probability
        band = _map_score_to_band(probability)
        reason_codes = _reason_codes(features)
        top_features = [name for name, _ in sorted(features.items(), key=lambda kv: abs(kv[1]), reverse=True)[:3]]

        return {
            "risk_score": probability,
            "risk_band": band,
            "reason_codes": reason_codes or decision.reason_codes,
            "top_features": top_features,
            "trace_id": "fallback-risk",
            "engine": "ContextLedgerRiskModel",
            "version": "fallback",
            "anomaly_score": 0.0,
        }

    @staticmethod
    def _merge_metadata(context: SettlementContext, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine context metadata with provided metadata defensively."""
        base = metadata or {}
        context_meta = getattr(context, "metadata", {}) or {}
        if not isinstance(context_meta, dict):
            context_meta = {}
        if not isinstance(base, dict):
            base = {}
        # Context metadata is considered the baseline; explicit metadata overrides keys.
        merged: Dict[str, Any] = {**context_meta, **base}
        return merged

    def _build_payout_plan(
        self,
        *,
        metadata: Dict[str, Any],
        total_amount: float,
        risk_score: float,
        corridor_id: str,
    ) -> Optional[Dict[str, Any]]:
        event_type = str(metadata.get("event_type") or self.decision_type)
        risk_band = None
        if isinstance(metadata.get("risk"), dict):
            risk_band = metadata["risk"].get("risk_band")
        plan = compute_milestone_release(
            risk_score=risk_score,
            event_type=event_type,
            base_total_amount=total_amount,
            corridor_id=corridor_id,
            risk_band=risk_band,
        )
        if plan.event_type not in self._MILESTONE_EVENTS:
            return None

        plan_dict = plan.as_dict()
        plan_dict["computed_at"] = datetime.now(timezone.utc).isoformat()
        return plan_dict

    def _build_context_event(
        self,
        *,
        context: SettlementContext,
        decision: GovernanceDecision,
        agent_meta: AgentMeta,
        metadata: Dict[str, Any],
    ) -> ContextLedgerEvent:
        event_id = str(
            metadata.get("event_id")
            or f"{context.shipment_id}:{self.decision_type}:{agent_meta.agent_id}:{int(decision.decided_at.timestamp())}"
        )

        event_type = metadata.get("event_type")
        if not event_type and any(code.upper() == "REVERSAL_EVENT" for code in decision.reason_codes):
            event_type = "REVERSAL"
        event_type = (event_type or self.decision_type).upper()

        settlement_channel = str(
            metadata.get("settlement_channel")
            or metadata.get("channel")
            or metadata.get("rail")
            or "BANK"
        )

        counterparty_id = str(
            metadata.get("counterparty_id")
            or metadata.get("payee_id")
            or context.payee
            or context.payer
            or "UNKNOWN"
        )
        counterparty_role = str(
            metadata.get("counterparty_role")
            or metadata.get("payee_role")
            or metadata.get("counterparty_type")
            or ("carrier" if context.payee else "buyer")
        ).lower()
        if counterparty_role not in {"buyer", "seller", "carrier", "broker", "anchor"}:
            counterparty_role = "carrier"

        timestamp = decision.decided_at if isinstance(decision.decided_at, datetime) else datetime.now(timezone.utc)

        return ContextLedgerEvent(
            event_id=event_id,
            timestamp=timestamp,
            amount=float(context.amount),
            currency=context.currency,
            corridor_id=context.corridor,
            counterparty_id=counterparty_id,
            counterparty_role=counterparty_role,  # type: ignore[arg-type]
            settlement_channel=settlement_channel,
            event_type=event_type,
            recent_event_count_24h=self._coerce_int(metadata.get("recent_event_count_24h")),
            recent_failed_count_7d=self._coerce_int(metadata.get("recent_failed_count_7d")),
            route_notional_7d_usd=self._coerce_float(metadata.get("route_notional_7d_usd")),
            counterparty_notional_30d_usd=self._coerce_float(metadata.get("counterparty_notional_30d_usd")),
        )

    @staticmethod
    def _coerce_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            if value is None:
                return default
            return int(value)
        except (TypeError, ValueError):
            return default
