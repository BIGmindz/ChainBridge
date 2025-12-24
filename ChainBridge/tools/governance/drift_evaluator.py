"""
Drift Evaluator for ChainBridge Governance.

PAC Reference: PAC-ATLAS-P41-GOVERNANCE-REGRESSION-AND-DRIFT-ENFORCEMENT-INTEGRATION-01
Agent: ATLAS (GID-05) | 🔵 BLUE
Authority: BENSON (GID-00)

Purpose:
  - Detect distribution drift vs calibration envelope
  - Identify semantic drift in agent behavior patterns
  - Emit GS_095 on drift detection
  - Enforce FAIL_CLOSED or ESCALATED outcome

Pattern: GOVERNANCE_MUST_NOT_DECAY
"""

import re
import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple
from enum import Enum
from datetime import datetime


class DriftType(Enum):
    """Types of drift detected."""
    NONE = "NONE"
    STATISTICAL = "STATISTICAL"        # Distribution shift
    SEMANTIC = "SEMANTIC"              # Behavioral pattern change
    TEMPORAL = "TEMPORAL"              # Time-based degradation
    SCOPE = "SCOPE"                    # Execution scope creep
    AUTHORITY = "AUTHORITY"            # Authority boundary drift


class DriftSeverity(Enum):
    """Drift severity levels (per GOVERNANCE_AGENT_BASELINES.md)."""
    NONE = "NONE"
    MINOR = "MINOR"           # Below P50 for 3 consecutive PACs → BEHAVIORAL_ADJUSTMENT
    MODERATE = "MODERATE"     # Below P25 for 2 consecutive PACs → agent-specific review
    SEVERE = "SEVERE"         # Below P10 for any PAC → immediate BENSON review


@dataclass
class DriftSignal:
    """A single drift detection signal."""
    drift_type: DriftType
    severity: DriftSeverity
    metric_name: str
    current_value: float
    expected_value: float
    deviation: float
    consecutive_violations: int
    should_block: bool
    should_escalate: bool
    error_code: Optional[str] = None
    message: str = ""


@dataclass
class CalibrationEnvelope:
    """
    Defines acceptable bounds for metric values.
    
    Based on GOVERNANCE_AGENT_BASELINES.md drift detection:
      - MINOR: Below P50 for 3 consecutive PACs
      - MODERATE: Below P25 for 2 consecutive PACs  
      - SEVERE: Below P10 for any PAC
    """
    metric_name: str
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    is_inverted: bool = False  # True if higher values are worse
    
    def is_within_envelope(self, value: float) -> bool:
        """Check if value is within acceptable envelope (P10-P90)."""
        if self.is_inverted:
            return value <= self.p90
        return value >= self.p10
    
    def get_threshold_violation(self, value: float) -> Tuple[str, float]:
        """
        Determine which threshold is violated.
        
        Returns: (threshold_name, deviation_from_threshold)
        """
        if self.is_inverted:
            # Higher is worse (time, violations)
            if value > self.p90:
                return ("P90", value - self.p90)
            if value > self.p75:
                return ("P75", value - self.p75)
            if value > self.p50:
                return ("P50", value - self.p50)
            return ("NONE", 0.0)
        else:
            # Lower is worse (accuracy, compliance)
            if value < self.p10:
                return ("P10", self.p10 - value)
            if value < self.p25:
                return ("P25", self.p25 - value)
            if value < self.p50:
                return ("P50", self.p50 - value)
            return ("NONE", 0.0)


@dataclass
class DriftReport:
    """Complete drift evaluation report."""
    agent_gid: str
    agent_name: str
    execution_lane: str
    evaluation_timestamp: str
    total_signals: int
    drift_signals: List[DriftSignal]
    has_blocking_drift: bool
    has_escalation_required: bool
    execution_time_ms: int = 0
    
    @property
    def summary(self) -> str:
        """Generate summary string."""
        if not self.drift_signals:
            return f"✓ PASS: {self.agent_name} ({self.agent_gid}) — No drift detected"
        
        blocking = [d for d in self.drift_signals if d.should_block]
        if blocking:
            return f"✗ FAIL: {self.agent_name} ({self.agent_gid}) — {len(blocking)} blocking drift signals (GS_095)"
        
        escalate = [d for d in self.drift_signals if d.should_escalate]
        if escalate:
            return f"⚠ ESCALATE: {self.agent_name} ({self.agent_gid}) — {len(escalate)} drift signals require review"
        
        return f"⚠ WARN: {self.agent_name} ({self.agent_gid}) — {len(self.drift_signals)} minor drift signals"


