import datetime

from app.models import MilestoneSettlement, PaymentIntent, PaymentStatus, RiskTier
from app.payment_rails import CbUsdxRail, InternalLedgerRail, SettlementProvider
from app.services.payment_rails_engine import PaymentRailsEngine


def test_engine_defaults_to_internal(db_session):
    engine = PaymentRailsEngine(db_session, use_cb_usdx=False)

    rail = engine.get_immediate_rail()

    assert isinstance(rail, InternalLedgerRail)
    assert engine.default_provider() == SettlementProvider.INTERNAL_LEDGER


def test_engine_returns_cb_usdx_when_enabled(db_session):
    engine = PaymentRailsEngine(db_session, use_cb_usdx=True)

    rail = engine.get_immediate_rail()

    assert isinstance(rail, CbUsdxRail)
    assert engine.default_provider() == SettlementProvider.CB_USDX


def test_cb_usdx_stub_sets_provider_and_status(db_session):
    intent = PaymentIntent(
        freight_token_id=999,
        amount=100.0,
        currency="USD",
        risk_tier=RiskTier.LOW,
        status=PaymentStatus.PENDING,
    )
    db_session.add(intent)
    db_session.commit()
    db_session.refresh(intent)

    milestone = MilestoneSettlement(
        payment_intent_id=intent.id,
        event_type="POD_CONFIRMED",
        amount=70.0,
        currency="USD",
        status=PaymentStatus.PENDING,
        occurred_at=datetime.datetime.utcnow(),
        provider="INTERNAL_LEDGER",
    )
    db_session.add(milestone)
    db_session.commit()
    db_session.refresh(milestone)

    rail = CbUsdxRail(db_session)
    result = rail.process_settlement(milestone_id=milestone.id, amount=70.0, currency="USD")

    db_session.refresh(milestone)

    assert result.success is True
    assert result.provider == SettlementProvider.CB_USDX
    assert milestone.status == PaymentStatus.APPROVED
    assert milestone.provider == SettlementProvider.CB_USDX.value
    assert milestone.reference is not None
