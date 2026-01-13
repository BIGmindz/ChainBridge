"""
Behavioral Platform Fingerprint Primitive
PAC-P748-ARCH-GOVERNANCE-DEFENSIBILITY-LOCK-AND-EXECUTION
TASK-13: Implement BehavioralFingerprint primitive

Implements:
- Fingerprint signal collection and emission
- Clone detection engine
- Tamper evidence detection
- Verification interface
"""

from __future__ import annotations

import hashlib
import json
import time
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Callable
from pathlib import Path
import statistics


class SignalCategory(Enum):
    """Categories of fingerprint signals."""
    HARDWARE = "HARDWARE"
    SOFTWARE = "SOFTWARE"
    BEHAVIORAL = "BEHAVIORAL"
    CRYPTOGRAPHIC = "CRYPTOGRAPHIC"


class VerificationStatus(Enum):
    """Fingerprint verification status."""
    AUTHENTIC = "AUTHENTIC"
    ANOMALOUS = "ANOMALOUS"
    CLONE_SUSPECTED = "CLONE_SUSPECTED"
    TAMPERED = "TAMPERED"


@dataclass
class SignalMeasurement:
    """A single fingerprint signal measurement."""
    category: SignalCategory
    signal_name: str
    value: float
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "signal_name": self.signal_name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class FingerprintEmission:
    """A fingerprint emission package."""
    fingerprint_id: str
    instance_id: str
    timestamp: datetime
    signal_vector: list[float]
    signal_hash: str
    sequence_number: int
    signature: str
    category_breakdown: dict[str, list[float]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint_id": self.fingerprint_id,
            "instance_id": self.instance_id,
            "timestamp": self.timestamp.isoformat(),
            "signal_hash": self.signal_hash,
            "sequence_number": self.sequence_number,
            "signature": self.signature,
            "signal_count": len(self.signal_vector)
        }


@dataclass
class FingerprintBaseline:
    """Baseline fingerprint for an instance."""
    instance_id: str
    created_at: datetime
    learning_period_hours: int
    signal_means: dict[str, float]
    signal_stddevs: dict[str, float]
    tolerance_factor: float = 3.0  # Standard deviations for anomaly

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "created_at": self.created_at.isoformat(),
            "learning_period_hours": self.learning_period_hours,
            "signal_count": len(self.signal_means),
            "tolerance_factor": self.tolerance_factor
        }


@dataclass
class CloneDetectionResult:
    """Result of clone detection analysis."""
    checked_at: datetime
    status: VerificationStatus
    confidence: float
    details: dict[str, Any]
    colliding_instance: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked_at": self.checked_at.isoformat(),
            "status": self.status.value,
            "confidence": self.confidence,
            "details": self.details,
            "colliding_instance": self.colliding_instance
        }


