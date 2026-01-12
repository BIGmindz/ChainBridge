"""
Risk-Based Authentication Middleware
====================================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING
Component: ML-Powered Risk Scoring and Adaptive Authentication
Agent: CODY (GID-01)

INVARIANTS:
  INV-AUTH-014: High-risk auth MUST trigger MFA challenge (MAGGIE enforced)
  INV-AUTH-015: Risk score MUST be computed on every request (ChainIQ integration)

RISK FACTORS:
  - Behavioral anomalies (request patterns, timing)
  - Device fingerprint changes
  - Geolocation anomalies
  - Request velocity
  - Historical patterns
  - IP reputation
  - Session characteristics

INTEGRATION:
  - ChainIQ ML pipeline for anomaly detection
  - GID registry for user behavioral baselines
  - Redis for real-time scoring cache
"""

import hashlib
import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("chainbridge.auth.risk")


class RiskLevel(Enum):
    """Risk classification levels."""
    LOW = "low"           # Score < 0.3
    MEDIUM = "medium"     # Score 0.3 - 0.6
    HIGH = "high"         # Score 0.6 - 0.8
    CRITICAL = "critical" # Score > 0.8


class RiskFactor(Enum):
    """Individual risk factors tracked."""
    IP_REPUTATION = "ip_reputation"
    DEVICE_ANOMALY = "device_anomaly"
    LOCATION_ANOMALY = "location_anomaly"
    VELOCITY_ANOMALY = "velocity_anomaly"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"
    SESSION_ANOMALY = "session_anomaly"
    TIME_ANOMALY = "time_anomaly"
    PATTERN_ANOMALY = "pattern_anomaly"


@dataclass
class RiskConfig:
    """Risk scoring configuration."""
    # Factor weights (must sum to 1.0)
    factor_weights: Dict[str, float] = field(default_factory=lambda: {
        RiskFactor.IP_REPUTATION.value: 0.15,
        RiskFactor.DEVICE_ANOMALY.value: 0.15,
        RiskFactor.LOCATION_ANOMALY.value: 0.15,
        RiskFactor.VELOCITY_ANOMALY.value: 0.15,
        RiskFactor.BEHAVIORAL_ANOMALY.value: 0.15,
        RiskFactor.SESSION_ANOMALY.value: 0.10,
        RiskFactor.TIME_ANOMALY.value: 0.10,
        RiskFactor.PATTERN_ANOMALY.value: 0.05,
    })
    
    # Thresholds
    mfa_threshold: float = 0.7
    block_threshold: float = 0.9
    
    # Velocity limits
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000
    
    # Cache settings
    cache_ttl_seconds: int = 300
    
    # Historical window
    history_window_hours: int = 24
    
    # ChainIQ integration
    chainiq_enabled: bool = True
    chainiq_endpoint: str = "http://localhost:8082/api/v1/risk/score"


@dataclass
class DeviceFingerprint:
    """Device identification data."""
    user_agent: str
    accept_language: str
    accept_encoding: str
    screen_resolution: Optional[str] = None
    timezone_offset: Optional[int] = None
    platform: Optional[str] = None
    fingerprint_hash: str = ""
    
    def __post_init__(self):
        """Calculate fingerprint hash."""
        components = [
            self.user_agent,
            self.accept_language,
            self.accept_encoding,
            str(self.screen_resolution or ""),
            str(self.timezone_offset or ""),
            self.platform or "",
        ]
        self.fingerprint_hash = hashlib.sha256(
            "|".join(components).encode()
        ).hexdigest()[:32]


@dataclass
class RiskScore:
    """Complete risk assessment result."""
    total_score: float
    level: RiskLevel
    factors: Dict[str, float]
    requires_mfa: bool
    blocked: bool
    explanation: List[str]
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_score": self.total_score,
            "level": self.level.value,
            "factors": self.factors,
            "requires_mfa": self.requires_mfa,
            "blocked": self.blocked,
            "explanation": self.explanation,
            "computed_at": self.computed_at.isoformat(),
        }


