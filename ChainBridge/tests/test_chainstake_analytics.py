from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.chainstake_analytics import (
    get_liquidity_overview,
    list_pool_positions,
    list_stake_pools,
)
from api.database import Base
from api.models.chainstake import StakePosition


def _seed_positions(session):
    now = datetime.utcnow()
    positions = [
        StakePosition(
            id="POS-1",
            shipment_id="SHIP-1",
            payment_intent_id="PAY-1",
            pool_id="POOL-A",
            corridor="CN-US",
            notional_usd=1000.0,
            staked_at=now - timedelta(days=5),
            expected_maturity_at=now + timedelta(days=25),
            realized_apy=10.0,
            status="STAKING_IN_POOL",
            risk_level="LOW",
        ),
        StakePosition(
            id="POS-2",
            shipment_id="SHIP-2",
            payment_intent_id="PAY-2",
            pool_id="POOL-A",
            corridor="CN-US",
            notional_usd=500.0,
            staked_at=now - timedelta(days=3),
            expected_maturity_at=now + timedelta(days=20),
            realized_apy=8.0,
            status="LIQUIDITY_SENT",
            risk_level="MEDIUM",
        ),
        StakePosition(
            id="POS-3",
            shipment_id="SHIP-3",
            payment_intent_id="PAY-3",
            pool_id="POOL-B",
            corridor="EU-UK",
            notional_usd=700.0,
            staked_at=now - timedelta(days=2),
            expected_maturity_at=now + timedelta(days=18),
            realized_apy=9.0,
            status="FAILED",
            risk_level="HIGH",
        ),
    ]
    session.add_all(positions)
    session.commit()
    return positions


def setup_module():
    pass


def test_liquidity_overview():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    _seed_positions(session)

    overview = get_liquidity_overview(session)
    assert overview.total_tvl_usd == 1500.0
    assert overview.total_utilized_usd == 1500.0
    assert overview.active_positions == 2
    assert overview.overall_realized_apy > 0
    session.close()


def test_pool_summaries_and_positions():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    _seed_positions(session)

    pools = list_stake_pools(session)
    assert len(pools) == 2
    pool_a = next(p for p in pools if p.pool_id == "POOL-A")
    assert pool_a.tvl_usd == 1500.0
    assert pool_a.utilized_usd == 1500.0
    assert pool_a.open_positions >= 1

    positions = list_pool_positions(session, "POOL-A")
    assert len(positions) == 2
    assert positions[0].pool_id == "POOL-A"
    session.close()
