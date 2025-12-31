# ═══════════════════════════════════════════════════════════════════════════════
# AML Shadow Signal Emitter (SHADOW MODE ONLY)
# PAC-BENSON-P29: AML SHADOW PILOT EXECUTION
# Agent: MAGGIE (GID-10)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Shadow Signal Emitter — Pattern Signal Generation (SHADOW MODE)

PURPOSE:
    Emit behavioral pattern signals in SHADOW mode for pilot testing.
    Wires pattern detection to shadow pilot scenarios.

CONSTRAINTS:
    - SHADOW MODE ONLY: No live transaction feeds
    - NO production data
    - All signals are synthetic
    - Deterministic emission for reproducibility

LANE: EXECUTION (AML SHADOW PILOT)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple

from core.aml.pattern_signals import (
    DetectionMethod,
    PatternRule,
    PatternSignal,
    PatternType,
    SignalSeverity,
    TransactionMetrics,
    RULE_STRUCTURING,
    RULE_VELOCITY_SPIKE,
    RULE_RAPID_MOVEMENT,
    RULE_DORMANT_ACTIVATION,
    RULE_ROUND_AMOUNTS,
)
from core.aml.shadow_pilot import (
    ShadowDataGenerator,
    ShadowEntity,
    ShadowScenario,
    ShadowTransaction,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW SIGNAL ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class ShadowSignalScenario(Enum):
    """Pre-defined shadow signal scenarios."""

    # Benign scenarios (should not trigger)
    NORMAL_ACTIVITY = "NORMAL_ACTIVITY"
    LOW_VOLUME = "LOW_VOLUME"
    CONSISTENT_PATTERNS = "CONSISTENT_PATTERNS"

    # Alert scenarios (should trigger signals)
    STRUCTURING_BEHAVIOR = "STRUCTURING_BEHAVIOR"
    VELOCITY_ANOMALY = "VELOCITY_ANOMALY"
    RAPID_FUND_MOVEMENT = "RAPID_FUND_MOVEMENT"
    DORMANT_REACTIVATION = "DORMANT_REACTIVATION"
    ROUND_AMOUNT_PATTERN = "ROUND_AMOUNT_PATTERN"
    LAYERING_PATTERN = "LAYERING_PATTERN"
    CIRCULAR_FLOW = "CIRCULAR_FLOW"


class EmissionMode(Enum):
    """Signal emission mode."""

    SHADOW = "SHADOW"  # Always shadow - production disabled
    DISABLED = "DISABLED"  # Completely disabled


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ShadowSignalBatch:
    """
    Batch of shadow signals emitted together.

    Groups related signals for a scenario execution.
    """

    batch_id: str
    scenario: ShadowSignalScenario
    entity_id: str
    signals: List[PatternSignal] = field(default_factory=list)
    transactions: List[ShadowTransaction] = field(default_factory=list)
    metrics: Optional[TransactionMetrics] = None
    emitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    shadow_mode: bool = True  # ALWAYS TRUE

    def __post_init__(self) -> None:
        if not self.batch_id.startswith("SHBAT-"):
            raise ValueError(f"Batch ID must start with 'SHBAT-': {self.batch_id}")
        if not self.shadow_mode:
            raise ValueError("FAIL-CLOSED: Shadow mode must be enabled")

    @property
    def signal_count(self) -> int:
        """Number of signals in batch."""
        return len(self.signals)

    @property
    def transaction_count(self) -> int:
        """Number of transactions in batch."""
        return len(self.transactions)

    def add_signal(self, signal: PatternSignal) -> None:
        """Add signal to batch."""
        self.signals.append(signal)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "scenario": self.scenario.value,
            "entity_id": self.entity_id,
            "signal_count": self.signal_count,
            "transaction_count": self.transaction_count,
            "signals": [s.to_dict() for s in self.signals],
            "emitted_at": self.emitted_at,
            "shadow_mode": self.shadow_mode,
        }


