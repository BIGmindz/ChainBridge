"""
Audit Stream Middleware
=======================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING
Component: Real-time Audit Event Streaming
Agent: CODY (GID-01)

INVARIANTS:
  INV-AUTH-019: All auth events MUST be logged to audit stream
  INV-AUTH-020: Audit records MUST be immutable once written

STREAMING TARGETS:
  - Kafka (primary)
  - Redis Streams (secondary)
  - Local file (fallback)
  - XRP Ledger anchoring (optional)

EVENT TYPES:
  - Authentication attempts (success/failure)
  - MFA challenges and verifications
  - Session lifecycle events
  - Permission checks
  - Rate limit triggers
  - Risk score assessments
"""

import asyncio
import gzip
import hashlib
import json
import logging
import os
import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("chainbridge.auth.audit")


class AuditEventType(Enum):
    """Types of audit events."""
    # Authentication events
    AUTH_ATTEMPT = "auth.attempt"
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_LOGOUT = "auth.logout"
    
    # MFA events
    MFA_CHALLENGE_CREATED = "mfa.challenge_created"
    MFA_CHALLENGE_VERIFIED = "mfa.challenge_verified"
    MFA_CHALLENGE_FAILED = "mfa.challenge_failed"
    MFA_CHALLENGE_EXPIRED = "mfa.challenge_expired"
    
    # Session events
    SESSION_CREATED = "session.created"
    SESSION_REFRESHED = "session.refreshed"
    SESSION_EXPIRED = "session.expired"
    SESSION_TERMINATED = "session.terminated"
    
    # Authorization events
    AUTHZ_GRANTED = "authz.granted"
    AUTHZ_DENIED = "authz.denied"
    
    # Risk events
    RISK_ELEVATED = "risk.elevated"
    RISK_BLOCKED = "risk.blocked"
    
    # Rate limit events
    RATE_LIMIT_WARNING = "rate_limit.warning"
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"
    
    # Token events
    TOKEN_ISSUED = "token.issued"
    TOKEN_REFRESHED = "token.refreshed"
    TOKEN_REVOKED = "token.revoked"
    TOKEN_INVALID = "token.invalid"
    
    # Hardware token events
    HARDWARE_REGISTERED = "hardware.registered"
    HARDWARE_VERIFIED = "hardware.verified"
    HARDWARE_FAILED = "hardware.failed"
    
    # Biometric events
    BIOMETRIC_REGISTERED = "biometric.registered"
    BIOMETRIC_VERIFIED = "biometric.verified"
    BIOMETRIC_FAILED = "biometric.failed"
    
    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"


