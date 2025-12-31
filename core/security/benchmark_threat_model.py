# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark Threat Model — Security Analysis for Benchmarking Infrastructure
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# Agent: SAM (GID-06)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Benchmark Threat Model — Threat Surface Analysis

PURPOSE:
    Identify and mitigate security threats specific to the benchmarking
    infrastructure. Even in SHADOW mode, benchmark data and configurations
    must be protected.

THREAT VECTORS (TMV-BENCH-*):
    TMV-BENCH-001: Benchmark Result Tampering
    TMV-BENCH-002: Timing Side Channels
    TMV-BENCH-003: Cost Estimation Manipulation
    TMV-BENCH-004: Determinism Bypass
    TMV-BENCH-005: Readiness Gate Circumvention
    TMV-BENCH-006: Instrumentation Leak
    TMV-BENCH-007: Replay Attack on Benchmarks
    TMV-BENCH-008: Dashboard Data Injection

MITIGATIONS (TMM-BENCH-*):
    TMM-BENCH-001: Result Hash Verification
    TMM-BENCH-002: Timing Normalization
    TMM-BENCH-003: Cost Audit Trail
    TMM-BENCH-004: Determinism Enforcement
    TMM-BENCH-005: Multi-Gate Approval
    TMM-BENCH-006: Instrumentation Isolation
    TMM-BENCH-007: Sequence Validation
    TMM-BENCH-008: Input Sanitization

CONSTRAINTS:
    - SHADOW MODE only
    - No live data exposure
    - Audit all benchmark operations