@dataclass
class SignalExpectation:
    """
    Expected signals for a scenario.

    Defines what signals should be emitted for validation.
    """

    scenario: ShadowSignalScenario
    expected_pattern_types: List[PatternType]
    expected_severity_range: Tuple[SignalSeverity, SignalSeverity]
    should_trigger: bool
    min_signals: int = 0
    max_signals: int = 10


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW SIGNAL EMITTER
# ═══════════════════════════════════════════════════════════════════════════════


class ShadowSignalEmitter:
    """
    Emitter for shadow pattern signals.

    Generates pattern signals in SHADOW mode only.
    NO production data, NO live feeds.
    """

    # Scenario to signal expectations
    SCENARIO_EXPECTATIONS: Dict[ShadowSignalScenario, SignalExpectation] = {
        ShadowSignalScenario.NORMAL_ACTIVITY: SignalExpectation(
            scenario=ShadowSignalScenario.NORMAL_ACTIVITY,
            expected_pattern_types=[],
            expected_severity_range=(SignalSeverity.LOW, SignalSeverity.LOW),
            should_trigger=False,
        ),
        ShadowSignalScenario.STRUCTURING_BEHAVIOR: SignalExpectation(
            scenario=ShadowSignalScenario.STRUCTURING_BEHAVIOR,
            expected_pattern_types=[PatternType.STRUCTURING, PatternType.ROUND_AMOUNTS],
            expected_severity_range=(SignalSeverity.MEDIUM, SignalSeverity.HIGH),
            should_trigger=True,
            min_signals=1,
            max_signals=3,
        ),
        ShadowSignalScenario.VELOCITY_ANOMALY: SignalExpectation(
            scenario=ShadowSignalScenario.VELOCITY_ANOMALY,
            expected_pattern_types=[PatternType.VELOCITY_SPIKE, PatternType.UNUSUAL_TIMING],
            expected_severity_range=(SignalSeverity.MEDIUM, SignalSeverity.HIGH),
            should_trigger=True,
            min_signals=1,
            max_signals=2,
        ),
        ShadowSignalScenario.RAPID_FUND_MOVEMENT: SignalExpectation(
            scenario=ShadowSignalScenario.RAPID_FUND_MOVEMENT,
            expected_pattern_types=[PatternType.RAPID_MOVEMENT, PatternType.LAYERING],
            expected_severity_range=(SignalSeverity.MEDIUM, SignalSeverity.HIGH),
            should_trigger=True,
            min_signals=1,
            max_signals=2,
        ),
        ShadowSignalScenario.DORMANT_REACTIVATION: SignalExpectation(
            scenario=ShadowSignalScenario.DORMANT_REACTIVATION,
            expected_pattern_types=[PatternType.DORMANT_ACTIVATION],
            expected_severity_range=(SignalSeverity.MEDIUM, SignalSeverity.MEDIUM),
            should_trigger=True,
            min_signals=1,
            max_signals=1,
        ),
        ShadowSignalScenario.ROUND_AMOUNT_PATTERN: SignalExpectation(
            scenario=ShadowSignalScenario.ROUND_AMOUNT_PATTERN,
            expected_pattern_types=[PatternType.ROUND_AMOUNTS],
            expected_severity_range=(SignalSeverity.LOW, SignalSeverity.MEDIUM),
            should_trigger=True,
            min_signals=1,
            max_signals=1,
        ),
        ShadowSignalScenario.LAYERING_PATTERN: SignalExpectation(
            scenario=ShadowSignalScenario.LAYERING_PATTERN,
            expected_pattern_types=[PatternType.LAYERING, PatternType.CHAIN_PATTERN],
            expected_severity_range=(SignalSeverity.HIGH, SignalSeverity.CRITICAL),
            should_trigger=True,
            min_signals=1,
            max_signals=2,
        ),
        ShadowSignalScenario.CIRCULAR_FLOW: SignalExpectation(
            scenario=ShadowSignalScenario.CIRCULAR_FLOW,
            expected_pattern_types=[PatternType.CIRCULAR_FLOW],
            expected_severity_range=(SignalSeverity.HIGH, SignalSeverity.CRITICAL),
            should_trigger=True,
            min_signals=1,
            max_signals=1,
        ),
    }

    def __init__(self, seed: int = 42) -> None:
        """
        Initialize emitter.

        Args:
            seed: Random seed for reproducibility
        """
        self._seed = seed
        self._generator = ShadowDataGenerator(seed=seed)
        self._signal_counter = 0
        self._batch_counter = 0
        self._mode = EmissionMode.SHADOW  # ALWAYS SHADOW

    @property
    def is_shadow_mode(self) -> bool:
        """Verify shadow mode is enabled (always true)."""
        return self._mode == EmissionMode.SHADOW

    def _generate_signal_id(self) -> str:
        """Generate unique signal ID."""
        self._signal_counter += 1
        return f"PSIG-SH-{self._signal_counter:08d}"

    def _generate_batch_id(self) -> str:
        """Generate unique batch ID."""
        self._batch_counter += 1
        return f"SHBAT-{self._batch_counter:08d}"

    def emit_scenario_signals(
        self,
        scenario: ShadowSignalScenario,
        entity: ShadowEntity,
        transactions: Optional[List[ShadowTransaction]] = None,
    ) -> ShadowSignalBatch:
        """
        Emit signals for a specific scenario.

        Args:
            scenario: The shadow scenario to emit
            entity: The entity to emit signals for
            transactions: Optional list of transactions

        Returns:
            Batch of emitted signals
        """
        if not self.is_shadow_mode:
            raise RuntimeError("FAIL-CLOSED: Shadow mode must be enabled")

        batch = ShadowSignalBatch(
            batch_id=self._generate_batch_id(),
            scenario=scenario,
            entity_id=entity.entity_id,
            transactions=transactions or [],
        )

        expectation = self.SCENARIO_EXPECTATIONS.get(scenario)
        if expectation is None or not expectation.should_trigger:
            return batch

        # Generate signals based on scenario
        for pattern_type in expectation.expected_pattern_types:
            signal = self._create_signal_for_pattern(
                pattern_type=pattern_type,
                entity=entity,
                severity=expectation.expected_severity_range[0],
            )
            batch.add_signal(signal)

        return batch

    def _create_signal_for_pattern(
        self,
        pattern_type: PatternType,
        entity: ShadowEntity,
        severity: SignalSeverity,
    ) -> PatternSignal:
        """Create a signal for a specific pattern type."""
        rule_map = {
            PatternType.STRUCTURING: RULE_STRUCTURING,
            PatternType.VELOCITY_SPIKE: RULE_VELOCITY_SPIKE,
            PatternType.RAPID_MOVEMENT: RULE_RAPID_MOVEMENT,
            PatternType.DORMANT_ACTIVATION: RULE_DORMANT_ACTIVATION,
            PatternType.ROUND_AMOUNTS: RULE_ROUND_AMOUNTS,
        }

        rule = rule_map.get(pattern_type)
        rule_id = rule.rule_id if rule else f"RULE-SH-{pattern_type.value}"
        threshold = rule.threshold if rule else 1.0

        # Detected value exceeds threshold for triggering scenarios
        detected_value = threshold * 1.5

        return PatternSignal(
            signal_id=self._generate_signal_id(),
            pattern_type=pattern_type,
            rule_id=rule_id,
            entity_id=entity.entity_id,
            severity=severity,
            confidence=0.85,
            detected_value=detected_value,
            threshold_value=threshold,
            description=f"Shadow signal: {pattern_type.value} detected",
            evidence_refs=[f"SHEV-{uuid.uuid4().hex[:8].upper()}"],
        )

    def emit_structuring_signals(
        self,
        entity: ShadowEntity,
        transaction_count: int = 5,
    ) -> ShadowSignalBatch:
        """
        Emit structuring pattern signals.

        Simulates multiple transactions just below reporting threshold.
        """
        # Generate structuring transactions
        transactions = []
        counterparty = self._generator.generate_entity()

        for i in range(transaction_count):
            # Amounts just below $10,000 threshold
            amount = 9500 + (i * 50)  # $9,500 to $9,750
            txn = self._generator.generate_transaction(
                entity_id=entity.entity_id,
                counterparty_id=counterparty.entity_id,
                amount_range=(amount, amount + 10),
            )
            transactions.append(txn)

        return self.emit_scenario_signals(
            scenario=ShadowSignalScenario.STRUCTURING_BEHAVIOR,
            entity=entity,
            transactions=transactions,
        )

    def emit_velocity_signals(
        self,
        entity: ShadowEntity,
        spike_factor: float = 5.0,
    ) -> ShadowSignalBatch:
        """
        Emit velocity spike signals.

        Simulates sudden increase in transaction frequency.
        """
        batch = self.emit_scenario_signals(
            scenario=ShadowSignalScenario.VELOCITY_ANOMALY,
            entity=entity,
        )

        # Adjust detected value to reflect spike factor
        for signal in batch.signals:
            if signal.pattern_type == PatternType.VELOCITY_SPIKE:
                signal.detected_value = signal.threshold_value * spike_factor

        return batch

    def emit_layering_signals(
        self,
        entity: ShadowEntity,
        hop_count: int = 4,
    ) -> ShadowSignalBatch:
        """
        Emit layering pattern signals.

        Simulates funds moving through multiple intermediaries.
        """
        batch = self.emit_scenario_signals(
            scenario=ShadowSignalScenario.LAYERING_PATTERN,
            entity=entity,
        )

        # Add hop count to signal metadata
        for signal in batch.signals:
            signal.evidence_refs.append(f"HOP_COUNT:{hop_count}")

        return batch


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════


