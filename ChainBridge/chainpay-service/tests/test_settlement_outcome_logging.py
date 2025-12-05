from app.models_analytics import SettlementOutcome
from app.services.settlement_service import (
    get_mock_settlement_status,
    record_settlement_outcome,
)


def test_insert_new_outcome(db_session):
    status = get_mock_settlement_status("SHIP-1")

    outcome = record_settlement_outcome(db_session, status)

    rows = db_session.query(SettlementOutcome).all()
    assert len(rows) == 1
    assert outcome.shipment_id == "SHIP-1"
    assert outcome.cb_usd_total == status.cb_usd.total
    assert outcome.analytics_version == "v1"
    assert outcome.payout_policy_version == "v1"


def test_idempotent_update_same_combo(db_session):
    status = get_mock_settlement_status("SHIP-2")

    first = record_settlement_outcome(db_session, status, cb_usd_loss_realized=0.0)
    assert first.had_claim is False

    updated = record_settlement_outcome(
        db_session,
        status,
        cb_usd_loss_realized=10.0,
        had_claim=True,
        settlement_status_label="LOSS_WITHIN_RESERVE",
    )

    rows = db_session.query(SettlementOutcome).all()
    assert len(rows) == 1
    assert updated.id == first.id
    assert updated.had_claim is True
    assert updated.cb_usd_loss_realized == 10.0
    assert updated.settlement_status == "LOSS_WITHIN_RESERVE"


def test_multiple_versions_create_multiple_rows(db_session):
    status = get_mock_settlement_status("SHIP-3")

    record_settlement_outcome(db_session, status, analytics_version="v1")
    record_settlement_outcome(db_session, status, analytics_version="v2")

    rows = db_session.query(SettlementOutcome).filter(
        SettlementOutcome.shipment_id == "SHIP-3"
    ).all()
    assert len(rows) == 2
    versions = {row.analytics_version for row in rows}
    assert versions == {"v1", "v2"}
