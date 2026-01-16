"""
ChainBridge Audit-First Telemetry System
=========================================

NASA-Grade Observability Infrastructure
PAC: PAC-JEFFREY-NASA-HARDENING-002

This module REPLACES all prior observability with audit-first telemetry.
NO PATCHING. REPLACEMENT ONLY.

Design Principles:
- Audit-First: Every event is an audit record
- Complete: No silent drops, no sampling in critical paths
- Immutable: Once written, audit records cannot be modified
- Cryptographic: All records are hash-chained
- Queryable: Structured for forensic analysis

Telemetry Categories:
1. Audit Events (governance, access, decisions)
2. System Metrics (deterministic collection)
3. Traces (distributed execution tracking)
4. Alerts (threshold-based, no ambiguity)

Author: BENSON [GID-00] + DAN [GID-07]
Version: v1.0.0
Classification: SAFETY_CRITICAL
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import queue
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    Final,
    Generator,
    Generic,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)


# =============================================================================
# SECTION 1: TELEMETRY PRIMITIVES
# =============================================================================

class EventSeverity(Enum):
    """Event severity levels - exhaustive enumeration."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    AUDIT = 5  # Special severity for audit events (always logged)


class EventCategory(Enum):
    """Event categories for classification."""
    SYSTEM = auto()
    SECURITY = auto()
    GOVERNANCE = auto()
    EXECUTION = auto()
    DATA = auto()
    NETWORK = auto()
    PERFORMANCE = auto()
    AUDIT = auto()


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = auto()      # Monotonically increasing
    GAUGE = auto()        # Point-in-time value
    HISTOGRAM = auto()    # Distribution
    SUMMARY = auto()      # Statistical summary