class DriftHistoryTracker:
    """
    Track historical metric values for consecutive violation detection.
    
    Per GOVERNANCE_AGENT_BASELINES.md:
      - MINOR: Below P50 for 3 consecutive PACs
      - MODERATE: Below P25 for 2 consecutive PACs
    """
    
    def __init__(self):
        # Structure: {agent_gid: {metric_name: [recent_values]}}
        self._history: Dict[str, Dict[str, List[float]]] = {}
        self._max_history = 10  # Keep last 10 values per metric
    
    def record(self, agent_gid: str, metric_name: str, value: float) -> None:
        """Record a metric value."""
        if agent_gid not in self._history:
            self._history[agent_gid] = {}
        if metric_name not in self._history[agent_gid]:
            self._history[agent_gid][metric_name] = []
        
        self._history[agent_gid][metric_name].append(value)
        
        # Trim to max history
        if len(self._history[agent_gid][metric_name]) > self._max_history:
            self._history[agent_gid][metric_name] = self._history[agent_gid][metric_name][-self._max_history:]
    
    def get_history(self, agent_gid: str, metric_name: str) -> List[float]:
        """Get historical values for a metric."""
        return self._history.get(agent_gid, {}).get(metric_name, [])
    
    def count_consecutive_violations(
        self,
        agent_gid: str,
        metric_name: str,
        threshold: float,
        is_inverted: bool = False,
    ) -> int:
        """
        Count consecutive violations of a threshold (most recent).
        
        Args:
            agent_gid: Agent identifier
            metric_name: Metric name
            threshold: Threshold value
            is_inverted: If True, values above threshold are violations
            
        Returns:
            Number of consecutive violations from most recent
        """
        history = self.get_history(agent_gid, metric_name)
        if not history:
            return 0
        
        consecutive = 0
        for value in reversed(history):
            if is_inverted:
                if value > threshold:
                    consecutive += 1
                else:
                    break
            else:
                if value < threshold:
                    consecutive += 1
                else:
                    break
        
        return consecutive


