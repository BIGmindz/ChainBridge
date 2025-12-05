"""
Feature registry for ChainBridge ML.
Supports as-of joins, versioning, ChainIQ integration.
"""

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from .models import ShipmentFeature
from ..ingestion.config import POSTGRES_URI

engine = create_engine(POSTGRES_URI)
Session = sessionmaker(bind=engine)

# Registry API for ChainIQ

def get_shipment_features(shipment_id, as_of=None):
    session = Session()
    q = session.query(ShipmentFeature).filter_by(shipment_id=shipment_id)
    if as_of:
        q = q.filter(ShipmentFeature.updated_at <= as_of)
    result = q.order_by(ShipmentFeature.updated_at.desc()).first()
    session.close()
    return result

# Similar get functions for CarrierFeature and RiskFinanceFeature

def register_feature_update(feature_type, entity_id):
    # Placeholder for hooks/notifications
    pass

# Model registry entries
MODEL_REGISTRY = {}

def register_model_metadata(model_name, version, dataset_hash, train_time, hyperparams, metrics):
        MODEL_REGISTRY[model_name] = {
            "version": version,
            "dataset_hash": dataset_hash,
            "train_time": train_time,
            "hyperparameters": hyperparams,
            "metrics": metrics,
            "features_used": hyperparams.get("features", []),
            "explanation_blob": hyperparams.get("explanation", ""),
        }
        # Optionally persist to DB or file
        return MODEL_REGISTRY[model_name]

def get_model_metadata(model_name):
    return MODEL_REGISTRY.get(model_name, None)