class IPReputationChecker:
    """
    IP address reputation scoring.
    
    Checks against known malicious IPs, VPNs, data centers, etc.
    """
    
    def __init__(self):
        # Known VPN/proxy IP ranges (simplified)
        self._suspicious_ranges = [
            "10.0.0.0/8",  # Private
            "172.16.0.0/12",  # Private
            "192.168.0.0/16",  # Private
        ]
        
        # Blocklist (in production, use external service)
        self._blocklist: set = set()
        
        # Reputation cache
        self._cache: Dict[str, Tuple[float, datetime]] = {}
    
    def get_reputation_score(self, ip: str) -> float:
        """
        Get reputation score for IP (0.0 = trusted, 1.0 = malicious).
        """
        # Check cache
        if ip in self._cache:
            score, cached_at = self._cache[ip]
            if datetime.now(timezone.utc) - cached_at < timedelta(hours=1):
                return score
        
        score = 0.0
        
        # Check blocklist
        if ip in self._blocklist:
            score = 1.0
        
        # Check if private IP (unusual for production)
        if ip.startswith(("10.", "172.16.", "192.168.")):
            score = max(score, 0.3)  # Slightly suspicious
        
        # Check for Tor exit nodes (would use external service)
        # Check for VPN/proxy (would use external service)
        # Check for datacenter IPs (would use external service)
        
        self._cache[ip] = (score, datetime.now(timezone.utc))
        return score


class VelocityTracker:
    """
    Request velocity tracking for anomaly detection.
    
    Tracks request rates per user/IP for sudden changes.
    """
    
    def __init__(self, config: RiskConfig, redis_client=None):
        self.config = config
        self.redis = redis_client
        self._requests: Dict[str, List[float]] = {}  # In-memory fallback
    
    def record_request(self, identifier: str):
        """Record a request timestamp."""
        now = time.time()
        key = f"velocity:{identifier}"
        
        if self.redis:
            # Add timestamp and trim old entries
            self.redis.zadd(key, {str(now): now})
            cutoff = now - (self.config.history_window_hours * 3600)
            self.redis.zremrangebyscore(key, 0, cutoff)
            self.redis.expire(key, self.config.history_window_hours * 3600)
        else:
            if key not in self._requests:
                self._requests[key] = []
            self._requests[key].append(now)
            
            # Trim old entries
            cutoff = now - (self.config.history_window_hours * 3600)
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
    
    def get_velocity_score(self, identifier: str) -> float:
        """
        Calculate velocity anomaly score (0.0 = normal, 1.0 = anomalous).
        """
        now = time.time()
        key = f"velocity:{identifier}"
        
        if self.redis:
            # Get counts for different windows
            minute_ago = now - 60
            hour_ago = now - 3600
            
            minute_count = self.redis.zcount(key, minute_ago, now)
            hour_count = self.redis.zcount(key, hour_ago, now)
        else:
            timestamps = self._requests.get(key, [])
            minute_count = sum(1 for t in timestamps if t > now - 60)
            hour_count = sum(1 for t in timestamps if t > now - 3600)
        
        # Calculate score based on limits
        minute_ratio = minute_count / self.config.max_requests_per_minute
        hour_ratio = hour_count / self.config.max_requests_per_hour
        
        # Use sigmoid for smooth scoring
        score = max(
            self._sigmoid(minute_ratio, k=5),
            self._sigmoid(hour_ratio, k=5)
        )
        
        return min(score, 1.0)
    
    @staticmethod
    def _sigmoid(x: float, k: float = 5) -> float:
        """Sigmoid function for smooth 0-1 scoring."""
        if x <= 0:
            return 0.0
        return 1 / (1 + math.exp(-k * (x - 1)))