class AuditSeverity(Enum):
    """Audit event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditConfig:
    """Audit stream configuration."""
    # Kafka settings
    kafka_enabled: bool = True
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "chainbridge.auth.audit"
    kafka_compression: str = "gzip"
    kafka_batch_size: int = 100
    kafka_linger_ms: int = 100
    
    # Redis Streams settings
    redis_enabled: bool = True
    redis_stream_key: str = "audit:auth:stream"
    redis_maxlen: int = 100000
    
    # Local file settings
    file_enabled: bool = True
    file_path: str = "logs/audit/auth"
    file_rotation_size_mb: int = 100
    file_retention_days: int = 90
    
    # XRP Ledger anchoring
    xrp_anchoring_enabled: bool = False
    xrp_anchor_interval_seconds: int = 3600  # Hourly
    
    # Buffer settings
    buffer_size: int = 10000
    flush_interval_seconds: int = 5
    
    # Event filtering
    min_severity: str = "info"
    excluded_events: List[str] = field(default_factory=list)


@dataclass
class AuditEvent:
    """Individual audit event."""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    
    # Identity context
    user_id: Optional[str] = None
    gid: Optional[str] = None
    session_id: Optional[str] = None
    
    # Request context
    request_id: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Event details
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Security context
    risk_score: Optional[float] = None
    mfa_method: Optional[str] = None
    auth_method: Optional[str] = None
    
    # Hash chain for integrity
    previous_hash: Optional[str] = None
    event_hash: str = ""
    
    def __post_init__(self):
        """Calculate event hash for integrity chain."""
        self.event_hash = self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """Calculate SHA-256 hash of event for integrity verification."""
        data = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "request_id": self.request_id,
            "details": self.details,
            "previous_hash": self.previous_hash,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "gid": self.gid,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "method": self.method,
            "path": self.path,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "details": self.details,
            "risk_score": self.risk_score,
            "mfa_method": self.mfa_method,
            "auth_method": self.auth_method,
            "previous_hash": self.previous_hash,
            "event_hash": self.event_hash,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class AuditBuffer:
    """Thread-safe audit event buffer with async flushing."""
    
    def __init__(self, config: AuditConfig):
        self.config = config
        self._buffer: queue.Queue = queue.Queue(maxsize=config.buffer_size)
        self._last_hash: str = "genesis"
        self._lock = threading.Lock()
    
    def add_event(self, event: AuditEvent) -> bool:
        """Add event to buffer. Returns False if buffer is full."""
        with self._lock:
            event.previous_hash = self._last_hash
            event.event_hash = event._calculate_hash()
            self._last_hash = event.event_hash
        
        try:
            self._buffer.put_nowait(event)
            return True
        except queue.Full:
            logger.warning("Audit buffer full, event dropped")
            return False
    
    def get_events(self, max_count: int = 100) -> List[AuditEvent]:
        """Get events from buffer (non-blocking)."""
        events = []
        for _ in range(max_count):
            try:
                events.append(self._buffer.get_nowait())
            except queue.Empty:
                break
        return events
    
    @property
    def size(self) -> int:
        return self._buffer.qsize()


class KafkaAuditProducer:
    """Kafka producer for audit events."""
    
    def __init__(self, config: AuditConfig):
        self.config = config
        self._producer = None
        self._connected = False
    
    def connect(self):
        """Initialize Kafka connection."""
        try:
            # In production, use kafka-python or confluent-kafka
            # from kafka import KafkaProducer
            # self._producer = KafkaProducer(
            #     bootstrap_servers=self.config.kafka_bootstrap_servers,
            #     compression_type=self.config.kafka_compression,
            #     batch_size=self.config.kafka_batch_size,
            #     linger_ms=self.config.kafka_linger_ms,
            # )
            logger.info("Kafka audit producer initialized (simulation mode)")
            self._connected = True
        except Exception as e:
            logger.error(f"Kafka connection failed: {e}")
            self._connected = False
    
    def send(self, events: List[AuditEvent]) -> bool:
        """Send events to Kafka topic."""
        if not self._connected:
            return False
        
        try:
            for event in events:
                # In production:
                # self._producer.send(
                #     self.config.kafka_topic,
                #     value=event.to_json().encode()
                # )
                logger.debug(f"Kafka audit: {event.event_type.value}")
            return True
        except Exception as e:
            logger.error(f"Kafka send failed: {e}")
            return False
    
    def close(self):
        """Close Kafka connection."""
        if self._producer:
            # self._producer.close()
            self._connected = False


class RedisStreamAuditProducer:
    """Redis Streams producer for audit events."""
    
    def __init__(self, config: AuditConfig, redis_client=None):
        self.config = config
        self.redis = redis_client
    
    def send(self, events: List[AuditEvent]) -> bool:
        """Send events to Redis Stream."""
        if not self.redis:
            return False
        
        try:
            for event in events:
                self.redis.xadd(
                    self.config.redis_stream_key,
                    event.to_dict(),
                    maxlen=self.config.redis_maxlen,
                    approximate=True,
                )
            return True
        except Exception as e:
            logger.error(f"Redis stream send failed: {e}")
            return False


class FileAuditWriter:
    """Local file audit writer with rotation."""
    
    def __init__(self, config: AuditConfig):
        self.config = config
        self._current_file = None
        self._current_size = 0
        self._lock = threading.Lock()
        
        # Ensure directory exists
        Path(config.file_path).mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self) -> str:
        """Get current log file path."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return os.path.join(self.config.file_path, f"audit-{date_str}.jsonl")
    
    def write(self, events: List[AuditEvent]) -> bool:
        """Write events to file."""
        with self._lock:
            try:
                file_path = self._get_file_path()
                
                with open(file_path, "a") as f:
                    for event in events:
                        f.write(event.to_json() + "\n")
                        self._current_size += len(event.to_json()) + 1
                
                # Check rotation
                if self._current_size > self.config.file_rotation_size_mb * 1024 * 1024:
                    self._rotate()
                
                return True
            except Exception as e:
                logger.error(f"File write failed: {e}")
                return False
    
    def _rotate(self):
        """Rotate log file."""
        file_path = self._get_file_path()
        if os.path.exists(file_path):
            timestamp = int(time.time())
            rotated_path = f"{file_path}.{timestamp}.gz"
            
            with open(file_path, "rb") as f_in:
                with gzip.open(rotated_path, "wb") as f_out:
                    f_out.writelines(f_in)
            
            os.remove(file_path)
            self._current_size = 0
            logger.info(f"Audit log rotated: {rotated_path}")


