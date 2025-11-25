from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base
from api.models.chaindocs import Shipment
from app.services.marketplace.auctioneer import create_liquidation_listing, place_bid, execute_sale

pytestmark = pytest.mark.phase2


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_bid_increment_logic():
    session = _session()
    session.add(Shipment(id="SHIP-X", corridor_code="CN-US", mode="OCEAN", collateral_value=100.0))
    session.commit()
    listing = create_liquidation_listing("SHIP-X", session=session)
    bid1 = place_bid(listing, listing.start_price + 10, "0x" + "a" * 40, session=session)
    try:
        place_bid(listing, listing.start_price + 5, "0x" + "b" * 40, session=session)
        assert False, "bid should fail"
    except ValueError:
        pass
    bid2 = place_bid(listing, bid1.amount + 5, "0x" + "c" * 40, session=session)
    assert bid2.amount > bid1.amount
    session.close()


def test_buy_now_execution():
    session = _session()
    session.add(Shipment(id="SHIP-Y", corridor_code="EU-UK", mode="AIR", collateral_value=200.0))
    session.commit()
    listing = create_liquidation_listing("SHIP-Y", session=session)
    sold = execute_sale(listing, "0x" + "f" * 40, listing.buy_now_price or listing.start_price, session=session)
    assert sold.status == "SOLD"
    session.close()