class DriftEvaluator:
    """
    Evaluate metrics for drift against calibration envelope.
    
    Enforcement (per GOVERNANCE_AGENT_BASELINES.md):
      - MINOR drift: TRAINING_SIGNAL emitted, non-blocking
      - MODERATE drift: TRAINING_SIGNAL + review, optionally blocking
      - SEVERE drift: FAIL_CLOSED, immediate BENSON review (GS_095)
    """
    
    # Default calibration envelopes (can be overridden per agent)
    DEFAULT_ENVELOPES = {
        # Accuracy metrics (lower is worse)
        "first_pass_validity": CalibrationEnvelope("first_pass_validity", 0.40, 0.55, 0.70, 0.85, 0.95, False),
        "deliverable_completeness": CalibrationEnvelope("deliverable_completeness", 0.90, 0.95, 1.0, 1.0, 1.0, False),
        "test_pass_rate": CalibrationEnvelope("test_pass_rate", 0.80, 0.90, 0.95, 0.98, 1.0, False),
        "gold_standard_compliance": CalibrationEnvelope("gold_standard_compliance", 0.80, 0.90, 0.95, 1.0, 1.0, False),
        
        # Speed metrics (higher is worse)
        "pac_completion_time": CalibrationEnvelope("pac_completion_time", 60, 120, 300, 600, 900, True),
        "iterations_to_valid": CalibrationEnvelope("iterations_to_valid", 1, 1, 2, 3, 5, True),
        "correction_cycles": CalibrationEnvelope("correction_cycles", 0, 1, 2, 4, 6, True),
        
        # Scope metrics (higher is worse, zero-tolerance)
        "lane_violations": CalibrationEnvelope("lane_violations", 0, 0, 0, 0, 0, True),
        "tool_violations": CalibrationEnvelope("tool_violations", 0, 0, 0, 0, 0, True),
        "scope_drift_events": CalibrationEnvelope("scope_drift_events", 0, 0, 0, 1, 2, True),
        "authority_overreach": CalibrationEnvelope("authority_overreach", 0, 0, 0, 0, 0, True),
        
        # Failure quality metrics (lower is worse)
        "failure_explainability": CalibrationEnvelope("failure_explainability", 0.80, 0.90, 1.0, 1.0, 1.0, False),
        "failure_evidence": CalibrationEnvelope("failure_evidence", 0.80, 0.90, 1.0, 1.0, 1.0, False),
        
        # Silent failure rate (higher is worse)
        "silent_failure_rate": CalibrationEnvelope("silent_failure_rate", 0, 0, 0, 0.05, 0.10, True),
    }
    
    def __init__(self, history_tracker: Optional[DriftHistoryTracker] = None):
        """Initialize evaluator with optional history tracker."""
        self.history = history_tracker or DriftHistoryTracker()
        self.envelopes = dict(self.DEFAULT_ENVELOPES)
    
    def add_envelope(self, envelope: CalibrationEnvelope) -> None:
        """Add or override a calibration envelope."""
        self.envelopes[envelope.metric_name] = envelope
    
    def evaluate(
        self,
        agent_gid: str,
        agent_name: str,
        execution_lane: str,
        metrics: Dict[str, float],
        record_history: bool = True,
    ) -> DriftReport:
        """
        Evaluate metrics for drift.
        
        Args:
            agent_gid: Agent GID
            agent_name: Agent name
            execution_lane: Execution lane
            metrics: Dict of metric_name -> current_value
            record_history: Whether to record values for future consecutive tracking
            
        Returns:
            DriftReport with all evaluation results
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        drift_signals = []
        
        for metric_name, value in metrics.items():
            envelope = self.envelopes.get(metric_name)
            if not envelope:
                continue
            
            # Record history first (if enabled)
            if record_history:
                self.history.record(agent_gid, metric_name, value)
            
            # Get consecutive violations
            p50_violations = self.history.count_consecutive_violations(
                agent_gid, metric_name, envelope.p50, envelope.is_inverted
            )
            p25_violations = self.history.count_consecutive_violations(
                agent_gid, metric_name, envelope.p25, envelope.is_inverted
            )
            
            # Evaluate current value
            signal = self._evaluate_metric(
                metric_name=metric_name,
                value=value,
                envelope=envelope,
                p50_consecutive=p50_violations,
                p25_consecutive=p25_violations,
            )
            
            if signal.severity != DriftSeverity.NONE:
                drift_signals.append(signal)
        
        has_blocking = any(d.should_block for d in drift_signals)
        has_escalation = any(d.should_escalate for d in drift_signals)
        
        return DriftReport(
            agent_gid=agent_gid,
            agent_name=agent_name,
            execution_lane=execution_lane,
            evaluation_timestamp=timestamp,
            total_signals=len(drift_signals),
            drift_signals=drift_signals,
            has_blocking_drift=has_blocking,
            has_escalation_required=has_escalation,
        )
    
    def _evaluate_metric(
        self,
        metric_name: str,
        value: float,
        envelope: CalibrationEnvelope,
        p50_consecutive: int,
        p25_consecutive: int,
    ) -> DriftSignal:
        """Evaluate a single metric for drift."""
        
        # Get threshold violation
        threshold, deviation = envelope.get_threshold_violation(value)
        
        # Determine severity and actions per GOVERNANCE_AGENT_BASELINES.md
        if threshold == "NONE":
            return DriftSignal(
                drift_type=DriftType.NONE,
                severity=DriftSeverity.NONE,
                metric_name=metric_name,
                current_value=value,
                expected_value=envelope.p50,
                deviation=0.0,
                consecutive_violations=0,
                should_block=False,
                should_escalate=False,
            )
        
        # P10 violation = SEVERE (immediate block, GS_095)
        if threshold == "P10":
            return DriftSignal(
                drift_type=DriftType.STATISTICAL,
                severity=DriftSeverity.SEVERE,
                metric_name=metric_name,
                current_value=value,
                expected_value=envelope.p10,
                deviation=deviation,
                consecutive_violations=1,
                should_block=True,
                should_escalate=True,
                error_code="GS_095",
                message=f"{metric_name}: {value} below P10 threshold {envelope.p10} — immediate BENSON review required",
            )
        
        # P25 violation for 2+ consecutive = MODERATE (escalation)
        if threshold == "P25" and p25_consecutive >= 2:
            return DriftSignal(
                drift_type=DriftType.STATISTICAL,
                severity=DriftSeverity.MODERATE,
                metric_name=metric_name,
                current_value=value,
                expected_value=envelope.p25,
                deviation=deviation,
                consecutive_violations=p25_consecutive,
                should_block=False,  # Per spec: MODERATE is optionally blocking
                should_escalate=True,
                error_code="GS_095",
                message=f"{metric_name}: {value} below P25 for {p25_consecutive} consecutive PACs — agent review required",
            )
        
        # P50 violation for 3+ consecutive = MINOR (training signal)
        if threshold in ("P50", "P25") and p50_consecutive >= 3:
            return DriftSignal(
                drift_type=DriftType.STATISTICAL,
                severity=DriftSeverity.MINOR,
                metric_name=metric_name,
                current_value=value,
                expected_value=envelope.p50,
                deviation=deviation,
                consecutive_violations=p50_consecutive,
                should_block=False,
                should_escalate=False,
                message=f"{metric_name}: {value} below P50 for {p50_consecutive} consecutive PACs — BEHAVIORAL_ADJUSTMENT signal",
            )
        
        # Single P50/P25 violation without consecutive pattern = no drift signal
        return DriftSignal(
            drift_type=DriftType.NONE,
            severity=DriftSeverity.NONE,
            metric_name=metric_name,
            current_value=value,
            expected_value=envelope.p50,
            deviation=0.0,
            consecutive_violations=max(p50_consecutive, p25_consecutive),
            should_block=False,
            should_escalate=False,
        )


def evaluate_drift(
    agent_gid: str,
    agent_name: str,
    execution_lane: str,
    metrics: Dict[str, float],
) -> Tuple[bool, bool, List[str]]:
    """
    Convenience function for gate_pack.py integration.
    
    Returns:
        Tuple of (has_blocking_drift, has_escalation, error_messages)
    """
    evaluator = DriftEvaluator()
    report = evaluator.evaluate(
        agent_gid=agent_gid,
        agent_name=agent_name,
        execution_lane=execution_lane,
        metrics=metrics,
    )
    
    errors = []
    for d in report.drift_signals:
        if d.should_block:
            errors.append(f"[GS_095] {d.message}")
        elif d.should_escalate:
            errors.append(f"[ESCALATE] {d.message}")
    
    return (report.has_blocking_drift, report.has_escalation_required, errors)


def main():
    """CLI entry point for drift evaluation."""
    import argparse
    import json
    import time
    
    parser = argparse.ArgumentParser(
        description="Evaluate metrics for drift against calibration envelope"
    )
    parser.add_argument("--gid", required=True, help="Agent GID (e.g., GID-01)")
    parser.add_argument("--name", required=True, help="Agent name (e.g., Cody)")
    parser.add_argument("--lane", required=True, help="Execution lane (e.g., BACKEND)")
    parser.add_argument(
        "--metrics",
        required=True,
        help="JSON string of metrics (e.g., '{\"first_pass_validity\": 0.5}')",
    )
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument(
        "--history",
        help="JSON string of historical metrics for consecutive violation detection",
    )
    
    args = parser.parse_args()
    
    try:
        metrics = json.loads(args.metrics)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid metrics JSON: {e}")
        return 1
    
    # Pre-populate history if provided
    evaluator = DriftEvaluator()
    if args.history:
        try:
            history_data = json.loads(args.history)
            for metric_name, values in history_data.items():
                for value in values:
                    evaluator.history.record(args.gid, metric_name, value)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid history JSON: {e}")
            return 1
    
    start_time = time.time()
    
    report = evaluator.evaluate(
        agent_gid=args.gid,
        agent_name=args.name,
        execution_lane=args.lane,
        metrics=metrics,
    )
    report.execution_time_ms = int((time.time() - start_time) * 1000)
    
    if args.format == "json":
        output = {
            "agent_gid": report.agent_gid,
            "agent_name": report.agent_name,
            "execution_lane": report.execution_lane,
            "evaluation_timestamp": report.evaluation_timestamp,
            "total_signals": report.total_signals,
            "has_blocking_drift": report.has_blocking_drift,
            "has_escalation_required": report.has_escalation_required,
            "execution_time_ms": report.execution_time_ms,
            "drift_signals": [
                {
                    "drift_type": d.drift_type.value,
                    "severity": d.severity.value,
                    "metric_name": d.metric_name,
                    "current_value": d.current_value,
                    "expected_value": d.expected_value,
                    "deviation": d.deviation,
                    "consecutive_violations": d.consecutive_violations,
                    "should_block": d.should_block,
                    "should_escalate": d.should_escalate,
                    "error_code": d.error_code,
                    "message": d.message,
                }
                for d in report.drift_signals
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print("=" * 70)
        print("DRIFT EVALUATION REPORT")
        print("=" * 70)
        print(f"Agent: {report.agent_name} ({report.agent_gid})")
        print(f"Lane: {report.execution_lane}")
        print(f"Timestamp: {report.evaluation_timestamp}")
        print(f"Drift Signals: {report.total_signals}")
        print(f"Execution Time: {report.execution_time_ms}ms")
        print("-" * 70)
        
        if not report.drift_signals:
            print("✓ NO DRIFT DETECTED")
        else:
            for d in report.drift_signals:
                if d.should_block:
                    icon = "✗"
                elif d.should_escalate:
                    icon = "⚠"
                else:
                    icon = "•"
                print(f"{icon} [{d.severity.value}] {d.message}")
        
        print("-" * 70)
        print(report.summary)
        print("=" * 70)
    
    return 1 if report.has_blocking_drift else 0


if __name__ == "__main__":
    exit(main())
