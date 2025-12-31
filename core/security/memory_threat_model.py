# ═══════════════════════════════════════════════════════════════════════════════
# Memory Threat Model — Neural Memory Security Analysis
# PAC-BENSON-P26: TITANS-READY NEURAL MEMORY ARCHITECTURE (SHADOW MODE)
# Agent: SAM (GID-06)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Memory Threat Model — Security Analysis for Neural Memory

PURPOSE:
    Define threat vectors specific to neural memory systems and their
    mitigations. Covers memory poisoning, unauthorized updates, freeze/rollback
    attacks, and exfiltration risks.

THREAT CATEGORIES:
    TMV-MEM-001..003: Memory Poisoning (data injection, gradient manipulation)
    TMV-MEM-004..006: Unauthorized Access (read/write/delete)
    TMV-MEM-007..009: State Manipulation (freeze bypass, rollback attacks)
    TMV-MEM-010..012: Exfiltration (memory extraction, inference attacks)

MITIGATIONS:
    TMM-MEM-001..015: Corresponding mitigations for each threat vector

LANE: ARCHITECTURE_ONLY (NON-INFERENCING)
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


class ThreatCategory(Enum):
    """Category of memory threat."""

    MEMORY_POISONING = "MEMORY_POISONING"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    STATE_MANIPULATION = "STATE_MANIPULATION"
    EXFILTRATION = "EXFILTRATION"
    DENIAL_OF_SERVICE = "DENIAL_OF_SERVICE"


class ThreatSeverity(Enum):
    """Severity rating for threats."""

    CRITICAL = "CRITICAL"  # Immediate action required
    HIGH = "HIGH"  # Urgent mitigation needed
    MEDIUM = "MEDIUM"  # Should be addressed
    LOW = "LOW"  # Monitor and plan


class MitigationStatus(Enum):
    """Status of threat mitigation."""

    IMPLEMENTED = "IMPLEMENTED"
    PARTIAL = "PARTIAL"
    PLANNED = "PLANNED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AttackVector(Enum):
    """Attack vector classification."""

    INTERNAL = "INTERNAL"  # From within system
    EXTERNAL = "EXTERNAL"  # From outside system
    SUPPLY_CHAIN = "SUPPLY_CHAIN"  # Via dependencies
    PHYSICAL = "PHYSICAL"  # Physical access
    SOCIAL = "SOCIAL"  # Social engineering


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY THREAT VECTOR
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MemoryThreatVector:
    """
    Definition of a memory-specific threat vector.

    Describes the threat, its severity, attack vectors, and potential impact.
    """

    threat_id: str
    name: str
    description: str
    category: ThreatCategory
    severity: ThreatSeverity
    attack_vectors: List[AttackVector]
    preconditions: List[str]
    impact: str
    likelihood: str  # "HIGH" | "MEDIUM" | "LOW"
    affected_components: List[str]
    cve_references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate threat ID format."""
        if not self.threat_id.startswith("TMV-MEM-"):
            raise ValueError(f"Threat ID must start with 'TMV-MEM-': {self.threat_id}")

    def compute_risk_score(self) -> float:
        """Compute risk score based on severity and likelihood."""
        severity_weights = {
            ThreatSeverity.CRITICAL: 1.0,
            ThreatSeverity.HIGH: 0.75,
            ThreatSeverity.MEDIUM: 0.5,
            ThreatSeverity.LOW: 0.25,
        }
        likelihood_weights = {
            "HIGH": 1.0,
            "MEDIUM": 0.6,
            "LOW": 0.3,
        }
        return severity_weights.get(self.severity, 0.5) * likelihood_weights.get(self.likelihood, 0.5)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY MITIGATION
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MemoryMitigation:
    """
    Mitigation strategy for memory threats.
    """

    mitigation_id: str
    name: str
    description: str
    threat_ids: List[str]  # TMV-MEM-* IDs this mitigates
    status: MitigationStatus
    implementation_notes: str
    effectiveness: str  # "HIGH" | "MEDIUM" | "LOW"
    cost: str  # "HIGH" | "MEDIUM" | "LOW"
    invariants_enforced: List[str] = field(default_factory=list)  # INV-MEM-* IDs
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate mitigation ID format."""
        if not self.mitigation_id.startswith("TMM-MEM-"):
            raise ValueError(f"Mitigation ID must start with 'TMM-MEM-': {self.mitigation_id}")


