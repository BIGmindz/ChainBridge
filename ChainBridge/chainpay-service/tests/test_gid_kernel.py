from decimal import Decimal

import pytest

from app.governance.gid_kernel import (
    GIDKernel,
    GIDKernelConfig,
    GovernanceDecision,
    InMemoryContextLedgerClient,
    SettlementContext,
)
from app.governance.models import AgentMeta, VerificationResult


class LowRiskStub:
    def verify_material_facts(self, context: SettlementContext):  # pragma: no cover - stub used in tests
        return []


class HighRiskStubEngine:
    def score_settlement(self, context: SettlementContext) -> int:  # pragma: no cover - stub used in tests
        return 95


class LowRiskStubEngine:
    def score_settlement(self, context: SettlementContext) -> int:  # pragma: no cover - stub used in tests
        return 10


class RejectingSoRValidator:
    def verify_material_facts(self, context: SettlementContext):  # pragma: no cover - stub used in tests
        return [
            VerificationResult(field="shipment_id", verified=False, source="TEST", details="mismatch"),
        ]


TEST_AGENT_META = AgentMeta(agent_id="Cody", gid="GID-01", role_tier=2, gid_hgp_version="1.0")


@pytest.fixture
def base_context() -> SettlementContext:
    return SettlementContext(
        shipment_id="SHIP-123",
        payer="payer_co",
        payee="carrier_inc",
        amount=Decimal("1000.00"),
        currency="USD",
        corridor="US-MX",
        economic_justification="milestone_release",
    )


def test_approve_low_risk_settlement(base_context):
    ledger = InMemoryContextLedgerClient()
    kernel = GIDKernel(
        sor_validator=LowRiskStub(),
        risk_engine=LowRiskStubEngine(),
        ledger_client=ledger,
        agent_meta=TEST_AGENT_META,
    )

    decision = kernel.evaluate_settlement(base_context)

    assert decision.status == "APPROVE"
    assert decision.risk_score == 10
    assert "L1_CodeEqualsCash" in decision.policies_applied
    assert len(ledger.records) == 1


def test_freeze_high_risk_settlement(base_context):
    ledger = InMemoryContextLedgerClient()
    kernel = GIDKernel(
        config=GIDKernelConfig(risk_freeze_threshold=90),
        sor_validator=LowRiskStub(),
        risk_engine=HighRiskStubEngine(),
        ledger_client=ledger,
        agent_meta=TEST_AGENT_META,
    )

    decision = kernel.evaluate_settlement(base_context)

    assert decision.status == "FREEZE"
    assert decision.reason_codes == ["L3_RISK_THRESHOLD_EXCEEDED"]
    assert len(ledger.records) == 1


def test_reject_missing_economic_justification(base_context):
    ledger = InMemoryContextLedgerClient()
    context = base_context.model_copy(update={"economic_justification": None})
    kernel = GIDKernel(ledger_client=ledger, agent_meta=TEST_AGENT_META)

    decision = kernel.evaluate_settlement(context)

    assert decision.status == "REJECT"
    assert decision.reason_codes == ["L1_ECONOMIC_JUSTIFICATION_MISSING"]
    assert len(ledger.records) == 1


def test_reject_on_sor_failure(base_context):
    ledger = InMemoryContextLedgerClient()
    kernel = GIDKernel(
        sor_validator=RejectingSoRValidator(),
        ledger_client=ledger,
        agent_meta=TEST_AGENT_META,
    )

    decision = kernel.evaluate_settlement(base_context)

    assert decision.status == "REJECT"
    assert decision.reason_codes == ["L2_VERIFICATION_FAILED"]
    assert len(ledger.records) == 1
    assert ledger.records[0]["metadata"]["failed_fields"] == ["shipment_id"]


def test_context_ledger_called(base_context):
    ledger = InMemoryContextLedgerClient()
    kernel = GIDKernel(ledger_client=ledger, agent_meta=TEST_AGENT_META)

    decision = kernel.evaluate_settlement(base_context)

    assert isinstance(decision, GovernanceDecision)
    assert len(ledger.records) == 1
