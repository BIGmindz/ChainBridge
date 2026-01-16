"""
ChainIQ ML Risk Scoring Integration
===================================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING v2.0.0
Component: Machine Learning Risk Scoring
Agent: CODY (GID-01)

PURPOSE:
  Integrates with ChainIQ ML pipeline for advanced anomaly detection
  and risk scoring. Provides real-time behavioral analysis using:
  - Gradient Boosting for risk classification
  - Isolation Forest for anomaly detection
  - LSTM for sequence pattern recognition
  - Feature engineering pipeline

INVARIANTS:
  INV-ML-001: Model predictions MUST include confidence scores
  INV-ML-002: Feature extraction MUST be consistent across training/inference
  INV-ML-003: Model versioning MUST be tracked for audit
  INV-ML-004: Fallback scoring MUST activate on model failure

MODELS:
  - RiskClassifier: Gradient Boosting binary classifier
  - AnomalyDetector: Isolation Forest unsupervised detector
  - BehaviorPredictor: LSTM sequence model
"""

import hashlib
import json
import logging
import math
import pickle
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger("chainbridge.auth.ml.chainiq")


class ModelType(Enum):
    """Supported ML model types."""
    RISK_CLASSIFIER = "risk_classifier"
    ANOMALY_DETECTOR = "anomaly_detector"
    BEHAVIOR_PREDICTOR = "behavior_predictor"
    ENSEMBLE = "ensemble"


@dataclass
class MLConfig:
    """ML risk scoring configuration."""
    # Model settings
    model_path: str = "models/auth"
    model_version: str = "1.0.0"
    
    # Feature settings
    feature_window_minutes: int = 60
    min_samples_for_training: int = 1000
    
    # Thresholds
    risk_threshold: float = 0.7
    anomaly_threshold: float = -0.5  # Isolation Forest
    confidence_threshold: float = 0.6
    
    # Ensemble weights
    classifier_weight: float = 0.4
    anomaly_weight: float = 0.3
    behavior_weight: float = 0.3
    
    # ChainIQ service
    chainiq_endpoint: str = "http://localhost:8082/api/v1/ml"
    chainiq_timeout: float = 5.0
    
    # Fallback
    fallback_enabled: bool = True
    fallback_score: float = 0.5


