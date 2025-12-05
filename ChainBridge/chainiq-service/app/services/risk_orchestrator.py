import logging
from datetime import datetime
import uuid

try:
    from ChainBridge.common.events.risk_event import RiskEvent
    from ChainBridge.common.events.event_types import EventType
    from ChainBridge.common.events.event_base import EventBase
except ModuleNotFoundError:  # pragma: no cover - allow service to run standalone
    from common.events.risk_event import RiskEvent
    from common.events.event_types import EventType

from .event_publisher import EventPublisher

logger = logging.getLogger("chainbridge.chainiq.risk_orchestrator")

class RiskOrchestrator:
    def __init__(self, publisher: EventPublisher):
        self.publisher = publisher

    # ChainBridge ML feature registry integration
    def get_risk_score_baseline(self, shipment_id):
        try:
            from ChainBridge.ml_engine.feature_store.registry import get_shipment_features
            features = get_shipment_features(shipment_id)
            if features:
                return features.risk_score_drift
        except Exception as e:
            logger.error(f"Failed to get risk_score_baseline: {e}")
        return None

    def get_historical_shipment_patterns(self, carrier_id):
        try:
            from ChainBridge.ml_engine.feature_store.registry import get_carrier_features
            features = get_carrier_features(carrier_id)
            if features:
                return {
                    "on_time_pct": features.on_time_pct,
                    "anomaly_freq": features.anomaly_freq,
                    "claim_freq": features.claim_freq,
                }
        except Exception as e:
            logger.error(f"Failed to get historical_shipment_patterns: {e}")
        return None

    def get_anomaly_context(self, shipment_id):
        try:
            from ChainBridge.ml_engine.feature_store.registry import get_shipment_features
            features = get_shipment_features(shipment_id)
            if features:
                return {
                    "eta_drift": features.eta_drift,
                    "delay_severity": features.delay_severity,
                }
        except Exception as e:
            logger.error(f"Failed to get anomaly_context: {e}")
        return None

    def get_carrier_performance_prior(self, carrier_id):
        try:
            from ChainBridge.ml_engine.feature_store.registry import get_carrier_features
            features = get_carrier_features(carrier_id)
            if features:
                return features.on_time_pct
        except Exception as e:
            logger.error(f"Failed to get carrier_performance_prior: {e}")
        return None

    async def handle_risk_result(self, shipment_id: str, risk_score: int, severity: str, reasons: list, source: str = "chainiq-risk-engine"):
        event = RiskEvent(
            canonical_shipment_id=shipment_id,
            event_type=EventType.RISK_OK if severity in ("LOW", "MEDIUM") else EventType.RISK_FAIL,
            timestamp=datetime.utcnow(),
            source=source,
            payload={
                "risk_score": risk_score,
                "severity": severity,
                "reasons": reasons
            },
            trace_id=str(uuid.uuid4())
        )
        await self.publisher.publish_risk_event(event)
        logger.info(f"Published risk event for shipment {shipment_id} with severity {severity}")
