from decimal import Decimal
import importlib
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.governance.models import AgentMeta, GovernanceDecision, SettlementContext
from app.models import Base
from app.models_context_ledger import ContextLedgerEntry
from app.services.context_ledger_service import ContextLedgerService


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def ledger_service(db_session: Session) -> ContextLedgerService:
    return ContextLedgerService(db_session)


@pytest.fixture
def sample_context() -> SettlementContext:
    return SettlementContext(
        shipment_id="SHIP-ABC",
        payer="payer_co",
        payee="carrier_inc",
        amount=Decimal("5000"),
        currency="USD",
        corridor="US-CA",
        economic_justification="milestone_release",
    )


@pytest.fixture
def agent_meta() -> AgentMeta:
    return AgentMeta(agent_id="Cody", gid="GID-01", role_tier=2, gid_hgp_version="1.0")


@pytest.fixture
def approve_decision() -> GovernanceDecision:
    return GovernanceDecision(
        status="APPROVE",
        reason_codes=[],
        risk_score=0.1,
        policies_applied=["L1_CodeEqualsCash"],
    )


@pytest.fixture
def freeze_decision() -> GovernanceDecision:
    return GovernanceDecision(
        status="FREEZE",
        reason_codes=["L3_RISK_THRESHOLD_EXCEEDED"],
        risk_score=0.95,
        policies_applied=["L1_CodeEqualsCash", "L3_SecurityOverSpeed"],
    )


@pytest.fixture
def reject_decision_missing_justification() -> GovernanceDecision:
    return GovernanceDecision(
        status="REJECT",
        reason_codes=["L1_ECONOMIC_JUSTIFICATION_MISSING"],
        risk_score=0.0,
        policies_applied=["L1_CodeEqualsCash"],
    )


def _assert_plan_payload(plan: dict) -> None:
    required = {"event_type", "risk_band", "percentage", "release_amount", "strategy", "claim_window_days"}
    assert required.issubset(plan.keys())
    assert isinstance(plan["percentage"], float)
    assert plan["percentage"] >= 0.0
    assert isinstance(plan["release_amount"], float)
    assert plan["release_amount"] >= 0.0
    assert isinstance(plan["strategy"], str) and plan["strategy"]
    assert isinstance(plan["claim_window_days"], (int, float))
    if "requires_manual_review" in plan:
        assert isinstance(plan["requires_manual_review"], bool)
    if plan.get("delay_hours") is not None:
        assert isinstance(plan["delay_hours"], int)


def _assert_risk_payload(risk: dict) -> None:
    required_keys = {"risk_score", "risk_band", "reason_codes", "trace_id", "engine", "version"}
    assert required_keys.issubset(risk.keys())
    assert isinstance(risk["risk_score"], float)
    assert 0.0 <= risk["risk_score"] <= 1.0
    assert isinstance(risk["reason_codes"], list)
    assert isinstance(risk.get("top_features", []), list)
    assert isinstance(risk["trace_id"], str) and risk["trace_id"].strip()
    assert risk["engine"] == "ContextLedgerRiskModel"
    assert isinstance(risk["risk_band"], str)
    if isinstance(risk.get("payout_plan"), dict):
        _assert_plan_payload(risk["payout_plan"])


def _extract_risk(entry: ContextLedgerEntry):
    metadata = json.loads(entry.metadata_json or "{}")
    payout_plan = metadata.pop("payout_plan", None)
    if payout_plan:
        _assert_plan_payload(payout_plan)
    assert "risk" in metadata
    risk = metadata.pop("risk")
    _assert_risk_payload(risk)
    return risk, metadata, payout_plan


def _fake_risk_snapshot(band: str = "LOW") -> dict:
    return {
        "risk_score": 0.15 if band != "CRITICAL" else 0.95,
        "risk_band": band,
        "reason_codes": ["UNIT_TEST_SCENARIO"],
        "top_features": ["unit_test"],
        "trace_id": f"trace-{band.lower()}",
        "engine": "ContextLedgerRiskModel",
        "version": "unit-test",
        "anomaly_score": 0.01,
    }


