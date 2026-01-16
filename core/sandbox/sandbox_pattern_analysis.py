"""
Sandbox Pattern Analysis - Read-Only Pattern Clustering Engine
PAC-P752-GOV-SANDBOX-GOVERNANCE-EVOLUTION
TASK-03: Pattern Clustering Engine (GID-03)

Analyzes sandbox PDO records to identify:
- Invariant gaps (rules that should exist but don't)
- Proof schema ambiguities (unclear evidence requirements)
- Decision pattern anomalies (inconsistent governance)

CRITICAL: This engine operates in READ-ONLY mode.
No production systems may be modified.

Core Law: Sandbox observes. Humans decide. Production evolves only through PAC.

INVARIANTS ENFORCED:
- INV-SDGE-001: Sandbox data SHALL NOT modify production logic directly
- INV-SDGE-003: Audit trail completeness mandatory
"""

from __future__ import annotations

import json
import secrets
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pathlib import Path


class PatternType(Enum):
    """Types of patterns detected in sandbox data."""
    INVARIANT_GAP = "INVARIANT_GAP"
    PROOF_AMBIGUITY = "PROOF_AMBIGUITY"
    DECISION_INCONSISTENCY = "DECISION_INCONSISTENCY"
    OUTCOME_ANOMALY = "OUTCOME_ANOMALY"
    RULE_OVERLAP = "RULE_OVERLAP"
    COVERAGE_GAP = "COVERAGE_GAP"


