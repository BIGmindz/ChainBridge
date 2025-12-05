"""
Feature store logic for ChainBridge ML.
Insert/update/query features, versioning, TTL, as-of joins.
"""

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from .models import Base, ShipmentFeature
from .registry import register_feature_update
from datetime import datetime
from ..ingestion.config import POSTGRES_URI

engine = create_engine(POSTGRES_URI)
Session = sessionmaker(bind=engine)

# Create tables if not exist
Base.metadata.create_all(engine)

def upsert_shipment_feature(data):
    session = Session()
    obj = session.query(ShipmentFeature).filter_by(shipment_id=data["shipment_id"]).first()
    if obj:
        for k, v in data.items():
            setattr(obj, k, v)
        obj.updated_at = datetime.utcnow()
    else:
        obj = ShipmentFeature(**data, updated_at=datetime.utcnow())
        session.add(obj)
    session.commit()
    register_feature_update("shipment", data["shipment_id"])
    session.close()

# Similar upsert functions for CarrierFeature and RiskFinanceFeature