def test_context_ledger_service_module_importable():
    module = importlib.import_module("app.services.context_ledger_service")
    assert module is not None


def test_context_ledger_service_exposes_service_class():
    module = importlib.import_module("app.services.context_ledger_service")
    assert hasattr(module, "ContextLedgerService")
    assert hasattr(module.ContextLedgerService, "record_decision")


def test_record_approve_decision_persists_correct_fields(db_session, ledger_service, sample_context, approve_decision, agent_meta):
    entry = ledger_service.record_decision(
        context=sample_context,
        decision=approve_decision,
        agent_meta=agent_meta,
    )
    db_session.commit()

    assert entry.decision_status == "APPROVE"
    assert entry.shipment_id == "SHIP-ABC"
    assert entry.payer_id == sample_context.payer
    assert entry.payee_id == sample_context.payee
    assert entry.currency == sample_context.currency
    assert entry.corridor == sample_context.corridor
    assert entry.economic_justification == sample_context.economic_justification
    assert entry.amount == float(sample_context.amount)
    assert entry.risk_score == approve_decision.risk_score
    assert json.loads(entry.reason_codes) == []
    assert json.loads(entry.policies_applied) == ["L1_CodeEqualsCash"]
    assert entry.decision_type == "settlement_precheck"
    risk, remaining_metadata, payout_plan = _extract_risk(entry)
    assert remaining_metadata == {}
    assert payout_plan is None
    assert risk["risk_band"].upper() in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_record_freeze_decision_persists_risk_and_reason_codes(db_session, ledger_service, sample_context, freeze_decision, agent_meta):
    metadata = {"alert": "risk_review_required"}
    entry = ledger_service.record_decision(
        context=sample_context,
        decision=freeze_decision,
        agent_meta=agent_meta,
        metadata=metadata,
    )
    db_session.commit()

    assert entry.decision_status == "FREEZE"
    assert entry.risk_score == pytest.approx(0.95)
    assert "L3_RISK_THRESHOLD_EXCEEDED" in json.loads(entry.reason_codes)
    risk, remaining_metadata, payout_plan = _extract_risk(entry)
    assert remaining_metadata == metadata
    assert "RISK" not in {k.upper() for k in metadata.keys()}
    assert payout_plan is None
    assert risk["risk_band"].upper() in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_get_decisions_for_shipment_returns_expected_records(db_session, ledger_service, sample_context, approve_decision, agent_meta):
    ledger_service.record_decision(context=sample_context, decision=approve_decision, agent_meta=agent_meta)
    second_context = sample_context.model_copy(update={"shipment_id": "SHIP-OTHER"})
    ledger_service.record_decision(context=second_context, decision=approve_decision, agent_meta=agent_meta)
    db_session.commit()

    results = ledger_service.get_decisions_for_shipment("SHIP-ABC")
    assert len(results) == 1
    assert results[0].shipment_id == "SHIP-ABC"
    assert results[0].payer_id == sample_context.payer
    assert all(entry.shipment_id == "SHIP-ABC" for entry in results)


def test_ledger_write_failure_raises(db_session, ledger_service, sample_context, approve_decision, agent_meta, monkeypatch):
    def fail_flush():
        raise RuntimeError("flush failed")

    monkeypatch.setattr(db_session, "flush", fail_flush)

    with pytest.raises(RuntimeError):
        ledger_service.record_decision(context=sample_context, decision=approve_decision, agent_meta=agent_meta)


def test_record_reject_decision_captures_reason_and_metadata(
    db_session,
    ledger_service,
    sample_context,
    reject_decision_missing_justification,
    agent_meta,
):
    metadata = {"failed_fields": ["economic_justification"]}
    entry = ledger_service.record_decision(
        context=sample_context,
        decision=reject_decision_missing_justification,
        agent_meta=agent_meta,
        metadata=metadata,
    )
    db_session.commit()

    assert entry.decision_status == "REJECT"
    assert json.loads(entry.reason_codes) == ["L1_ECONOMIC_JUSTIFICATION_MISSING"]
    assert json.loads(entry.policies_applied) == ["L1_CodeEqualsCash"]
    risk, remaining_metadata, payout_plan = _extract_risk(entry)
    assert remaining_metadata == metadata
    assert entry.risk_score == 0
    assert payout_plan is None


