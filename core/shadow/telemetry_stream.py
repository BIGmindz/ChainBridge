"""
PAC-SHADOW-BUILD-001: DUAL-PANE TELEMETRY STREAM
=================================================

Real-time telemetry streaming for shadow vs production comparison.
Enables God View Dashboard to visualize shadow execution congruence.

CAPABILITIES:
- Dual-stream telemetry (shadow + production)
- Real-time hash comparison
- Latency tracking (<50ms target)
- Divergence detection and alerting
- WebSocket streaming for UI
- Time-series event buffering

VISUALIZATION HOOKS:
- Shadow request stream (blue)
- Production request stream (green)
- Hash match indicator (congruence %)
- Latency histogram
- Divergence alerts (red)

Author: SONNY (GID-02)
PAC: CB-SHADOW-BUILD-001
Status: PRODUCTION-READY
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List, Deque, Callable
from decimal import Decimal


logger = logging.getLogger("TelemetryStream")


class ExecutionPath(Enum):
    """Execution path identifier."""
    SHADOW = "SHADOW"
    PRODUCTION = "PRODUCTION"


class TelemetryEventType(Enum):
    """Telemetry event types."""
    REQUEST_INITIATED = "REQUEST_INITIATED"
    RESPONSE_RECEIVED = "RESPONSE_RECEIVED"
    HASH_COMPARISON = "HASH_COMPARISON"
    DIVERGENCE_DETECTED = "DIVERGENCE_DETECTED"
    LATENCY_THRESHOLD = "LATENCY_THRESHOLD"
    STREAM_HEARTBEAT = "STREAM_HEARTBEAT"


@dataclass
class TelemetryEvent:
    """
    Single telemetry event for shadow/production comparison.
    
    Attributes:
        event_id: Unique event identifier
        event_type: Type of telemetry event
        execution_path: SHADOW or PRODUCTION
        timestamp_ms: Event timestamp (milliseconds since epoch)
        request_id: Associated request ID
        request_hash: SHA3-256 hash of request payload
        response_hash: SHA3-256 hash of response payload (if applicable)
        latency_ms: Request-to-response latency
        metadata: Additional event metadata
        congruence_score: Hash match score (0.0 to 1.0)
    """
    event_id: str
    event_type: TelemetryEventType
    execution_path: ExecutionPath
    timestamp_ms: int
    request_id: str = ""
    request_hash: str = ""
    response_hash: str = ""
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    congruence_score: float = 1.0


@dataclass
class StreamStatistics:
    """
    Telemetry stream statistics.
    
    Attributes:
        total_shadow_events: Total shadow path events
        total_production_events: Total production path events
        hash_matches: Number of exact hash matches
        hash_mismatches: Number of hash divergences
        avg_congruence_score: Average congruence score
        avg_shadow_latency_ms: Average shadow path latency
        avg_production_latency_ms: Average production path latency
        divergence_alerts: Number of divergence alerts triggered
        uptime_seconds: Stream uptime
    """
    total_shadow_events: int = 0
    total_production_events: int = 0
    hash_matches: int = 0
    hash_mismatches: int = 0
    avg_congruence_score: float = 1.0
    avg_shadow_latency_ms: float = 0.0
    avg_production_latency_ms: float = 0.0
    divergence_alerts: int = 0
    uptime_seconds: float = 0.0


class DualPaneTelemetryStream:
    """
    Dual-pane telemetry stream for shadow vs production comparison.
    
    Real-time telemetry streaming for God View Dashboard visualization.
    Tracks shadow and production execution paths, compares hashes,
    detects divergences, and streams events to UI via WebSocket.
    
    Features:
    - Dual-stream buffering (shadow + production)
    - Real-time hash comparison
    - Latency tracking (<50ms target)
    - Divergence detection and alerting
    - Time-series event buffering (configurable window)
    - WebSocket streaming hooks
    
    Usage:
        stream = DualPaneTelemetryStream(buffer_size=1000)
        
        # Track shadow request
        shadow_event = stream.track_request(
            execution_path=ExecutionPath.SHADOW,
            request_id="REQ-001",
            request_payload={"amount": 1000.00}
        )
        
        # Track production request
        prod_event = stream.track_request(
            execution_path=ExecutionPath.PRODUCTION,
            request_id="REQ-001",
            request_payload={"amount": 1000.00}
        )
        
        # Compare hashes
        congruence = stream.compare_hashes(shadow_event.event_id, prod_event.event_id)
    """
    
    def __init__(
        self,
        buffer_size: int = 1000,
        latency_threshold_ms: float = 50.0,
        heartbeat_interval_seconds: float = 5.0
    ):
        """
        Initialize dual-pane telemetry stream.
        
        Args:
            buffer_size: Maximum events to buffer per stream
            latency_threshold_ms: Latency alert threshold
            heartbeat_interval_seconds: Heartbeat interval
        """
        self.buffer_size = buffer_size
        self.latency_threshold_ms = latency_threshold_ms
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        
        # Dual buffers
        self.shadow_buffer: Deque[TelemetryEvent] = deque(maxlen=buffer_size)
        self.production_buffer: Deque[TelemetryEvent] = deque(maxlen=buffer_size)
        
        # Event lookup
        self.event_registry: Dict[str, TelemetryEvent] = {}
        
        # Statistics
        self.stats = StreamStatistics()
        self.start_time = time.time()
        
        # Subscribers (WebSocket handlers)
        self.subscribers: List[Callable[[TelemetryEvent], None]] = []
        
        # Heartbeat task
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        logger.info(
            f"📊 Dual-Pane Telemetry Stream initialized | "
            f"Buffer: {buffer_size} events | "
            f"Latency threshold: {latency_threshold_ms}ms"
        )
    
    def track_request(
        self,
        execution_path: ExecutionPath,
        request_id: str,
        request_payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> TelemetryEvent:
        """
        Track a request in the telemetry stream.
        
        Args:
            execution_path: SHADOW or PRODUCTION
            request_id: Request identifier
            request_payload: Request payload for hashing
            metadata: Optional metadata
            
        Returns:
            TelemetryEvent created
        """
        start_time = time.time()
        
        # Compute request hash
        request_json = json.dumps(request_payload, sort_keys=True, default=str)
        request_hash = hashlib.sha3_256(request_json.encode()).hexdigest()
        
        # Create event
        event = TelemetryEvent(
            event_id=self._generate_event_id(),
            event_type=TelemetryEventType.REQUEST_INITIATED,
            execution_path=execution_path,
            timestamp_ms=int(time.time() * 1000),
            request_id=request_id,
            request_hash=request_hash,
            metadata=metadata or {}
        )
        
        # Buffer event
        self._buffer_event(event)
        
        # Update statistics
        if execution_path == ExecutionPath.SHADOW:
            self.stats.total_shadow_events += 1
        else:
            self.stats.total_production_events += 1
        
        # Notify subscribers
        self._notify_subscribers(event)
        
        latency = (time.time() - start_time) * 1000
        logger.debug(
            f"📥 Request tracked | "
            f"Path: {execution_path.value} | "
            f"ID: {request_id} | "
            f"Hash: {request_hash[:16]}... | "
            f"Latency: {latency:.2f}ms"
        )
        
        return event
    
    def track_response(
        self,
        execution_path: ExecutionPath,
        request_id: str,
        response_payload: Dict[str, Any],
        request_start_ms: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TelemetryEvent:
        """
        Track a response in the telemetry stream.
        
        Args:
            execution_path: SHADOW or PRODUCTION
            request_id: Request identifier
            response_payload: Response payload for hashing
            request_start_ms: Request start timestamp (for latency calculation)
            metadata: Optional metadata
            
        Returns:
            TelemetryEvent created
        """
        # Compute response hash
        response_json = json.dumps(response_payload, sort_keys=True, default=str)
        response_hash = hashlib.sha3_256(response_json.encode()).hexdigest()
        
        # Calculate latency
        now_ms = int(time.time() * 1000)
        latency_ms = now_ms - request_start_ms
        
        # Create event
        event = TelemetryEvent(
            event_id=self._generate_event_id(),
            event_type=TelemetryEventType.RESPONSE_RECEIVED,
            execution_path=execution_path,
            timestamp_ms=now_ms,
            request_id=request_id,
            response_hash=response_hash,
            latency_ms=latency_ms,
            metadata=metadata or {}
        )
        
        # Buffer event
        self._buffer_event(event)
        
        # Update latency statistics
        if execution_path == ExecutionPath.SHADOW:
            self._update_avg_latency(latency_ms, is_shadow=True)
        else:
            self._update_avg_latency(latency_ms, is_shadow=False)
        
        # Check latency threshold
        if latency_ms > self.latency_threshold_ms:
            self._alert_latency_threshold(execution_path, request_id, latency_ms)
        
        # Notify subscribers
        self._notify_subscribers(event)
        
        logger.debug(
            f"📤 Response tracked | "
            f"Path: {execution_path.value} | "
            f"ID: {request_id} | "
            f"Hash: {response_hash[:16]}... | "
            f"Latency: {latency_ms:.2f}ms"
        )
        
        return event
    
    def compare_hashes(
        self,
        shadow_event_id: str,
        production_event_id: str
    ) -> float:
        """
        Compare hashes between shadow and production events.
        
        Args:
            shadow_event_id: Shadow event ID
            production_event_id: Production event ID
            
        Returns:
            Congruence score (1.0 = perfect match, 0.0 = mismatch)
        """
        shadow_event = self.event_registry.get(shadow_event_id)
        prod_event = self.event_registry.get(production_event_id)
        
        if not shadow_event or not prod_event:
            logger.warning("⚠️ Event not found for hash comparison")
            return 0.0
        
        # Compare request hashes
        request_match = shadow_event.request_hash == prod_event.request_hash
        
        # Compare response hashes (if both present)
        response_match = True
        if shadow_event.response_hash and prod_event.response_hash:
            response_match = shadow_event.response_hash == prod_event.response_hash
        
        # Compute congruence score
        congruence = 1.0 if (request_match and response_match) else 0.0
        
        # Create comparison event
        comparison_event = TelemetryEvent(
            event_id=self._generate_event_id(),
            event_type=TelemetryEventType.HASH_COMPARISON,
            execution_path=ExecutionPath.SHADOW,  # Arbitrary
            timestamp_ms=int(time.time() * 1000),
            request_id=shadow_event.request_id,
            congruence_score=congruence,
            metadata={
                "shadow_event_id": shadow_event_id,
                "production_event_id": production_event_id,
                "request_match": request_match,
                "response_match": response_match
            }
        )
        
        # Update statistics
        if congruence == 1.0:
            self.stats.hash_matches += 1
        else:
            self.stats.hash_mismatches += 1
            self._alert_divergence(shadow_event, prod_event)
        
        self._update_avg_congruence(congruence)
        
        # Notify subscribers
        self._notify_subscribers(comparison_event)
        
        logger.info(
            f"🔍 Hash comparison | "
            f"Request: {shadow_event.request_id} | "
            f"Congruence: {congruence * 100:.1f}% | "
            f"Request match: {request_match} | "
            f"Response match: {response_match}"
        )
        
        return congruence
    
    def _buffer_event(self, event: TelemetryEvent):
        """Buffer event in appropriate stream."""
        if event.execution_path == ExecutionPath.SHADOW:
            self.shadow_buffer.append(event)
        else:
            self.production_buffer.append(event)
        
        self.event_registry[event.event_id] = event
    
    def _alert_divergence(
        self,
        shadow_event: TelemetryEvent,
        prod_event: TelemetryEvent
    ):
        """Alert on hash divergence."""
        divergence_event = TelemetryEvent(
            event_id=self._generate_event_id(),
            event_type=TelemetryEventType.DIVERGENCE_DETECTED,
            execution_path=ExecutionPath.SHADOW,
            timestamp_ms=int(time.time() * 1000),
            request_id=shadow_event.request_id,
            metadata={
                "shadow_hash": shadow_event.request_hash or shadow_event.response_hash,
                "production_hash": prod_event.request_hash or prod_event.response_hash,
                "alert_severity": "HIGH"
            }
        )
        
        self.stats.divergence_alerts += 1
        self._notify_subscribers(divergence_event)
        
        logger.warning(
            f"🚨 DIVERGENCE DETECTED | "
            f"Request: {shadow_event.request_id} | "
            f"Shadow hash: {shadow_event.request_hash[:16]}... | "
            f"Production hash: {prod_event.request_hash[:16]}..."
        )
    
    def _alert_latency_threshold(
        self,
        execution_path: ExecutionPath,
        request_id: str,
        latency_ms: float
    ):
        """Alert on latency threshold breach."""
        alert_event = TelemetryEvent(
            event_id=self._generate_event_id(),
            event_type=TelemetryEventType.LATENCY_THRESHOLD,
            execution_path=execution_path,
            timestamp_ms=int(time.time() * 1000),
            request_id=request_id,
            latency_ms=latency_ms,
            metadata={
                "threshold_ms": self.latency_threshold_ms,
                "breach_ms": latency_ms - self.latency_threshold_ms
            }
        )
        
        self._notify_subscribers(alert_event)
        
        logger.warning(
            f"⏱️ LATENCY THRESHOLD BREACH | "
            f"Path: {execution_path.value} | "
            f"Request: {request_id} | "
            f"Latency: {latency_ms:.2f}ms (threshold: {self.latency_threshold_ms}ms)"
        )
    
    def _update_avg_latency(self, latency_ms: float, is_shadow: bool):
        """Update average latency statistics."""
        if is_shadow:
            total = self.stats.total_shadow_events
            if total > 0:
                self.stats.avg_shadow_latency_ms = (
                    (self.stats.avg_shadow_latency_ms * (total - 1) + latency_ms) / total
                )
        else:
            total = self.stats.total_production_events
            if total > 0:
                self.stats.avg_production_latency_ms = (
                    (self.stats.avg_production_latency_ms * (total - 1) + latency_ms) / total
                )
    
    def _update_avg_congruence(self, congruence: float):
        """Update average congruence score."""
        total_comparisons = self.stats.hash_matches + self.stats.hash_mismatches
        if total_comparisons > 0:
            self.stats.avg_congruence_score = (
                (self.stats.avg_congruence_score * (total_comparisons - 1) + congruence) / total_comparisons
            )
    
    def subscribe(self, handler: Callable[[TelemetryEvent], None]):
        """Subscribe to telemetry events (WebSocket hook)."""
        self.subscribers.append(handler)
        logger.info(f"📡 Subscriber added (total: {len(self.subscribers)})")
    
    def unsubscribe(self, handler: Callable[[TelemetryEvent], None]):
        """Unsubscribe from telemetry events."""
        if handler in self.subscribers:
            self.subscribers.remove(handler)
            logger.info(f"📡 Subscriber removed (total: {len(self.subscribers)})")
    
    def _notify_subscribers(self, event: TelemetryEvent):
        """Notify all subscribers of new event."""
        for handler in self.subscribers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"❌ Subscriber notification failed: {e}")
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        import uuid
        return f"EVT-{uuid.uuid4().hex[:16].upper()}"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get stream statistics."""
        self.stats.uptime_seconds = time.time() - self.start_time
        return asdict(self.stats)
    
    def get_recent_events(
        self,
        execution_path: Optional[ExecutionPath] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent events from buffer.
        
        Args:
            execution_path: Filter by path (None = both)
            limit: Maximum events to return
            
        Returns:
            List of event dictionaries
        """
        if execution_path == ExecutionPath.SHADOW:
            events = list(self.shadow_buffer)[-limit:]
        elif execution_path == ExecutionPath.PRODUCTION:
            events = list(self.production_buffer)[-limit:]
        else:
            # Merge both buffers
            events = list(self.shadow_buffer) + list(self.production_buffer)
            events = sorted(events, key=lambda e: e.timestamp_ms)[-limit:]
        
        return [asdict(e) for e in events]
    
    async def start_heartbeat(self):
        """Start heartbeat task."""
        async def heartbeat_loop():
            while True:
                await asyncio.sleep(self.heartbeat_interval_seconds)
                
                heartbeat_event = TelemetryEvent(
                    event_id=self._generate_event_id(),
                    event_type=TelemetryEventType.STREAM_HEARTBEAT,
                    execution_path=ExecutionPath.SHADOW,
                    timestamp_ms=int(time.time() * 1000),
                    metadata=self.get_statistics()
                )
                
                self._notify_subscribers(heartbeat_event)
                logger.debug("💓 Heartbeat sent")
        
        self.heartbeat_task = asyncio.create_task(heartbeat_loop())
        logger.info(f"💓 Heartbeat task started (interval: {self.heartbeat_interval_seconds}s)")
    
    async def stop_heartbeat(self):
        """Stop heartbeat task."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info("💓 Heartbeat task stopped")


if __name__ == "__main__":
    # Self-test
    logging.basicConfig(level=logging.INFO)
    
    print("═" * 80)
    print("DUAL-PANE TELEMETRY STREAM - SELF-TEST")
    print("═" * 80)
    
    stream = DualPaneTelemetryStream(
        buffer_size=100,
        latency_threshold_ms=50.0
    )
    
    # Test 1: Track shadow request
    print("\n📋 TEST 1: Track Shadow Request")
    shadow_req_event = stream.track_request(
        execution_path=ExecutionPath.SHADOW,
        request_id="REQ-001",
        request_payload={"amount": 1000.00, "from": "CITIUS33", "to": "HSBCUS33"}
    )
    print(f"Event ID: {shadow_req_event.event_id}")
    print(f"Request Hash: {shadow_req_event.request_hash[:32]}...")
    
    # Test 2: Track production request (matching)
    print("\n📋 TEST 2: Track Production Request (Matching)")
    prod_req_event = stream.track_request(
        execution_path=ExecutionPath.PRODUCTION,
        request_id="REQ-001",
        request_payload={"amount": 1000.00, "from": "CITIUS33", "to": "HSBCUS33"}
    )
    print(f"Event ID: {prod_req_event.event_id}")
    print(f"Request Hash: {prod_req_event.request_hash[:32]}...")
    
    # Test 3: Compare hashes (should match)
    print("\n📋 TEST 3: Compare Hashes (Should Match)")
    congruence = stream.compare_hashes(shadow_req_event.event_id, prod_req_event.event_id)
    print(f"Congruence: {congruence * 100:.1f}% (expected 100%)")
    
    # Test 4: Track responses
    print("\n📋 TEST 4: Track Responses")
    shadow_resp_event = stream.track_response(
        execution_path=ExecutionPath.SHADOW,
        request_id="REQ-001",
        response_payload={"status": "ACCP", "txn_id": "TXN-001"},
        request_start_ms=shadow_req_event.timestamp_ms
    )
    print(f"Shadow Response Latency: {shadow_resp_event.latency_ms:.2f}ms")
    
    prod_resp_event = stream.track_response(
        execution_path=ExecutionPath.PRODUCTION,
        request_id="REQ-001",
        response_payload={"status": "ACCP", "txn_id": "TXN-001"},
        request_start_ms=prod_req_event.timestamp_ms
    )
    print(f"Production Response Latency: {prod_resp_event.latency_ms:.2f}ms")
    
    # Test 5: Divergence detection
    print("\n📋 TEST 5: Divergence Detection")
    divergent_event = stream.track_request(
        execution_path=ExecutionPath.PRODUCTION,
        request_id="REQ-002",
        request_payload={"amount": 2000.00, "from": "DIFFERENT", "to": "HSBCUS33"}
    )
    shadow_event2 = stream.track_request(
        execution_path=ExecutionPath.SHADOW,
        request_id="REQ-002",
        request_payload={"amount": 1000.00, "from": "CITIUS33", "to": "HSBCUS33"}
    )
    congruence2 = stream.compare_hashes(shadow_event2.event_id, divergent_event.event_id)
    print(f"Congruence: {congruence2 * 100:.1f}% (expected 0% - divergent)")
    
    # Test 6: Subscriber notification
    print("\n📋 TEST 6: Subscriber Notification")
    received_events = []
    
    def test_handler(event: TelemetryEvent):
        received_events.append(event)
    
    stream.subscribe(test_handler)
    stream.track_request(
        execution_path=ExecutionPath.SHADOW,
        request_id="REQ-003",
        request_payload={"test": "subscriber"}
    )
    print(f"Events received by subscriber: {len(received_events)}")
    
    # Statistics
    print("\n📊 STREAM STATISTICS:")
    stats = stream.get_statistics()
    print(json.dumps(stats, indent=2, default=str))
    
    # Recent events
    print("\n📋 RECENT EVENTS (Shadow):")
    recent = stream.get_recent_events(execution_path=ExecutionPath.SHADOW, limit=3)
    print(f"Total recent shadow events: {len(recent)}")
    
    print("\n✅ DUAL-PANE TELEMETRY STREAM OPERATIONAL")
    print("═" * 80)