# ═══════════════════════════════════════════════════════════════════════════════
# P26 MEMORY THREAT VECTORS
# ═══════════════════════════════════════════════════════════════════════════════

# Memory Poisoning Threats
TMV_MEM_001 = MemoryThreatVector(
    threat_id="TMV-MEM-001",
    name="Direct Memory Poisoning",
    description="Attacker injects malicious data directly into neural memory state, corrupting stored representations and causing incorrect inference results.",
    category=ThreatCategory.MEMORY_POISONING,
    severity=ThreatSeverity.CRITICAL,
    attack_vectors=[AttackVector.INTERNAL, AttackVector.EXTERNAL],
    preconditions=["Write access to memory storage", "Bypass of input validation"],
    impact="Corrupted memory leads to incorrect model outputs, potential downstream decision failures.",
    likelihood="MEDIUM",
    affected_components=["NeuralMemoryInterface", "MemoryStateHash", "SnapshotRegistry"],
)

TMV_MEM_002 = MemoryThreatVector(
    threat_id="TMV-MEM-002",
    name="Gradient-Based Memory Manipulation",
    description="Attacker exploits test-time training to inject adversarial gradients that shift memory state toward malicious representations.",
    category=ThreatCategory.MEMORY_POISONING,
    severity=ThreatSeverity.CRITICAL,
    attack_vectors=[AttackVector.EXTERNAL],
    preconditions=["Test-time training enabled", "Access to input stream"],
    impact="Subtle memory corruption that evades detection, long-term model degradation.",
    likelihood="LOW",  # Mitigated by INV-MEM-006 (no production learning)
    affected_components=["NeuralMemoryInterface", "SurpriseMetric"],
)

TMV_MEM_003 = MemoryThreatVector(
    threat_id="TMV-MEM-003",
    name="Snapshot Tampering",
    description="Attacker modifies stored memory snapshots to inject poisoned state that gets restored during rollback operations.",
    category=ThreatCategory.MEMORY_POISONING,
    severity=ThreatSeverity.HIGH,
    attack_vectors=[AttackVector.INTERNAL, AttackVector.PHYSICAL],
    preconditions=["Access to snapshot storage", "Ability to modify snapshot data"],
    impact="Poisoned snapshots propagate through rollback, corrupting recovery operations.",
    likelihood="LOW",
    affected_components=["MemorySnapshot", "SnapshotRegistry"],
)

# Unauthorized Access Threats
TMV_MEM_004 = MemoryThreatVector(
    threat_id="TMV-MEM-004",
    name="Unauthorized Memory Read",
    description="Attacker gains read access to neural memory contents, potentially exposing sensitive patterns or proprietary knowledge.",
    category=ThreatCategory.UNAUTHORIZED_ACCESS,
    severity=ThreatSeverity.HIGH,
    attack_vectors=[AttackVector.INTERNAL, AttackVector.EXTERNAL],
    preconditions=["Network access to memory service", "Bypass of authentication"],
    impact="Exposure of learned representations, potential competitive intelligence leak.",
    likelihood="MEDIUM",
    affected_components=["NeuralMemoryInterface", "MemoryStateHash"],
)

