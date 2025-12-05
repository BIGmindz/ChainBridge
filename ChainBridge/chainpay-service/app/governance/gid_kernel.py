"""GID Kernel v0.1 for ChainPay pre-settlement governance.

This module implements a minimal governance middleware that enforces the
GID-HGP v1.0 laws before any settlement request can proceed. It deliberately
stops short of moving funds; it only evaluates whether a proposed settlement
should be APPROVED, FREEZE'd, or REJECTED and records that decision so the
execution layer can act accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

from app.database import SessionLocal
from app.governance.models import (
    AgentMeta,
    GovernanceDecision,
    SettlementContext,
    VerificationResult,
)
from app.services.context_ledger_service import ContextLedgerService
from pydantic import BaseModel


class GIDKernelConfig(BaseModel):
    risk_freeze_threshold: int = 90


# ---------------------------------------------------------------------------
# Interfaces (PROPOSED — replace with real integrations later)
# ---------------------------------------------------------------------------


class SoRValidator(Protocol):  # pragma: no cover - interface only
    """Systems-of-Record verification interface (PROPOSED)."""

    def verify_material_facts(self, context: SettlementContext) -> List[VerificationResult]: ...


class RiskEngineClient(Protocol):  # pragma: no cover - interface only
    """ChainIQ risk scoring interface (PROPOSED)."""

    def score_settlement(self, context: SettlementContext) -> int: ...


class ContextLedgerClient(Protocol):  # pragma: no cover - interface only
    """Context Ledger logging interface (PROPOSED)."""

    def record_governance_decision(
        self,
        *,
        context: SettlementContext,
        decision: GovernanceDecision,
        agent_meta: AgentMeta,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None: ...


# ---------------------------------------------------------------------------
# Stub implementations to keep v0.1 self-contained
# ---------------------------------------------------------------------------


class StubSoRValidator:
    """Accept-all verifier while we define real SoR clients."""

    def verify_material_facts(self, context: SettlementContext) -> List[VerificationResult]:
        return [
            VerificationResult(
                field="shipment_id",
                verified=True,
                source="PROPOSED_SoR",
                details="Stub verification accepted",
            )
        ]


class StubRiskEngineClient:
    """Simple risk scoring heuristic for MVP."""

    def score_settlement(self, context: SettlementContext) -> int:
        # PROPOSED heuristic: scale by amount for now.
        if context.amount >= Decimal("100000"):
            return 95
        if context.amount >= Decimal("50000"):
            return 80
        return 15


@dataclass
class InMemoryContextLedgerClient:
    """Captures governance decisions for inspection in tests."""

    records: List[Dict[str, Any]] = field(default_factory=list)

    def record_governance_decision(
        self,
        *,
        context: SettlementContext,
        decision: GovernanceDecision,
        agent_meta: AgentMeta,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.records.append(
            {
                "context": context.model_dump(),
                "decision": decision.model_dump(),
                "metadata": metadata or {},
            }
        )


class SQLContextLedgerClient:
    """Default implementation that persists decisions to the Context Ledger."""

    def __init__(self, agent_meta: AgentMeta) -> None:
        self.agent_meta = agent_meta

    def record_governance_decision(
        self,
        *,
        context: SettlementContext,
        decision: GovernanceDecision,
        agent_meta: AgentMeta,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        session = SessionLocal()
        try:
            service = ContextLedgerService(session)
            service.record_decision(
                context=context,
                decision=decision,
                agent_meta=agent_meta,
                metadata=metadata,
            )
        except Exception:
            session.rollback()
            raise
        else:
            session.commit()
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Kernel implementation
# ---------------------------------------------------------------------------


class GIDKernel:
    def __init__(
        self,
        *,
        config: Optional[GIDKernelConfig] = None,
        sor_validator: Optional[SoRValidator] = None,
        risk_engine: Optional[RiskEngineClient] = None,
        ledger_client: Optional[ContextLedgerClient] = None,
        agent_meta: Optional[AgentMeta] = None,
    ) -> None:
        self.config = config or GIDKernelConfig()
        self.sor_validator = sor_validator or StubSoRValidator()
        self.risk_engine = risk_engine or StubRiskEngineClient()
        self.agent_meta = agent_meta or AgentMeta(
            agent_id="Cody",
            gid="GID-01",
            role_tier=2,
            gid_hgp_version="1.0",
        )
        self.ledger_client = ledger_client or SQLContextLedgerClient(agent_meta=self.agent_meta)

    def evaluate_settlement(self, context: SettlementContext) -> GovernanceDecision:
        """Apply GID-HGP checks and return a decision."""

        policies = ["L1_CodeEqualsCash", "L2_TrustEqualsTruth", "L3_SecurityOverSpeed"]

        # L1: Economic justification required
        if not context.economic_justification:
            decision = GovernanceDecision(
                status="REJECT",
                reason_codes=["L1_ECONOMIC_JUSTIFICATION_MISSING"],
                risk_score=0,
                policies_applied=["L1_CodeEqualsCash"],
            )
            self._record_decision(context, decision)
            return decision

        # L2: Verify material facts via SoR
        verification_results = self.sor_validator.verify_material_facts(context)
        failed_fields = [r.field for r in verification_results if not r.verified]
        if failed_fields:
            decision = GovernanceDecision(
                status="REJECT",
                reason_codes=["L2_VERIFICATION_FAILED"],
                risk_score=0,
                policies_applied=["L2_TrustEqualsTruth"],
            )
            self._record_decision(context, decision, metadata={"failed_fields": failed_fields})
            return decision

        # L3: Risk check and Freeze protocol
        risk_score = self.risk_engine.score_settlement(context)
        if risk_score >= self.config.risk_freeze_threshold:
            decision = GovernanceDecision(
                status="FREEZE",
                reason_codes=["L3_RISK_THRESHOLD_EXCEEDED"],
                risk_score=risk_score,
                policies_applied=policies,
            )
            self._record_decision(context, decision)
            return decision

        decision = GovernanceDecision(
            status="APPROVE",
            reason_codes=[],
            risk_score=risk_score,
            policies_applied=policies,
        )
        self._record_decision(context, decision)
        return decision

    def _record_decision(
        self,
        context: SettlementContext,
        decision: GovernanceDecision,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.ledger_client.record_governance_decision(
            context=context,
            decision=decision,
            agent_meta=self.agent_meta,
            metadata=metadata,
        )


def pre_settlement_check(
    context: SettlementContext,
    kernel: Optional[GIDKernel] = None,
    agent_meta: Optional[AgentMeta] = None,
) -> GovernanceDecision:
    """Convenience entrypoint for ChainPay pipeline."""

    kernel = kernel or GIDKernel(agent_meta=agent_meta)
    return kernel.evaluate_settlement(context)
