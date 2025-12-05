"""Unit tests for the settlement API service."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base
from app.models_context_ledger import ContextLedgerEntry
from app.schemas_settlement import RiskBand, SettleOnchainRequest, SettlementAckRequest
from app.services.settlement_api import (
    SettlementAPIService,
    SettlementConflictError,
    SettlementNotFoundError,
)


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _insert_entry(session: Session, settlement_id: str = "SET-001", amount: float = 1250.0) -> ContextLedgerEntry:
    metadata = {
        "settlement": {
            "settlement_id": settlement_id,
            "amount": amount,
            "asset": "CB-USDx",
            "status": "PENDING",
        }
    }
    entry = ContextLedgerEntry(
        agent_id="CODY",
        gid="GID-01",
        role_tier=2,
        gid_hgp_version="1.0",
        decision_type="settlement_released",
        decision_status="APPROVE",
        shipment_id="SHIP-001",
        payer_id="payer",
        payee_id="carrier",
        amount=amount,
        currency="USD",
        corridor="US-MX",
        risk_score=42,
        reason_codes=json.dumps(["SETTLEMENT_RELEASED"]),
        policies_applied=json.dumps(["L1_CodeEqualsCash"]),
        economic_justification="auto_release",
        metadata_json=json.dumps(metadata),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def test_trigger_onchain_settlement_updates_metadata(db_session: Session):
    entry = _insert_entry(db_session, settlement_id="SET-900", amount=1500.0)
    service = SettlementAPIService(db_session)
    payload = SettleOnchainRequest(
        settlement_id="SET-900",
        carrier_wallet="rTEST",
        amount=1500.0,
        asset="CB-USDx",
        risk_band=RiskBand.LOW,
        trace_id="trace-900",
        memo="daily-window",
    )

    response = service.trigger_onchain_settlement(payload)

    assert response.status in {response.status.SUBMITTED, response.status.CONFIRMED}
    assert response.settlement_id == "SET-900"
    updated = db_session.query(ContextLedgerEntry).filter(ContextLedgerEntry.id == entry.id).one()
    metadata = json.loads(updated.metadata_json)
    block = metadata.get("settlement")
    assert block["carrier_wallet"] == "rTEST"
    assert block["risk_trace_id"] == "trace-900"
    assert block["tx_hash"] == response.tx_hash


def test_trigger_onchain_settlement_amount_mismatch(db_session: Session):
    _insert_entry(db_session, settlement_id="SET-901", amount=5000.0)
    service = SettlementAPIService(db_session)
    payload = SettleOnchainRequest(
        settlement_id="SET-901",
        carrier_wallet="rWALLET",
        amount=4000.0,
        asset="CB-USDx",
        risk_band=RiskBand.MEDIUM,
        trace_id="trace-901",
    )

    with pytest.raises(SettlementConflictError):
        service.trigger_onchain_settlement(payload)


def test_trigger_onchain_missing_entry_raises(db_session: Session):
    service = SettlementAPIService(db_session)
    payload = SettleOnchainRequest(
        settlement_id="SET-UNKNOWN",
        carrier_wallet="rNONE",
        amount=10.0,
        asset="CB-USDx",
        risk_band=RiskBand.HIGH,
        trace_id="trace-missing",
    )

    with pytest.raises(SettlementNotFoundError):
        service.trigger_onchain_settlement(payload)


def test_get_settlement_detail_reflects_metadata(db_session: Session):
    _insert_entry(db_session, settlement_id="SET-DETAIL", amount=640.0)
    service = SettlementAPIService(db_session)

    detail = service.get_settlement_detail("SET-DETAIL")

    assert detail.settlement_id == "SET-DETAIL"
    assert detail.amount == 640.0
    assert detail.asset == "CB-USDx"
    assert detail.status.value in {"PENDING", "RELEASED", "ONCHAIN_CONFIRMED"}


def test_record_acknowledgement_is_idempotent(db_session: Session):
    _insert_entry(db_session, settlement_id="SET-ACK", amount=300.0)
    service = SettlementAPIService(db_session)
    payload = SettlementAckRequest(trace_id="trace-ack", consumer_id="chainboard-ui", notes="first")

    first = service.record_acknowledgement("SET-ACK", payload)
    assert first.ack_count == 1
    payload_second = SettlementAckRequest(trace_id="trace-ack", consumer_id="chainboard-ui", notes="repeat")
    second = service.record_acknowledgement("SET-ACK", payload_second)
    assert second.ack_count == 1

    entry = db_session.query(ContextLedgerEntry).filter(ContextLedgerEntry.shipment_id == "SHIP-001").first()
    metadata = json.loads(entry.metadata_json)
    acks = metadata.get("acks")
    assert isinstance(acks, list)
    assert acks[0]["notes"] == "repeat"