class ShadowSignalValidator:
    """
    Validator for shadow signal emissions.

    Ensures signals match expected patterns for test scenarios.
    """

    def __init__(self) -> None:
        """Initialize validator."""
        self._validation_results: List[Dict[str, Any]] = []

    def validate_batch(
        self,
        batch: ShadowSignalBatch,
        expectation: SignalExpectation,
    ) -> Dict[str, Any]:
        """
        Validate a signal batch against expectations.

        Args:
            batch: The batch to validate
            expectation: Expected signal characteristics

        Returns:
            Validation result
        """
        result = {
            "batch_id": batch.batch_id,
            "scenario": batch.scenario.value,
            "valid": True,
            "errors": [],
        }

        # Check signal count
        if expectation.should_trigger:
            if batch.signal_count < expectation.min_signals:
                result["valid"] = False
                result["errors"].append(
                    f"Too few signals: {batch.signal_count} < {expectation.min_signals}"
                )
            if batch.signal_count > expectation.max_signals:
                result["valid"] = False
                result["errors"].append(
                    f"Too many signals: {batch.signal_count} > {expectation.max_signals}"
                )
        else:
            if batch.signal_count > 0:
                result["valid"] = False
                result["errors"].append(
                    f"Should not trigger but emitted {batch.signal_count} signals"
                )

        # Check pattern types
        emitted_types = {s.pattern_type for s in batch.signals}
        expected_types = set(expectation.expected_pattern_types)

        if expectation.should_trigger and not emitted_types.intersection(expected_types):
            result["valid"] = False
            result["errors"].append(
                f"No expected pattern types emitted. Expected: {expected_types}, Got: {emitted_types}"
            )

        # Check severity
        for signal in batch.signals:
            min_sev, max_sev = expectation.expected_severity_range
            sev_order = [SignalSeverity.LOW, SignalSeverity.MEDIUM, SignalSeverity.HIGH, SignalSeverity.CRITICAL]

            sig_idx = sev_order.index(signal.severity)
            min_idx = sev_order.index(min_sev)
            max_idx = sev_order.index(max_sev)

            if sig_idx < min_idx or sig_idx > max_idx:
                result["errors"].append(
                    f"Signal {signal.signal_id} severity {signal.severity.value} out of range [{min_sev.value}, {max_sev.value}]"
                )

        self._validation_results.append(result)
        return result

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validations."""
        total = len(self._validation_results)
        valid = sum(1 for r in self._validation_results if r["valid"])

        return {
            "total_validations": total,
            "valid_count": valid,
            "invalid_count": total - valid,
            "pass_rate": valid / total if total > 0 else 0.0,
        }