def test_record_decision_respects_custom_decision_type(
    db_session,
    sample_context,
    approve_decision,
    agent_meta,
):
    custom_service = ContextLedgerService(db_session, decision_type="claim_window_release")
    entry = custom_service.record_decision(
        context=sample_context,
        decision=approve_decision,
        agent_meta=agent_meta,
    )
    db_session.commit()

    assert entry.decision_type == "claim_window_release"


@pytest.mark.parametrize(
    "event_type, expected_metadata",
    [
        ("PICKUP_CONFIRMED", {"release_pct": 0.20, "sequence": 1}),
        ("POD_CONFIRMED", {"release_pct": 0.70, "sequence": 2}),
        ("CLAIM_WINDOW_CLOSED", {"release_pct": 0.10, "sequence": 3}),
    ],
)
def test_context_ledger_records_milestone_events(
    db_session,
    sample_context,
    approve_decision,
    agent_meta,
    event_type,
    expected_metadata,
):
    service = ContextLedgerService(db_session, decision_type=event_type)
    entry = service.record_decision(
        context=sample_context,
        decision=approve_decision,
        agent_meta=agent_meta,
        metadata={**expected_metadata, "event_type": event_type},
    )
    db_session.commit()

    assert entry.decision_type == event_type
    assert entry.shipment_id == sample_context.shipment_id
    assert entry.payer_id == sample_context.payer
    assert entry.payee_id == sample_context.payee
    assert entry.amount == float(sample_context.amount)
    assert entry.currency == sample_context.currency
    risk, remaining_metadata, payout_plan = _extract_risk(entry)
    assert remaining_metadata == {**expected_metadata, "event_type": event_type}
    assert payout_plan is not None
    expected_event = {
        "PICKUP_CONFIRMED": "pickup_confirmed",
        "POD_CONFIRMED": "mid_transit_verified",
        "CLAIM_WINDOW_CLOSED": "settlement_released",
    }[event_type]
    assert payout_plan["event_type"] == expected_event
    assert isinstance(payout_plan["claim_window_days"], (int, float))
    assert risk["payout_plan"] == payout_plan
    assert risk["risk_band"].upper() in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_payout_plan_copied_into_risk_metadata(
    db_session,
    sample_context,
    approve_decision,
    agent_meta,
    monkeypatch,
):
    monkeypatch.setattr(
        ContextLedgerService,
        "_compute_risk_snapshot",
        lambda self, **_: _fake_risk_snapshot("LOW"),
    )
    service = ContextLedgerService(db_session, decision_type="PICKUP_CONFIRMED")
    entry = service.record_decision(
        context=sample_context,
        decision=approve_decision,
        agent_meta=agent_meta,
        metadata={"event_type": "PICKUP_CONFIRMED"},
    )

    risk, remaining_metadata, payout_plan = _extract_risk(entry)
    assert remaining_metadata == {"event_type": "PICKUP_CONFIRMED"}
    assert payout_plan is not None
    assert payout_plan["event_type"] == "pickup_confirmed"
    assert payout_plan["percentage"] == pytest.approx(20.0)
    assert payout_plan["release_amount"] == pytest.approx(float(sample_context.amount) * 0.20)
    assert payout_plan["claim_window_days"] == 3
    assert risk["payout_plan"] == payout_plan