TMV_MEM_005 = MemoryThreatVector(
    threat_id="TMV-MEM-005",
    name="Unauthorized Memory Write",
    description="Attacker gains write access to neural memory without proper authorization, enabling arbitrary state modification.",
    category=ThreatCategory.UNAUTHORIZED_ACCESS,
    severity=ThreatSeverity.CRITICAL,
    attack_vectors=[AttackVector.INTERNAL, AttackVector.EXTERNAL],
    preconditions=["Network access", "Authentication bypass or privilege escalation"],
    impact="Complete memory corruption, loss of model integrity.",
    likelihood="LOW",
    affected_components=["NeuralMemoryInterface", "MemoryUpdateRecord"],
)

TMV_MEM_006 = MemoryThreatVector(
    threat_id="TMV-MEM-006",
    name="Unauthorized Snapshot Deletion",
    description="Attacker deletes memory snapshots, preventing rollback and destroying audit trail.",
    category=ThreatCategory.UNAUTHORIZED_ACCESS,
    severity=ThreatSeverity.HIGH,
    attack_vectors=[AttackVector.INTERNAL],
    preconditions=["Admin access to snapshot storage", "Bypass of deletion controls"],
    impact="Loss of recovery capability, audit trail destruction.",
    likelihood="LOW",
    affected_components=["SnapshotRegistry", "MemorySnapshot"],
)

# State Manipulation Threats
TMV_MEM_007 = MemoryThreatVector(
    threat_id="TMV-MEM-007",
    name="Freeze Bypass Attack",
    description="Attacker bypasses frozen memory protection to modify state that should be immutable.",
    category=ThreatCategory.STATE_MANIPULATION,
    severity=ThreatSeverity.CRITICAL,
    attack_vectors=[AttackVector.INTERNAL],
    preconditions=["Access to memory internals", "Exploit in freeze implementation"],
    impact="Violation of immutability guarantees, potential silent corruption.",
    likelihood="LOW",
    affected_components=["NeuralMemoryInterface", "ShadowModeMemory"],
)

TMV_MEM_008 = MemoryThreatVector(
    threat_id="TMV-MEM-008",
    name="Rollback Chain Manipulation",
    description="Attacker manipulates snapshot chain to insert malicious snapshots or remove legitimate ones, corrupting rollback history.",
    category=ThreatCategory.STATE_MANIPULATION,
    severity=ThreatSeverity.HIGH,
    attack_vectors=[AttackVector.INTERNAL],
    preconditions=["Write access to snapshot registry", "Chain validation bypass"],
    impact="Corrupted rollback history, potential recovery to malicious state.",
    likelihood="LOW",
    affected_components=["SnapshotRegistry", "MemorySnapshot"],
)

TMV_MEM_009 = MemoryThreatVector(
    threat_id="TMV-MEM-009",
    name="Mode Escalation Attack",
    description="Attacker escalates memory mode from SHADOW to LEARNING/INFERENCE without authorization, enabling forbidden operations.",
    category=ThreatCategory.STATE_MANIPULATION,
    severity=ThreatSeverity.CRITICAL,
    attack_vectors=[AttackVector.INTERNAL, AttackVector.EXTERNAL],
    preconditions=["Access to mode configuration", "Bypass of mode controls"],
    impact="Unauthorized inference or learning in production, violation of operational constraints.",
    likelihood="MEDIUM",
    affected_components=["MemoryMode", "NeuralMemoryInterface"],
)

# Exfiltration Threats
TMV_MEM_010 = MemoryThreatVector(
    threat_id="TMV-MEM-010",
    name="Memory Extraction Attack",
    description="Attacker extracts full neural memory state through API abuse or direct storage access.",
    category=ThreatCategory.EXFILTRATION,
    severity=ThreatSeverity.HIGH,
    attack_vectors=[AttackVector.EXTERNAL, AttackVector.INTERNAL],
    preconditions=["API access", "Insufficient rate limiting or access controls"],
    impact="Complete memory exfiltration, loss of proprietary knowledge.",
    likelihood="MEDIUM",
    affected_components=["NeuralMemoryInterface", "MemoryStateHash"],
)