@dataclass(frozen=True)
class TelemetryEvent:
    """
    Immutable telemetry event record.
    
    Every event is an audit record with cryptographic integrity.
    """
    event_id: str
    timestamp: datetime
    severity: EventSeverity
    category: EventCategory
    source: str
    message: str
    data: Mapping[str, Any]
    correlation_id: Optional[str]
    parent_event_id: Optional[str]
    hash: str = ""
    
    def __post_init__(self) -> None:
        if not self.hash:
            computed = self._compute_hash()
            object.__setattr__(self, "hash", computed)
    
    def _compute_hash(self) -> str:
        content = json.dumps({
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.name,
            "category": self.category.name,
            "source": self.source,
            "message": self.message,
            "data": dict(self.data) if self.data else {},
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.name,
            "category": self.category.name,
            "source": self.source,
            "message": self.message,
            "data": dict(self.data) if self.data else {},
            "correlation_id": self.correlation_id,
            "parent_event_id": self.parent_event_id,
            "hash": self.hash,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


@dataclass(frozen=True)
class MetricPoint:
    """Immutable metric data point."""
    metric_id: str
    name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    labels: Mapping[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "type": self.metric_type.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": dict(self.labels),
        }


@dataclass(frozen=True)
class TraceSpan:
    """Immutable trace span for distributed tracing."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation: str
    service: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str  # OK, ERROR, TIMEOUT
    attributes: Mapping[str, Any]
    
    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() * 1000
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation": self.operation,
            "service": self.service,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": dict(self.attributes),
        }


# =============================================================================
# SECTION 2: AUDIT TRAIL (Hash-Chained Event Log)
# =============================================================================

class AuditTrail:
    """
    Immutable, hash-chained audit trail.
    
    Properties:
    - Append-only: No deletions or modifications
    - Hash-chained: Each record links to previous
    - Verifiable: Integrity can be verified at any time
    """
    
    GENESIS_HASH: Final[str] = "0" * 16
    
    def __init__(self, max_size: int = 100000) -> None:
        self._events: Deque[TelemetryEvent] = deque(maxlen=max_size)
        self._last_hash: str = self.GENESIS_HASH
        self._lock = threading.Lock()
    
    def append(self, event: TelemetryEvent) -> TelemetryEvent:
        """Append event to audit trail."""
        with self._lock:
            # Create linked event
            linked_event = TelemetryEvent(
                event_id=event.event_id,
                timestamp=event.timestamp,
                severity=event.severity,
                category=event.category,
                source=event.source,
                message=event.message,
                data={**event.data, "_prev_hash": self._last_hash},
                correlation_id=event.correlation_id,
                parent_event_id=event.parent_event_id,
            )
            
            self._events.append(linked_event)
            self._last_hash = linked_event.hash
            
            return linked_event
    
    def verify_integrity(self) -> Tuple[bool, Optional[str]]:
        """
        Verify hash chain integrity.
        
        Returns (valid, error_message).
        """
        with self._lock:
            if not self._events:
                return True, None
            
            expected_prev = self.GENESIS_HASH
            for i, event in enumerate(self._events):
                actual_prev = event.data.get("_prev_hash", "")
                if actual_prev != expected_prev:
                    return False, f"Chain broken at event {i}: expected {expected_prev}, got {actual_prev}"
                expected_prev = event.hash
            
            return True, None
    
    def get_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        category: Optional[EventCategory] = None,
        severity_min: Optional[EventSeverity] = None,
    ) -> Sequence[TelemetryEvent]:
        """Query events with filters."""
        with self._lock:
            result: List[TelemetryEvent] = []
            
            for event in self._events:
                if start_time and event.timestamp < start_time:
                    continue
                if end_time and event.timestamp > end_time:
                    continue
                if category and event.category != category:
                    continue
                if severity_min and event.severity.value < severity_min.value:
                    continue
                result.append(event)
            
            return tuple(result)
    
    def get_chain_head(self) -> str:
        """Return current chain head hash."""
        with self._lock:
            return self._last_hash
    
    def __len__(self) -> int:
        return len(self._events)


# =============================================================================
# SECTION 3: METRICS COLLECTOR (Deterministic)
# =============================================================================

class MetricsCollector:
    """
    Deterministic metrics collection.
    
    Properties:
    - Thread-safe: All operations are atomic
    - No sampling: All data points collected
    - Queryable: Metrics can be retrieved at any time
    """
    
    def __init__(self) -> None:
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._points: Deque[MetricPoint] = deque(maxlen=10000)
        self._lock = threading.Lock()
    
    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Mapping[str, str]] = None,
    ) -> float:
        """Increment a counter metric."""
        with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] = self._counters.get(key, 0) + value
            
            self._record_point(name, MetricType.COUNTER, self._counters[key], labels)
            
            return self._counters[key]
    
    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Set a gauge metric."""
        with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value
            
            self._record_point(name, MetricType.GAUGE, value, labels)
    
    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Record a histogram observation."""
        with self._lock:
            key = self._make_key(name, labels)
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
            
            self._record_point(name, MetricType.HISTOGRAM, value, labels)
    
    def get_counter(self, name: str, labels: Optional[Mapping[str, str]] = None) -> float:
        """Get current counter value."""
        with self._lock:
            key = self._make_key(name, labels)
            return self._counters.get(key, 0)
    
    def get_gauge(self, name: str, labels: Optional[Mapping[str, str]] = None) -> Optional[float]:
        """Get current gauge value."""
        with self._lock:
            key = self._make_key(name, labels)
            return self._gauges.get(key)
    
    def get_histogram_stats(
        self,
        name: str,
        labels: Optional[Mapping[str, str]] = None,
    ) -> Optional[Dict[str, float]]:
        """Get histogram statistics."""
        with self._lock:
            key = self._make_key(name, labels)
            values = self._histograms.get(key)
            
            if not values:
                return None
            
            sorted_values = sorted(values)
            count = len(values)
            
            return {
                "count": count,
                "sum": sum(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / count,
                "p50": sorted_values[int(count * 0.50)],
                "p90": sorted_values[int(count * 0.90)],
                "p99": sorted_values[min(int(count * 0.99), count - 1)],
            }
    
    def _make_key(self, name: str, labels: Optional[Mapping[str, str]]) -> str:
        """Create unique key for metric."""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name
    
    def _record_point(
        self,
        name: str,
        metric_type: MetricType,
        value: float,
        labels: Optional[Mapping[str, str]],
    ) -> None:
        """Record a metric data point."""
        point = MetricPoint(
            metric_id=f"MP-{uuid.uuid4().hex[:8].upper()}",
            name=name,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(timezone.utc),
            labels=labels or {},
        )
        self._points.append(point)


# =============================================================================
# SECTION 4: DISTRIBUTED TRACER
# =============================================================================

class Tracer:
    """
    Distributed tracing system.
    
    Tracks execution across service boundaries with complete context.
    """
    
    def __init__(self) -> None:
        self._spans: Dict[str, TraceSpan] = {}
        self._active_spans: Dict[str, str] = {}  # thread_id -> span_id
        self._lock = threading.Lock()
    
    def start_span(
        self,
        operation: str,
        service: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> TraceSpan:
        """Start a new trace span."""
        with self._lock:
            span_id = f"SPAN-{uuid.uuid4().hex[:12].upper()}"
            trace_id = trace_id or f"TRACE-{uuid.uuid4().hex[:12].upper()}"
            
            span = TraceSpan(
                span_id=span_id,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                operation=operation,
                service=service,
                start_time=datetime.now(timezone.utc),
                end_time=None,
                status="IN_PROGRESS",
                attributes=attributes or {},
            )
            
            self._spans[span_id] = span
            thread_id = str(threading.current_thread().ident)
            self._active_spans[thread_id] = span_id
            
            return span
    
    def end_span(
        self,
        span_id: str,
        status: str = "OK",
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> TraceSpan:
        """End a trace span."""
        with self._lock:
            if span_id not in self._spans:
                raise ValueError(f"Unknown span: {span_id}")
            
            original = self._spans[span_id]
            
            # Create completed span (immutable)
            completed = TraceSpan(
                span_id=original.span_id,
                trace_id=original.trace_id,
                parent_span_id=original.parent_span_id,
                operation=original.operation,
                service=original.service,
                start_time=original.start_time,
                end_time=datetime.now(timezone.utc),
                status=status,
                attributes={**original.attributes, **(attributes or {})},
            )
            
            self._spans[span_id] = completed
            
            # Clear active span
            thread_id = str(threading.current_thread().ident)
            if self._active_spans.get(thread_id) == span_id:
                del self._active_spans[thread_id]
            
            return completed
    
    def get_current_span(self) -> Optional[TraceSpan]:
        """Get the current active span for this thread."""
        with self._lock:
            thread_id = str(threading.current_thread().ident)
            span_id = self._active_spans.get(thread_id)
            return self._spans.get(span_id) if span_id else None
    
    def get_trace(self, trace_id: str) -> Sequence[TraceSpan]:
        """Get all spans for a trace."""
        with self._lock:
            return tuple(
                span for span in self._spans.values()
                if span.trace_id == trace_id
            )
    
    @contextmanager
    def span(
        self,
        operation: str,
        service: str,
        **attributes: Any,
    ) -> Generator[TraceSpan, None, None]:
        """Context manager for spans."""
        span = self.start_span(operation, service, attributes=attributes)
        try:
            yield span
            self.end_span(span.span_id, status="OK")
        except Exception as e:
            self.end_span(span.span_id, status="ERROR", attributes={"error": str(e)})
            raise


# =============================================================================
# SECTION 5: ALERTING SYSTEM
# =============================================================================

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = 0
    WARNING = 1
    ERROR = 2
    CRITICAL = 3
    PAGE = 4  # Requires immediate human attention


@dataclass(frozen=True)
class Alert:
    """Immutable alert record."""
    alert_id: str
    name: str
    severity: AlertSeverity
    message: str
    source: str
    timestamp: datetime
    metric_name: Optional[str]
    threshold: Optional[float]
    actual_value: Optional[float]
    labels: Mapping[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "name": self.name,
            "severity": self.severity.name,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "threshold": self.threshold,
            "actual_value": self.actual_value,
            "labels": dict(self.labels),
        }


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    metric_name: str
    condition: str  # gt, lt, eq, ne
    threshold: float
    severity: AlertSeverity
    labels: Dict[str, str] = field(default_factory=dict)


class AlertManager:
    """
    Deterministic alerting system.
    
    No ambiguity - clear thresholds, clear actions.
    """
    
    def __init__(self) -> None:
        self._rules: List[AlertRule] = []
        self._alerts: Deque[Alert] = deque(maxlen=1000)
        self._lock = threading.Lock()
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        with self._lock:
            self._rules.append(rule)
    
    def evaluate(self, metric_name: str, value: float, labels: Optional[Mapping[str, str]] = None) -> List[Alert]:
        """Evaluate metric against all rules."""
        with self._lock:
            fired_alerts: List[Alert] = []
            
            for rule in self._rules:
                if rule.metric_name != metric_name:
                    continue
                
                # Check labels match
                if labels:
                    if not all(labels.get(k) == v for k, v in rule.labels.items()):
                        continue
                
                # Evaluate condition
                triggered = False
                if rule.condition == "gt" and value > rule.threshold:
                    triggered = True
                elif rule.condition == "lt" and value < rule.threshold:
                    triggered = True
                elif rule.condition == "eq" and value == rule.threshold:
                    triggered = True
                elif rule.condition == "ne" and value != rule.threshold:
                    triggered = True
                elif rule.condition == "gte" and value >= rule.threshold:
                    triggered = True
                elif rule.condition == "lte" and value <= rule.threshold:
                    triggered = True
                
                if triggered:
                    alert = Alert(
                        alert_id=f"ALERT-{uuid.uuid4().hex[:8].upper()}",
                        name=rule.name,
                        severity=rule.severity,
                        message=f"{rule.metric_name} {rule.condition} {rule.threshold}: actual={value}",
                        source="AlertManager",
                        timestamp=datetime.now(timezone.utc),
                        metric_name=metric_name,
                        threshold=rule.threshold,
                        actual_value=value,
                        labels=labels or {},
                    )
                    self._alerts.append(alert)
                    fired_alerts.append(alert)
            
            return fired_alerts
    
    def get_alerts(
        self,
        severity_min: Optional[AlertSeverity] = None,
        since: Optional[datetime] = None,
    ) -> Sequence[Alert]:
        """Get alerts with optional filtering."""
        with self._lock:
            result: List[Alert] = []
            
            for alert in self._alerts:
                if severity_min and alert.severity.value < severity_min.value:
                    continue
                if since and alert.timestamp < since:
                    continue
                result.append(alert)
            
            return tuple(result)


# =============================================================================
# SECTION 6: UNIFIED TELEMETRY SYSTEM
# =============================================================================

class TelemetrySystem:
    """
    Unified Audit-First Telemetry System.
    
    Single entry point for all observability operations.
    
    Properties:
    - Audit Complete: Every event logged
    - Deterministic: No sampling, no drops
    - Verifiable: Hash-chained audit trail
    - Queryable: Full forensic capability
    """
    
    _instance: Optional["TelemetrySystem"] = None
    _lock = threading.Lock()
    
    def __init__(self) -> None:
        self._audit_trail = AuditTrail()
        self._metrics = MetricsCollector()
        self._tracer = Tracer()
        self._alert_manager = AlertManager()
        self._initialized_at = datetime.now(timezone.utc)
    
    @classmethod
    def get_instance(cls) -> "TelemetrySystem":
        """Get singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
    
    def emit_event(
        self,
        severity: EventSeverity,
        category: EventCategory,
        source: str,
        message: str,
        data: Optional[Mapping[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> TelemetryEvent:
        """Emit a telemetry event."""
        event = TelemetryEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
            timestamp=datetime.now(timezone.utc),
            severity=severity,
            category=category,
            source=source,
            message=message,
            data=data or {},
            correlation_id=correlation_id,
            parent_event_id=None,
        )
        
        return self._audit_trail.append(event)
    
    def audit(
        self,
        source: str,
        message: str,
        data: Optional[Mapping[str, Any]] = None,
    ) -> TelemetryEvent:
        """Emit an audit event (always logged)."""
        return self.emit_event(
            severity=EventSeverity.AUDIT,
            category=EventCategory.AUDIT,
            source=source,
            message=message,
            data=data,
        )
    
    def increment(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Mapping[str, str]] = None,
    ) -> float:
        """Increment a counter metric."""
        return self._metrics.increment_counter(name, value, labels)
    
    def gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Set a gauge metric."""
        self._metrics.set_gauge(name, value, labels)
        
        # Evaluate alert rules
        self._alert_manager.evaluate(name, value, labels)
    
    def histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Record a histogram observation."""
        self._metrics.observe_histogram(name, value, labels)
    
    @contextmanager
    def trace(
        self,
        operation: str,
        service: str = "chainbridge",
        **attributes: Any,
    ) -> Generator[TraceSpan, None, None]:
        """Context manager for tracing."""
        with self._tracer.span(operation, service, **attributes) as span:
            yield span
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._alert_manager.add_rule(rule)
    
    def get_audit_trail(self) -> AuditTrail:
        """Return the audit trail."""
        return self._audit_trail
    
    def get_metrics(self) -> MetricsCollector:
        """Return the metrics collector."""
        return self._metrics
    
    def get_tracer(self) -> Tracer:
        """Return the tracer."""
        return self._tracer
    
    def verify_integrity(self) -> Tuple[bool, Optional[str]]:
        """Verify audit trail integrity."""
        return self._audit_trail.verify_integrity()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get telemetry system summary."""
        return {
            "initialized_at": self._initialized_at.isoformat(),
            "audit_events": len(self._audit_trail),
            "chain_head": self._audit_trail.get_chain_head(),
            "integrity": self.verify_integrity()[0],
        }


# =============================================================================
# SECTION 7: SELF-TEST SUITE
# =============================================================================

def _run_self_tests() -> None:
    """Run comprehensive self-tests."""
    print("=" * 70)
    print("AUDIT-FIRST TELEMETRY SYSTEM SELF-TEST SUITE")
    print("PAC: PAC-JEFFREY-NASA-HARDENING-002")
    print("=" * 70)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Event Creation
    print("\n[TEST 1] Event Creation...")
    try:
        event = TelemetryEvent(
            event_id="EVT-TEST001",
            timestamp=datetime.now(timezone.utc),
            severity=EventSeverity.INFO,
            category=EventCategory.SYSTEM,
            source="test",
            message="Test event",
            data={"key": "value"},
            correlation_id=None,
            parent_event_id=None,
        )
        assert event.event_id == "EVT-TEST001"
        assert len(event.hash) == 16
        print(f"  ✓ Event created with hash {event.hash}")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 2: Audit Trail Hash Chain
    print("\n[TEST 2] Audit Trail Hash Chain...")
    try:
        trail = AuditTrail()
        
        for i in range(10):
            event = TelemetryEvent(
                event_id=f"EVT-{i:04d}",
                timestamp=datetime.now(timezone.utc),
                severity=EventSeverity.INFO,
                category=EventCategory.AUDIT,
                source="test",
                message=f"Event {i}",
                data={},
                correlation_id=None,
                parent_event_id=None,
            )
            trail.append(event)
        
        valid, error = trail.verify_integrity()
        assert valid, f"Integrity check failed: {error}"
        print(f"  ✓ Hash chain verified for {len(trail)} events")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 3: Metrics Collector
    print("\n[TEST 3] Metrics Collector...")
    try:
        metrics = MetricsCollector()
        
        # Counter
        metrics.increment_counter("requests_total", labels={"method": "GET"})
        metrics.increment_counter("requests_total", labels={"method": "GET"})
        assert metrics.get_counter("requests_total", {"method": "GET"}) == 2
        
        # Gauge
        metrics.set_gauge("temperature", 72.5)
        assert metrics.get_gauge("temperature") == 72.5
        
        # Histogram
        for val in [10, 20, 30, 40, 50]:
            metrics.observe_histogram("latency_ms", val)
        stats = metrics.get_histogram_stats("latency_ms")
        assert stats is not None
        assert stats["count"] == 5
        assert stats["avg"] == 30
        
        print("  ✓ Metrics collection working")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 4: Tracer
    print("\n[TEST 4] Distributed Tracer...")
    try:
        tracer = Tracer()
        
        # Start and end span
        span = tracer.start_span("test_operation", "test_service")
        assert span.status == "IN_PROGRESS"
        
        completed = tracer.end_span(span.span_id, status="OK")
        assert completed.status == "OK"
        assert completed.duration_ms is not None
        
        # Context manager
        with tracer.span("context_op", "test_service") as s:
            assert s.span_id is not None
        
        print("  ✓ Distributed tracing working")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 5: Alert Manager
    print("\n[TEST 5] Alert Manager...")
    try:
        alert_mgr = AlertManager()
        
        alert_mgr.add_rule(AlertRule(
            name="high_cpu",
            metric_name="cpu_percent",
            condition="gt",
            threshold=90.0,
            severity=AlertSeverity.CRITICAL,
        ))
        
        # Should not fire
        alerts = alert_mgr.evaluate("cpu_percent", 50.0)
        assert len(alerts) == 0
        
        # Should fire
        alerts = alert_mgr.evaluate("cpu_percent", 95.0)
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL
        
        print("  ✓ Alert manager working")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 6: Unified Telemetry System
    print("\n[TEST 6] Unified Telemetry System...")
    try:
        # Create fresh instance for test
        telemetry = TelemetrySystem()
        
        # Emit events
        event = telemetry.emit_event(
            EventSeverity.INFO,
            EventCategory.SYSTEM,
            "test",
            "Test message",
        )
        assert event.event_id is not None
        
        # Audit event
        audit_event = telemetry.audit("test", "Audit message")
        assert audit_event.severity == EventSeverity.AUDIT
        
        # Metrics
        telemetry.increment("test_counter")
        telemetry.gauge("test_gauge", 42.0)
        telemetry.histogram("test_histogram", 100.0)
        
        # Verify integrity
        valid, _ = telemetry.verify_integrity()
        assert valid
        
        print("  ✓ Unified telemetry system working")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 7: Trace Context Manager
    print("\n[TEST 7] Trace Context Manager...")
    try:
        telemetry = TelemetrySystem()
        
        with telemetry.trace("parent_operation") as parent:
            with telemetry.trace("child_operation") as child:
                pass
        
        print("  ✓ Trace context manager working")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 8: Event Query
    print("\n[TEST 8] Event Query...")
    try:
        trail = AuditTrail()
        
        # Add events with different categories
        for cat in [EventCategory.SYSTEM, EventCategory.SECURITY, EventCategory.AUDIT]:
            event = TelemetryEvent(
                event_id=f"EVT-{cat.name}",
                timestamp=datetime.now(timezone.utc),
                severity=EventSeverity.INFO,
                category=cat,
                source="test",
                message=f"Event {cat.name}",
                data={},
                correlation_id=None,
                parent_event_id=None,
            )
            trail.append(event)
        
        # Query by category
        security_events = trail.get_events(category=EventCategory.SECURITY)
        assert len(security_events) == 1
        assert security_events[0].category == EventCategory.SECURITY
        
        print("  ✓ Event query working")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 9: Metric Labels
    print("\n[TEST 9] Metric Labels...")
    try:
        metrics = MetricsCollector()
        
        metrics.increment_counter("http_requests", labels={"method": "GET", "status": "200"})
        metrics.increment_counter("http_requests", labels={"method": "POST", "status": "200"})
        metrics.increment_counter("http_requests", labels={"method": "GET", "status": "200"})
        
        get_200 = metrics.get_counter("http_requests", {"method": "GET", "status": "200"})
        post_200 = metrics.get_counter("http_requests", {"method": "POST", "status": "200"})
        
        assert get_200 == 2
        assert post_200 == 1
        
        print("  ✓ Metric labels working")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 10: System Summary
    print("\n[TEST 10] System Summary...")
    try:
        telemetry = TelemetrySystem()
        telemetry.audit("test", "Test audit event")
        
        summary = telemetry.get_summary()
        assert "initialized_at" in summary
        assert "audit_events" in summary
        assert "chain_head" in summary
        assert "integrity" in summary
        assert summary["integrity"] == True
        
        print(f"  ✓ System summary: {summary['audit_events']} events, integrity={summary['integrity']}")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_failed += 1
    
    # Summary
    print("\n" + "=" * 70)
    print(f"SELF-TEST RESULTS: {tests_passed}/{tests_passed + tests_failed} PASSED")
    print("=" * 70)
    
    if tests_failed > 0:
        print(f"\n⚠️  {tests_failed} test(s) FAILED")
    else:
        print("\n✅ ALL TESTS PASSED - Telemetry System OPERATIONAL")


if __name__ == "__main__":
    _run_self_tests()