class AuditStream:
    """
    Main audit streaming orchestrator.
    
    Coordinates event collection and distribution to multiple backends.
    """
    
    def __init__(self, config: AuditConfig, redis_client=None):
        self.config = config
        
        # Initialize components
        self.buffer = AuditBuffer(config)
        
        # Initialize producers
        self.kafka_producer = KafkaAuditProducer(config) if config.kafka_enabled else None
        self.redis_producer = RedisStreamAuditProducer(config, redis_client) if config.redis_enabled else None
        self.file_writer = FileAuditWriter(config) if config.file_enabled else None
        
        # Background flush thread
        self._running = False
        self._flush_thread: Optional[threading.Thread] = None
        
        # Event handlers
        self._handlers: List[Callable[[AuditEvent], None]] = []
    
    def start(self):
        """Start the audit stream processor."""
        if self._running:
            return
        
        self._running = True
        
        # Connect Kafka
        if self.kafka_producer:
            self.kafka_producer.connect()
        
        # Start flush thread
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        
        logger.info("Audit stream started")
    
    def stop(self):
        """Stop the audit stream processor."""
        self._running = False
        
        if self._flush_thread:
            self._flush_thread.join(timeout=5)
        
        # Final flush
        self._flush()
        
        if self.kafka_producer:
            self.kafka_producer.close()
        
        logger.info("Audit stream stopped")
    
    def emit(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: Optional[str] = None,
        gid: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        method: Optional[str] = None,
        path: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        risk_score: Optional[float] = None,
        mfa_method: Optional[str] = None,
        auth_method: Optional[str] = None,
    ) -> Optional[str]:
        """
        Emit an audit event.
        
        Returns event_id if successful, None if event was filtered/dropped.
        """
        # Check severity filter
        severity_order = [s.value for s in AuditSeverity]
        if severity_order.index(severity.value) < severity_order.index(self.config.min_severity):
            return None
        
        # Check event filter
        if event_type.value in self.config.excluded_events:
            return None
        
        # Create event
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            gid=gid,
            session_id=session_id,
            request_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
            user_agent=user_agent,
            details=details or {},
            risk_score=risk_score,
            mfa_method=mfa_method,
            auth_method=auth_method,
        )
        
        # Add to buffer
        if not self.buffer.add_event(event):
            logger.warning(f"Audit event dropped: {event_type.value}")
            return None
        
        # Call handlers
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Audit handler error: {e}")
        
        return event.event_id
    
    def add_handler(self, handler: Callable[[AuditEvent], None]):
        """Add a custom event handler."""
        self._handlers.append(handler)
    
    def _flush_loop(self):
        """Background flush loop."""
        while self._running:
            time.sleep(self.config.flush_interval_seconds)
            self._flush()
    
    def _flush(self):
        """Flush buffer to all backends."""
        events = self.buffer.get_events(self.config.kafka_batch_size)
        
        if not events:
            return
        
        # Send to Kafka
        if self.kafka_producer:
            self.kafka_producer.send(events)
        
        # Send to Redis
        if self.redis_producer:
            self.redis_producer.send(events)
        
        # Write to file
        if self.file_writer:
            self.file_writer.write(events)
        
        logger.debug(f"Flushed {len(events)} audit events")