TMV_MEM_011 = MemoryThreatVector(
    threat_id="TMV-MEM-011",
    name="Model Inversion Attack",
    description="Attacker uses inference queries to reconstruct memory contents by analyzing model outputs.",
    category=ThreatCategory.EXFILTRATION,
    severity=ThreatSeverity.MEDIUM,
    attack_vectors=[AttackVector.EXTERNAL],
    preconditions=["Inference API access", "Sufficient query volume"],
    impact="Partial memory reconstruction, privacy violations.",
    likelihood="LOW",  # Mitigated by SHADOW mode (no inference)
    affected_components=["NeuralMemoryInterface", "DualBrainRouter"],
)

TMV_MEM_012 = MemoryThreatVector(
    threat_id="TMV-MEM-012",
    name="Surprise Metric Leakage",
    description="Attacker infers memory contents by observing surprise metrics, which reveal what the model considers novel.",
    category=ThreatCategory.EXFILTRATION,
    severity=ThreatSeverity.MEDIUM,
    attack_vectors=[AttackVector.EXTERNAL],
    preconditions=["Access to surprise metrics", "Statistical analysis capability"],
    impact="Indirect memory inference, privacy leakage.",
    likelihood="LOW",
    affected_components=["SurpriseMetric", "DualBrainRouter"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# P26 MEMORY MITIGATIONS
# ═══════════════════════════════════════════════════════════════════════════════

TMM_MEM_001 = MemoryMitigation(
    mitigation_id="TMM-MEM-001",
    name="Cryptographic State Hashing",
    description="All memory states are hashed using SHA-256 with integrity verification on read.",
    threat_ids=["TMV-MEM-001", "TMV-MEM-003", "TMV-MEM-007"],
    status=MitigationStatus.IMPLEMENTED,
    implementation_notes="MemoryStateHash.compute() and .verify() methods enforce hash integrity.",
    effectiveness="HIGH",
    cost="LOW",
    invariants_enforced=["INV-MEM-001", "INV-MEM-003"],
)

TMM_MEM_002 = MemoryMitigation(
    mitigation_id="TMM-MEM-002",
    name="Production Learning Prohibition",
    description="Test-time training and learning mode are strictly forbidden in production environment.",
    threat_ids=["TMV-MEM-002"],
    status=MitigationStatus.IMPLEMENTED,
    implementation_notes="INV-MEM-006 enforced by check_no_production_learning(). Mode transition blocked.",
    effectiveness="HIGH",
    cost="LOW",
    invariants_enforced=["INV-MEM-006", "INV-MEM-010"],
)

TMM_MEM_003 = MemoryMitigation(
    mitigation_id="TMM-MEM-003",
    name="Snapshot Chain Validation",
    description="Snapshot registry validates chain integrity on every operation, preventing chain manipulation.",
    threat_ids=["TMV-MEM-003", "TMV-MEM-008"],
    status=MitigationStatus.IMPLEMENTED,
    implementation_notes="SnapshotRegistry.verify_chain() validates predecessor linkage.",
    effectiveness="HIGH",
    cost="LOW",
    invariants_enforced=["INV-MEM-005"],
)

TMM_MEM_004 = MemoryMitigation(
    mitigation_id="TMM-MEM-004",
    name="Freeze Lock Enforcement",
    description="Frozen memory enforces immutability through mode check on all update paths.",
    threat_ids=["TMV-MEM-007"],
    status=MitigationStatus.IMPLEMENTED,
    implementation_notes="ShadowModeMemory.restore_snapshot() checks is_frozen() before any modification.",
    effectiveness="HIGH",
    cost="LOW",
    invariants_enforced=["INV-MEM-004"],
)

TMM_MEM_005 = MemoryMitigation(
    mitigation_id="TMM-MEM-005",
    name="Audit Trail Requirement",
    description="All memory updates must create MemoryUpdateRecord with pre/post hashes.",
    threat_ids=["TMV-MEM-001", "TMV-MEM-005"],
    status=MitigationStatus.IMPLEMENTED,
    implementation_notes="MemoryUpdateRecord created for every state transition.",
    effectiveness="MEDIUM",
    cost="LOW",
    invariants_enforced=["INV-MEM-002"],
)

TMM_MEM_006 = MemoryMitigation(
    mitigation_id="TMM-MEM-006",
    name="Shadow Mode Default",
    description="Memory system defaults to SHADOW mode, preventing inference and learning.",
    threat_ids=["TMV-MEM-002", "TMV-MEM-009", "TMV-MEM-011"],
    status=MitigationStatus.IMPLEMENTED,
    implementation_notes="ShadowModeMemory initializes with MemoryMode.SHADOW.",
    effectiveness="HIGH",
    cost="LOW",
    invariants_enforced=["INV-MEM-010", "INV-MEM-011", "INV-MEM-012"],
)

TMM_MEM_007 = MemoryMitigation(
    mitigation_id="TMM-MEM-007",
    name="Access Control Layer",
    description="Memory operations protected by role-based access control.",
    threat_ids=["TMV-MEM-004", "TMV-MEM-005", "TMV-MEM-006"],
    status=MitigationStatus.PLANNED,
    implementation_notes="To be implemented in production deployment phase.",
    effectiveness="HIGH",
    cost="MEDIUM",
)

TMM_MEM_008 = MemoryMitigation(
    mitigation_id="TMM-MEM-008",
    name="Rate Limiting",
    description="API rate limiting prevents bulk extraction and inference attacks.",
    threat_ids=["TMV-MEM-010", "TMV-MEM-011"],
    status=MitigationStatus.PLANNED,
    implementation_notes="To be implemented with API gateway.",
    effectiveness="MEDIUM",
    cost="LOW",
)

TMM_MEM_009 = MemoryMitigation(
    mitigation_id="TMM-MEM-009",
    name="Ledger Anchoring",
    description="Production snapshots anchored to immutable ledger for tamper detection.",
    threat_ids=["TMV-MEM-003", "TMV-MEM-006", "TMV-MEM-008"],
    status=MitigationStatus.PARTIAL,
    implementation_notes="MemorySnapshot.ledger_anchor field defined, anchoring in ATLAS deliverable.",
    effectiveness="HIGH",
    cost="MEDIUM",
    invariants_enforced=["INV-MEM-009"],
)

TMM_MEM_010 = MemoryMitigation(
    mitigation_id="TMM-MEM-010",
    name="Surprise Metric Obfuscation",
    description="Surprise metrics are quantized and noised before external exposure.",
    threat_ids=["TMV-MEM-012"],
    status=MitigationStatus.PLANNED,
    implementation_notes="To be implemented when inference mode is enabled.",
    effectiveness="MEDIUM",
    cost="LOW",
)


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT MODEL REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


class MemoryThreatModelRegistry:
    """
    Registry for memory threat model.

    Provides threat and mitigation lookup, coverage analysis, and risk scoring.
    """

    _instance: Optional["MemoryThreatModelRegistry"] = None
    _initialized: bool = False

    def __new__(cls) -> "MemoryThreatModelRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if MemoryThreatModelRegistry._initialized:
            return
        MemoryThreatModelRegistry._initialized = True

        self._threats: Dict[str, MemoryThreatVector] = {}
        self._mitigations: Dict[str, MemoryMitigation] = {}

        # Register P26 threats and mitigations
        self._register_p26_model()

    def _register_p26_model(self) -> None:
        """Register P26 threat model."""
        threats = [
            TMV_MEM_001, TMV_MEM_002, TMV_MEM_003,
            TMV_MEM_004, TMV_MEM_005, TMV_MEM_006,
            TMV_MEM_007, TMV_MEM_008, TMV_MEM_009,
            TMV_MEM_010, TMV_MEM_011, TMV_MEM_012,
        ]
        for threat in threats:
            self._threats[threat.threat_id] = threat

        mitigations = [
            TMM_MEM_001, TMM_MEM_002, TMM_MEM_003,
            TMM_MEM_004, TMM_MEM_005, TMM_MEM_006,
            TMM_MEM_007, TMM_MEM_008, TMM_MEM_009,
            TMM_MEM_010,
        ]
        for mitigation in mitigations:
            self._mitigations[mitigation.mitigation_id] = mitigation

    def get_threat(self, threat_id: str) -> Optional[MemoryThreatVector]:
        """Get threat by ID."""
        return self._threats.get(threat_id)

    def get_mitigation(self, mitigation_id: str) -> Optional[MemoryMitigation]:
        """Get mitigation by ID."""
        return self._mitigations.get(mitigation_id)

    def list_threats(self) -> List[MemoryThreatVector]:
        """List all threats."""
        return list(self._threats.values())

    def list_mitigations(self) -> List[MemoryMitigation]:
        """List all mitigations."""
        return list(self._mitigations.values())

    def list_by_category(self, category: ThreatCategory) -> List[MemoryThreatVector]:
        """List threats by category."""
        return [t for t in self._threats.values() if t.category == category]

    def list_by_severity(self, severity: ThreatSeverity) -> List[MemoryThreatVector]:
        """List threats by severity."""
        return [t for t in self._threats.values() if t.severity == severity]

    def get_mitigations_for_threat(self, threat_id: str) -> List[MemoryMitigation]:
        """Get mitigations that address a specific threat."""
        return [m for m in self._mitigations.values() if threat_id in m.threat_ids]

    def get_unmitigated_threats(self) -> List[MemoryThreatVector]:
        """Get threats with no implemented mitigations."""
        mitigated_ids = set()
        for m in self._mitigations.values():
            if m.status == MitigationStatus.IMPLEMENTED:
                mitigated_ids.update(m.threat_ids)
        return [t for t in self._threats.values() if t.threat_id not in mitigated_ids]

    def compute_coverage(self) -> Dict[str, Any]:
        """Compute mitigation coverage statistics."""
        total_threats = len(self._threats)
        implemented_mits = [m for m in self._mitigations.values() if m.status == MitigationStatus.IMPLEMENTED]
        mitigated_threat_ids = set()
        for m in implemented_mits:
            mitigated_threat_ids.update(m.threat_ids)

        return {
            "total_threats": total_threats,
            "total_mitigations": len(self._mitigations),
            "implemented_mitigations": len(implemented_mits),
            "mitigated_threats": len(mitigated_threat_ids),
            "coverage_percentage": round(len(mitigated_threat_ids) / total_threats * 100, 1) if total_threats > 0 else 0,
            "unmitigated_threat_ids": [t.threat_id for t in self._threats.values() if t.threat_id not in mitigated_threat_ids],
        }

    def threat_count(self) -> int:
        """Return count of registered threats."""
        return len(self._threats)

    def mitigation_count(self) -> int:
        """Return count of registered mitigations."""
        return len(self._mitigations)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "ThreatCategory",
    "ThreatSeverity",
    "MitigationStatus",
    "AttackVector",
    # Data classes
    "MemoryThreatVector",
    "MemoryMitigation",
    # Threat definitions
    "TMV_MEM_001", "TMV_MEM_002", "TMV_MEM_003",
    "TMV_MEM_004", "TMV_MEM_005", "TMV_MEM_006",
    "TMV_MEM_007", "TMV_MEM_008", "TMV_MEM_009",
    "TMV_MEM_010", "TMV_MEM_011", "TMV_MEM_012",
    # Mitigation definitions
    "TMM_MEM_001", "TMM_MEM_002", "TMM_MEM_003",
    "TMM_MEM_004", "TMM_MEM_005", "TMM_MEM_006",
    "TMM_MEM_007", "TMM_MEM_008", "TMM_MEM_009",
    "TMM_MEM_010",
    # Registry
    "MemoryThreatModelRegistry",
]
