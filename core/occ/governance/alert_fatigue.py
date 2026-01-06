"""
Alert Fatigue Detection — Approval Velocity & Cultural Drift Monitoring

PAC: PAC-OCC-P07
Lane: EX6 — Alert Fatigue Detection
Agent: Maggie (GID-10)

Addresses existential failure EX6: "Alert Fatigue"
BER-P05 finding: No cultural drift detection, approval velocity unmonitored

MECHANICAL ENFORCEMENT:
- Track approval velocity (approvals per hour/day)
- Detect anomalous approval patterns (rubber-stamping)
- Monitor rejection rates and justification quality
- Alert on cultural drift indicators

INVARIANTS:
- INV-FATIGUE-001: Approval velocity ABOVE threshold triggers review
- INV-FATIGUE-002: Rejection rate BELOW threshold triggers alert
- INV-FATIGUE-003: Justification quality degradation is flagged
- INV-FATIGUE-004: All cultural drift metrics are logged
"""

from __future__ import annotations

import json
import logging
import math
import os
import statistics
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Velocity thresholds
MAX_APPROVALS_PER_HOUR = int(os.environ.get("CHAINBRIDGE_MAX_APPROVALS_PER_HOUR", "20"))
MAX_APPROVALS_PER_DAY = int(os.environ.get("CHAINBRIDGE_MAX_APPROVALS_PER_DAY", "100"))

# Quality thresholds
MIN_REJECTION_RATE = float(os.environ.get("CHAINBRIDGE_MIN_REJECTION_RATE", "0.05"))  # 5%
MIN_JUSTIFICATION_LENGTH = int(os.environ.get("CHAINBRIDGE_MIN_JUSTIFICATION_LENGTH", "20"))
MIN_REVIEW_DURATION_SECONDS = int(os.environ.get("CHAINBRIDGE_MIN_REVIEW_DURATION", "30"))

# Window sizes
HOURLY_WINDOW_HOURS = 1
DAILY_WINDOW_HOURS = 24
DRIFT_ANALYSIS_DAYS = 7

# Paths
DEFAULT_METRICS_PATH = "./data/alert_fatigue_metrics.json"


class DriftIndicator(str, Enum):
    """Types of cultural drift indicators."""
    
    HIGH_VELOCITY = "high_velocity"          # Too many approvals
    LOW_REJECTION = "low_rejection"          # Not rejecting enough
    SHORT_REVIEWS = "short_reviews"          # Reviews too fast
    WEAK_JUSTIFICATIONS = "weak_justifications"  # Poor justification quality
    PATTERN_REPETITION = "pattern_repetition"    # Same justifications repeated
    TIME_CLUSTERING = "time_clustering"      # Approvals clustered in time
    OPERATOR_BIAS = "operator_bias"          # Single operator dominance