def test_high_risk_final_event_requires_manual_review(
    db_session,
    sample_context,
    approve_decision,
    agent_meta,
    monkeypatch,
):
    monkeypatch.setattr(
        ContextLedgerService,
        "_compute_risk_snapshot",
        lambda self, **_: _fake_risk_snapshot("HIGH"),
    )
    service = ContextLedgerService(db_session, decision_type="SETTLEMENT_RELEASED")
    entry = service.record_decision(
        context=sample_context,
        decision=approve_decision.model_copy(update={"risk_score": 0.7}),
        agent_meta=agent_meta,
        metadata={"event_type": "SETTLEMENT_RELEASED"},
    )

    risk, remaining_metadata, payout_plan = _extract_risk(entry)
    assert remaining_metadata == {"event_type": "SETTLEMENT_RELEASED"}
    assert payout_plan is not None
    assert payout_plan["event_type"] == "settlement_released"
    assert payout_plan["percentage"] == pytest.approx(30.0)
    assert payout_plan["strategy"] == "manual_review"
    assert payout_plan.get("claim_window_days") == 7
    assert payout_plan.get("requires_manual_review") is True
    assert risk["payout_plan"] == payout_plan


def test_critical_risk_holds_all_tranches(
    db_session,
    sample_context,
    approve_decision,
    agent_meta,
    monkeypatch,
):
    monkeypatch.setattr(
        ContextLedgerService,
        "_compute_risk_snapshot",
        lambda self, **_: _fake_risk_snapshot("CRITICAL"),
    )
    service = ContextLedgerService(db_session, decision_type="CLAIM_WINDOW_CLOSED")
    entry = service.record_decision(
        context=sample_context,
        decision=approve_decision.model_copy(update={"risk_score": 0.95}),
        agent_meta=agent_meta,
        metadata={"event_type": "CLAIM_WINDOW_CLOSED"},
    )

    risk, remaining_metadata, payout_plan = _extract_risk(entry)
    assert remaining_metadata == {"event_type": "CLAIM_WINDOW_CLOSED"}
    assert payout_plan is not None
    assert payout_plan["event_type"] == "settlement_released"
    assert payout_plan["percentage"] == pytest.approx(100.0)
    assert payout_plan["release_amount"] == pytest.approx(float(sample_context.amount))
    assert payout_plan["strategy"] == "manual_review"
    assert risk["payout_plan"] == payout_plan


def test_non_milestone_events_do_not_add_payout_plan(
    db_session,
    sample_context,
    freeze_decision,
    agent_meta,
    monkeypatch,
):
    monkeypatch.setattr(
        ContextLedgerService,
        "_compute_risk_snapshot",
        lambda self, **_: _fake_risk_snapshot("MEDIUM"),
    )
    service = ContextLedgerService(db_session, decision_type="reversal_detected")
    entry = service.record_decision(
        context=sample_context,
        decision=freeze_decision,
        agent_meta=agent_meta,
        metadata={"event_type": "REVERSAL"},
    )

    risk, remaining_metadata, payout_plan = _extract_risk(entry)
    assert remaining_metadata == {"event_type": "REVERSAL"}
    assert payout_plan is None
    assert "payout_plan" not in risk


@pytest.mark.parametrize(
    "decision_type, decision_status, reason_codes, metadata",
    [
        ("context_created", "PENDING", ["CTX_CREATED"], {"event": "contract_created"}),
        ("pickup_confirmed", "APPROVE_PENDING_RELEASE", ["PICKUP_CONFIRMED"], {"milestone": "pickup"}),
        ("delivery_confirmed", "APPROVE", ["DELIVERY_CONFIRMED"], {"milestone": "pod"}),
        ("reversal_detected", "FREEZE", ["REVERSAL_EVENT"], {"exception": "reversal"}),
        ("settlement_released", "APPROVE", ["SETTLEMENT_RELEASED"], {"milestone": "claims_closed"}),
    ],
)
def test_context_ledger_records_core_events(
    db_session,
    sample_context,
    agent_meta,
    decision_type,
    decision_status,
    reason_codes,
    metadata,
):
    decision = GovernanceDecision(
        status=decision_status,
        reason_codes=reason_codes,
        risk_score=0.42,
        policies_applied=["L1_CodeEqualsCash"],
    )
    service = ContextLedgerService(db_session, decision_type=decision_type)
    entry = service.record_decision(
        context=sample_context,
        decision=decision,
        agent_meta=agent_meta,
        metadata=metadata,
    )
    db_session.commit()

    stored = (
        db_session.query(ContextLedgerEntry)
        .filter(ContextLedgerEntry.id == entry.id)
        .first()
    )
    assert stored is not None
    assert stored.decision_type == decision_type
    assert stored.decision_status == decision_status
    assert stored.shipment_id == sample_context.shipment_id
    assert stored.payer_id == sample_context.payer
    assert stored.payee_id == sample_context.payee
    assert stored.amount == float(sample_context.amount)
    assert stored.currency == sample_context.currency
    assert json.loads(stored.reason_codes) == reason_codes
    risk, remaining_metadata, payout_plan = _extract_risk(stored)
    assert remaining_metadata == metadata
    if decision_type.upper() in {"PICKUP_CONFIRMED", "DELIVERY_CONFIRMED", "SETTLEMENT_RELEASED"}:
        assert isinstance(payout_plan, dict)
    else:
        assert payout_plan is None


