"""Test helpers for the Global Event Router."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from chainbridge.chainiq.risk_client import RiskEvaluationResult
from chainbridge.chainpay.settlement_client import SettlementResponse
from chainbridge.events.oc_adapter import OCAdapter
from chainbridge.events.orchestrator import EventOrchestrator, OrchestratorConfig
from chainbridge.events.router import GlobalEventRouter
from chainbridge.events.token_router import TokenRouter
from chainbridge.governance.alex_gate import AlexGate
from chainbridge.sxt.proof_client import ProofResult
from chainbridge.tokens.at02 import AT02Token
from chainbridge.tokens.base_token import BaseToken
from chainbridge.tokens.pt01 import PT01Token
from chainbridge.tokens.st01 import ST01Token


@dataclass
class StubRiskClient:
    queue: List[RiskEvaluationResult] = field(default_factory=list)
    default_score: int = 20

    async def evaluate(self, request) -> RiskEvaluationResult:  # noqa: D401 - test helper
        if self.queue:
            return self.queue.pop(0)
        return RiskEvaluationResult(
            risk_score=self.default_score,
            risk_label="LOW" if self.default_score < 30 else "MEDIUM",
            confidence=0.7,
            recommended_action="RELEASE",
            anomalies=request.anomalies,
            requires_proof=False,
            freeze=False,
            halt_transition=False,
            message="stub",
        )


@dataclass
class StubProofClient:
    succeed: bool = True
    verdict: str = "APPROVED"

    async def request_proof(self, request) -> ProofResult:  # noqa: D401
        if not self.succeed:
            return ProofResult(
                proof_hash=None,
                verified=False,
                verdict="REJECTED",
                confidence=0.1,
                metadata={"error": "forced"},
            )
        return ProofResult(
            proof_hash=f"proof-{request.token_id}",
            verified=True,
            verdict=self.verdict,
            confidence=0.99,
            metadata={"offline": True},
        )


@dataclass
class StubSettlementClient:
    accept: bool = True
    stage: str = "PARTIAL_RELEASE"

    async def trigger(self, request) -> SettlementResponse:  # noqa: D401
        if not self.accept:
            return SettlementResponse(
                accepted=False,
                pt01_state="ERROR",
                xrpl_tx_hash=None,
                message="forced failure",
            )
        return SettlementResponse(
            accepted=True,
            pt01_state=self.stage,
            xrpl_tx_hash=f"xrpl-{request.st01_id}-{self.stage}",
            message="stub",
        )


@dataclass
class RouterTestHarness:
    router: GlobalEventRouter
    token_router: TokenRouter
    risk_client: StubRiskClient
    proof_client: StubProofClient
    settlement_client: StubSettlementClient
    oc_adapter: OCAdapter


def _merge(base: Dict[str, Any], overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged = dict(base)
    if overrides:
        merged.update(overrides)
    return merged


_DEFAULT_ST01_METADATA: Dict[str, Any] = {
    "origin": "DAL",
    "destination": "LAX",
    "carrier_id": "CARR-1",
    "broker_id": "BROKER-9",
    "customer_id": "ACME",
}

_DEFAULT_AT02_METADATA: Dict[str, Any] = {
    "accessorial_type": "DETENTION",
    "amount": 125.0,
    "timestamp": "2025-01-01T00:00:00Z",
    "actor": "carrier",
    "currency": "USD",
    "policy_match_id": "policy-01",
}

_DEFAULT_PT01_METADATA: Dict[str, Any] = {
    "payment_reference": "INV-001",
    "currency": "USD",
    "amount": 5000.0,
    "escrow_account": "rEscrowSeed",
    "xrpl_tx_hash": "xrpl-seed",
    "release_schedule": {"milestones": [{"state": "FINAL_RELEASE", "amount": 5000.0}]},
}

_DEFAULT_AT02_RELATIONS = {"mt01_id": "mt01-seed"}
_DEFAULT_PT01_RELATIONS = {"it01_id": "it01-seed"}


def build_router_harness() -> RouterTestHarness:
    token_router = TokenRouter()
    risk_client = StubRiskClient()
    proof_client = StubProofClient()
    settlement_client = StubSettlementClient()
    oc_adapter = OCAdapter()
    alex_gate = AlexGate()
    orchestrator = EventOrchestrator(config=OrchestratorConfig())
    router = GlobalEventRouter(
        token_router=token_router,
        risk_client=risk_client,
        proof_client=proof_client,
        alex_gate=alex_gate,
        settlement_client=settlement_client,
        oc_adapter=oc_adapter,
        orchestrator=orchestrator,
    )
    return RouterTestHarness(
        router=router,
        token_router=token_router,
        risk_client=risk_client,
        proof_client=proof_client,
        settlement_client=settlement_client,
        oc_adapter=oc_adapter,
    )


def seed_st01(
    token_router: TokenRouter,
    shipment_id: str,
    state: str = "DISPATCHED",
    metadata: Optional[Dict[str, Any]] = None,
    relations: Optional[Dict[str, Any]] = None,
) -> ST01Token:
    token = ST01Token(
        parent_shipment_id=shipment_id,
        state=state,
        metadata=_merge(_DEFAULT_ST01_METADATA, metadata),
        relations=relations,
    )
    token_router._store_token(token)  # type: ignore[attr-defined]
    return token


def seed_at02(
    token_router: TokenRouter,
    shipment_id: str,
    state: str = "PROPOSED",
    metadata: Optional[Dict[str, Any]] = None,
    relations: Optional[Dict[str, Any]] = None,
    proof_hash: Optional[str] = None,
) -> AT02Token:
    proof_payload = None
    if proof_hash:
        proof_payload = {"hash": proof_hash}
    elif state in {"PROOF_ATTACHED", "VERIFIED", "PUBLISHED"}:
        proof_payload = {"hash": f"proof-{shipment_id}"}
    token = AT02Token(
        parent_shipment_id=shipment_id,
        state=state,
        metadata=_merge(_DEFAULT_AT02_METADATA, metadata),
        relations=_merge(_DEFAULT_AT02_RELATIONS, relations),
        proof=proof_payload,
    )
    token_router._store_token(token)  # type: ignore[attr-defined]
    return token


def seed_pt01(
    token_router: TokenRouter,
    shipment_id: str,
    state: str = "ESCROWED",
    metadata: Optional[Dict[str, Any]] = None,
    relations: Optional[Dict[str, Any]] = None,
) -> PT01Token:
    token = PT01Token(
        parent_shipment_id=shipment_id,
        state=state,
        metadata=_merge(_DEFAULT_PT01_METADATA, metadata),
        relations=_merge(_DEFAULT_PT01_RELATIONS, relations),
    )
    token_router._store_token(token)  # type: ignore[attr-defined]
    return token


def get_token(token_router: TokenRouter, token_id: str) -> Optional[BaseToken]:
    return token_router._token_store.get(token_id)  # type: ignore[attr-defined]


__all__ = [
    "build_router_harness",
    "seed_st01",
    "seed_at02",
    "seed_pt01",
    "get_token",
    "StubRiskClient",
    "StubProofClient",
    "StubSettlementClient",
    "RouterTestHarness",
]