class AlertSeverity(str, Enum):
    """Severity levels for drift alerts."""
    
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ApprovalEvent:
    """Record of an approval/rejection event."""
    
    event_id: str
    timestamp: str
    operator_id: str
    action: str  # "approve" or "reject"
    target_type: str  # What was approved/rejected
    target_id: str
    justification: str
    review_duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "operator_id": self.operator_id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "justification": self.justification,
            "review_duration_seconds": self.review_duration_seconds,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalEvent":
        """Create from dictionary."""
        return cls(
            event_id=data["event_id"],
            timestamp=data["timestamp"],
            operator_id=data["operator_id"],
            action=data["action"],
            target_type=data["target_type"],
            target_id=data["target_id"],
            justification=data["justification"],
            review_duration_seconds=data.get("review_duration_seconds"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DriftAlert:
    """Alert for detected cultural drift."""
    
    alert_id: str
    timestamp: str
    indicator: DriftIndicator
    severity: AlertSeverity
    message: str
    
    # Context
    operator_id: Optional[str] = None
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None
    window_hours: Optional[int] = None
    
    # Evidence
    evidence: List[str] = field(default_factory=list)
    recommended_action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp,
            "indicator": self.indicator.value,
            "severity": self.severity.value,
            "message": self.message,
            "operator_id": self.operator_id,
            "metric_value": self.metric_value,
            "threshold_value": self.threshold_value,
            "window_hours": self.window_hours,
            "evidence": self.evidence,
            "recommended_action": self.recommended_action,
        }


@dataclass
class VelocityMetrics:
    """Approval velocity metrics."""
    
    timestamp: str
    window_hours: int
    
    # Counts
    total_approvals: int
    total_rejections: int
    total_events: int
    
    # Rates
    approval_rate: float  # approvals / total
    rejection_rate: float  # rejections / total
    velocity_per_hour: float  # events / hour
    
    # Quality indicators
    avg_review_duration: Optional[float] = None
    avg_justification_length: float = 0
    unique_justifications_ratio: float = 0  # unique / total
    
    # Per-operator breakdown
    by_operator: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class CulturalDriftReport:
    """Comprehensive cultural drift analysis report."""
    
    report_id: str
    generated_at: str
    analysis_window_days: int
    
    # Overall metrics
    total_events: int
    avg_daily_approvals: float
    avg_daily_rejections: float
    overall_rejection_rate: float
    
    # Drift indicators detected
    indicators_detected: List[DriftIndicator]
    alerts: List[DriftAlert]
    
    # Trend analysis
    velocity_trend: str  # "increasing", "stable", "decreasing"
    rejection_trend: str
    quality_trend: str
    
    # Recommendations
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "analysis_window_days": self.analysis_window_days,
            "total_events": self.total_events,
            "avg_daily_approvals": self.avg_daily_approvals,
            "avg_daily_rejections": self.avg_daily_rejections,
            "overall_rejection_rate": self.overall_rejection_rate,
            "indicators_detected": [i.value for i in self.indicators_detected],
            "alerts": [a.to_dict() for a in self.alerts],
            "velocity_trend": self.velocity_trend,
            "rejection_trend": self.rejection_trend,
            "quality_trend": self.quality_trend,
            "recommendations": self.recommendations,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ALERT FATIGUE DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════


class AlertFatigueDetector:
    """
    Monitors approval patterns for cultural drift indicators.
    
    INVARIANT ENFORCEMENT:
    - INV-FATIGUE-001: Alert on high velocity
    - INV-FATIGUE-002: Alert on low rejection rate
    - INV-FATIGUE-003: Flag justification quality issues
    - INV-FATIGUE-004: Log all drift metrics
    """
    
    def __init__(self, metrics_path: Optional[str] = None):
        """Initialize the alert fatigue detector."""
        self._lock = threading.Lock()
        
        self._metrics_path = Path(metrics_path or DEFAULT_METRICS_PATH)
        self._metrics_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Event storage
        self._events: List[ApprovalEvent] = []
        self._alerts: List[DriftAlert] = []
        
        # Alert callbacks
        self._alert_callbacks: List[Callable[[DriftAlert], None]] = []
        
        # Justification cache for pattern detection
        self._justification_hashes: Dict[str, int] = defaultdict(int)
        
        # Load existing data
        self._load()
        
        logger.info("AlertFatigueDetector initialized")
    
    def _load(self) -> None:
        """Load existing metrics."""
        if not self._metrics_path.exists():
            return
        
        try:
            data = json.loads(self._metrics_path.read_text(encoding="utf-8"))
            self._events = [ApprovalEvent.from_dict(e) for e in data.get("events", [])]
            # Keep last 30 days of events
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            self._events = [
                e for e in self._events
                if datetime.fromisoformat(e.timestamp.replace("Z", "+00:00")) > cutoff
            ]
            logger.info(f"Loaded {len(self._events)} approval events")
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
    
    def _save(self) -> None:
        """Save metrics to file."""
        data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "events": [e.to_dict() for e in self._events[-10000:]],  # Keep last 10000
            "alerts": [a.to_dict() for a in self._alerts[-1000:]],  # Keep last 1000
        }
        
        tmp_path = self._metrics_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(self._metrics_path)
    
    def _trigger_alert(self, alert: DriftAlert) -> None:
        """Trigger alert callbacks."""
        self._alerts.append(alert)
        
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.CRITICAL: logging.CRITICAL,
        }.get(alert.severity, logging.WARNING)
        
        logger.log(
            log_level,
            f"CULTURAL_DRIFT_ALERT [{alert.severity.value}]: {alert.indicator.value} — {alert.message}"
        )
        
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def _get_events_in_window(
        self,
        window_hours: int,
        operator_id: Optional[str] = None
    ) -> List[ApprovalEvent]:
        """Get events within a time window."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        
        events = []
        for event in self._events:
            event_time = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
            if event_time > cutoff:
                if operator_id is None or event.operator_id == operator_id:
                    events.append(event)
        
        return events
    
    def _compute_justification_hash(self, justification: str) -> str:
        """Compute a normalized hash of justification for pattern detection."""
        # Normalize: lowercase, strip, collapse whitespace
        normalized = " ".join(justification.lower().split())
        return str(hash(normalized))
    
    def register_alert_callback(self, callback: Callable[[DriftAlert], None]) -> None:
        """Register callback for drift alerts."""
        self._alert_callbacks.append(callback)
    
    def record_event(
        self,
        operator_id: str,
        action: str,
        target_type: str,
        target_id: str,
        justification: str,
        review_duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ApprovalEvent, List[DriftAlert]]:
        """
        Record an approval/rejection event and check for drift.
        
        Args:
            operator_id: Operator performing the action
            action: "approve" or "reject"
            target_type: What was approved/rejected
            target_id: ID of the target
            justification: Operator's justification
            review_duration_seconds: Time spent reviewing
            metadata: Additional context
            
        Returns:
            (event, list of any triggered alerts)
        """
        with self._lock:
            event = ApprovalEvent(
                event_id=str(uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                operator_id=operator_id,
                action=action.lower(),
                target_type=target_type,
                target_id=target_id,
                justification=justification,
                review_duration_seconds=review_duration_seconds,
                metadata=metadata or {},
            )
            
            self._events.append(event)
            
            # Track justification patterns
            j_hash = self._compute_justification_hash(justification)
            self._justification_hashes[j_hash] += 1
            
            # Check for drift indicators
            alerts = self._check_drift_indicators(event)
            
            self._save()
            
            return event, alerts
    
    def _check_drift_indicators(self, new_event: ApprovalEvent) -> List[DriftAlert]:
        """Check for cultural drift indicators after new event."""
        alerts = []
        
        # Only check if we have enough data
        if len(self._events) < 10:
            return alerts
        
        # Get recent windows
        hourly_events = self._get_events_in_window(HOURLY_WINDOW_HOURS)
        daily_events = self._get_events_in_window(DAILY_WINDOW_HOURS)
        operator_hourly = self._get_events_in_window(HOURLY_WINDOW_HOURS, new_event.operator_id)
        
        # INV-FATIGUE-001: Check velocity
        if len(hourly_events) > MAX_APPROVALS_PER_HOUR:
            alert = DriftAlert(
                alert_id=str(uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                indicator=DriftIndicator.HIGH_VELOCITY,
                severity=AlertSeverity.WARNING,
                message=f"Approval velocity exceeds threshold: {len(hourly_events)}/hour (max: {MAX_APPROVALS_PER_HOUR})",
                metric_value=len(hourly_events),
                threshold_value=MAX_APPROVALS_PER_HOUR,
                window_hours=1,
                recommended_action="Review recent approvals for rubber-stamping",
            )
            self._trigger_alert(alert)
            alerts.append(alert)
        
        if len(daily_events) > MAX_APPROVALS_PER_DAY:
            alert = DriftAlert(
                alert_id=str(uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                indicator=DriftIndicator.HIGH_VELOCITY,
                severity=AlertSeverity.CRITICAL,
                message=f"Daily approval velocity critical: {len(daily_events)}/day (max: {MAX_APPROVALS_PER_DAY})",
                metric_value=len(daily_events),
                threshold_value=MAX_APPROVALS_PER_DAY,
                window_hours=24,
                recommended_action="Mandatory review of approval process",
            )
            self._trigger_alert(alert)
            alerts.append(alert)
        
        # INV-FATIGUE-002: Check rejection rate
        if len(daily_events) >= 20:  # Need enough data
            approvals = sum(1 for e in daily_events if e.action == "approve")
            rejections = sum(1 for e in daily_events if e.action == "reject")
            total = approvals + rejections
            
            if total > 0:
                rejection_rate = rejections / total
                if rejection_rate < MIN_REJECTION_RATE:
                    alert = DriftAlert(
                        alert_id=str(uuid4()),
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        indicator=DriftIndicator.LOW_REJECTION,
                        severity=AlertSeverity.WARNING,
                        message=f"Rejection rate too low: {rejection_rate:.1%} (min: {MIN_REJECTION_RATE:.1%})",
                        metric_value=rejection_rate,
                        threshold_value=MIN_REJECTION_RATE,
                        window_hours=24,
                        evidence=[
                            f"Approvals: {approvals}",
                            f"Rejections: {rejections}",
                            f"Total: {total}",
                        ],
                        recommended_action="Review approval criteria and ensure proper scrutiny",
                    )
                    self._trigger_alert(alert)
                    alerts.append(alert)
        
        # INV-FATIGUE-003: Check review duration
        if new_event.review_duration_seconds is not None:
            if new_event.review_duration_seconds < MIN_REVIEW_DURATION_SECONDS:
                alert = DriftAlert(
                    alert_id=str(uuid4()),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    indicator=DriftIndicator.SHORT_REVIEWS,
                    severity=AlertSeverity.INFO,
                    message=f"Review completed too quickly: {new_event.review_duration_seconds:.1f}s (min: {MIN_REVIEW_DURATION_SECONDS}s)",
                    operator_id=new_event.operator_id,
                    metric_value=new_event.review_duration_seconds,
                    threshold_value=MIN_REVIEW_DURATION_SECONDS,
                    recommended_action="Ensure thorough review before approval",
                )
                self._trigger_alert(alert)
                alerts.append(alert)
        
        # Check justification quality
        if len(new_event.justification) < MIN_JUSTIFICATION_LENGTH:
            alert = DriftAlert(
                alert_id=str(uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                indicator=DriftIndicator.WEAK_JUSTIFICATIONS,
                severity=AlertSeverity.INFO,
                message=f"Justification too short: {len(new_event.justification)} chars (min: {MIN_JUSTIFICATION_LENGTH})",
                operator_id=new_event.operator_id,
                metric_value=len(new_event.justification),
                threshold_value=MIN_JUSTIFICATION_LENGTH,
                recommended_action="Provide detailed justification for audit trail",
            )
            self._trigger_alert(alert)
            alerts.append(alert)
        
        # Check pattern repetition
        j_hash = self._compute_justification_hash(new_event.justification)
        if self._justification_hashes[j_hash] > 5:  # Same justification used 5+ times
            alert = DriftAlert(
                alert_id=str(uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                indicator=DriftIndicator.PATTERN_REPETITION,
                severity=AlertSeverity.WARNING,
                message=f"Repeated justification pattern detected ({self._justification_hashes[j_hash]} times)",
                operator_id=new_event.operator_id,
                evidence=[f"Justification: '{new_event.justification[:50]}...'"],
                recommended_action="Vary justifications to demonstrate individual review",
            )
            self._trigger_alert(alert)
            alerts.append(alert)
        
        # Check operator bias
        if len(hourly_events) >= 5:
            operator_counts = defaultdict(int)
            for e in hourly_events:
                operator_counts[e.operator_id] += 1
            
            max_operator = max(operator_counts.items(), key=lambda x: x[1])
            if max_operator[1] / len(hourly_events) > 0.8:  # One operator > 80%
                alert = DriftAlert(
                    alert_id=str(uuid4()),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    indicator=DriftIndicator.OPERATOR_BIAS,
                    severity=AlertSeverity.WARNING,
                    message=f"Single operator dominance: {max_operator[0]} has {max_operator[1]}/{len(hourly_events)} recent approvals",
                    operator_id=max_operator[0],
                    metric_value=max_operator[1] / len(hourly_events),
                    threshold_value=0.8,
                    recommended_action="Distribute approval load across multiple operators",
                )
                self._trigger_alert(alert)
                alerts.append(alert)
        
        return alerts
    
    def compute_velocity_metrics(self, window_hours: int = 24) -> VelocityMetrics:
        """Compute velocity metrics for a time window."""
        with self._lock:
            events = self._get_events_in_window(window_hours)
            
            approvals = [e for e in events if e.action == "approve"]
            rejections = [e for e in events if e.action == "reject"]
            
            total = len(events)
            approval_rate = len(approvals) / total if total > 0 else 0
            rejection_rate = len(rejections) / total if total > 0 else 0
            velocity = total / window_hours if window_hours > 0 else 0
            
            # Review duration stats
            durations = [e.review_duration_seconds for e in events if e.review_duration_seconds is not None]
            avg_duration = statistics.mean(durations) if durations else None
            
            # Justification stats
            justifications = [e.justification for e in events]
            avg_justification_len = statistics.mean([len(j) for j in justifications]) if justifications else 0
            unique_justifications = len(set(justifications))
            unique_ratio = unique_justifications / len(justifications) if justifications else 0
            
            # Per-operator breakdown
            by_operator: Dict[str, Dict[str, Any]] = {}
            operator_events = defaultdict(list)
            for e in events:
                operator_events[e.operator_id].append(e)
            
            for op_id, op_events in operator_events.items():
                op_approvals = sum(1 for e in op_events if e.action == "approve")
                op_rejections = sum(1 for e in op_events if e.action == "reject")
                by_operator[op_id] = {
                    "total": len(op_events),
                    "approvals": op_approvals,
                    "rejections": op_rejections,
                    "rejection_rate": op_rejections / len(op_events) if op_events else 0,
                }
            
            return VelocityMetrics(
                timestamp=datetime.now(timezone.utc).isoformat(),
                window_hours=window_hours,
                total_approvals=len(approvals),
                total_rejections=len(rejections),
                total_events=total,
                approval_rate=approval_rate,
                rejection_rate=rejection_rate,
                velocity_per_hour=velocity,
                avg_review_duration=avg_duration,
                avg_justification_length=avg_justification_len,
                unique_justifications_ratio=unique_ratio,
                by_operator=by_operator,
            )
    
    def generate_drift_report(self, analysis_days: int = 7) -> CulturalDriftReport:
        """Generate comprehensive cultural drift analysis report."""
        with self._lock:
            events = self._get_events_in_window(analysis_days * 24)
            
            if not events:
                return CulturalDriftReport(
                    report_id=str(uuid4()),
                    generated_at=datetime.now(timezone.utc).isoformat(),
                    analysis_window_days=analysis_days,
                    total_events=0,
                    avg_daily_approvals=0,
                    avg_daily_rejections=0,
                    overall_rejection_rate=0,
                    indicators_detected=[],
                    alerts=[],
                    velocity_trend="insufficient_data",
                    rejection_trend="insufficient_data",
                    quality_trend="insufficient_data",
                    recommendations=["Insufficient data for analysis"],
                )
            
            # Compute overall metrics
            approvals = [e for e in events if e.action == "approve"]
            rejections = [e for e in events if e.action == "reject"]
            
            total = len(events)
            rejection_rate = len(rejections) / total if total > 0 else 0
            
            # Group by day for trend analysis
            daily_approvals = defaultdict(int)
            daily_rejections = defaultdict(int)
            
            for event in events:
                day = event.timestamp[:10]  # YYYY-MM-DD
                if event.action == "approve":
                    daily_approvals[day] += 1
                else:
                    daily_rejections[day] += 1
            
            # Compute averages
            days_with_data = len(set(daily_approvals.keys()) | set(daily_rejections.keys()))
            avg_daily_approvals = len(approvals) / days_with_data if days_with_data > 0 else 0
            avg_daily_rejections = len(rejections) / days_with_data if days_with_data > 0 else 0
            
            # Trend analysis
            def compute_trend(daily_values: Dict[str, int]) -> str:
                if len(daily_values) < 3:
                    return "insufficient_data"
                
                sorted_days = sorted(daily_values.keys())
                values = [daily_values[d] for d in sorted_days]
                
                # Simple linear regression slope
                n = len(values)
                x_mean = (n - 1) / 2
                y_mean = sum(values) / n
                
                numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
                denominator = sum((i - x_mean) ** 2 for i in range(n))
                
                if denominator == 0:
                    return "stable"
                
                slope = numerator / denominator
                
                if slope > 0.5:
                    return "increasing"
                elif slope < -0.5:
                    return "decreasing"
                else:
                    return "stable"
            
            velocity_trend = compute_trend(daily_approvals)
            rejection_trend = compute_trend(daily_rejections)
            
            # Quality trend (based on justification length)
            daily_justification_lengths: Dict[str, List[int]] = defaultdict(list)
            for event in events:
                day = event.timestamp[:10]
                daily_justification_lengths[day].append(len(event.justification))
            
            daily_avg_lengths = {
                day: statistics.mean(lengths) for day, lengths in daily_justification_lengths.items()
            }
            quality_trend = compute_trend({k: int(v) for k, v in daily_avg_lengths.items()})
            
            # Collect indicators and generate recommendations
            indicators_detected = []
            recommendations = []
            
            if rejection_rate < MIN_REJECTION_RATE:
                indicators_detected.append(DriftIndicator.LOW_REJECTION)
                recommendations.append("Increase scrutiny in approval process")
            
            if avg_daily_approvals > MAX_APPROVALS_PER_DAY:
                indicators_detected.append(DriftIndicator.HIGH_VELOCITY)
                recommendations.append("Reduce approval velocity or add more reviewers")
            
            if velocity_trend == "increasing":
                recommendations.append("Monitor increasing approval velocity trend")
            
            if quality_trend == "decreasing":
                indicators_detected.append(DriftIndicator.WEAK_JUSTIFICATIONS)
                recommendations.append("Address declining justification quality")
            
            # Get recent alerts
            recent_alerts = [
                a for a in self._alerts[-100:]
                if datetime.fromisoformat(a.timestamp.replace("Z", "+00:00")) >
                   datetime.now(timezone.utc) - timedelta(days=analysis_days)
            ]
            
            return CulturalDriftReport(
                report_id=str(uuid4()),
                generated_at=datetime.now(timezone.utc).isoformat(),
                analysis_window_days=analysis_days,
                total_events=total,
                avg_daily_approvals=round(avg_daily_approvals, 2),
                avg_daily_rejections=round(avg_daily_rejections, 2),
                overall_rejection_rate=round(rejection_rate, 3),
                indicators_detected=indicators_detected,
                alerts=recent_alerts,
                velocity_trend=velocity_trend,
                rejection_trend=rejection_trend,
                quality_trend=quality_trend,
                recommendations=recommendations or ["No immediate action required"],
            )
    
    def get_alerts(self, limit: int = 100) -> List[DriftAlert]:
        """Get recent drift alerts."""
        with self._lock:
            return self._alerts[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        with self._lock:
            hourly = self.compute_velocity_metrics(1)
            daily = self.compute_velocity_metrics(24)
            
            return {
                "total_events_tracked": len(self._events),
                "total_alerts": len(self._alerts),
                "hourly_velocity": hourly.velocity_per_hour,
                "daily_velocity": daily.velocity_per_hour * 24,
                "current_rejection_rate": daily.rejection_rate,
                "unique_operators": len(daily.by_operator),
            }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_detector_instance: Optional[AlertFatigueDetector] = None
_detector_lock = threading.Lock()


def get_alert_fatigue_detector() -> AlertFatigueDetector:
    """Get the singleton alert fatigue detector instance."""
    global _detector_instance
    
    if _detector_instance is None:
        with _detector_lock:
            if _detector_instance is None:
                _detector_instance = AlertFatigueDetector()
    
    return _detector_instance
