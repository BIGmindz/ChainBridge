"""Event router bridging IoT telemetry with token engines.

This module now contains two routing layers:

1. ``IoTEventRouter`` – legacy helper that converts normalized telemetry into
   MT-01 tokens (kept for backward compatibility).
2. ``GlobalEventRouter`` – the deterministic orchestrator that wires events to
   the token router, risk adapter, SxT proof pipeline, governance gate,
   ChainPay settlement client, and Operator Console adapter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Union

from chainbridge.chainiq.risk_client import (
    ChainIQRiskClient,
    RiskEvaluationRequest,
    RiskEvaluationResult,
)
from chainbridge.chainpay.settlement_client import (
    SettlementClient,
    SettlementRequest,
    SettlementResponse,
)
from chainbridge.events.oc_adapter import OCAdapter, OCEvent
from chainbridge.events.orchestrator import EventOrchestrator, OrchestratorConfig
from chainbridge.events.token_router import TokenRouter, TokenRoutingResult
from chainbridge.governance.alex_gate import AlexGate, GovernanceDecision
from chainbridge.sxt.proof_client import ProofClient, ProofRequest, ProofResult
from chainbridge.tokens.base_token import BaseToken
from chainbridge.tokens.mt01 import MT01Token

from ..chainsense.geofence import GeofenceEvent
from ..chainsense.mt01_builder import MT01Builder, MT01Context
from ..chainsense.normalizer import TelemetryRecord
from .schemas import BaseEvent, EventType, RoutingDecision, RoutingResult

logger = logging.getLogger(__name__)


@dataclass
class IoTRoutingResult:
    mt01_tokens: List[MT01Token]
    geofence_events: List[GeofenceEvent]


class IoTEventRouter:
    """Routes normalized events into the MT-01 builder pipeline."""

    def __init__(self, mt01_builder: MT01Builder):
        self._mt01_builder = mt01_builder

    async def route(
        self,
        *,
        record: TelemetryRecord,
        context: MT01Context,
        geofence_events: List[GeofenceEvent],
    ) -> IoTRoutingResult:
        tokens = self._mt01_builder.build(context, record, geofence_events)
        if tokens:
            logger.debug(
                "Generated %s MT-01 tokens for shipment %s",
                len(tokens),
                context.st01_id,
            )
        return IoTRoutingResult(mt01_tokens=tokens, geofence_events=geofence_events)


# =============================================================================
# Global Event Router
# =============================================================================


class RouterConstraintError(RuntimeError):
    """Raised when an event violates risk/proof/governance constraints."""


class GlobalEventRouter:
    """Deterministic event orchestrator for ChainBridge."""

    def __init__(
        self,
        *,
        token_router: TokenRouter,
        risk_client: ChainIQRiskClient,
        proof_client: ProofClient,
        alex_gate: AlexGate,
        settlement_client: SettlementClient,
        oc_adapter: OCAdapter,
        orchestrator: Optional[EventOrchestrator] = None,
    ) -> None:
        self._token_router = token_router
        self._risk_client = risk_client
        self._proof_client = proof_client
        self._alex_gate = alex_gate
        self._settlement_client = settlement_client
        self._oc_adapter = oc_adapter
        self._orchestrator = orchestrator or EventOrchestrator(config=OrchestratorConfig())
        self._orchestrator.set_handler(self._handle_event)

    async def start(self) -> None:
        await self._orchestrator.start()

    async def stop(self) -> None:
        await self._orchestrator.stop()

    @property
    def orchestrator(self) -> EventOrchestrator:
        return self._orchestrator

    async def get_shipment_tokens(self, shipment_id: str, token_type: Optional[str] = None) -> List[BaseToken]:
        return await self._token_router.get_shipment_tokens(shipment_id, token_type)

    async def get_token(self, token_id: str) -> Optional[BaseToken]:
        return await self._token_router.get_token(token_id)

    async def submit(self, event: BaseEvent) -> RoutingResult:
        """Public entrypoint used by producers."""

        signature_valid = True
        if event.signature:
            signature_valid = event.verify_signature(b"router-placeholder-secret")
        if not signature_valid:
            return RoutingResult(
                event_id=event.event_id,
                decision=RoutingDecision.REJECTED,
                processing_time_ms=0,
                error_message="Invalid signature",
            )

        return await self._orchestrator.submit(event)

    # ------------------------------------------------------------------
    # Core pipeline (Risk → Proof → Governance → Settlement → OC)
    # ------------------------------------------------------------------

    async def _handle_event(self, event: BaseEvent) -> RoutingResult:
        start = datetime.now(timezone.utc)

        try:
            token_result = await self._token_router.route(event)
            tokens_snapshot = await self._token_router.get_shipment_tokens(event.parent_shipment_id)

            risk = await self._maybe_run_risk(event, token_result, tokens_snapshot)
            proof = await self._maybe_request_proof(event, token_result, risk)
            governance = await self._maybe_evaluate_governance(event, token_result, risk, proof)
            settlement = await self._maybe_trigger_settlement(event, token_result, risk, governance)

            await self._emit_oc_event(
                event,
                tokens_snapshot,
                risk,
                proof,
                settlement,
                token_result,
            )

            elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return RoutingResult(
                event_id=event.event_id,
                decision=RoutingDecision.PROCESSED,
                tokens_affected=[t.token_id for t in token_result.tokens_created] + [tid for tid, *_ in token_result.tokens_transitioned],
                tokens_created=[t.token_id for t in token_result.tokens_created],
                downstream_events=[],
                risk_signals_emitted=risk is not None,
                proof_requests_emitted=proof is not None,
                settlement_triggers=settlement is not None,
                oc_events_emitted=True,
                processing_time_ms=elapsed_ms,
                error_message=None,
                governance_required=token_result.governance_required,
            )
        except RouterConstraintError as exc:
            elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            logger.warning("Router constraint triggered for %s: %s", event.event_id, exc)
            return RoutingResult(
                event_id=event.event_id,
                decision=RoutingDecision.REJECTED,
                tokens_affected=[],
                tokens_created=[],
                downstream_events=[],
                risk_signals_emitted=False,
                proof_requests_emitted=False,
                settlement_triggers=False,
                oc_events_emitted=False,
                processing_time_ms=elapsed_ms,
                error_message=str(exc),
                governance_required=False,
            )

    async def _maybe_run_risk(
        self,
        event: BaseEvent,
        token_result: TokenRoutingResult,
        tokens: List[BaseToken],
    ) -> Optional[RiskEvaluationResult]:
        if not (token_result.tokens_created or token_result.tokens_transitioned or token_result.tokens_updated):
            return None

        request = RiskEvaluationRequest(
            shipment_id=event.parent_shipment_id,
            event_type=event.event_type.value if isinstance(event.event_type, EventType) else str(event.event_type),
            tokens=[token.to_dict() for token in tokens],
            actor_id=event.actor_id,
            anomalies=token_result.warnings,
            requires_proof_hint=token_result.proof_required,
        )
        result = await self._risk_client.evaluate(request)

        if result.freeze or result.halt_transition:
            raise RouterConstraintError(f"Risk engine blocked transition: {result.message or result.recommended_action}")
        return result

    async def _maybe_request_proof(
        self,
        event: BaseEvent,
        token_result: TokenRoutingResult,
        risk: Optional[RiskEvaluationResult],
    ) -> Optional[ProofResult]:
        requires_proof = token_result.proof_required or (risk.requires_proof if risk else False)
        if not requires_proof:
            return None

        target_token = await self._select_proof_token(token_result)
        if not target_token:
            raise RouterConstraintError("Proof requested but no target token found")

        proof_request = ProofRequest(
            proof_type=self._infer_proof_type(event.event_type),
            shipment_id=event.parent_shipment_id,
            token_id=target_token.token_id,
            token_type=target_token.token_type,
            payload_hash=event.event_id,
            metadata={"event_type": event.event_type.value if isinstance(event.event_type, EventType) else str(event.event_type)},
        )

        proof_result = await self._proof_client.request_proof(proof_request)
        if not proof_result.is_valid:
            raise RouterConstraintError("Proof computation rejected the event")
        return proof_result

    async def _maybe_evaluate_governance(
        self,
        event: BaseEvent,
        token_result: TokenRoutingResult,
        risk: Optional[RiskEvaluationResult],
        proof: Optional[ProofResult],
    ) -> Optional[GovernanceDecision]:
        if not (token_result.tokens_transitioned or token_result.governance_required):
            return None

        if not token_result.tokens_transitioned:
            logger.warning(
                "Governance required but no transitions recorded for event %s",
                event.event_id,
            )
            return None

        latest_transition = token_result.tokens_transitioned[-1]
        token_id, old_state, new_state = latest_transition
        token = await self._token_router.get_token(token_id)
        if not token:
            return None

        decision = await self._alex_gate.evaluate(
            token_type=token.token_type,
            current_state=old_state,
            new_state=new_state,
            risk_score=risk.risk_score if risk else 0,
            requires_proof=token_result.proof_required,
            proof_attached=bool(token.proof_hash or (proof and proof.is_valid)),
            disputes_open=0,
        )
        if decision.blocked:
            raise RouterConstraintError(decision.reason)
        return decision

    async def _maybe_trigger_settlement(
        self,
        event: BaseEvent,
        token_result: TokenRoutingResult,
        risk: Optional[RiskEvaluationResult],
        decision: Optional[GovernanceDecision],
    ) -> Optional[SettlementResponse]:
        trigger = False
        stage = "PARTIAL_RELEASE"
        for token_id, _, new_state in token_result.tokens_transitioned:
            token = await self._token_router.get_token(token_id)
            if not token:
                continue
            if token.token_type == "ST-01" and new_state == "DELIVERED":
                trigger = True
                stage = "PARTIAL_RELEASE"
            if token.token_type == "ST-01" and new_state == "SETTLED":
                trigger = True
                stage = "FINAL_RELEASE"

        if not trigger:
            return None

        if risk and risk.risk_score >= 60:
            raise RouterConstraintError("High risk blocks settlement")
        if decision and decision.blocked:
            raise RouterConstraintError(decision.reason)

        request = SettlementRequest(
            st01_id=event.parent_shipment_id,
            it01_id=event.parent_shipment_id.replace("ST01", "IT01"),
            pt01_id=None,
            amount=1.0,
            currency="USD",
            stage=stage,
            reason=f"Auto-trigger {stage.lower()} after {event.event_type}",
            metadata={"event_id": event.event_id},
        )
        response = await self._settlement_client.trigger(request)
        if not response.accepted:
            raise RouterConstraintError(response.message)
        return response

    async def _emit_oc_event(
        self,
        event: BaseEvent,
        tokens: List[BaseToken],
        risk: Optional[RiskEvaluationResult],
        proof: Optional[ProofResult],
        settlement: Optional[SettlementResponse],
        token_result: TokenRoutingResult,
    ) -> None:
        change_from = None
        change_to = None
        if token_result.tokens_transitioned:
            _, change_from, change_to = token_result.tokens_transitioned[-1]

        eta_adjustment = None
        payload = event.payload
        if isinstance(payload, dict):
            eta_adjustment = payload.get("eta_adjustment_minutes") or payload.get("eta_delta_minutes")
        else:
            eta_adjustment = getattr(payload, "eta_adjustment_minutes", None)

        oc_event = OCEvent(
            shipment_id=event.parent_shipment_id,
            tokens=[token.to_dict() for token in tokens],
            risk={
                "risk_score": risk.risk_score if risk else 0,
                "risk_label": risk.risk_label if risk else "LOW",
                "confidence": risk.confidence if risk else 0,
                "anomalies": risk.anomalies if risk else [],
            },
            anomalies=token_result.warnings,
            timeline=[
                {
                    "token_id": tid,
                    "from": old,
                    "to": new,
                }
                for tid, old, new in token_result.tokens_transitioned
            ],
            proofs=[
                {
                    "proof_hash": proof.proof_hash if proof else None,
                    "verdict": proof.verdict if proof else None,
                }
            ],
            settlement={
                "pt01_state": settlement.pt01_state if settlement else None,
                "xrpl_tx_hash": settlement.xrpl_tx_hash if settlement else None,
            },
            actor=event.actor_id,
            event_type=event.event_type.value if isinstance(event.event_type, EventType) else str(event.event_type),
            updated_at=datetime.now(timezone.utc),
            change_from=change_from,
            change_to=change_to,
            eta_adjustment_minutes=eta_adjustment,
            active_anomalies=token_result.warnings,
        )
        await self._oc_adapter.emit(oc_event)

    async def _select_proof_token(self, result: TokenRoutingResult) -> Optional[BaseToken]:
        candidates = list(result.tokens_created)
        for token_id, *_ in result.tokens_transitioned:
            token = await self._token_router.get_token(token_id)
            if token:
                candidates.append(token)
        if not candidates:
            return None
        # Prefer AT-02 then MT-01, else first
        for token in candidates:
            if token.token_type in {"AT-02", "MT-01"}:
                return token
        return candidates[-1]

    @staticmethod
    def _infer_proof_type(event_type: Union[EventType, str]) -> str:
        mapping = {
            EventType.IOT_ALERT_CRITICAL: "ROUTE_DEVIATION",
            EventType.IOT_GEOFENCE_ENTER: "LAYOVER",
            EventType.IOT_GEOFENCE_EXIT: "DEPARTURE",
            EventType.TOKEN_TRANSITION: "TOKEN",
        }
        if isinstance(event_type, EventType):
            return mapping.get(event_type, "ACCESSORIAL")
        try:
            evt = EventType(event_type)
            return mapping.get(evt, "ACCESSORIAL")
        except ValueError:
            return "ACCESSORIAL"


__all__ = ["IoTEventRouter", "IoTRoutingResult", "GlobalEventRouter", "RouterConstraintError"]
