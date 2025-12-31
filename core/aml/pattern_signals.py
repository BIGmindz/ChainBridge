# ═══════════════════════════════════════════════════════════════════════════════
# AML Pattern Signals — Behavioral Analysis (SHADOW MODE)
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# Agent: MAGGIE (GID-10)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Pattern Signals — Behavioral & Sequence Pattern Detection

PURPOSE:
    Identify behavioral patterns indicative of money laundering or
    financial crime using deterministic analysis only.

SIGNALS DETECTED:
    - Transaction velocity anomalies
    - Structuring patterns
    - Layering indicators
    - Unusual network patterns
    - Timing anomalies

CONSTRAINTS:
    - SHADOW MODE: No live inference
    - NO neural learning
    - Deterministic rules only
    - All signals require evidence backing

LANE: EXECUTION (AML SIGNALS)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN SIGNAL ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class PatternType(Enum):
    """Type of behavioral pattern."""

    # Transaction patterns
    STRUCTURING = "STRUCTURING"
    SMURFING = "SMURFING"
    LAYERING = "LAYERING"
    RAPID_MOVEMENT = "RAPID_MOVEMENT"
    ROUND_AMOUNTS = "ROUND_AMOUNTS"

    # Velocity patterns
    VELOCITY_SPIKE = "VELOCITY_SPIKE"
    DORMANT_ACTIVATION = "DORMANT_ACTIVATION"
    UNUSUAL_TIMING = "UNUSUAL_TIMING"

    # Network patterns
    STAR_PATTERN = "STAR_PATTERN"  # One central node many edges
    CHAIN_PATTERN = "CHAIN_PATTERN"  # Linear movement
    CIRCULAR_FLOW = "CIRCULAR_FLOW"  # Funds returning to origin

    # Geographic patterns
    JURISDICTION_HOPPING = "JURISDICTION_HOPPING"
    HIGH_RISK_GEOGRAPHY = "HIGH_RISK_GEOGRAPHY"

    # Behavioral patterns
    INCONSISTENT_PROFILE = "INCONSISTENT_PROFILE"
    UNUSUAL_PRODUCT_USE = "UNUSUAL_PRODUCT_USE"