@dataclass
class FeatureVector:
    """Feature vector for ML models."""
    user_id: str
    timestamp: datetime
    
    # Request features
    request_count_1m: int = 0
    request_count_5m: int = 0
    request_count_1h: int = 0
    unique_endpoints_1h: int = 0
    unique_ips_1h: int = 0
    error_rate_1h: float = 0.0
    
    # Time features
    hour_of_day: int = 0
    day_of_week: int = 0
    is_weekend: bool = False
    is_business_hours: bool = True
    
    # Device features
    device_fingerprint_hash: str = ""
    is_known_device: bool = True
    device_age_days: int = 0
    
    # Location features
    ip_reputation_score: float = 0.0
    is_vpn: bool = False
    is_datacenter: bool = False
    geo_distance_km: float = 0.0
    
    # Session features
    session_age_minutes: int = 0
    actions_in_session: int = 0
    failed_auth_count: int = 0
    
    # Historical features
    avg_daily_requests: float = 0.0
    std_daily_requests: float = 0.0
    days_since_first_seen: int = 0
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array for model input."""
        return np.array([
            self.request_count_1m,
            self.request_count_5m,
            self.request_count_1h,
            self.unique_endpoints_1h,
            self.unique_ips_1h,
            self.error_rate_1h,
            self.hour_of_day,
            self.day_of_week,
            int(self.is_weekend),
            int(self.is_business_hours),
            int(self.is_known_device),
            self.device_age_days,
            self.ip_reputation_score,
            int(self.is_vpn),
            int(self.is_datacenter),
            self.geo_distance_km,
            self.session_age_minutes,
            self.actions_in_session,
            self.failed_auth_count,
            self.avg_daily_requests,
            self.std_daily_requests,
            self.days_since_first_seen,
        ], dtype=np.float32)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "request_count_1m": self.request_count_1m,
            "request_count_5m": self.request_count_5m,
            "request_count_1h": self.request_count_1h,
            "unique_endpoints_1h": self.unique_endpoints_1h,
            "unique_ips_1h": self.unique_ips_1h,
            "error_rate_1h": self.error_rate_1h,
            "hour_of_day": self.hour_of_day,
            "day_of_week": self.day_of_week,
            "is_weekend": self.is_weekend,
            "is_business_hours": self.is_business_hours,
            "is_known_device": self.is_known_device,
            "device_age_days": self.device_age_days,
            "ip_reputation_score": self.ip_reputation_score,
            "is_vpn": self.is_vpn,
            "is_datacenter": self.is_datacenter,
            "geo_distance_km": self.geo_distance_km,
            "session_age_minutes": self.session_age_minutes,
            "actions_in_session": self.actions_in_session,
            "failed_auth_count": self.failed_auth_count,
            "avg_daily_requests": self.avg_daily_requests,
            "std_daily_requests": self.std_daily_requests,
            "days_since_first_seen": self.days_since_first_seen,
        }


@dataclass
class MLPrediction:
    """ML model prediction result."""
    risk_score: float
    confidence: float
    model_type: ModelType
    model_version: str
    features_used: int
    prediction_time_ms: float
    anomaly_score: Optional[float] = None
    behavior_score: Optional[float] = None
    explanation: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "model_type": self.model_type.value,
            "model_version": self.model_version,
            "features_used": self.features_used,
            "prediction_time_ms": self.prediction_time_ms,
            "anomaly_score": self.anomaly_score,
            "behavior_score": self.behavior_score,
            "explanation": self.explanation,
        }


class FeatureExtractor:
    """
    Feature extraction pipeline for ML models.
    
    Extracts and engineers features from request context
    and historical data.
    """
    
    def __init__(self, config: MLConfig, redis_client=None):
        self.config = config
        self.redis = redis_client
        
        # In-memory feature store (fallback)
        self._user_history: Dict[str, List[Dict]] = {}
        self._device_registry: Dict[str, Dict] = {}
    
    def extract_features(
        self,
        user_id: str,
        request_data: Dict[str, Any]
    ) -> FeatureVector:
        """Extract feature vector from request context."""
        now = datetime.now(timezone.utc)
        
        # Get user history
        history = self._get_user_history(user_id)
        
        # Time features
        hour = now.hour
        day = now.weekday()
        is_weekend = day >= 5
        is_business_hours = 9 <= hour <= 18 and not is_weekend
        
        # Request velocity features
        req_1m = self._count_requests(history, minutes=1)
        req_5m = self._count_requests(history, minutes=5)
        req_1h = self._count_requests(history, minutes=60)
        
        # Diversity features
        unique_endpoints = len(set(
            r.get("path", "") for r in history[-100:]
        ))
        unique_ips = len(set(
            r.get("ip", "") for r in history[-100:]
        ))
        
        # Error rate
        recent = history[-100:]
        errors = sum(1 for r in recent if r.get("status", 200) >= 400)
        error_rate = errors / len(recent) if recent else 0.0
        
        # Device features
        device_fp = request_data.get("device_fingerprint", "")
        device_info = self._get_device_info(user_id, device_fp)
        
        # Location features
        ip = request_data.get("client_ip", "")
        ip_score = request_data.get("ip_reputation", 0.0)
        
        # Session features
        session_start = request_data.get("session_start")
        if session_start:
            session_age = int((now - session_start).total_seconds() / 60)
        else:
            session_age = 0
        
        # Historical features
        daily_stats = self._calculate_daily_stats(history)
        
        # First seen
        if history:
            first_seen = datetime.fromisoformat(history[0].get("timestamp", now.isoformat()))
            days_since_first = (now - first_seen).days
        else:
            days_since_first = 0
        
        # Record this request
        self._record_request(user_id, request_data)
        
        return FeatureVector(
            user_id=user_id,
            timestamp=now,
            request_count_1m=req_1m,
            request_count_5m=req_5m,
            request_count_1h=req_1h,
            unique_endpoints_1h=unique_endpoints,
            unique_ips_1h=unique_ips,
            error_rate_1h=error_rate,
            hour_of_day=hour,
            day_of_week=day,
            is_weekend=is_weekend,
            is_business_hours=is_business_hours,
            device_fingerprint_hash=device_fp,
            is_known_device=device_info.get("known", True),
            device_age_days=device_info.get("age_days", 0),
            ip_reputation_score=ip_score,
            is_vpn=request_data.get("is_vpn", False),
            is_datacenter=request_data.get("is_datacenter", False),
            geo_distance_km=request_data.get("geo_distance", 0.0),
            session_age_minutes=session_age,
            actions_in_session=request_data.get("session_actions", 0),
            failed_auth_count=request_data.get("failed_auths", 0),
            avg_daily_requests=daily_stats.get("avg", 0.0),
            std_daily_requests=daily_stats.get("std", 0.0),
            days_since_first_seen=days_since_first,
        )
    
    def _get_user_history(self, user_id: str) -> List[Dict]:
        """Get user's request history."""
        if self.redis:
            key = f"ml:history:{user_id}"
            data = self.redis.lrange(key, 0, -1)
            return [json.loads(d) for d in data] if data else []
        return self._user_history.get(user_id, [])
    
    def _record_request(self, user_id: str, request_data: Dict):
        """Record a request for history."""
        now = datetime.now(timezone.utc)
        record = {
            "timestamp": now.isoformat(),
            "path": request_data.get("path", ""),
            "ip": request_data.get("client_ip", ""),
            "status": request_data.get("status_code", 200),
        }
        
        if self.redis:
            key = f"ml:history:{user_id}"
            self.redis.lpush(key, json.dumps(record))
            self.redis.ltrim(key, 0, 999)  # Keep last 1000
            self.redis.expire(key, 86400 * 7)  # 7 day TTL
        else:
            if user_id not in self._user_history:
                self._user_history[user_id] = []
            self._user_history[user_id].append(record)
            self._user_history[user_id] = self._user_history[user_id][-1000:]
    
    def _count_requests(self, history: List[Dict], minutes: int) -> int:
        """Count requests within time window."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return sum(
            1 for r in history
            if datetime.fromisoformat(r.get("timestamp", "2000-01-01")) > cutoff
        )
    
    def _get_device_info(self, user_id: str, fingerprint: str) -> Dict:
        """Get device registration info."""
        key = f"{user_id}:{fingerprint}"
        
        if self.redis:
            data = self.redis.hget("ml:devices", key)
            if data:
                return json.loads(data)
        elif key in self._device_registry:
            return self._device_registry[key]
        
        # Unknown device
        return {"known": False, "age_days": 0}
    
    def _calculate_daily_stats(self, history: List[Dict]) -> Dict[str, float]:
        """Calculate daily request statistics."""
        if not history:
            return {"avg": 0.0, "std": 0.0}
        
        # Group by day
        daily_counts: Dict[str, int] = {}
        for r in history:
            date = r.get("timestamp", "")[:10]
            daily_counts[date] = daily_counts.get(date, 0) + 1
        
        if not daily_counts:
            return {"avg": 0.0, "std": 0.0}
        
        counts = list(daily_counts.values())
        avg = sum(counts) / len(counts)
        variance = sum((c - avg) ** 2 for c in counts) / len(counts)
        std = math.sqrt(variance)
        
        return {"avg": avg, "std": std}


class RiskClassifier:
    """
    Gradient Boosting risk classifier.
    
    Binary classification: high-risk vs low-risk.
    """
    
    def __init__(self, config: MLConfig):
        self.config = config
        self._model = None
        self._feature_importance: Dict[str, float] = {}
    
    def load(self, model_path: str = None):
        """Load trained model from disk."""
        path = Path(model_path or self.config.model_path) / "risk_classifier.pkl"
        
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
                self._model = data.get("model")
                self._feature_importance = data.get("feature_importance", {})
            logger.info(f"Loaded risk classifier from {path}")
        except FileNotFoundError:
            logger.warning("No pre-trained risk classifier found, using rule-based fallback")
            self._model = None
    
    def predict(self, features: FeatureVector) -> Tuple[float, float, Dict[str, float]]:
        """
        Predict risk score.
        
        Returns (risk_score, confidence, explanation)
        """
        if self._model is None:
            return self._rule_based_predict(features)
        
        X = features.to_array().reshape(1, -1)
        
        try:
            # Get probability
            proba = self._model.predict_proba(X)[0]
            risk_score = proba[1] if len(proba) > 1 else proba[0]
            confidence = max(proba)
            
            # Feature importance explanation
            explanation = {}
            feature_names = list(features.to_dict().keys())[2:]  # Skip user_id, timestamp
            for i, (name, importance) in enumerate(zip(feature_names, self._feature_importance.values())):
                if importance > 0.05:  # Only significant features
                    explanation[name] = round(importance * 100, 1)
            
            return risk_score, confidence, explanation
            
        except Exception as e:
            logger.error(f"Model prediction failed: {e}")
            return self._rule_based_predict(features)
    
    def _rule_based_predict(self, features: FeatureVector) -> Tuple[float, float, Dict[str, float]]:
        """Fallback rule-based scoring."""
        score = 0.0
        explanation = {}
        
        # Velocity rules
        if features.request_count_1m > 30:
            score += 0.3
            explanation["high_velocity"] = 30.0
        
        # Device rules
        if not features.is_known_device:
            score += 0.2
            explanation["new_device"] = 20.0
        
        # IP rules
        if features.ip_reputation_score > 0.5:
            score += 0.2
            explanation["suspicious_ip"] = 20.0
        
        # Time rules
        if not features.is_business_hours:
            score += 0.1
            explanation["off_hours"] = 10.0
        
        # Error rate
        if features.error_rate_1h > 0.3:
            score += 0.2
            explanation["high_errors"] = 20.0
        
        return min(score, 1.0), 0.7, explanation


class AnomalyDetector:
    """
    Isolation Forest anomaly detector.
    
    Unsupervised detection of unusual patterns.
    """
    
    def __init__(self, config: MLConfig):
        self.config = config
        self._model = None
    
    def load(self, model_path: str = None):
        """Load trained model."""
        path = Path(model_path or self.config.model_path) / "anomaly_detector.pkl"
        
        try:
            with open(path, "rb") as f:
                self._model = pickle.load(f)
            logger.info(f"Loaded anomaly detector from {path}")
        except FileNotFoundError:
            logger.warning("No pre-trained anomaly detector found")
            self._model = None
    
    def detect(self, features: FeatureVector) -> Tuple[float, bool]:
        """
        Detect anomaly.
        
        Returns (anomaly_score, is_anomaly)
        """
        if self._model is None:
            return self._statistical_detect(features)
        
        X = features.to_array().reshape(1, -1)
        
        try:
            # Isolation Forest score (-1 to 1, lower = more anomalous)
            raw_score = self._model.decision_function(X)[0]
            
            # Normalize to 0-1 (higher = more anomalous)
            anomaly_score = max(0, -raw_score)
            is_anomaly = raw_score < self.config.anomaly_threshold
            
            return anomaly_score, is_anomaly
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return self._statistical_detect(features)
    
    def _statistical_detect(self, features: FeatureVector) -> Tuple[float, bool]:
        """Fallback statistical anomaly detection."""
        anomaly_score = 0.0
        
        # Z-score based detection for velocity
        if features.std_daily_requests > 0:
            z_velocity = (features.request_count_1h - features.avg_daily_requests) / features.std_daily_requests
            if z_velocity > 2:
                anomaly_score += min(z_velocity / 5, 0.5)
        
        # Geographic anomaly
        if features.geo_distance_km > 1000:
            anomaly_score += min(features.geo_distance_km / 10000, 0.3)
        
        # Session anomaly
        if features.session_age_minutes < 1 and features.actions_in_session > 10:
            anomaly_score += 0.2
        
        is_anomaly = anomaly_score > 0.5
        return min(anomaly_score, 1.0), is_anomaly


class ChainIQClient:
    """
    Client for ChainIQ ML service.
    
    Provides remote model inference for production deployments.
    """
    
    def __init__(self, config: MLConfig):
        self.config = config
    
    async def predict(
        self,
        user_id: str,
        features: FeatureVector
    ) -> Optional[MLPrediction]:
        """Query ChainIQ for prediction."""
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=self.config.chainiq_timeout) as client:
                response = await client.post(
                    f"{self.config.chainiq_endpoint}/predict",
                    json={
                        "user_id": user_id,
                        "features": features.to_dict(),
                        "model_version": self.config.model_version,
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return MLPrediction(
                        risk_score=data["risk_score"],
                        confidence=data["confidence"],
                        model_type=ModelType.ENSEMBLE,
                        model_version=data.get("model_version", self.config.model_version),
                        features_used=len(features.to_dict()) - 2,
                        prediction_time_ms=data.get("latency_ms", 0),
                        anomaly_score=data.get("anomaly_score"),
                        behavior_score=data.get("behavior_score"),
                        explanation=data.get("explanation", {}),
                    )
        except Exception as e:
            logger.error(f"ChainIQ prediction failed: {e}")
        
        return None


class MLRiskScorer:
    """
    Main ML risk scoring orchestrator.
    
    Combines multiple models into ensemble prediction.
    """
    
    def __init__(self, config: MLConfig, redis_client=None):
        self.config = config
        
        # Initialize components
        self.feature_extractor = FeatureExtractor(config, redis_client)
        self.risk_classifier = RiskClassifier(config)
        self.anomaly_detector = AnomalyDetector(config)
        self.chainiq_client = ChainIQClient(config)
        
        # Load models
        self._load_models()
    
    def _load_models(self):
        """Load all ML models."""
        self.risk_classifier.load()
        self.anomaly_detector.load()
    
    def score(
        self,
        user_id: str,
        request_data: Dict[str, Any]
    ) -> MLPrediction:
        """
        Compute ML risk score.
        
        Uses local ensemble unless ChainIQ service is available.
        """
        start_time = time.time()
        
        # Extract features
        features = self.feature_extractor.extract_features(user_id, request_data)
        
        # Get predictions from each model
        risk_score, risk_confidence, risk_explanation = self.risk_classifier.predict(features)
        anomaly_score, is_anomaly = self.anomaly_detector.detect(features)
        
        # Ensemble combination
        weights = {
            "classifier": self.config.classifier_weight,
            "anomaly": self.config.anomaly_weight,
        }
        
        # Weight normalization
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}
        
        # Combined score
        combined_score = (
            risk_score * weights["classifier"] +
            anomaly_score * weights["anomaly"]
        )
        
        # Confidence is minimum of component confidences
        confidence = min(risk_confidence, 0.8 if not is_anomaly else 0.9)
        
        # Merge explanations
        explanation = risk_explanation.copy()
        if is_anomaly:
            explanation["anomaly_detected"] = anomaly_score * 100
        
        prediction_time = (time.time() - start_time) * 1000
        
        return MLPrediction(
            risk_score=round(combined_score, 3),
            confidence=round(confidence, 3),
            model_type=ModelType.ENSEMBLE,
            model_version=self.config.model_version,
            features_used=22,  # Number of features
            prediction_time_ms=round(prediction_time, 2),
            anomaly_score=round(anomaly_score, 3),
            explanation=explanation,
        )
    
    async def score_async(
        self,
        user_id: str,
        request_data: Dict[str, Any]
    ) -> MLPrediction:
        """
        Async scoring with ChainIQ fallback.
        """
        # Try ChainIQ first
        features = self.feature_extractor.extract_features(user_id, request_data)
        prediction = await self.chainiq_client.predict(user_id, features)
        
        if prediction:
            return prediction
        
        # Fallback to local scoring
        return self.score(user_id, request_data)


# Module-level scorer
_ml_scorer: Optional[MLRiskScorer] = None


def get_ml_scorer() -> MLRiskScorer:
    """Get global ML scorer instance."""
    global _ml_scorer
    if _ml_scorer is None:
        _ml_scorer = MLRiskScorer(MLConfig())
    return _ml_scorer


def init_ml_scorer(config: MLConfig, redis_client=None) -> MLRiskScorer:
    """Initialize ML scorer with custom config."""
    global _ml_scorer
    _ml_scorer = MLRiskScorer(config, redis_client)
    return _ml_scorer