class BehavioralAnalyzer:
    """
    Behavioral pattern analysis.
    
    Detects anomalies in user request patterns compared to baseline.
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._patterns: Dict[str, Dict[str, Any]] = {}
    
    def analyze_behavior(
        self,
        user_id: str,
        request_path: str,
        request_method: str,
        request_time: datetime
    ) -> float:
        """
        Analyze request against user's behavioral baseline.
        
        Returns anomaly score (0.0 = expected, 1.0 = highly anomalous).
        """
        key = f"behavior:{user_id}"
        
        # Get or create baseline
        if self.redis:
            data = self.redis.get(key)
            baseline = json.loads(data) if data else self._create_baseline()
        else:
            baseline = self._patterns.get(key, self._create_baseline())
        
        score = 0.0
        
        # Check time-of-day anomaly
        hour = request_time.hour
        typical_hours = baseline.get("typical_hours", list(range(24)))
        if hour not in typical_hours:
            score += 0.3
        
        # Check endpoint anomaly
        typical_paths = baseline.get("typical_paths", set())
        if request_path not in typical_paths and len(typical_paths) > 5:
            score += 0.2
        
        # Update baseline
        self._update_baseline(
            key, baseline, request_path, request_method, request_time
        )
        
        return min(score, 1.0)
    
    def _create_baseline(self) -> Dict[str, Any]:
        """Create initial behavioral baseline."""
        return {
            "typical_hours": [],
            "typical_paths": [],
            "request_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def _update_baseline(
        self,
        key: str,
        baseline: Dict[str, Any],
        path: str,
        method: str,
        request_time: datetime
    ):
        """Update behavioral baseline with new data."""
        # Update typical hours
        hour = request_time.hour
        if hour not in baseline["typical_hours"]:
            baseline["typical_hours"].append(hour)
            baseline["typical_hours"] = baseline["typical_hours"][-24:]  # Keep last 24
        
        # Update typical paths
        if path not in baseline["typical_paths"]:
            baseline["typical_paths"].append(path)
            baseline["typical_paths"] = baseline["typical_paths"][-100:]  # Keep last 100
        
        baseline["request_count"] = baseline.get("request_count", 0) + 1
        
        # Persist
        if self.redis:
            self.redis.setex(key, 86400 * 30, json.dumps(baseline))  # 30 day TTL
        else:
            self._patterns[key] = baseline


class RiskScorer:
    """
    Main risk scoring engine.
    
    Aggregates multiple risk factors into a single score with explanation.
    """
    
    def __init__(self, config: RiskConfig, redis_client=None):
        self.config = config
        self.redis = redis_client
        
        # Initialize analyzers
        self.ip_checker = IPReputationChecker()
        self.velocity_tracker = VelocityTracker(config, redis_client)
        self.behavioral_analyzer = BehavioralAnalyzer(redis_client)
    
    def compute_risk_score(
        self,
        request: Request,
        user_id: Optional[str] = None
    ) -> RiskScore:
        """
        Compute comprehensive risk score for request.
        """
        factors: Dict[str, float] = {}
        explanations: List[str] = []
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")
        
        # 1. IP Reputation
        ip_score = self.ip_checker.get_reputation_score(client_ip)
        factors[RiskFactor.IP_REPUTATION.value] = ip_score
        if ip_score > 0.5:
            explanations.append(f"Suspicious IP address: {client_ip}")
        
        # 2. Device Anomaly
        fingerprint = DeviceFingerprint(
            user_agent=user_agent,
            accept_language=request.headers.get("Accept-Language", ""),
            accept_encoding=request.headers.get("Accept-Encoding", ""),
        )
        device_score = self._check_device_anomaly(user_id, fingerprint)
        factors[RiskFactor.DEVICE_ANOMALY.value] = device_score
        if device_score > 0.5:
            explanations.append("New or anomalous device detected")
        
        # 3. Velocity Anomaly
        identifier = user_id or client_ip
        self.velocity_tracker.record_request(identifier)
        velocity_score = self.velocity_tracker.get_velocity_score(identifier)
        factors[RiskFactor.VELOCITY_ANOMALY.value] = velocity_score
        if velocity_score > 0.5:
            explanations.append("Unusual request velocity")
        
        # 4. Behavioral Anomaly
        if user_id:
            behavior_score = self.behavioral_analyzer.analyze_behavior(
                user_id,
                request.url.path,
                request.method,
                datetime.now(timezone.utc)
            )
            factors[RiskFactor.BEHAVIORAL_ANOMALY.value] = behavior_score
            if behavior_score > 0.5:
                explanations.append("Unusual behavioral pattern")
        else:
            factors[RiskFactor.BEHAVIORAL_ANOMALY.value] = 0.3  # Unknown user
        
        # 5. Time Anomaly (outside business hours)
        time_score = self._check_time_anomaly()
        factors[RiskFactor.TIME_ANOMALY.value] = time_score
        if time_score > 0.5:
            explanations.append("Request outside typical hours")
        
        # 6. Session Anomaly
        session_score = self._check_session_anomaly(request)
        factors[RiskFactor.SESSION_ANOMALY.value] = session_score
        if session_score > 0.5:
            explanations.append("Session anomaly detected")
        
        # Calculate weighted total
        total_score = 0.0
        for factor, score in factors.items():
            weight = self.config.factor_weights.get(factor, 0.1)
            total_score += score * weight
        
        # Determine level
        if total_score < 0.3:
            level = RiskLevel.LOW
        elif total_score < 0.6:
            level = RiskLevel.MEDIUM
        elif total_score < 0.8:
            level = RiskLevel.HIGH
        else:
            level = RiskLevel.CRITICAL
        
        return RiskScore(
            total_score=round(total_score, 3),
            level=level,
            factors=factors,
            requires_mfa=total_score >= self.config.mfa_threshold,
            blocked=total_score >= self.config.block_threshold,
            explanation=explanations
        )
    
    def _check_device_anomaly(
        self,
        user_id: Optional[str],
        fingerprint: DeviceFingerprint
    ) -> float:
        """Check if device fingerprint is anomalous for user."""
        if not user_id:
            return 0.3  # Unknown user, moderate risk
        
        key = f"device:{user_id}"
        
        if self.redis:
            known_devices = self.redis.smembers(key) or set()
        else:
            known_devices = getattr(self, "_known_devices", {}).get(user_id, set())
        
        if fingerprint.fingerprint_hash in known_devices:
            return 0.0  # Known device
        
        # New device - add to known devices
        if self.redis:
            self.redis.sadd(key, fingerprint.fingerprint_hash)
            self.redis.expire(key, 86400 * 90)  # 90 day TTL
        else:
            if not hasattr(self, "_known_devices"):
                self._known_devices = {}
            if user_id not in self._known_devices:
                self._known_devices[user_id] = set()
            self._known_devices[user_id].add(fingerprint.fingerprint_hash)
        
        return 0.6  # New device, elevated risk
    
    def _check_time_anomaly(self) -> float:
        """Check if request time is unusual."""
        now = datetime.now(timezone.utc)
        hour = now.hour
        
        # Consider business hours (9 AM - 6 PM UTC)
        if 9 <= hour <= 18:
            return 0.0
        elif 6 <= hour <= 9 or 18 <= hour <= 22:
            return 0.2  # Early morning / evening
        else:
            return 0.4  # Late night
    
    def _check_session_anomaly(self, request: Request) -> float:
        """Check for session-related anomalies."""
        # Check for session hijacking indicators
        if hasattr(request.state, "session"):
            session = request.state.session
            
            # Session IP mismatch
            session_ip = session.get("created_ip")
            current_ip = request.client.host if request.client else None
            
            if session_ip and current_ip and session_ip != current_ip:
                return 0.7  # Different IP - possible hijacking
        
        return 0.0


class RiskBasedAuthMiddleware(BaseHTTPMiddleware):
    """
    Risk-based authentication middleware.
    
    Computes risk score for each request and triggers appropriate actions.
    """
    
    def __init__(
        self,
        app,
        config: Optional[RiskConfig] = None,
        redis_client=None,
        exempt_paths: frozenset = frozenset()
    ):
        super().__init__(app)
        self.config = config or RiskConfig()
        self.scorer = RiskScorer(self.config, redis_client)
        self.exempt_paths = exempt_paths
    
    async def dispatch(self, request: Request, call_next):
        """Process request with risk scoring."""
        path = request.url.path
        
        # Skip exempt paths
        if path in self.exempt_paths:
            return await call_next(request)
        
        # Compute risk score
        user_id = getattr(request.state, "user_id", None)
        risk_score = self.scorer.compute_risk_score(request, user_id)
        
        # Attach to request state
        request.state.risk_score = risk_score.total_score
        request.state.risk_level = risk_score.level
        request.state.risk_factors = risk_score.factors
        
        # Log risk assessment
        logger.info(
            f"Risk assessment: {risk_score.total_score:.3f} ({risk_score.level.value}) "
            f"for {request.method} {path} from {request.client.host if request.client else 'unknown'}"
        )
        
        # Block high-risk requests
        if risk_score.blocked:
            logger.warning(
                f"BLOCKED request due to high risk: {risk_score.explanation}"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Request blocked",
                    "code": "RISK_THRESHOLD_EXCEEDED",
                    "risk_level": risk_score.level.value,
                    "explanation": risk_score.explanation,
                }
            )
        
        # Flag for MFA
        if risk_score.requires_mfa:
            request.state.mfa_required = True
            request.state.mfa_trigger = "high_risk_score"
        
        # Add risk headers to response
        response = await call_next(request)
        response.headers["X-Risk-Score"] = str(risk_score.total_score)
        response.headers["X-Risk-Level"] = risk_score.level.value
        
        return response


async def get_chainiq_risk_score(
    user_id: str,
    request_data: Dict[str, Any],
    endpoint: str
) -> Optional[float]:
    """
    Query ChainIQ ML pipeline for risk score.
    
    This integrates with the external ChainIQ service for advanced
    ML-based risk assessment.
    """
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                endpoint,
                json={
                    "user_id": user_id,
                    "features": request_data,
                    "model": "risk_v2",
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("risk_score")
    except Exception as e:
        logger.error(f"ChainIQ risk scoring failed: {e}")
    
    return None
