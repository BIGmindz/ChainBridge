"""Tests for the ChainPay context-ledger risk feed endpoint."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.governance.models import AgentMeta, GovernanceDecision, SettlementContext
from app.services.context_ledger_service import ContextLedgerService


@pytest.fixture
def agent_meta() -> AgentMeta:
    return AgentMeta(agent_id="CODY", gid="GID-01", role_tier=2, gid_hgp_version="1.2.3")


@pytest.fixture
def base_context() -> SettlementContext:
    return SettlementContext(
        shipment_id="SHIP-RISK-001",
        payer="payer_co",
        payee="carrier_inc",
        amount=Decimal("25000"),
        currency="USD",
        corridor="US-BR",
        economic_justification="risk_review",
    )


@pytest.fixture
def approve_decision() -> GovernanceDecision:
    return GovernanceDecision(
        status="APPROVE",
        reason_codes=["L1_BASE"],
        risk_score=25,
        policies_applied=["L1_CodeEqualsCash"],
    )


@pytest.fixture
def freeze_decision() -> GovernanceDecision:
    return GovernanceDecision(
        status="FREEZE",
        reason_codes=["REVERSAL"],
        risk_score=92,
        policies_applied=["L3_SecurityOverSpeed"],
    )


def _record_entry(db_session, *, context, decision, agent_meta, metadata=None):
    service = ContextLedgerService(db_session)
    entry = service.record_decision(
        context=context,
        decision=decision,
        agent_meta=agent_meta,
        metadata=metadata,
    )
    db_session.commit()
    return entry


def test_context_ledger_risk_feed_returns_items_with_risk_snapshot(
    client,
    db_session,
    base_context,
    agent_meta,
    approve_decision,
    freeze_decision,
):
    rich_metadata = {
        "risk_snapshot": {
            "risk_score": 0.87,
            "risk_band": "HIGH",
            "reason_codes": ["REVERSAL_EVENT", "XRPL_CHANNEL"],
            "trace_id": "ctx-risk-123",
            "model_version": "context-ledger-risk-v1",
        }
    }
    _record_entry(
        db_session,
        context=base_context,
        decision=freeze_decision,
        agent_meta=agent_meta,
        metadata=rich_metadata,
    )
    _record_entry(
        db_session,
        context=base_context.model_copy(update={"shipment_id": "SHIP-RISK-002"}),
        decision=approve_decision,
        agent_meta=agent_meta,
        metadata=None,
    )

    response = client.get("/context-ledger/risk?limit=5")
    assert response.status_code == 200

    payload = response.json()
    assert "items" in payload
    assert len(payload["items"]) == 2
    newest = payload["items"][0]
    assert newest["shipment_id"] == "SHIP-RISK-002"
    assert newest["risk"] is None  # no metadata provided

    older = payload["items"][1]
    assert older["risk"]["risk_score"] == pytest.approx(0.87)
    assert older["risk"]["risk_band"] == "HIGH"
    assert older["risk"]["reason_codes"] == rich_metadata["risk_snapshot"]["reason_codes"]
    assert older["risk"]["trace_id"] == "ctx-risk-123"


def test_context_ledger_risk_feed_enforces_limit(client, db_session, base_context, approve_decision, agent_meta):
    for idx in range(3):
        ctx = base_context.model_copy(update={"shipment_id": f"SHIP-LIMIT-{idx}"})
        decision = approve_decision.model_copy(update={"risk_score": 10 * (idx + 1)})
        _record_entry(
            db_session,
            context=ctx,
            decision=decision,
            agent_meta=agent_meta,
            metadata=None,
        )

    response = client.get("/context-ledger/risk?limit=2")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2
    returned_shipments = [item["shipment_id"] for item in payload["items"]]
    assert returned_shipments == ["SHIP-LIMIT-2", "SHIP-LIMIT-1"]