class Severity(Enum):
    """Severity levels for detected patterns."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class DetectedPattern:
    """A pattern detected through sandbox analysis."""
    pattern_id: str
    pattern_type: PatternType
    severity: Severity
    description: str
    evidence: dict[str, Any]
    affected_invariants: list[str]
    occurrence_count: int
    confidence: float
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "evidence": self.evidence,
            "affected_invariants": self.affected_invariants,
            "occurrence_count": self.occurrence_count,
            "confidence": self.confidence,
            "detected_at": self.detected_at.isoformat(),
            "recommendations": self.recommendations
        }


@dataclass
class PatternCluster:
    """A cluster of related patterns."""
    cluster_id: str
    cluster_name: str
    patterns: list[DetectedPattern]
    aggregate_severity: Severity
    governance_impact: str
    proposed_action: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "cluster_name": self.cluster_name,
            "pattern_count": len(self.patterns),
            "patterns": [p.to_dict() for p in self.patterns],
            "aggregate_severity": self.aggregate_severity.value,
            "governance_impact": self.governance_impact,
            "proposed_action": self.proposed_action,
            "created_at": self.created_at.isoformat()
        }


class SandboxPatternAnalyzer:
    """
    READ-ONLY pattern analysis engine for sandbox PDO data.
    
    Core Law: Sandbox observes. Humans decide. Production evolves only through PAC.
    
    This analyzer:
    - Reads PDO records from sandbox collector
    - Identifies governance patterns
    - Generates analysis reports
    - NEVER modifies production systems
    """

    ACCESS_MODE = "READ_ONLY"
    PRODUCTION_WRITE = False

    def __init__(self):
        self._patterns: list[DetectedPattern] = []
        self._clusters: list[PatternCluster] = []
        self._analysis_log: list[dict[str, Any]] = []

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}-{secrets.token_hex(6).upper()}"

    def _log_analysis(self, event: str, details: dict[str, Any]) -> None:
        self._analysis_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": details,
            "access_mode": self.ACCESS_MODE,
            "production_write": self.PRODUCTION_WRITE
        })

    def analyze_invariant_gaps(self, pdo_records: list[dict[str, Any]]) -> list[DetectedPattern]:
        """
        Detect invariant gaps - rules that should exist but don't.
        
        Analyzes blocked attempts to find missing governance coverage.
        """
        patterns = []
        
        # Group blocked attempts by block reason
        block_reasons: dict[str, list[dict]] = defaultdict(list)
        for record in pdo_records:
            if record.get("decision", {}).get("decision_type") == "BLOCKED":
                evidence = record.get("proof", {}).get("evidence", {})
                for reason in evidence.get("block_reasons", []):
                    block_reasons[reason].append(record)

        # Find reasons without corresponding invariants
        known_invariants = set()
        for record in pdo_records:
            known_invariants.update(record.get("proof", {}).get("invariants_checked", []))

        for reason, records in block_reasons.items():
            if len(records) >= 3:  # Threshold for pattern significance
                # Check if there's a formal invariant for this block reason
                has_invariant = any(
                    reason.lower() in inv.lower() 
                    for inv in known_invariants
                )
                
                if not has_invariant:
                    pattern = DetectedPattern(
                        pattern_id=self._generate_id("PAT"),
                        pattern_type=PatternType.INVARIANT_GAP,
                        severity=Severity.HIGH if len(records) > 10 else Severity.MEDIUM,
                        description=f"Block reason '{reason}' has no formal invariant",
                        evidence={
                            "block_reason": reason,
                            "occurrence_count": len(records),
                            "sample_pdo_ids": [r["pdo_id"] for r in records[:5]]
                        },
                        affected_invariants=[],
                        occurrence_count=len(records),
                        confidence=min(len(records) / 20, 1.0),
                        recommendations=[
                            f"Consider formalizing invariant for: {reason}",
                            "Review blocked attempts for governance coverage"
                        ]
                    )
                    patterns.append(pattern)

        self._log_analysis("INVARIANT_GAP_ANALYSIS", {
            "records_analyzed": len(pdo_records),
            "patterns_found": len(patterns)
        })

        return patterns

    def analyze_proof_ambiguities(self, pdo_records: list[dict[str, Any]]) -> list[DetectedPattern]:
        """
        Detect proof schema ambiguities - unclear evidence requirements.
        
        Finds cases where proof structure varies for same decision type.
        """
        patterns = []
        
        # Group proofs by type
        proof_schemas: dict[str, list[set]] = defaultdict(list)
        for record in pdo_records:
            proof = record.get("proof", {})
            proof_type = proof.get("proof_type", "UNKNOWN")
            evidence_keys = set(proof.get("evidence", {}).keys())
            proof_schemas[proof_type].append(evidence_keys)

        # Find inconsistent schemas
        for proof_type, schemas in proof_schemas.items():
            if len(schemas) < 3:
                continue
                
            # Check for schema variation
            all_keys = set()
            for schema in schemas:
                all_keys.update(schema)
            
            common_keys = set.intersection(*schemas) if schemas else set()
            
            if len(common_keys) < len(all_keys) * 0.5:  # High variation
                pattern = DetectedPattern(
                    pattern_id=self._generate_id("PAT"),
                    pattern_type=PatternType.PROOF_AMBIGUITY,
                    severity=Severity.MEDIUM,
                    description=f"Proof type '{proof_type}' has inconsistent schema",
                    evidence={
                        "proof_type": proof_type,
                        "common_keys": list(common_keys),
                        "all_keys": list(all_keys),
                        "variation_count": len(schemas)
                    },
                    affected_invariants=["INV-SDGE-003"],
                    occurrence_count=len(schemas),
                    confidence=1.0 - (len(common_keys) / max(len(all_keys), 1)),
                    recommendations=[
                        f"Standardize proof schema for: {proof_type}",
                        "Define required evidence fields"
                    ]
                )
                patterns.append(pattern)

        self._log_analysis("PROOF_AMBIGUITY_ANALYSIS", {
            "proof_types_analyzed": len(proof_schemas),
            "patterns_found": len(patterns)
        })

        return patterns

    def analyze_decision_inconsistencies(self, pdo_records: list[dict[str, Any]]) -> list[DetectedPattern]:
        """
        Detect decision inconsistencies - similar inputs with different decisions.
        """
        patterns = []
        
        # Group by invariants checked
        decision_groups: dict[tuple, list] = defaultdict(list)
        for record in pdo_records:
            invariants = tuple(sorted(record.get("proof", {}).get("invariants_checked", [])))
            decision_type = record.get("decision", {}).get("decision_type")
            decision_groups[invariants].append({
                "decision_type": decision_type,
                "pdo_id": record.get("pdo_id")
            })

        # Find inconsistent decisions
        for invariants, decisions in decision_groups.items():
            if len(decisions) < 5:
                continue
                
            decision_types = Counter(d["decision_type"] for d in decisions)
            
            if len(decision_types) > 1:
                majority_type = decision_types.most_common(1)[0][0]
                minority_count = sum(c for t, c in decision_types.items() if t != majority_type)
                
                if minority_count >= 2:  # At least 2 inconsistent decisions
                    pattern = DetectedPattern(
                        pattern_id=self._generate_id("PAT"),
                        pattern_type=PatternType.DECISION_INCONSISTENCY,
                        severity=Severity.HIGH,
                        description=f"Inconsistent decisions for invariants: {invariants}",
                        evidence={
                            "invariants": list(invariants),
                            "decision_distribution": dict(decision_types),
                            "inconsistent_count": minority_count
                        },
                        affected_invariants=list(invariants),
                        occurrence_count=len(decisions),
                        confidence=minority_count / len(decisions),
                        recommendations=[
                            "Review decision logic for consistency",
                            "Consider additional context factors"
                        ]
                    )
                    patterns.append(pattern)

        self._log_analysis("DECISION_INCONSISTENCY_ANALYSIS", {
            "groups_analyzed": len(decision_groups),
            "patterns_found": len(patterns)
        })

        return patterns

    def analyze_coverage_gaps(self, pdo_records: list[dict[str, Any]], known_invariants: list[str]) -> list[DetectedPattern]:
        """
        Detect coverage gaps - invariants never exercised in sandbox.
        """
        patterns = []
        
        # Find which invariants were actually checked
        exercised = set()
        for record in pdo_records:
            exercised.update(record.get("proof", {}).get("invariants_checked", []))

        # Find never-exercised invariants
        never_exercised = set(known_invariants) - exercised
        
        for invariant in never_exercised:
            pattern = DetectedPattern(
                pattern_id=self._generate_id("PAT"),
                pattern_type=PatternType.COVERAGE_GAP,
                severity=Severity.MEDIUM,
                description=f"Invariant '{invariant}' never exercised in sandbox",
                evidence={
                    "invariant": invariant,
                    "total_records": len(pdo_records),
                    "exercised_invariants": len(exercised)
                },
                affected_invariants=[invariant],
                occurrence_count=0,
                confidence=1.0,
                recommendations=[
                    f"Create sandbox scenarios that exercise: {invariant}",
                    "Verify invariant is still relevant"
                ]
            )
            patterns.append(pattern)

        self._log_analysis("COVERAGE_GAP_ANALYSIS", {
            "known_invariants": len(known_invariants),
            "exercised": len(exercised),
            "gaps_found": len(patterns)
        })

        return patterns

    def run_full_analysis(
        self,
        pdo_records: list[dict[str, Any]],
        known_invariants: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Run complete pattern analysis on sandbox data.
        
        Returns analysis report with all detected patterns.
        """
        self._log_analysis("FULL_ANALYSIS_STARTED", {
            "record_count": len(pdo_records)
        })

        # Run all analyzers
        gap_patterns = self.analyze_invariant_gaps(pdo_records)
        ambiguity_patterns = self.analyze_proof_ambiguities(pdo_records)
        inconsistency_patterns = self.analyze_decision_inconsistencies(pdo_records)
        
        coverage_patterns = []
        if known_invariants:
            coverage_patterns = self.analyze_coverage_gaps(pdo_records, known_invariants)

        all_patterns = gap_patterns + ambiguity_patterns + inconsistency_patterns + coverage_patterns
        self._patterns.extend(all_patterns)

        # Create clusters
        clusters = self._create_clusters(all_patterns)
        self._clusters.extend(clusters)

        self._log_analysis("FULL_ANALYSIS_COMPLETED", {
            "total_patterns": len(all_patterns),
            "clusters_created": len(clusters)
        })

        return {
            "analysis_id": self._generate_id("ANALYSIS"),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "access_mode": self.ACCESS_MODE,
            "production_write": self.PRODUCTION_WRITE,
            "records_analyzed": len(pdo_records),
            "summary": {
                "invariant_gaps": len(gap_patterns),
                "proof_ambiguities": len(ambiguity_patterns),
                "decision_inconsistencies": len(inconsistency_patterns),
                "coverage_gaps": len(coverage_patterns),
                "total_patterns": len(all_patterns),
                "clusters": len(clusters)
            },
            "patterns": [p.to_dict() for p in all_patterns],
            "clusters": [c.to_dict() for c in clusters]
        }

    def _create_clusters(self, patterns: list[DetectedPattern]) -> list[PatternCluster]:
        """Group related patterns into clusters."""
        clusters = []
        
        # Cluster by pattern type
        by_type: dict[PatternType, list[DetectedPattern]] = defaultdict(list)
        for pattern in patterns:
            by_type[pattern.pattern_type].append(pattern)

        for pattern_type, type_patterns in by_type.items():
            if not type_patterns:
                continue
                
            # Determine aggregate severity
            severities = [p.severity for p in type_patterns]
            if Severity.CRITICAL in severities:
                agg_severity = Severity.CRITICAL
            elif Severity.HIGH in severities:
                agg_severity = Severity.HIGH
            else:
                agg_severity = Severity.MEDIUM

            cluster = PatternCluster(
                cluster_id=self._generate_id("CLUSTER"),
                cluster_name=f"{pattern_type.value} Cluster",
                patterns=type_patterns,
                aggregate_severity=agg_severity,
                governance_impact=f"{len(type_patterns)} patterns affecting governance rules",
                proposed_action=f"Review and address {pattern_type.value.lower().replace('_', ' ')} issues"
            )
            clusters.append(cluster)

        return clusters

    def export(self) -> dict[str, Any]:
        """Export analyzer state."""
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "access_mode": self.ACCESS_MODE,
            "production_write": self.PRODUCTION_WRITE,
            "patterns": [p.to_dict() for p in self._patterns],
            "clusters": [c.to_dict() for c in self._clusters],
            "analysis_log_size": len(self._analysis_log)
        }


# Singleton instance
_pattern_analyzer: Optional[SandboxPatternAnalyzer] = None


def get_sandbox_pattern_analyzer() -> SandboxPatternAnalyzer:
    """Get global pattern analyzer instance."""
    global _pattern_analyzer
    if _pattern_analyzer is None:
        _pattern_analyzer = SandboxPatternAnalyzer()
    return _pattern_analyzer
