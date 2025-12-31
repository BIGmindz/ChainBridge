# ═══════════════════════════════════════════════════════════════════════════════
# AML Shadow Threat Validator (SHADOW MODE)
# PAC-BENSON-P29: AML SHADOW PILOT EXECUTION
# Agent: SAM (GID-06)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Shadow Threat Validator — Threat Vector Validation for Pilot Scope

PURPOSE:
    Validate AML threat vectors against shadow pilot scope:
    - Identify applicable threats for pilot
    - Validate mitigation coverage
    - Generate threat assessment report

SCOPE:
    - Shadow pilot threats only
    - No production threat vectors
    - Focused on pilot components

LANE: SECURITY (SHADOW VALIDATION)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from core.security.aml_threat_model import (
    AttackVector,
    Mitigation,
    MitigationStatus,
    RiskLikelihood,
    ThreatCategory,
    ThreatSeverity,
    ThreatVector,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW PILOT SCOPE
# ═══════════════════════════════════════════════════════════════════════════════


class ShadowPilotComponent(Enum):
    """Components in shadow pilot scope."""

    CASE_ENGINE = "CASE_ENGINE"
    PATTERN_ANALYZER = "PATTERN_ANALYZER"
    TIER_ROUTER = "TIER_ROUTER"
    GUARDRAIL_ENGINE = "GUARDRAIL_ENGINE"
    PROOFPACK_SERVICE = "PROOFPACK_SERVICE"
    OCC_PANEL = "OCC_PANEL"
    SHADOW_ADAPTER = "SHADOW_ADAPTER"
    SIGNAL_EMITTER = "SIGNAL_EMITTER"


class ThreatApplicability(Enum):
    """Applicability of threat to shadow pilot."""

    FULLY_APPLICABLE = "FULLY_APPLICABLE"  # Threat applies in shadow
    PARTIALLY_APPLICABLE = "PARTIALLY_APPLICABLE"  # Some aspects apply
    NOT_APPLICABLE = "NOT_APPLICABLE"  # Does not apply in shadow
    DEFERRED = "DEFERRED"  # Deferred to production pilot


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ShadowThreatAssessment:
    """
    Assessment of a threat for shadow pilot.

    Captures threat applicability and mitigation status for pilot scope.
    """

    assessment_id: str
    threat_id: str
    threat_name: str
    applicability: ThreatApplicability
    shadow_components: List[ShadowPilotComponent]
    mitigation_status: str
    residual_risk: float
    notes: str
    assessed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.assessment_id.startswith("SHTA-"):
            raise ValueError(f"Assessment ID must start with 'SHTA-': {self.assessment_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "threat_id": self.threat_id,
            "threat_name": self.threat_name,
            "applicability": self.applicability.value,
            "shadow_components": [c.value for c in self.shadow_components],
            "mitigation_status": self.mitigation_status,
            "residual_risk": self.residual_risk,
            "notes": self.notes,
            "assessed_at": self.assessed_at,
        }


@dataclass
class ShadowMitigationControl:
    """
    Mitigation control for shadow pilot.

    Defines controls implemented in shadow pilot scope.
    """

    control_id: str
    name: str
    description: str
    control_type: str  # Preventive, Detective, Corrective
    threat_ids: List[str]
    status: MitigationStatus
    effectiveness: float
    shadow_only: bool = True  # True = only applies in shadow

    def __post_init__(self) -> None:
        if not self.control_id.startswith("SHCTL-"):
            raise ValueError(f"Control ID must start with 'SHCTL-': {self.control_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_id": self.control_id,
            "name": self.name,
            "description": self.description,
            "control_type": self.control_type,
            "threat_ids": self.threat_ids,
            "status": self.status.value,
            "effectiveness": self.effectiveness,
            "shadow_only": self.shadow_only,
        }


@dataclass
class ShadowPilotThreatReport:
    """
    Comprehensive threat report for shadow pilot.

    Aggregates all threat assessments and mitigation status.
    """

    report_id: str
    pilot_id: str
    generated_at: str
    total_threats: int = 0
    applicable_threats: int = 0
    mitigated_threats: int = 0
    residual_risks: List[Dict[str, Any]] = field(default_factory=list)
    assessments: List[ShadowThreatAssessment] = field(default_factory=list)
    controls: List[ShadowMitigationControl] = field(default_factory=list)
    overall_risk_score: float = 0.0
    recommendation: str = ""

    def __post_init__(self) -> None:
        if not self.report_id.startswith("SHTRPT-"):
            raise ValueError(f"Report ID must start with 'SHTRPT-': {self.report_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "pilot_id": self.pilot_id,
            "generated_at": self.generated_at,
            "total_threats": self.total_threats,
            "applicable_threats": self.applicable_threats,
            "mitigated_threats": self.mitigated_threats,
            "residual_risks": self.residual_risks,
            "assessments": [a.to_dict() for a in self.assessments],
            "controls": [c.to_dict() for c in self.controls],
            "overall_risk_score": self.overall_risk_score,
            "recommendation": self.recommendation,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW THREAT VECTORS
# ═══════════════════════════════════════════════════════════════════════════════


# Threats applicable to shadow pilot
SHADOW_TMV_DECISION_OVERRIDE = ThreatVector(
    threat_id="TMV-AML-001",
    name="Decision Override Attack",
    category=ThreatCategory.DECISION_INTEGRITY,
    severity=ThreatSeverity.CRITICAL,
    description="Attacker manipulates decision logic to force incorrect clearances",
    attack_vectors=[AttackVector.INTERNAL, AttackVector.API],
    impact="False negative - suspicious activity cleared incorrectly",
    likelihood=RiskLikelihood.POSSIBLE,
    preconditions=["Access to decision API", "Knowledge of tier logic"],
    affected_components=["TIER_ROUTER", "GUARDRAIL_ENGINE"],
    regulatory_impact="BSA/AML violation, regulatory enforcement",
    detection_indicators=["Unusual clearance patterns", "Tier boundary violations"],
)

SHADOW_TMV_THRESHOLD_GAMING = ThreatVector(
    threat_id="TMV-AML-003",
    name="Threshold Gaming",
    category=ThreatCategory.DATA_INTEGRITY,
    severity=ThreatSeverity.HIGH,
    description="Manipulating transaction data to stay below detection thresholds",
    attack_vectors=[AttackVector.EXTERNAL, AttackVector.DATA],
    impact="Structuring behavior evades detection",
    likelihood=RiskLikelihood.LIKELY,
    preconditions=["Knowledge of thresholds", "Control over transactions"],
    affected_components=["PATTERN_ANALYZER", "CASE_ENGINE"],
    regulatory_impact="Failure to detect structuring, BSA violation",
    detection_indicators=["Clustered amounts near thresholds", "Velocity anomalies"],
)

SHADOW_TMV_TIER_MANIPULATION = ThreatVector(
    threat_id="TMV-AML-006",
    name="Tier Manipulation",
    category=ThreatCategory.PROCESS_INTEGRITY,
    severity=ThreatSeverity.CRITICAL,
    description="Manipulating tier classification to auto-clear suspicious cases",
    attack_vectors=[AttackVector.INTERNAL, AttackVector.MODEL],
    impact="Tier-2+ cases incorrectly classified as Tier-0/1",
    likelihood=RiskLikelihood.UNLIKELY,
    preconditions=["Access to tier logic", "Knowledge of classification rules"],
    affected_components=["TIER_ROUTER", "CASE_ENGINE"],
    regulatory_impact="Critical BSA violation, potential enforcement action",
    detection_indicators=["Tier distribution anomalies", "Classification overrides"],
)

SHADOW_TMV_CONFIDENCE_POISONING = ThreatVector(
    threat_id="TMV-AML-007",
    name="Confidence Score Poisoning",
    category=ThreatCategory.MODEL_INTEGRITY,
    severity=ThreatSeverity.HIGH,
    description="Injecting data to skew confidence scores toward clearance",
    attack_vectors=[AttackVector.DATA, AttackVector.MODEL],
    impact="High-risk alerts receive low confidence scores",
    likelihood=RiskLikelihood.POSSIBLE,
    preconditions=["Access to training data or inference pipeline"],
    affected_components=["PATTERN_ANALYZER"],
    regulatory_impact="Model risk failure, regulatory scrutiny",
    detection_indicators=["Score distribution shifts", "Calibration drift"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW MITIGATION CONTROLS
# ═══════════════════════════════════════════════════════════════════════════════


SHCTL_TIER_GUARDRAILS = ShadowMitigationControl(
    control_id="SHCTL-001",
    name="Tier Boundary Guardrails",
    description="Hard blocks preventing Tier-2+ auto-clearance",
    control_type="Preventive",
    threat_ids=["TMV-AML-001", "TMV-AML-006"],
    status=MitigationStatus.IMPLEMENTED,
    effectiveness=0.95,
)

SHCTL_SHADOW_ISOLATION = ShadowMitigationControl(
    control_id="SHCTL-002",
    name="Shadow Mode Isolation",
    description="Complete isolation from production data and systems",
    control_type="Preventive",
    threat_ids=["TMV-AML-001", "TMV-AML-003", "TMV-AML-006", "TMV-AML-007"],
    status=MitigationStatus.IMPLEMENTED,
    effectiveness=1.0,
)

SHCTL_PROOFPACK_AUDIT = ShadowMitigationControl(
    control_id="SHCTL-003",
    name="ProofPack Audit Trail",
    description="Merkle-bound audit trail for all decisions",
    control_type="Detective",
    threat_ids=["TMV-AML-001", "TMV-AML-006"],
    status=MitigationStatus.IMPLEMENTED,
    effectiveness=0.90,
)

SHCTL_DETERMINISTIC_DATA = ShadowMitigationControl(
    control_id="SHCTL-004",
    name="Deterministic Shadow Data",
    description="All shadow data is synthetic and reproducible",
    control_type="Preventive",
    threat_ids=["TMV-AML-003", "TMV-AML-007"],
    status=MitigationStatus.IMPLEMENTED,
    effectiveness=1.0,
)

SHCTL_CONFIDENCE_THRESHOLD = ShadowMitigationControl(
    control_id="SHCTL-005",
    name="Confidence Threshold Enforcement",
    description="Minimum 95% confidence required for auto-clearance",
    control_type="Preventive",
    threat_ids=["TMV-AML-007"],
    status=MitigationStatus.IMPLEMENTED,
    effectiveness=0.85,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW THREAT VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════


class ShadowThreatValidator:
    """
    Validator for AML threats against shadow pilot scope.

    Assesses threat applicability and mitigation coverage
    for shadow pilot components.
    """

    # Threats in scope for shadow pilot
    SHADOW_THREATS: List[ThreatVector] = [
        SHADOW_TMV_DECISION_OVERRIDE,
        SHADOW_TMV_THRESHOLD_GAMING,
        SHADOW_TMV_TIER_MANIPULATION,
        SHADOW_TMV_CONFIDENCE_POISONING,
    ]

    # Controls implemented in shadow pilot
    SHADOW_CONTROLS: List[ShadowMitigationControl] = [
        SHCTL_TIER_GUARDRAILS,
        SHCTL_SHADOW_ISOLATION,
        SHCTL_PROOFPACK_AUDIT,
        SHCTL_DETERMINISTIC_DATA,
        SHCTL_CONFIDENCE_THRESHOLD,
    ]

    def __init__(self) -> None:
        """Initialize validator."""
        self._assessment_counter = 0
        self._report_counter = 0
        self._assessments: List[ShadowThreatAssessment] = []

    def _generate_assessment_id(self) -> str:
        """Generate unique assessment ID."""
        self._assessment_counter += 1
        return f"SHTA-{self._assessment_counter:08d}"

    def _generate_report_id(self) -> str:
        """Generate unique report ID."""
        self._report_counter += 1
        return f"SHTRPT-{self._report_counter:08d}"

    def assess_threat(self, threat: ThreatVector) -> ShadowThreatAssessment:
        """
        Assess a threat for shadow pilot applicability.

        Args:
            threat: Threat vector to assess

        Returns:
            Shadow threat assessment
        """
        # Map affected components to shadow components
        component_map = {
            "TIER_ROUTER": ShadowPilotComponent.TIER_ROUTER,
            "GUARDRAIL_ENGINE": ShadowPilotComponent.GUARDRAIL_ENGINE,
            "PATTERN_ANALYZER": ShadowPilotComponent.PATTERN_ANALYZER,
            "CASE_ENGINE": ShadowPilotComponent.CASE_ENGINE,
            "PROOFPACK_SERVICE": ShadowPilotComponent.PROOFPACK_SERVICE,
            "OCC_PANEL": ShadowPilotComponent.OCC_PANEL,
        }

        shadow_components = []
        for comp in threat.affected_components:
            if comp in component_map:
                shadow_components.append(component_map[comp])

        # Determine applicability
        if shadow_components:
            applicability = ThreatApplicability.FULLY_APPLICABLE
        else:
            applicability = ThreatApplicability.DEFERRED

        # Find applicable controls
        applicable_controls = [
            ctrl for ctrl in self.SHADOW_CONTROLS
            if threat.threat_id in ctrl.threat_ids
        ]

        # Calculate mitigation coverage
        if applicable_controls:
            avg_effectiveness = sum(c.effectiveness for c in applicable_controls) / len(applicable_controls)
            mitigation_status = "MITIGATED"
        else:
            avg_effectiveness = 0.0
            mitigation_status = "UNMITIGATED"

        # Calculate residual risk
        residual_risk = threat.risk_score * (1 - avg_effectiveness)

        assessment = ShadowThreatAssessment(
            assessment_id=self._generate_assessment_id(),
            threat_id=threat.threat_id,
            threat_name=threat.name,
            applicability=applicability,
            shadow_components=shadow_components,
            mitigation_status=mitigation_status,
            residual_risk=residual_risk,
            notes=f"Controls: {[c.control_id for c in applicable_controls]}",
        )

        self._assessments.append(assessment)
        return assessment

    def generate_pilot_report(self, pilot_id: str) -> ShadowPilotThreatReport:
        """
        Generate comprehensive threat report for shadow pilot.

        Args:
            pilot_id: Shadow pilot identifier

        Returns:
            Complete threat report
        """
        report = ShadowPilotThreatReport(
            report_id=self._generate_report_id(),
            pilot_id=pilot_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Assess all shadow threats
        for threat in self.SHADOW_THREATS:
            assessment = self.assess_threat(threat)
            report.assessments.append(assessment)

            if assessment.applicability in (
                ThreatApplicability.FULLY_APPLICABLE,
                ThreatApplicability.PARTIALLY_APPLICABLE,
            ):
                report.applicable_threats += 1

                if assessment.mitigation_status == "MITIGATED":
                    report.mitigated_threats += 1
                else:
                    report.residual_risks.append({
                        "threat_id": assessment.threat_id,
                        "residual_risk": assessment.residual_risk,
                    })

        report.total_threats = len(self.SHADOW_THREATS)
        report.controls = self.SHADOW_CONTROLS

        # Calculate overall risk score
        if report.assessments:
            report.overall_risk_score = sum(
                a.residual_risk for a in report.assessments
            ) / len(report.assessments)
        else:
            report.overall_risk_score = 0.0

        # Generate recommendation
        if report.overall_risk_score < 0.1:
            report.recommendation = "PROCEED - Low residual risk, adequate controls"
        elif report.overall_risk_score < 0.3:
            report.recommendation = "PROCEED_WITH_MONITORING - Monitor residual risks"
        else:
            report.recommendation = "REVIEW_REQUIRED - High residual risk, additional controls needed"

        return report

    def validate_mitigation_coverage(self) -> Dict[str, Any]:
        """
        Validate that all threats have mitigation coverage.

        Returns:
            Coverage analysis
        """
        coverage = {
            "total_threats": len(self.SHADOW_THREATS),
            "covered_threats": 0,
            "uncovered_threats": [],
            "coverage_rate": 0.0,
        }

        for threat in self.SHADOW_THREATS:
            controls = [c for c in self.SHADOW_CONTROLS if threat.threat_id in c.threat_ids]
            if controls:
                coverage["covered_threats"] += 1
            else:
                coverage["uncovered_threats"].append(threat.threat_id)

        coverage["coverage_rate"] = (
            coverage["covered_threats"] / coverage["total_threats"]
            if coverage["total_threats"] > 0
            else 0.0
        )

        return coverage

    def get_critical_threats(self) -> List[ThreatVector]:
        """Get all critical severity threats."""
        return [t for t in self.SHADOW_THREATS if t.severity == ThreatSeverity.CRITICAL]

    def get_high_risk_threats(self, threshold: float = 0.5) -> List[ThreatVector]:
        """Get threats with risk score above threshold."""
        return [t for t in self.SHADOW_THREATS if t.risk_score >= threshold]
