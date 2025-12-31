# ═══════════════════════════════════════════════════════════════════════════════
# AML Threat Model — Security Vectors & Mitigations
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# Agent: SAM (GID-06)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Threat Model — TMV-AML Security Analysis

PURPOSE:
    Define and catalog threat vectors specific to AML automation:
    - Model manipulation attacks
    - Alert suppression attacks
    - Threshold gaming
    - Entity obfuscation
    - Decision poisoning

CATALOG:
    TMV-AML-001: Decision Override Attack
    TMV-AML-002: Alert Suppression Injection
    TMV-AML-003: Threshold Gaming
    TMV-AML-004: Entity Confusion Attack
    TMV-AML-005: Evidence Tampering
    TMV-AML-006: Tier Manipulation
    TMV-AML-007: Confidence Score Poisoning
    TMV-AML-008: Audit Trail Manipulation

LANE: SECURITY (THREAT MODELING)
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
    """Category of AML threat."""

    DECISION_INTEGRITY = "DECISION_INTEGRITY"
    DATA_INTEGRITY = "DATA_INTEGRITY"
    MODEL_INTEGRITY = "MODEL_INTEGRITY"
    ACCESS_CONTROL = "ACCESS_CONTROL"
    AUDIT_INTEGRITY = "AUDIT_INTEGRITY"
    PROCESS_INTEGRITY = "PROCESS_INTEGRITY"


class ThreatSeverity(Enum):
    """Severity of threat."""

    CRITICAL = "CRITICAL"  # System-wide impact, regulatory exposure
    HIGH = "HIGH"  # Significant financial/reputational risk
    MEDIUM = "MEDIUM"  # Limited impact, contained risk
    LOW = "LOW"  # Minimal impact


class AttackVector(Enum):
    """Method of attack."""

    INTERNAL = "INTERNAL"  # Insider threat
    EXTERNAL = "EXTERNAL"  # External attacker
    API = "API"  # API manipulation
    DATA = "DATA"  # Data injection
    MODEL = "MODEL"  # Model manipulation
    SOCIAL = "SOCIAL"  # Social engineering


class MitigationStatus(Enum):
    """Status of mitigation."""

    IMPLEMENTED = "IMPLEMENTED"
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    NOT_STARTED = "NOT_STARTED"


class RiskLikelihood(Enum):
    """Likelihood of threat materialization."""

    ALMOST_CERTAIN = "ALMOST_CERTAIN"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    UNLIKELY = "UNLIKELY"
    RARE = "RARE"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ThreatVector:
    """
    AML-specific threat vector definition.

    Captures a specific security threat to the AML system.
    """

    threat_id: str
    name: str
    category: ThreatCategory
    severity: ThreatSeverity
    description: str
    attack_vectors: List[AttackVector]
    impact: str
    likelihood: RiskLikelihood
    preconditions: List[str]
    affected_components: List[str]
    regulatory_impact: str
    detection_indicators: List[str]

    def __post_init__(self) -> None:
        if not self.threat_id.startswith("TMV-AML-"):
            raise ValueError(f"Threat ID must start with 'TMV-AML-': {self.threat_id}")

    def compute_threat_hash(self) -> str:
        """Compute deterministic hash."""
        data = {
            "threat_id": self.threat_id,
            "name": self.name,
            "category": self.category.value,
            "severity": self.severity.value,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    @property
    def risk_score(self) -> float:
        """Compute risk score from severity and likelihood."""
        severity_scores = {
            ThreatSeverity.CRITICAL: 1.0,
            ThreatSeverity.HIGH: 0.75,
            ThreatSeverity.MEDIUM: 0.5,
            ThreatSeverity.LOW: 0.25,
        }
        likelihood_scores = {
            RiskLikelihood.ALMOST_CERTAIN: 1.0,
            RiskLikelihood.LIKELY: 0.8,
            RiskLikelihood.POSSIBLE: 0.6,
            RiskLikelihood.UNLIKELY: 0.4,
            RiskLikelihood.RARE: 0.2,
        }
        return severity_scores[self.severity] * likelihood_scores[self.likelihood]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threat_id": self.threat_id,
            "name": self.name,
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "attack_vectors": [av.value for av in self.attack_vectors],
            "impact": self.impact,
            "likelihood": self.likelihood.value,
            "risk_score": self.risk_score,
            "preconditions": self.preconditions,
            "affected_components": self.affected_components,
            "regulatory_impact": self.regulatory_impact,
            "detection_indicators": self.detection_indicators,
            "threat_hash": self.compute_threat_hash(),
        }