def test_get_recent_decisions_respects_limit_and_order(
    db_session,
    ledger_service,
    sample_context,
    approve_decision,
    agent_meta,
):
    for idx in range(3):
        dynamic_context = sample_context.model_copy(
            update={"shipment_id": f"SHIP-{idx}", "amount": Decimal("5000") + Decimal(idx)}
        )
        ledger_service.record_decision(context=dynamic_context, decision=approve_decision, agent_meta=agent_meta)
    db_session.commit()

    recent_entries = ledger_service.get_recent_decisions(limit=2)
    assert len(recent_entries) == 2
    assert {entry.shipment_id for entry in recent_entries} == {"SHIP-2", "SHIP-1"}


def test_risk_snapshot_elevates_for_reversal_decisions(
    db_session,
    ledger_service,
    sample_context,
    approve_decision,
    freeze_decision,
    agent_meta,
):
    low_entry = ledger_service.record_decision(
        context=sample_context,
        decision=approve_decision,
        agent_meta=agent_meta,
    )

    high_context = sample_context.model_copy(update={"amount": Decimal("350000")})
    high_metadata = {
        "event_type": "REVERSAL",
        "settlement_channel": "XRPL",
        "recent_event_count_24h": 60,
        "recent_failed_count_7d": 8,
        "route_notional_7d_usd": 2_500_000,
        "counterparty_notional_30d_usd": 4_000_000,
        "counterparty_role": "broker",
    }
    reversal_service = ContextLedgerService(db_session, decision_type="reversal_detected")
    high_entry = reversal_service.record_decision(
        context=high_context,
        decision=freeze_decision,
        agent_meta=agent_meta,
        metadata=high_metadata,
    )

    low_risk, _, low_plan = _extract_risk(low_entry)
    high_risk, high_meta, high_plan = _extract_risk(high_entry)
    assert low_plan is None
    assert high_plan is None
    assert high_meta == high_metadata
    assert high_risk["risk_score"] > low_risk["risk_score"]
    assert high_risk["risk_band"].upper() in {"HIGH", "CRITICAL"}
    assert any(
        code in high_risk["reason_codes"]
        for code in {"REPEATED_REVERSALS_ON_ROUTE", "XRPL_SETTLEMENT_CHANNEL"}
    )


def test_risk_snapshot_includes_reason_codes_in_metadata(
    db_session,
    ledger_service,
    sample_context,
    agent_meta,
):
    metadata = {
        "event_type": "POD_CONFIRMED",
        "settlement_channel": "BANK",
        "recent_event_count_24h": 5,
        "recent_failed_count_7d": 0,
    }
    decision = GovernanceDecision(
        status="APPROVE",
        reason_codes=["DELIVERY_CONFIRMED"],
        risk_score=0.3,
        policies_applied=["L1_CodeEqualsCash"],
    )
    entry = ledger_service.record_decision(
        context=sample_context,
        decision=decision,
        agent_meta=agent_meta,
        metadata=metadata,
    )

    risk, remaining_metadata, payout_plan = _extract_risk(entry)
    assert remaining_metadata == metadata
    assert payout_plan is not None
    assert risk["risk_band"].upper() in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