LANE: EXECUTION (SECURITY)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class ThreatSeverity(Enum):
    """Severity level of threat."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ThreatStatus(Enum):
    """Status of threat mitigation."""

    OPEN = "OPEN"  # Not yet mitigated
    MITIGATED = "MITIGATED"  # Mitigation applied
    ACCEPTED = "ACCEPTED"  # Risk accepted
    MONITORING = "MONITORING"  # Under observation


class ThreatCategory(Enum):
    """Category of threat."""

    INTEGRITY = "INTEGRITY"  # Data tampering
    CONFIDENTIALITY = "CONFIDENTIALITY"  # Information leak
    AVAILABILITY = "AVAILABILITY"  # Service disruption
    AUTHENTICATION = "AUTHENTICATION"  # Identity bypass
    AUTHORIZATION = "AUTHORIZATION"  # Permission escalation


class MitigationType(Enum):
    """Type of mitigation."""

    PREVENTIVE = "PREVENTIVE"  # Prevent attack
    DETECTIVE = "DETECTIVE"  # Detect attack
    CORRECTIVE = "CORRECTIVE"  # Respond to attack


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT VECTOR
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class BenchmarkThreatVector:
    """Definition of a benchmark-specific threat vector."""

    vector_id: str
    name: str
    description: str
    category: ThreatCategory
    severity: ThreatSeverity
    status: ThreatStatus = ThreatStatus.OPEN
    attack_scenario: str = ""
    affected_components: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    mitigation_refs: List[str] = field(default_factory=list)
    cvss_score: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.vector_id.startswith("TMV-BENCH-"):
            raise ValueError(f"Benchmark threat vector ID must start with 'TMV-BENCH-': {self.vector_id}")

    @property
    def is_mitigated(self) -> bool:
        return self.status in (ThreatStatus.MITIGATED, ThreatStatus.ACCEPTED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vector_id": self.vector_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "status": self.status.value,
            "attack_scenario": self.attack_scenario,
            "affected_components": self.affected_components,
            "prerequisites": self.prerequisites,
            "mitigation_refs": self.mitigation_refs,
            "cvss_score": self.cvss_score,
            "is_mitigated": self.is_mitigated,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MITIGATION
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class BenchmarkMitigation:
    """Definition of a benchmark-specific mitigation."""

    mitigation_id: str
    name: str
    description: str
    mitigation_type: MitigationType
    implementation: str
    effectiveness: str  # Description of effectiveness
    threat_refs: List[str] = field(default_factory=list)
    verification_steps: List[str] = field(default_factory=list)
    is_implemented: bool = False
    implemented_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.mitigation_id.startswith("TMM-BENCH-"):
            raise ValueError(f"Benchmark mitigation ID must start with 'TMM-BENCH-': {self.mitigation_id}")

    def mark_implemented(self) -> None:
        self.is_implemented = True
        self.implemented_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mitigation_id": self.mitigation_id,
            "name": self.name,
            "description": self.description,
            "mitigation_type": self.mitigation_type.value,
            "implementation": self.implementation,
            "effectiveness": self.effectiveness,
            "threat_refs": self.threat_refs,
            "verification_steps": self.verification_steps,
            "is_implemented": self.is_implemented,
            "implemented_at": self.implemented_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PRE-DEFINED THREAT VECTORS
# ═══════════════════════════════════════════════════════════════════════════════


TMV_BENCH_001 = BenchmarkThreatVector(
    vector_id="TMV-BENCH-001",
    name="Benchmark Result Tampering",
    description="Attacker modifies benchmark results to falsely indicate readiness",
    category=ThreatCategory.INTEGRITY,
    severity=ThreatSeverity.HIGH,
    attack_scenario="Attacker gains write access to benchmark storage and modifies latency/throughput metrics to meet graduation thresholds",
    affected_components=["BenchmarkResult", "BenchmarkHarness", "result storage"],
    prerequisites=["Write access to benchmark storage", "Knowledge of result format"],
    mitigation_refs=["TMM-BENCH-001"],
    cvss_score=7.5,
)

TMV_BENCH_002 = BenchmarkThreatVector(
    vector_id="TMV-BENCH-002",
    name="Timing Side Channels",
    description="Attacker extracts sensitive information via timing analysis",
    category=ThreatCategory.CONFIDENTIALITY,
    severity=ThreatSeverity.MEDIUM,
    attack_scenario="Attacker measures benchmark execution times to infer internal processing patterns or data characteristics",
    affected_components=["LatencyProfiler", "TimingSpan", "benchmark execution"],
    prerequisites=["Access to timing data", "Statistical analysis capability"],
    mitigation_refs=["TMM-BENCH-002"],
    cvss_score=5.3,
)

TMV_BENCH_003 = BenchmarkThreatVector(
    vector_id="TMV-BENCH-003",
    name="Cost Estimation Manipulation",
    description="Attacker manipulates cost estimates to hide true operational costs",
    category=ThreatCategory.INTEGRITY,
    severity=ThreatSeverity.MEDIUM,
    attack_scenario="Attacker modifies cost coefficients or token counts to underreport costs, leading to budget overruns",
    affected_components=["CostMetrics", "CostRecord", "CostAttributor"],
    prerequisites=["Access to cost configuration", "Understanding of cost model"],
    mitigation_refs=["TMM-BENCH-003"],
    cvss_score=6.1,
)

TMV_BENCH_004 = BenchmarkThreatVector(
    vector_id="TMV-BENCH-004",
    name="Determinism Bypass",
    description="Attacker circumvents determinism checks to pass non-deterministic systems",
    category=ThreatCategory.INTEGRITY,
    severity=ThreatSeverity.CRITICAL,
    attack_scenario="Attacker provides pre-computed hashes or manipulates replay verification to falsely claim determinism",
    affected_components=["DeterminismTracker", "DeterminismMetrics", "replay verification"],
    prerequisites=["Access to hash storage", "Replay mechanism control"],
    mitigation_refs=["TMM-BENCH-004"],
    cvss_score=8.2,
)

TMV_BENCH_005 = BenchmarkThreatVector(
    vector_id="TMV-BENCH-005",
    name="Readiness Gate Circumvention",
    description="Attacker bypasses readiness gates to force premature graduation",
    category=ThreatCategory.AUTHORIZATION,
    severity=ThreatSeverity.CRITICAL,
    attack_scenario="Attacker directly marks graduation checklist items as PASSED without proper verification",
    affected_components=["GraduationChecklist", "ChecklistItem", "ReadinessInvariantRegistry"],
    prerequisites=["Access to checklist state", "Bypass verification logic"],
    mitigation_refs=["TMM-BENCH-005"],
    cvss_score=8.8,
)

TMV_BENCH_006 = BenchmarkThreatVector(
    vector_id="TMV-BENCH-006",
    name="Instrumentation Leak",
    description="Sensitive data exposed through instrumentation logs",
    category=ThreatCategory.CONFIDENTIALITY,
    severity=ThreatSeverity.MEDIUM,
    attack_scenario="Instrumentation captures and logs sensitive data (tokens, costs, internal state) accessible to unauthorized parties",
    affected_components=["InstrumentationRegistry", "InstrumentationContext", "log storage"],
    prerequisites=["Access to instrumentation logs", "Knowledge of data format"],
    mitigation_refs=["TMM-BENCH-006"],
    cvss_score=5.7,
)

TMV_BENCH_007 = BenchmarkThreatVector(
    vector_id="TMV-BENCH-007",
    name="Replay Attack on Benchmarks",
    description="Attacker replays old benchmark results to mask degradation",
    category=ThreatCategory.INTEGRITY,
    severity=ThreatSeverity.HIGH,
    attack_scenario="Attacker substitutes current benchmark results with historical 'good' results to hide performance regression",
    affected_components=["BenchmarkResult", "result history", "comparison logic"],
    prerequisites=["Access to historical results", "Ability to substitute results"],
    mitigation_refs=["TMM-BENCH-007"],
    cvss_score=7.1,
)

TMV_BENCH_008 = BenchmarkThreatVector(
    vector_id="TMV-BENCH-008",
    name="Dashboard Data Injection",
    description="Attacker injects malicious data into benchmark dashboard",
    category=ThreatCategory.INTEGRITY,
    severity=ThreatSeverity.MEDIUM,
    attack_scenario="Attacker injects crafted data that causes dashboard to display false information or execute XSS",
    affected_components=["OCCBenchmarkPanel", "chart components", "data rendering"],
    prerequisites=["Access to data pipeline", "Knowledge of dashboard format"],
    mitigation_refs=["TMM-BENCH-008"],
    cvss_score=6.5,
)


# ═══════════════════════════════════════════════════════════════════════════════
# PRE-DEFINED MITIGATIONS
# ═══════════════════════════════════════════════════════════════════════════════


TMM_BENCH_001 = BenchmarkMitigation(
    mitigation_id="TMM-BENCH-001",
    name="Result Hash Verification",
    description="Cryptographic hash verification of all benchmark results",
    mitigation_type=MitigationType.DETECTIVE,
    implementation="All BenchmarkResult objects compute and store SHA-256 hash. Verification checks hash on read.",
    effectiveness="Detects any modification to result data. Does not prevent initial corruption.",
    threat_refs=["TMV-BENCH-001"],
    verification_steps=[
        "Verify compute_result_hash() produces consistent output",
        "Test hash verification on load",
        "Confirm tampering is detected",
    ],
    is_implemented=True,
)

TMM_BENCH_002 = BenchmarkMitigation(
    mitigation_id="TMM-BENCH-002",
    name="Timing Normalization",
    description="Normalize timing data to prevent side-channel leakage",
    mitigation_type=MitigationType.PREVENTIVE,
    implementation="Add random jitter to timing measurements. Aggregate data before exposure.",
    effectiveness="Reduces timing precision available to attackers. Some information leakage possible with large samples.",
    threat_refs=["TMV-BENCH-002"],
    verification_steps=[
        "Verify jitter is applied to measurements",
        "Test aggregation before external exposure",
        "Confirm individual timing not accessible",
    ],
    is_implemented=True,
)

TMM_BENCH_003 = BenchmarkMitigation(
    mitigation_id="TMM-BENCH-003",
    name="Cost Audit Trail",
    description="Immutable audit trail for all cost calculations",
    mitigation_type=MitigationType.DETECTIVE,
    implementation="Log all cost coefficient changes. Track token counts with timestamps. Alert on anomalies.",
    effectiveness="Enables forensic analysis of cost manipulation. Does not prevent in real-time.",
    threat_refs=["TMV-BENCH-003"],
    verification_steps=[
        "Verify all cost changes logged",
        "Test anomaly detection triggers",
        "Confirm audit trail immutability",
    ],
    is_implemented=True,
)

TMM_BENCH_004 = BenchmarkMitigation(
    mitigation_id="TMM-BENCH-004",
    name="Determinism Enforcement",
    description="Multi-round verification with cryptographic binding",
    mitigation_type=MitigationType.PREVENTIVE,
    implementation="Require N independent replays with hash chain. Commit input hash before output computation.",
    effectiveness="Prevents pre-computation attacks. Requires substantial resources to forge determinism.",
    threat_refs=["TMV-BENCH-004"],
    verification_steps=[
        "Verify multi-round replay executed",
        "Test hash chain integrity",
        "Confirm commit-reveal pattern",
    ],
    is_implemented=True,
)

TMM_BENCH_005 = BenchmarkMitigation(
    mitigation_id="TMM-BENCH-005",
    name="Multi-Gate Approval",
    description="Require multiple independent approvals for graduation",
    mitigation_type=MitigationType.PREVENTIVE,
    implementation="All checklist items require evaluator signoff. Graduation requires N-of-M operator approval.",
    effectiveness="Prevents single-point-of-failure in approval process. Requires collusion to bypass.",
    threat_refs=["TMV-BENCH-005"],
    verification_steps=[
        "Verify evaluator required for each item",
        "Test N-of-M approval logic",
        "Confirm cannot bypass with single approval",
    ],
    is_implemented=True,
)

TMM_BENCH_006 = BenchmarkMitigation(
    mitigation_id="TMM-BENCH-006",
    name="Instrumentation Isolation",
    description="Isolate and sanitize instrumentation data",
    mitigation_type=MitigationType.PREVENTIVE,
    implementation="Scrub sensitive data before logging. Separate storage for instrumentation. Access controls on logs.",
    effectiveness="Reduces exposure of sensitive data. Some metadata may still leak.",
    threat_refs=["TMV-BENCH-006"],
    verification_steps=[
        "Verify sensitive data scrubbed",
        "Test storage isolation",
        "Confirm access controls enforced",
    ],
    is_implemented=True,
)

TMM_BENCH_007 = BenchmarkMitigation(
    mitigation_id="TMM-BENCH-007",
    name="Sequence Validation",
    description="Validate benchmark result sequence and timestamps",
    mitigation_type=MitigationType.DETECTIVE,
    implementation="Enforce monotonic timestamp sequence. Detect gaps in result IDs. Alert on out-of-sequence results.",
    effectiveness="Detects replay of historical results. Cannot prevent if attacker controls timestamp.",
    threat_refs=["TMV-BENCH-007"],
    verification_steps=[
        "Verify timestamp monotonicity enforced",
        "Test gap detection in result IDs",
        "Confirm alert on anomalies",
    ],
    is_implemented=True,
)

TMM_BENCH_008 = BenchmarkMitigation(
    mitigation_id="TMM-BENCH-008",
    name="Input Sanitization",
    description="Sanitize all data before dashboard rendering",
    mitigation_type=MitigationType.PREVENTIVE,
    implementation="Escape all user-controllable data. Validate data types and ranges. CSP headers on dashboard.",
    effectiveness="Prevents XSS and injection attacks. May not catch novel attack patterns.",
    threat_refs=["TMV-BENCH-008"],
    verification_steps=[
        "Verify all data escaped",
        "Test type/range validation",
        "Confirm CSP headers present",
    ],
    is_implemented=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT MODEL REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


class BenchmarkThreatModelRegistry:
    """
    Registry for benchmark threat vectors and mitigations.

    Manages:
    - Threat vector registration
    - Mitigation tracking
    - Coverage analysis
    - Report generation
    """

    def __init__(self) -> None:
        self._vectors: Dict[str, BenchmarkThreatVector] = {}
        self._mitigations: Dict[str, BenchmarkMitigation] = {}

        # Register defaults
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default threat vectors and mitigations."""
        vectors = [
            TMV_BENCH_001, TMV_BENCH_002, TMV_BENCH_003, TMV_BENCH_004,
            TMV_BENCH_005, TMV_BENCH_006, TMV_BENCH_007, TMV_BENCH_008,
        ]
        for v in vectors:
            self.register_vector(v)

        mitigations = [
            TMM_BENCH_001, TMM_BENCH_002, TMM_BENCH_003, TMM_BENCH_004,
            TMM_BENCH_005, TMM_BENCH_006, TMM_BENCH_007, TMM_BENCH_008,
        ]
        for m in mitigations:
            self.register_mitigation(m)

    def register_vector(self, vector: BenchmarkThreatVector) -> None:
        """Register a threat vector."""
        self._vectors[vector.vector_id] = vector

    def register_mitigation(self, mitigation: BenchmarkMitigation) -> None:
        """Register a mitigation."""
        self._mitigations[mitigation.mitigation_id] = mitigation

    def get_vector(self, vector_id: str) -> Optional[BenchmarkThreatVector]:
        """Get threat vector by ID."""
        return self._vectors.get(vector_id)

    def get_mitigation(self, mitigation_id: str) -> Optional[BenchmarkMitigation]:
        """Get mitigation by ID."""
        return self._mitigations.get(mitigation_id)

    def list_vectors(self) -> List[BenchmarkThreatVector]:
        """List all threat vectors."""
        return list(self._vectors.values())

    def list_mitigations(self) -> List[BenchmarkMitigation]:
        """List all mitigations."""
        return list(self._mitigations.values())

    def list_by_severity(self, severity: ThreatSeverity) -> List[BenchmarkThreatVector]:
        """List threats by severity."""
        return [v for v in self._vectors.values() if v.severity == severity]

    def list_by_category(self, category: ThreatCategory) -> List[BenchmarkThreatVector]:
        """List threats by category."""
        return [v for v in self._vectors.values() if v.category == category]

    def get_unmitigated_vectors(self) -> List[BenchmarkThreatVector]:
        """Get list of unmitigated threats."""
        return [v for v in self._vectors.values() if not v.is_mitigated]

    def get_coverage_score(self) -> float:
        """Get mitigation coverage score."""
        if not self._vectors:
            return 0.0
        mitigated = sum(1 for v in self._vectors.values() if v.is_mitigated)
        return mitigated / len(self._vectors)

    def apply_mitigation(self, vector_id: str, mitigation_id: str) -> bool:
        """Apply a mitigation to a threat vector."""
        vector = self._vectors.get(vector_id)
        mitigation = self._mitigations.get(mitigation_id)

        if vector is None or mitigation is None:
            return False

        if mitigation_id not in vector.mitigation_refs:
            vector.mitigation_refs.append(mitigation_id)

        if vector_id not in mitigation.threat_refs:
            mitigation.threat_refs.append(vector_id)

        if mitigation.is_implemented:
            vector.status = ThreatStatus.MITIGATED

        return True

    def generate_report(self) -> Dict[str, Any]:
        """Generate threat model report."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scope": "BENCHMARK_INFRASTRUCTURE",
            "vector_count": len(self._vectors),
            "mitigation_count": len(self._mitigations),
            "coverage_score": round(self.get_coverage_score(), 4),
            "unmitigated_count": len(self.get_unmitigated_vectors()),
            "by_severity": {
                "CRITICAL": len(self.list_by_severity(ThreatSeverity.CRITICAL)),
                "HIGH": len(self.list_by_severity(ThreatSeverity.HIGH)),
                "MEDIUM": len(self.list_by_severity(ThreatSeverity.MEDIUM)),
                "LOW": len(self.list_by_severity(ThreatSeverity.LOW)),
            },
            "by_category": {
                "INTEGRITY": len(self.list_by_category(ThreatCategory.INTEGRITY)),
                "CONFIDENTIALITY": len(self.list_by_category(ThreatCategory.CONFIDENTIALITY)),
                "AVAILABILITY": len(self.list_by_category(ThreatCategory.AVAILABILITY)),
                "AUTHENTICATION": len(self.list_by_category(ThreatCategory.AUTHENTICATION)),
                "AUTHORIZATION": len(self.list_by_category(ThreatCategory.AUTHORIZATION)),
            },
            "vectors": {vid: v.to_dict() for vid, v in self._vectors.items()},
            "mitigations": {mid: m.to_dict() for mid, m in self._mitigations.items()},
        }

    def compute_model_hash(self) -> str:
        """Compute hash of threat model state."""
        data = {
            "vectors": {vid: v.status.value for vid, v in self._vectors.items()},
            "mitigations": {mid: m.is_implemented for mid, m in self._mitigations.items()},
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "ThreatSeverity",
    "ThreatStatus",
    "ThreatCategory",
    "MitigationType",
    # Data classes
    "BenchmarkThreatVector",
    "BenchmarkMitigation",
    # Pre-defined vectors
    "TMV_BENCH_001",
    "TMV_BENCH_002",
    "TMV_BENCH_003",
    "TMV_BENCH_004",
    "TMV_BENCH_005",
    "TMV_BENCH_006",
    "TMV_BENCH_007",
    "TMV_BENCH_008",
    # Pre-defined mitigations
    "TMM_BENCH_001",
    "TMM_BENCH_002",
    "TMM_BENCH_003",
    "TMM_BENCH_004",
    "TMM_BENCH_005",
    "TMM_BENCH_006",
    "TMM_BENCH_007",
    "TMM_BENCH_008",
    # Registry
    "BenchmarkThreatModelRegistry",
]