@dataclass
class Mitigation:
    """
    Mitigation control for a threat.

    Defines a specific countermeasure for an AML threat.
    """

    mitigation_id: str
    name: str
    description: str
    threat_ids: List[str]  # Threats this mitigates
    control_type: str  # Preventive, Detective, Corrective
    implementation: str
    status: MitigationStatus
    effectiveness: float  # 0.0 to 1.0
    owner: str
    verification_method: str

    def __post_init__(self) -> None:
        if not self.mitigation_id.startswith("MIT-AML-"):
            raise ValueError(f"Mitigation ID must start with 'MIT-AML-': {self.mitigation_id}")
        if not 0.0 <= self.effectiveness <= 1.0:
            raise ValueError(f"Effectiveness must be between 0.0 and 1.0: {self.effectiveness}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mitigation_id": self.mitigation_id,
            "name": self.name,
            "description": self.description,
            "threat_ids": self.threat_ids,
            "control_type": self.control_type,
            "implementation": self.implementation,
            "status": self.status.value,
            "effectiveness": self.effectiveness,
            "owner": self.owner,
            "verification_method": self.verification_method,
        }


@dataclass
class SecurityIncident:
    """
    Record of a security incident.

    Captures when a threat materialized or was detected.
    """

    incident_id: str
    threat_id: str
    timestamp: str
    severity: ThreatSeverity
    description: str
    affected_cases: List[str]
    detected_by: str
    response_actions: List[str]
    resolution_status: str
    root_cause: Optional[str] = None
    lessons_learned: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.incident_id.startswith("INC-AML-"):
            raise ValueError(f"Incident ID must start with 'INC-AML-': {self.incident_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "threat_id": self.threat_id,
            "timestamp": self.timestamp,
            "severity": self.severity.value,
            "description": self.description,
            "affected_cases": self.affected_cases,
            "detected_by": self.detected_by,
            "response_actions": self.response_actions,
            "resolution_status": self.resolution_status,
            "root_cause": self.root_cause,
            "lessons_learned": self.lessons_learned,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT THREAT VECTORS
# ═══════════════════════════════════════════════════════════════════════════════


TMV_AML_001 = ThreatVector(
    threat_id="TMV-AML-001",
    name="Decision Override Attack",
    category=ThreatCategory.DECISION_INTEGRITY,
    severity=ThreatSeverity.CRITICAL,
    description="Attacker manipulates system to auto-clear cases that should be escalated",
    attack_vectors=[AttackVector.INTERNAL, AttackVector.API],
    impact="High-risk cases cleared without review, regulatory violations",
    likelihood=RiskLikelihood.POSSIBLE,
    preconditions=[
        "Access to decision API",
        "Knowledge of tier boundaries",
        "Ability to modify case attributes",
    ],
    affected_components=["TierRouter", "AMLCaseEngine", "GuardrailEngine"],
    regulatory_impact="BSA/AML violations, potential enforcement action",
    detection_indicators=[
        "Unexpected tier downgrades",
        "Clearances with low evidence scores",
        "Bypass of guardrail checks",
    ],
)

TMV_AML_002 = ThreatVector(
    threat_id="TMV-AML-002",
    name="Alert Suppression Injection",
    category=ThreatCategory.DATA_INTEGRITY,
    severity=ThreatSeverity.CRITICAL,
    description="Attacker injects false evidence to suppress legitimate alerts",
    attack_vectors=[AttackVector.DATA, AttackVector.API],
    impact="Legitimate suspicious activity undetected",
    likelihood=RiskLikelihood.UNLIKELY,
    preconditions=[
        "Access to evidence intake",
        "Knowledge of clearing criteria",
        "Ability to forge evidence",
    ],
    affected_components=["EvidenceGraph", "AMLCaseEngine", "PatternAnalyzer"],
    regulatory_impact="Failure to detect and report suspicious activity",
    detection_indicators=[
        "Evidence added without proper source attribution",
        "Conflicting evidence patterns",
        "Unusual evidence timing",
    ],
)

TMV_AML_003 = ThreatVector(
    threat_id="TMV-AML-003",
    name="Threshold Gaming",
    category=ThreatCategory.PROCESS_INTEGRITY,
    severity=ThreatSeverity.HIGH,
    description="Attacker structures activity to stay below detection thresholds",
    attack_vectors=[AttackVector.EXTERNAL],
    impact="Suspicious activity evades detection rules",
    likelihood=RiskLikelihood.LIKELY,
    preconditions=[
        "Knowledge of detection thresholds",
        "Ability to control transaction amounts/timing",
    ],
    affected_components=["PatternAnalyzer", "PatternRule"],
    regulatory_impact="Structuring goes undetected",
    detection_indicators=[
        "Transactions clustered below thresholds",
        "Unusual transaction timing patterns",
        "Split transactions across accounts",
    ],
)

TMV_AML_004 = ThreatVector(
    threat_id="TMV-AML-004",
    name="Entity Confusion Attack",
    category=ThreatCategory.DATA_INTEGRITY,
    severity=ThreatSeverity.HIGH,
    description="Attacker creates ambiguity in entity resolution to evade detection",
    attack_vectors=[AttackVector.DATA, AttackVector.EXTERNAL],
    impact="Related entities not linked, network analysis fails",
    likelihood=RiskLikelihood.POSSIBLE,
    preconditions=[
        "Multiple entity identities",
        "Inconsistent identifying information",
    ],
    affected_components=["EvidenceGraph", "Entity", "Relationship"],
    regulatory_impact="Failure to identify beneficial ownership",
    detection_indicators=[
        "Multiple entities with similar attributes",
        "Frequent name/address changes",
        "Conflicting identifying information",
    ],
)

TMV_AML_005 = ThreatVector(
    threat_id="TMV-AML-005",
    name="Evidence Tampering",
    category=ThreatCategory.DATA_INTEGRITY,
    severity=ThreatSeverity.CRITICAL,
    description="Attacker modifies or deletes evidence to change case outcome",
    attack_vectors=[AttackVector.INTERNAL, AttackVector.API],
    impact="Corrupted evidence leads to wrong decisions",
    likelihood=RiskLikelihood.UNLIKELY,
    preconditions=[
        "Write access to evidence store",
        "Knowledge of evidence structure",
    ],
    affected_components=["EvidenceGraph", "CaseEvidence", "AMLCase"],
    regulatory_impact="Unreliable case documentation, audit failures",
    detection_indicators=[
        "Evidence hash mismatches",
        "Gaps in audit trail",
        "Evidence version conflicts",
    ],
)

TMV_AML_006 = ThreatVector(
    threat_id="TMV-AML-006",
    name="Tier Manipulation",
    category=ThreatCategory.DECISION_INTEGRITY,
    severity=ThreatSeverity.CRITICAL,
    description="Attacker manipulates tier classification to affect routing",
    attack_vectors=[AttackVector.INTERNAL, AttackVector.API],
    impact="Cases routed incorrectly, missed escalations",
    likelihood=RiskLikelihood.POSSIBLE,
    preconditions=[
        "Access to tier classification logic",
        "Ability to modify case tier",
    ],
    affected_components=["TierRouter", "TierCriteria", "GuardrailEngine"],
    regulatory_impact="High-risk cases not reviewed appropriately",
    detection_indicators=[
        "Tier changes without supporting evidence",
        "Tier downgrades near auto-clear boundary",
        "Guardrail bypass patterns",
    ],
)

TMV_AML_007 = ThreatVector(
    threat_id="TMV-AML-007",
    name="Confidence Score Poisoning",
    category=ThreatCategory.MODEL_INTEGRITY,
    severity=ThreatSeverity.HIGH,
    description="Attacker manipulates confidence scores to affect decisions",
    attack_vectors=[AttackVector.MODEL, AttackVector.DATA],
    impact="Cases cleared with artificially inflated confidence",
    likelihood=RiskLikelihood.UNLIKELY,
    preconditions=[
        "Access to confidence calculation",
        "Knowledge of scoring factors",
    ],
    affected_components=["AMLCaseEngine", "CaseDecision", "PatternAnalyzer"],
    regulatory_impact="Unreliable automated decisions",
    detection_indicators=[
        "Confidence scores inconsistent with evidence",
        "Confidence jumps without new evidence",
        "Statistical anomalies in confidence distribution",
    ],
)

TMV_AML_008 = ThreatVector(
    threat_id="TMV-AML-008",
    name="Audit Trail Manipulation",
    category=ThreatCategory.AUDIT_INTEGRITY,
    severity=ThreatSeverity.CRITICAL,
    description="Attacker modifies or deletes audit logs to hide activity",
    attack_vectors=[AttackVector.INTERNAL],
    impact="Evidence of attack or error destroyed",
    likelihood=RiskLikelihood.UNLIKELY,
    preconditions=[
        "Access to audit storage",
        "Ability to modify logs",
    ],
    affected_components=["AMLProofPack", "AuditLedger"],
    regulatory_impact="Unable to demonstrate compliance, failed examinations",
    detection_indicators=[
        "Gaps in audit sequence",
        "Hash chain breaks",
        "Missing expected log entries",
    ],
)


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT MITIGATIONS
# ═══════════════════════════════════════════════════════════════════════════════


MIT_AML_001 = Mitigation(
    mitigation_id="MIT-AML-001",
    name="Hard Guardrail Enforcement",
    description="Enforce hard blocks on tier-2+ auto-clearance at code level",
    threat_ids=["TMV-AML-001", "TMV-AML-006"],
    control_type="Preventive",
    implementation="GuardrailEngine.evaluate_clearance() with hard blocks",
    status=MitigationStatus.IMPLEMENTED,
    effectiveness=0.95,
    owner="PAX (GID-05)",
    verification_method="Unit tests verify guardrail enforcement",
)

MIT_AML_002 = Mitigation(
    mitigation_id="MIT-AML-002",
    name="Evidence Hash Verification",
    description="Compute and verify hashes on all evidence objects",
    threat_ids=["TMV-AML-002", "TMV-AML-005"],
    control_type="Detective",
    implementation="Hash computation on CaseEvidence and EvidenceNode",
    status=MitigationStatus.IMPLEMENTED,
    effectiveness=0.90,
    owner="ATLAS (GID-11)",
    verification_method="Integrity checks in ProofPack generation",
)

MIT_AML_003 = Mitigation(
    mitigation_id="MIT-AML-003",
    name="Multi-Rule Pattern Detection",
    description="Use multiple overlapping rules to detect threshold gaming",
    threat_ids=["TMV-AML-003"],
    control_type="Detective",
    implementation="PatternAnalyzer with complementary rules",
    status=MitigationStatus.IMPLEMENTED,
    effectiveness=0.75,
    owner="MAGGIE (GID-10)",
    verification_method="Pattern detection test coverage",
)

MIT_AML_004 = Mitigation(
    mitigation_id="MIT-AML-004",
    name="Entity Resolution Graph",
    description="Graph-based entity resolution to link related entities",
    threat_ids=["TMV-AML-004"],
    control_type="Detective",
    implementation="EvidenceGraph entity linking and relationship analysis",
    status=MitigationStatus.IMPLEMENTED,
    effectiveness=0.80,
    owner="CODY (GID-01)",
    verification_method="Entity resolution test cases",
)

MIT_AML_005 = Mitigation(
    mitigation_id="MIT-AML-005",
    name="Immutable Audit Ledger",
    description="Append-only ledger with Merkle tree integrity",
    threat_ids=["TMV-AML-008"],
    control_type="Detective",
    implementation="AMLProofPack with Merkle anchoring",
    status=MitigationStatus.PLANNED,
    effectiveness=0.95,
    owner="ATLAS (GID-11)",
    verification_method="Ledger integrity verification tests",
)

MIT_AML_006 = Mitigation(
    mitigation_id="MIT-AML-006",
    name="Confidence Bound Checks",
    description="Require confidence scores within valid bounds and evidence support",
    threat_ids=["TMV-AML-007"],
    control_type="Preventive",
    implementation="Confidence validation in CaseDecision",
    status=MitigationStatus.IMPLEMENTED,
    effectiveness=0.85,
    owner="CODY (GID-01)",
    verification_method="Confidence bounds unit tests",
)

MIT_AML_007 = Mitigation(
    mitigation_id="MIT-AML-007",
    name="Tier Classification Audit",
    description="Log all tier changes with justification and reviewer",
    threat_ids=["TMV-AML-006"],
    control_type="Detective",
    implementation="TierRouter logs all routing decisions",
    status=MitigationStatus.IMPLEMENTED,
    effectiveness=0.85,
    owner="DAN (GID-07)",
    verification_method="Audit log review tests",
)


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT MODEL SERVICE
# ═══════════════════════════════════════════════════════════════════════════════


class AMLThreatModel:
    """
    AML Threat Model management service.

    Provides:
    - Threat catalog management
    - Mitigation tracking
    - Risk assessment
    - Incident recording
    """

    def __init__(self) -> None:
        self._threats: Dict[str, ThreatVector] = {}
        self._mitigations: Dict[str, Mitigation] = {}
        self._incidents: List[SecurityIncident] = []
        self._incident_counter = 0

        # Load defaults
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default threats and mitigations."""
        for threat in [
            TMV_AML_001,
            TMV_AML_002,
            TMV_AML_003,
            TMV_AML_004,
            TMV_AML_005,
            TMV_AML_006,
            TMV_AML_007,
            TMV_AML_008,
        ]:
            self._threats[threat.threat_id] = threat

        for mitigation in [
            MIT_AML_001,
            MIT_AML_002,
            MIT_AML_003,
            MIT_AML_004,
            MIT_AML_005,
            MIT_AML_006,
            MIT_AML_007,
        ]:
            self._mitigations[mitigation.mitigation_id] = mitigation

    # ───────────────────────────────────────────────────────────────────────────
    # THREAT QUERIES
    # ───────────────────────────────────────────────────────────────────────────

    def get_threat(self, threat_id: str) -> Optional[ThreatVector]:
        """Get threat by ID."""
        return self._threats.get(threat_id)

    def list_threats(self) -> List[ThreatVector]:
        """List all threats."""
        return list(self._threats.values())

    def get_threats_by_category(self, category: ThreatCategory) -> List[ThreatVector]:
        """Get threats by category."""
        return [t for t in self._threats.values() if t.category == category]

    def get_critical_threats(self) -> List[ThreatVector]:
        """Get critical severity threats."""
        return [t for t in self._threats.values() if t.severity == ThreatSeverity.CRITICAL]

    def get_threats_by_component(self, component: str) -> List[ThreatVector]:
        """Get threats affecting a specific component."""
        return [t for t in self._threats.values() if component in t.affected_components]

    # ───────────────────────────────────────────────────────────────────────────
    # MITIGATION QUERIES
    # ───────────────────────────────────────────────────────────────────────────

    def get_mitigation(self, mitigation_id: str) -> Optional[Mitigation]:
        """Get mitigation by ID."""
        return self._mitigations.get(mitigation_id)

    def list_mitigations(self) -> List[Mitigation]:
        """List all mitigations."""
        return list(self._mitigations.values())

    def get_mitigations_for_threat(self, threat_id: str) -> List[Mitigation]:
        """Get mitigations for a specific threat."""
        return [m for m in self._mitigations.values() if threat_id in m.threat_ids]

    def get_implemented_mitigations(self) -> List[Mitigation]:
        """Get implemented mitigations."""
        return [m for m in self._mitigations.values() if m.status == MitigationStatus.IMPLEMENTED]

    # ───────────────────────────────────────────────────────────────────────────
    # RISK ASSESSMENT
    # ───────────────────────────────────────────────────────────────────────────

    def compute_residual_risk(self, threat_id: str) -> float:
        """
        Compute residual risk for a threat after mitigations.

        Residual risk = inherent risk * (1 - mitigation effectiveness)
        """
        threat = self.get_threat(threat_id)
        if threat is None:
            return 0.0

        inherent_risk = threat.risk_score
        mitigations = self.get_mitigations_for_threat(threat_id)

        if not mitigations:
            return inherent_risk

        # Compute combined effectiveness
        implemented = [m for m in mitigations if m.status == MitigationStatus.IMPLEMENTED]
        if not implemented:
            return inherent_risk

        # Combined effectiveness: 1 - product of (1 - effectiveness)
        complement_product = 1.0
        for m in implemented:
            complement_product *= (1.0 - m.effectiveness)
        combined_effectiveness = 1.0 - complement_product

        return inherent_risk * (1.0 - combined_effectiveness)

    def get_risk_matrix(self) -> Dict[str, Any]:
        """Generate risk matrix for all threats."""
        matrix = []
        for threat in self._threats.values():
            residual = self.compute_residual_risk(threat.threat_id)
            matrix.append({
                "threat_id": threat.threat_id,
                "name": threat.name,
                "category": threat.category.value,
                "severity": threat.severity.value,
                "likelihood": threat.likelihood.value,
                "inherent_risk": threat.risk_score,
                "residual_risk": residual,
                "mitigation_count": len(self.get_mitigations_for_threat(threat.threat_id)),
            })
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "threats": sorted(matrix, key=lambda x: x["residual_risk"], reverse=True),
        }

    # ───────────────────────────────────────────────────────────────────────────
    # INCIDENT MANAGEMENT
    # ───────────────────────────────────────────────────────────────────────────

    def record_incident(
        self,
        threat_id: str,
        description: str,
        affected_cases: List[str],
        detected_by: str,
        response_actions: List[str],
    ) -> SecurityIncident:
        """Record a security incident."""
        self._incident_counter += 1
        threat = self.get_threat(threat_id)

        incident = SecurityIncident(
            incident_id=f"INC-AML-{self._incident_counter:06d}",
            threat_id=threat_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity=threat.severity if threat else ThreatSeverity.MEDIUM,
            description=description,
            affected_cases=affected_cases,
            detected_by=detected_by,
            response_actions=response_actions,
            resolution_status="OPEN",
        )

        self._incidents.append(incident)
        return incident

    def list_incidents(self) -> List[SecurityIncident]:
        """List all incidents."""
        return self._incidents.copy()

    def get_open_incidents(self) -> List[SecurityIncident]:
        """Get open incidents."""
        return [i for i in self._incidents if i.resolution_status == "OPEN"]

    # ───────────────────────────────────────────────────────────────────────────
    # REPORTING
    # ───────────────────────────────────────────────────────────────────────────

    def generate_report(self) -> Dict[str, Any]:
        """Generate threat model status report."""
        threats_by_severity: Dict[str, int] = {}
        for severity in ThreatSeverity:
            threats_by_severity[severity.value] = len([
                t for t in self._threats.values() if t.severity == severity
            ])

        mitigations_by_status: Dict[str, int] = {}
        for status in MitigationStatus:
            mitigations_by_status[status.value] = len([
                m for m in self._mitigations.values() if m.status == status
            ])

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_threats": len(self._threats),
            "total_mitigations": len(self._mitigations),
            "total_incidents": len(self._incidents),
            "open_incidents": len(self.get_open_incidents()),
            "threats_by_severity": threats_by_severity,
            "mitigations_by_status": mitigations_by_status,
            "critical_threats": len(self.get_critical_threats()),
            "average_residual_risk": sum(
                self.compute_residual_risk(t.threat_id) for t in self._threats.values()
            ) / len(self._threats) if self._threats else 0.0,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "ThreatCategory",
    "ThreatSeverity",
    "AttackVector",
    "MitigationStatus",
    "RiskLikelihood",
    # Data Classes
    "ThreatVector",
    "Mitigation",
    "SecurityIncident",
    # Service
    "AMLThreatModel",
    # Default Threats
    "TMV_AML_001",
    "TMV_AML_002",
    "TMV_AML_003",
    "TMV_AML_004",
    "TMV_AML_005",
    "TMV_AML_006",
    "TMV_AML_007",
    "TMV_AML_008",
    # Default Mitigations
    "MIT_AML_001",
    "MIT_AML_002",
    "MIT_AML_003",
    "MIT_AML_004",
    "MIT_AML_005",
    "MIT_AML_006",
    "MIT_AML_007",
]