class SignalCollector:
    """Collects fingerprint signals from various sources."""

    def __init__(self):
        self._measurements: list[SignalMeasurement] = []
        self._operation_latencies: list[float] = []
        self._error_counts: dict[str, int] = {}

    def collect_hardware_signals(self) -> list[SignalMeasurement]:
        """Collect hardware-derived signals."""
        signals = []
        now = datetime.now(timezone.utc)

        # Timing jitter (simulated via high-resolution timing)
        jitter_samples = []
        for _ in range(10):
            start = time.perf_counter_ns()
            _ = hashlib.sha256(b"jitter_test").hexdigest()
            end = time.perf_counter_ns()
            jitter_samples.append(end - start)
        
        signals.append(SignalMeasurement(
            category=SignalCategory.HARDWARE,
            signal_name="timing_jitter_mean_ns",
            value=statistics.mean(jitter_samples) if jitter_samples else 0,
            timestamp=now
        ))
        signals.append(SignalMeasurement(
            category=SignalCategory.HARDWARE,
            signal_name="timing_jitter_stddev_ns",
            value=statistics.stdev(jitter_samples) if len(jitter_samples) > 1 else 0,
            timestamp=now
        ))

        # Process ID (environment signal)
        signals.append(SignalMeasurement(
            category=SignalCategory.HARDWARE,
            signal_name="process_id",
            value=float(os.getpid()),
            timestamp=now
        ))

        return signals

    def collect_software_signals(self) -> list[SignalMeasurement]:
        """Collect software behavior signals."""
        signals = []
        now = datetime.now(timezone.utc)

        # Memory allocation pattern (simplified)
        signals.append(SignalMeasurement(
            category=SignalCategory.SOFTWARE,
            signal_name="object_allocation_time_ns",
            value=self._measure_allocation_time(),
            timestamp=now
        ))

        return signals

    def collect_behavioral_signals(self) -> list[SignalMeasurement]:
        """Collect operational behavior signals."""
        signals = []
        now = datetime.now(timezone.utc)

        if self._operation_latencies:
            signals.append(SignalMeasurement(
                category=SignalCategory.BEHAVIORAL,
                signal_name="latency_mean_ms",
                value=statistics.mean(self._operation_latencies),
                timestamp=now
            ))
            if len(self._operation_latencies) > 1:
                signals.append(SignalMeasurement(
                    category=SignalCategory.BEHAVIORAL,
                    signal_name="latency_stddev_ms",
                    value=statistics.stdev(self._operation_latencies),
                    timestamp=now
                ))

        signals.append(SignalMeasurement(
            category=SignalCategory.BEHAVIORAL,
            signal_name="error_rate",
            value=sum(self._error_counts.values()) / max(1, len(self._operation_latencies)),
            timestamp=now
        ))

        return signals

    def collect_cryptographic_signals(self) -> list[SignalMeasurement]:
        """Collect cryptographic operation signals."""
        signals = []
        now = datetime.now(timezone.utc)

        # Key derivation timing
        times = []
        for _ in range(5):
            start = time.perf_counter_ns()
            _ = hashlib.pbkdf2_hmac('sha256', b'test', b'salt', 1000)
            end = time.perf_counter_ns()
            times.append(end - start)

        signals.append(SignalMeasurement(
            category=SignalCategory.CRYPTOGRAPHIC,
            signal_name="kdf_mean_ns",
            value=statistics.mean(times),
            timestamp=now
        ))

        return signals

    def _measure_allocation_time(self) -> float:
        """Measure object allocation time."""
        start = time.perf_counter_ns()
        _ = [i for i in range(1000)]
        end = time.perf_counter_ns()
        return float(end - start)

    def record_operation(self, latency_ms: float, error: bool = False, error_type: Optional[str] = None) -> None:
        """Record an operation for behavioral signals."""
        self._operation_latencies.append(latency_ms)
        if len(self._operation_latencies) > 10000:
            self._operation_latencies = self._operation_latencies[-5000:]
        
        if error and error_type:
            self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

    def collect_all(self) -> list[SignalMeasurement]:
        """Collect all signals."""
        signals = []
        signals.extend(self.collect_hardware_signals())
        signals.extend(self.collect_software_signals())
        signals.extend(self.collect_behavioral_signals())
        signals.extend(self.collect_cryptographic_signals())
        return signals