class SignalSeverity(Enum):
    """Severity of detected signal."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DetectionMethod(Enum):
    """Method used to detect pattern."""

    THRESHOLD = "THRESHOLD"  # Simple threshold check
    STATISTICAL = "STATISTICAL"  # Statistical deviation
    RULE_BASED = "RULE_BASED"  # Business rule match
    SEQUENCE = "SEQUENCE"  # Sequential pattern match
    NETWORK = "NETWORK"  # Graph analysis


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN RULE
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class PatternRule:
    """
    Deterministic rule for pattern detection.

    Defines the conditions under which a pattern is flagged.
    """

    rule_id: str
    pattern_type: PatternType
    name: str
    description: str
    threshold: float
    severity: SignalSeverity
    detection_method: DetectionMethod
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.rule_id.startswith("RULE-"):
            raise ValueError(f"Rule ID must start with 'RULE-': {self.rule_id}")

    def compute_rule_hash(self) -> str:
        """Compute deterministic hash of rule."""
        data = {
            "rule_id": self.rule_id,
            "pattern_type": self.pattern_type.value,
            "threshold": self.threshold,
            "parameters": self.parameters,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "pattern_type": self.pattern_type.value,
            "name": self.name,
            "description": self.description,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "detection_method": self.detection_method.value,
            "parameters": self.parameters,
            "enabled": self.enabled,
            "rule_hash": self.compute_rule_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN SIGNAL
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class PatternSignal:
    """
    Detected behavioral pattern signal.

    Represents a single pattern detection with supporting
    evidence and confidence metrics.
    """

    signal_id: str
    pattern_type: PatternType
    rule_id: str
    entity_id: str
    severity: SignalSeverity
    confidence: float
    detected_value: float
    threshold_value: float
    description: str
    evidence_refs: List[str] = field(default_factory=list)
    contributing_transactions: List[str] = field(default_factory=list)
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    suppressed: bool = False
    suppression_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.signal_id.startswith("PSIG-"):
            raise ValueError(f"Signal ID must start with 'PSIG-': {self.signal_id}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0: {self.confidence}")

    @property
    def is_actionable(self) -> bool:
        """Check if signal is actionable (not suppressed)."""
        return not self.suppressed

    @property
    def exceeds_threshold(self) -> bool:
        """Check if detected value exceeds threshold."""
        return self.detected_value >= self.threshold_value

    def suppress(self, reason: str) -> None:
        """Suppress the signal with reason."""
        self.suppressed = True
        self.suppression_reason = reason

    def compute_signal_hash(self) -> str:
        """Compute deterministic hash of signal."""
        data = {
            "signal_id": self.signal_id,
            "pattern_type": self.pattern_type.value,
            "rule_id": self.rule_id,
            "entity_id": self.entity_id,
            "detected_value": self.detected_value,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "pattern_type": self.pattern_type.value,
            "rule_id": self.rule_id,
            "entity_id": self.entity_id,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "detected_value": self.detected_value,
            "threshold_value": self.threshold_value,
            "description": self.description,
            "evidence_refs": self.evidence_refs,
            "contributing_transactions": self.contributing_transactions,
            "detected_at": self.detected_at,
            "suppressed": self.suppressed,
            "suppression_reason": self.suppression_reason,
            "is_actionable": self.is_actionable,
            "exceeds_threshold": self.exceeds_threshold,
            "signal_hash": self.compute_signal_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSACTION METRICS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TransactionMetrics:
    """
    Aggregated transaction metrics for pattern detection.

    Provides computed statistics over a transaction set.
    """

    entity_id: str
    period_start: str
    period_end: str
    transaction_count: int = 0
    total_amount: float = 0.0
    average_amount: float = 0.0
    max_amount: float = 0.0
    min_amount: float = 0.0
    std_deviation: float = 0.0
    unique_counterparties: int = 0
    unique_jurisdictions: int = 0
    round_amount_count: int = 0
    just_under_threshold_count: int = 0
    weekend_count: int = 0
    night_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "transaction_count": self.transaction_count,
            "total_amount": self.total_amount,
            "average_amount": self.average_amount,
            "max_amount": self.max_amount,
            "min_amount": self.min_amount,
            "std_deviation": self.std_deviation,
            "unique_counterparties": self.unique_counterparties,
            "unique_jurisdictions": self.unique_jurisdictions,
            "round_amount_count": self.round_amount_count,
            "just_under_threshold_count": self.just_under_threshold_count,
            "weekend_count": self.weekend_count,
            "night_count": self.night_count,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT PATTERN RULES
# ═══════════════════════════════════════════════════════════════════════════════


# Structuring detection
RULE_STRUCTURING = PatternRule(
    rule_id="RULE-AML-001",
    pattern_type=PatternType.STRUCTURING,
    name="Cash Structuring Detection",
    description="Multiple transactions just below reporting threshold",
    threshold=3.0,  # 3+ transactions below threshold in period
    severity=SignalSeverity.HIGH,
    detection_method=DetectionMethod.THRESHOLD,
    parameters={
        "reporting_threshold": 10000.0,
        "margin_percentage": 0.15,  # 15% below threshold
        "lookback_days": 7,
    },
)

# Velocity spike detection
RULE_VELOCITY_SPIKE = PatternRule(
    rule_id="RULE-AML-002",
    pattern_type=PatternType.VELOCITY_SPIKE,
    name="Transaction Velocity Spike",
    description="Significant increase in transaction frequency",
    threshold=3.0,  # 3x normal activity
    severity=SignalSeverity.MEDIUM,
    detection_method=DetectionMethod.STATISTICAL,
    parameters={
        "baseline_period_days": 90,
        "comparison_period_days": 7,
        "min_baseline_transactions": 10,
    },
)

# Rapid movement detection
RULE_RAPID_MOVEMENT = PatternRule(
    rule_id="RULE-AML-003",
    pattern_type=PatternType.RAPID_MOVEMENT,
    name="Rapid Fund Movement",
    description="Funds moving quickly through account",
    threshold=0.9,  # 90% of funds move within window
    severity=SignalSeverity.MEDIUM,
    detection_method=DetectionMethod.RULE_BASED,
    parameters={
        "window_hours": 24,
        "min_amount": 5000.0,
    },
)

# Dormant account activation
RULE_DORMANT_ACTIVATION = PatternRule(
    rule_id="RULE-AML-004",
    pattern_type=PatternType.DORMANT_ACTIVATION,
    name="Dormant Account Activation",
    description="Inactive account with sudden activity",
    threshold=1.0,  # Any transaction after dormancy
    severity=SignalSeverity.MEDIUM,
    detection_method=DetectionMethod.RULE_BASED,
    parameters={
        "dormancy_days": 180,
        "min_transaction_amount": 1000.0,
    },
)

# Round amount detection
RULE_ROUND_AMOUNTS = PatternRule(
    rule_id="RULE-AML-005",
    pattern_type=PatternType.ROUND_AMOUNTS,
    name="Round Amount Pattern",
    description="High proportion of round-number transactions",
    threshold=0.7,  # 70% round amounts
    severity=SignalSeverity.LOW,
    detection_method=DetectionMethod.STATISTICAL,
    parameters={
        "round_amount_tolerance": 0.01,  # Allow 1% variance
        "min_transactions": 5,
    },
)

# Layering detection
RULE_LAYERING = PatternRule(
    rule_id="RULE-AML-006",
    pattern_type=PatternType.LAYERING,
    name="Layering Pattern",
    description="Multiple intermediate transfers obscuring origin",
    threshold=3.0,  # 3+ layers
    severity=SignalSeverity.HIGH,
    detection_method=DetectionMethod.SEQUENCE,
    parameters={
        "time_window_hours": 48,
        "min_transaction_count": 4,
        "variance_tolerance": 0.05,
    },
)

# Circular flow detection
RULE_CIRCULAR_FLOW = PatternRule(
    rule_id="RULE-AML-007",
    pattern_type=PatternType.CIRCULAR_FLOW,
    name="Circular Fund Flow",
    description="Funds returning to origin through intermediaries",
    threshold=0.8,  # 80% of amount returns
    severity=SignalSeverity.HIGH,
    detection_method=DetectionMethod.NETWORK,
    parameters={
        "max_hops": 5,
        "time_window_days": 30,
        "amount_tolerance": 0.1,
    },
)

# Unusual timing detection
RULE_UNUSUAL_TIMING = PatternRule(
    rule_id="RULE-AML-008",
    pattern_type=PatternType.UNUSUAL_TIMING,
    name="Unusual Transaction Timing",
    description="High proportion of off-hours or weekend transactions",
    threshold=0.5,  # 50% unusual timing
    severity=SignalSeverity.LOW,
    detection_method=DetectionMethod.STATISTICAL,
    parameters={
        "night_hours": [0, 1, 2, 3, 4, 5, 22, 23],
        "weekend_days": [5, 6],  # Saturday, Sunday
        "min_transactions": 10,
    },
)


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════


class PatternAnalyzer:
    """
    Deterministic pattern analyzer for AML signals.

    Provides:
    - Rule-based pattern detection
    - Statistical anomaly detection
    - Sequence pattern matching
    - Signal aggregation
    """

    def __init__(self) -> None:
        self._rules: Dict[str, PatternRule] = {}
        self._signals: Dict[str, PatternSignal] = {}
        self._signal_counter = 0

        # Register default rules
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default pattern rules."""
        defaults = [
            RULE_STRUCTURING,
            RULE_VELOCITY_SPIKE,
            RULE_RAPID_MOVEMENT,
            RULE_DORMANT_ACTIVATION,
            RULE_ROUND_AMOUNTS,
            RULE_LAYERING,
            RULE_CIRCULAR_FLOW,
            RULE_UNUSUAL_TIMING,
        ]
        for rule in defaults:
            self._rules[rule.rule_id] = rule

    # ───────────────────────────────────────────────────────────────────────────
    # PATTERN DETECTION
    # ───────────────────────────────────────────────────────────────────────────

    def analyze_transactions(
        self,
        entity_id: str,
        metrics: TransactionMetrics,
        transactions: Optional[List[Dict[str, Any]]] = None,
    ) -> List[PatternSignal]:
        """
        Analyze transactions for patterns.

        Args:
            entity_id: Entity being analyzed
            metrics: Pre-computed transaction metrics
            transactions: Optional raw transaction list

        Returns:
            List of detected pattern signals
        """
        detected_signals: List[PatternSignal] = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            signal = self._apply_rule(rule, entity_id, metrics, transactions)
            if signal is not None:
                self._signals[signal.signal_id] = signal
                detected_signals.append(signal)

        return detected_signals

    def _apply_rule(
        self,
        rule: PatternRule,
        entity_id: str,
        metrics: TransactionMetrics,
        transactions: Optional[List[Dict[str, Any]]],
    ) -> Optional[PatternSignal]:
        """Apply a single rule and return signal if triggered."""
        detected_value = 0.0
        confidence = 0.0
        description = ""
        contributing_txns: List[str] = []

        if rule.pattern_type == PatternType.STRUCTURING:
            detected_value = float(metrics.just_under_threshold_count)
            if detected_value >= rule.threshold:
                confidence = min(1.0, detected_value / (rule.threshold * 2))
                description = f"Detected {int(detected_value)} transactions just below reporting threshold"

        elif rule.pattern_type == PatternType.VELOCITY_SPIKE:
            # Would require historical baseline comparison
            # Using transaction count as proxy for demo
            baseline = rule.parameters.get("min_baseline_transactions", 10)
            if baseline > 0 and metrics.transaction_count >= baseline * rule.threshold:
                detected_value = metrics.transaction_count / baseline
                confidence = min(1.0, detected_value / (rule.threshold * 2))
                description = f"Transaction velocity {detected_value:.1f}x above baseline"

        elif rule.pattern_type == PatternType.ROUND_AMOUNTS:
            if metrics.transaction_count >= rule.parameters.get("min_transactions", 5):
                ratio = metrics.round_amount_count / metrics.transaction_count if metrics.transaction_count > 0 else 0
                detected_value = ratio
                if ratio >= rule.threshold:
                    confidence = ratio
                    description = f"{ratio*100:.0f}% of transactions are round amounts"

        elif rule.pattern_type == PatternType.UNUSUAL_TIMING:
            if metrics.transaction_count >= rule.parameters.get("min_transactions", 10):
                unusual_count = metrics.weekend_count + metrics.night_count
                ratio = unusual_count / metrics.transaction_count if metrics.transaction_count > 0 else 0
                detected_value = ratio
                if ratio >= rule.threshold:
                    confidence = ratio
                    description = f"{ratio*100:.0f}% of transactions at unusual times"

        elif rule.pattern_type == PatternType.DORMANT_ACTIVATION:
            # Would require account activity history
            # Placeholder for detection
            pass

        elif rule.pattern_type == PatternType.RAPID_MOVEMENT:
            # Would require inflow/outflow tracking
            # Placeholder for detection
            pass

        elif rule.pattern_type == PatternType.LAYERING:
            # Would require transaction sequence analysis
            # Placeholder for detection
            pass

        elif rule.pattern_type == PatternType.CIRCULAR_FLOW:
            # Would require network graph analysis
            # Placeholder for detection
            pass

        # Create signal if threshold exceeded
        if detected_value >= rule.threshold and confidence > 0:
            return self._create_signal(
                rule=rule,
                entity_id=entity_id,
                detected_value=detected_value,
                confidence=confidence,
                description=description,
                contributing_txns=contributing_txns,
            )

        return None

    def _create_signal(
        self,
        rule: PatternRule,
        entity_id: str,
        detected_value: float,
        confidence: float,
        description: str,
        contributing_txns: List[str],
    ) -> PatternSignal:
        """Create a pattern signal."""
        self._signal_counter += 1
        signal_id = f"PSIG-{self._signal_counter:08d}"

        return PatternSignal(
            signal_id=signal_id,
            pattern_type=rule.pattern_type,
            rule_id=rule.rule_id,
            entity_id=entity_id,
            severity=rule.severity,
            confidence=confidence,
            detected_value=detected_value,
            threshold_value=rule.threshold,
            description=description,
            contributing_transactions=contributing_txns,
        )

    # ───────────────────────────────────────────────────────────────────────────
    # QUERIES
    # ───────────────────────────────────────────────────────────────────────────

    def get_signals_for_entity(self, entity_id: str) -> List[PatternSignal]:
        """Get all signals for an entity."""
        return [s for s in self._signals.values() if s.entity_id == entity_id]

    def get_signals_by_type(self, pattern_type: PatternType) -> List[PatternSignal]:
        """Get all signals of a specific type."""
        return [s for s in self._signals.values() if s.pattern_type == pattern_type]

    def get_actionable_signals(self) -> List[PatternSignal]:
        """Get all actionable (non-suppressed) signals."""
        return [s for s in self._signals.values() if s.is_actionable]

    def get_high_severity_signals(self) -> List[PatternSignal]:
        """Get all high/critical severity signals."""
        return [s for s in self._signals.values() if s.severity in (SignalSeverity.HIGH, SignalSeverity.CRITICAL)]

    def get_rule(self, rule_id: str) -> Optional[PatternRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def list_rules(self) -> List[PatternRule]:
        """List all registered rules."""
        return list(self._rules.values())

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False

    # ───────────────────────────────────────────────────────────────────────────
    # REPORTING
    # ───────────────────────────────────────────────────────────────────────────

    def generate_report(self) -> Dict[str, Any]:
        """Generate analyzer status report."""
        signals_by_severity: Dict[str, int] = {}
        for severity in SignalSeverity:
            signals_by_severity[severity.value] = len([
                s for s in self._signals.values() if s.severity == severity
            ])

        signals_by_type: Dict[str, int] = {}
        for pattern_type in PatternType:
            signals_by_type[pattern_type.value] = len([
                s for s in self._signals.values() if s.pattern_type == pattern_type
            ])

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_rules": len(self._rules),
            "enabled_rules": len([r for r in self._rules.values() if r.enabled]),
            "total_signals": len(self._signals),
            "actionable_signals": len(self.get_actionable_signals()),
            "signals_by_severity": signals_by_severity,
            "signals_by_type": signals_by_type,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "PatternType",
    "SignalSeverity",
    "DetectionMethod",
    # Data Classes
    "PatternRule",
    "PatternSignal",
    "TransactionMetrics",
    # Services
    "PatternAnalyzer",
    # Default Rules
    "RULE_STRUCTURING",
    "RULE_VELOCITY_SPIKE",
    "RULE_RAPID_MOVEMENT",
    "RULE_DORMANT_ACTIVATION",
    "RULE_ROUND_AMOUNTS",
    "RULE_LAYERING",
    "RULE_CIRCULAR_FLOW",
    "RULE_UNUSUAL_TIMING",
]