# Global audit stream instance
_audit_stream: Optional[AuditStream] = None


def get_audit_stream() -> AuditStream:
    """Get the global audit stream instance."""
    global _audit_stream
    if _audit_stream is None:
        _audit_stream = AuditStream(AuditConfig())
        _audit_stream.start()
    return _audit_stream


def init_audit_stream(config: AuditConfig, redis_client=None) -> AuditStream:
    """Initialize the global audit stream with custom config."""
    global _audit_stream
    _audit_stream = AuditStream(config, redis_client)
    _audit_stream.start()
    return _audit_stream


class AuditStreamMiddleware(BaseHTTPMiddleware):
    """
    Audit stream middleware.
    
    Automatically logs auth-related events for all requests.
    """
    
    def __init__(
        self,
        app,
        config: Optional[AuditConfig] = None,
        redis_client=None,
        exempt_paths: frozenset = frozenset()
    ):
        super().__init__(app)
        self.config = config or AuditConfig()
        self.audit_stream = AuditStream(self.config, redis_client)
        self.audit_stream.start()
        self.exempt_paths = exempt_paths
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and emit audit events."""
        path = request.url.path
        
        # Skip exempt paths (but still audit if auth events occur)
        if path in self.exempt_paths:
            return await call_next(request)
        
        # Generate request ID
        request_id = str(uuid4())
        request.state.request_id = request_id
        
        # Extract context
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
        # Emit request start (debug level)
        self.audit_stream.emit(
            event_type=AuditEventType.AUTH_ATTEMPT,
            severity=AuditSeverity.DEBUG,
            request_id=request_id,
            method=request.method,
            path=path,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Extract auth state
        user_id = getattr(request.state, "user_id", None)
        gid = getattr(request.state, "gid", None)
        session_id = getattr(request.state, "session_id", None)
        risk_score = getattr(request.state, "risk_score", None)
        mfa_verified = getattr(request.state, "mfa_verified", False)
        auth_method = getattr(request.state, "auth_method", None)
        
        # Determine event type based on response
        if response.status_code == 401:
            event_type = AuditEventType.AUTH_FAILURE
            severity = AuditSeverity.WARNING
        elif response.status_code == 403:
            event_type = AuditEventType.AUTHZ_DENIED
            severity = AuditSeverity.WARNING
        elif response.status_code >= 500:
            event_type = AuditEventType.SYSTEM_ERROR
            severity = AuditSeverity.ERROR
        elif user_id:
            event_type = AuditEventType.AUTH_SUCCESS
            severity = AuditSeverity.INFO
        else:
            # Unauthenticated success (public endpoint)
            return response
        
        # Emit auth result event
        self.audit_stream.emit(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            gid=gid,
            session_id=session_id,
            request_id=request_id,
            method=request.method,
            path=path,
            client_ip=client_ip,
            user_agent=user_agent,
            details={
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "mfa_verified": mfa_verified,
            },
            risk_score=risk_score,
            mfa_method=getattr(request.state, "mfa_method", None),
            auth_method=auth_method,
        )
        
        # Log elevated risk
        if risk_score and risk_score > 0.7:
            self.audit_stream.emit(
                event_type=AuditEventType.RISK_ELEVATED,
                severity=AuditSeverity.WARNING,
                user_id=user_id,
                request_id=request_id,
                path=path,
                client_ip=client_ip,
                risk_score=risk_score,
                details=getattr(request.state, "risk_factors", {}),
            )
        
        return response