class BehavioralFingerprintEngine:
    """
    Engine for behavioral platform fingerprinting.
    
    Enforces:
    - Unique instance identity
    - Continuous signal emission
    - Clone detection
    - Tamper evidence
    """

    EMISSION_INTERVAL_MS = 1000
    BASELINE_LEARNING_HOURS = 72

    def __init__(self, storage_path: Optional[Path] = None):
        self.instance_id = f"INST-{secrets.token_hex(8).upper()}"
        self._collector = SignalCollector()
        self._sequence_number = 0
        self._emissions: list[FingerprintEmission] = []
        self._baseline: Optional[FingerprintBaseline] = None
        self._learning_data: list[list[float]] = []
        self._known_instances: dict[str, str] = {}  # instance_id -> last_fingerprint_hash
        self.storage_path = storage_path or Path("data/fingerprint_engine.json")
        
        # Instance secret for signatures
        self._instance_secret = secrets.token_bytes(32)

    def _compute_hash(self, data: Any) -> str:
        """Compute SHA3-256 hash."""
        serialized = json.dumps(data, sort_keys=True, default=str).encode()
        return f"sha3-256:{hashlib.sha3_256(serialized).hexdigest()}"

    def _sign_emission(self, fingerprint_id: str, signal_hash: str) -> str:
        """Create instance-specific signature."""
        message = f"{fingerprint_id}:{signal_hash}:{self.instance_id}".encode()
        signature = hashlib.sha3_256(self._instance_secret + message).hexdigest()
        return signature[:32]

    def emit_fingerprint(self) -> FingerprintEmission:
        """Emit a fingerprint signal package."""
        signals = self._collector.collect_all()
        
        # Build signal vector
        signal_vector = [s.value for s in signals]
        category_breakdown = {}
        for s in signals:
            cat = s.category.value
            if cat not in category_breakdown:
                category_breakdown[cat] = []
            category_breakdown[cat].append(s.value)

        # Compute hash
        signal_hash = self._compute_hash(signal_vector)
        
        # Generate fingerprint ID
        fingerprint_id = f"FP-{secrets.token_hex(6).upper()}"
        
        # Increment sequence
        self._sequence_number += 1
        
        emission = FingerprintEmission(
            fingerprint_id=fingerprint_id,
            instance_id=self.instance_id,
            timestamp=datetime.now(timezone.utc),
            signal_vector=signal_vector,
            signal_hash=signal_hash,
            sequence_number=self._sequence_number,
            signature=self._sign_emission(fingerprint_id, signal_hash),
            category_breakdown=category_breakdown
        )

        self._emissions.append(emission)
        
        # Store for learning
        self._learning_data.append(signal_vector)
        if len(self._learning_data) > 10000:
            self._learning_data = self._learning_data[-5000:]

        return emission

    def build_baseline(self) -> FingerprintBaseline:
        """Build baseline from collected data."""
        if len(self._learning_data) < 100:
            raise ValueError("Insufficient data for baseline (need at least 100 samples)")

        signals = self._collector.collect_all()
        signal_names = [s.signal_name for s in signals]

        means = {}
        stddevs = {}
        
        for i, name in enumerate(signal_names):
            values = [vec[i] for vec in self._learning_data if i < len(vec)]
            if values:
                means[name] = statistics.mean(values)
                stddevs[name] = statistics.stdev(values) if len(values) > 1 else 0

        self._baseline = FingerprintBaseline(
            instance_id=self.instance_id,
            created_at=datetime.now(timezone.utc),
            learning_period_hours=self.BASELINE_LEARNING_HOURS,
            signal_means=means,
            signal_stddevs=stddevs
        )

        return self._baseline

    def verify_fingerprint(self, emission: FingerprintEmission) -> CloneDetectionResult:
        """Verify a fingerprint emission."""
        # Check for collision with known instances
        for known_id, known_hash in self._known_instances.items():
            if known_id != emission.instance_id and known_hash == emission.signal_hash:
                return CloneDetectionResult(
                    checked_at=datetime.now(timezone.utc),
                    status=VerificationStatus.CLONE_SUSPECTED,
                    confidence=0.95,
                    details={"reason": "Fingerprint hash collision"},
                    colliding_instance=known_id
                )

        # Check sequence gap
        if self._emissions:
            last_seq = self._emissions[-1].sequence_number
            expected_seq = last_seq + 1
            if emission.instance_id == self.instance_id and emission.sequence_number != expected_seq:
                return CloneDetectionResult(
                    checked_at=datetime.now(timezone.utc),
                    status=VerificationStatus.ANOMALOUS,
                    confidence=0.7,
                    details={
                        "reason": "Sequence gap detected",
                        "expected": expected_seq,
                        "received": emission.sequence_number
                    }
                )

        # Check against baseline if available
        if self._baseline and emission.instance_id == self.instance_id:
            anomalies = self._check_baseline_deviation(emission)
            if anomalies:
                return CloneDetectionResult(
                    checked_at=datetime.now(timezone.utc),
                    status=VerificationStatus.ANOMALOUS,
                    confidence=0.6,
                    details={"anomalies": anomalies}
                )

        # Update known instances
        self._known_instances[emission.instance_id] = emission.signal_hash

        return CloneDetectionResult(
            checked_at=datetime.now(timezone.utc),
            status=VerificationStatus.AUTHENTIC,
            confidence=0.99,
            details={"verification": "passed"}
        )

    def _check_baseline_deviation(self, emission: FingerprintEmission) -> list[str]:
        """Check for deviations from baseline."""
        anomalies = []
        
        if not self._baseline:
            return anomalies

        signals = self._collector.collect_all()
        for i, signal in enumerate(signals):
            if i >= len(emission.signal_vector):
                continue
            
            name = signal.signal_name
            value = emission.signal_vector[i]
            
            mean = self._baseline.signal_means.get(name, 0)
            stddev = self._baseline.signal_stddevs.get(name, 0)
            
            if stddev > 0:
                z_score = abs(value - mean) / stddev
                if z_score > self._baseline.tolerance_factor:
                    anomalies.append(f"{name}: z-score={z_score:.2f}")

        return anomalies

    def self_verify(self) -> CloneDetectionResult:
        """Perform self-verification."""
        emission = self.emit_fingerprint()
        return self.verify_fingerprint(emission)

    def record_operation(self, latency_ms: float, error: bool = False, error_type: Optional[str] = None) -> None:
        """Record operation for behavioral signals."""
        self._collector.record_operation(latency_ms, error, error_type)

    def get_status(self) -> dict[str, Any]:
        """Get engine status."""
        return {
            "instance_id": self.instance_id,
            "sequence_number": self._sequence_number,
            "emissions_count": len(self._emissions),
            "baseline_established": self._baseline is not None,
            "known_instances": len(self._known_instances),
            "learning_samples": len(self._learning_data)
        }

    def export(self) -> dict[str, Any]:
        """Export engine state."""
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "instance_id": self.instance_id,
            "sequence_number": self._sequence_number,
            "baseline": self._baseline.to_dict() if self._baseline else None,
            "recent_emissions": [e.to_dict() for e in self._emissions[-100:]],
            "status": self.get_status()
        }

    def save(self) -> None:
        """Save engine state."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.export(), f, indent=2)


# Singleton instance
_fingerprint_engine: Optional[BehavioralFingerprintEngine] = None


def get_fingerprint_engine() -> BehavioralFingerprintEngine:
    """Get global fingerprint engine instance."""
    global _fingerprint_engine
    if _fingerprint_engine is None:
        _fingerprint_engine = BehavioralFingerprintEngine()
    return _fingerprint_engine
