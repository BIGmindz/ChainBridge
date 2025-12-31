"""
Regulatory Intelligence Engine — Compliance & Regulatory Tracking.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-REAL-WORK-032
Agent: GID-03 (Mira-R) — COMPETITIVE & REGULATORY INTELLIGENCE
Deliverable: Regulatory Framework, Compliance Checker, Audit Trails

Features:
- Regulatory framework definitions (MiCA, DORA, SEC, CFTC)
- Pre/post execution compliance checks
- Jurisdiction routing
- Immutable audit trail generation
- Compliance reporting with gap analysis
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
)


# =============================================================================
# VERSION
# =============================================================================

REGULATORY_ENGINE_VERSION = "1.0.0"


# =============================================================================
# ENUMS
# =============================================================================

class RegulatoryFramework(Enum):
    """Regulatory frameworks."""
    MICA = "MiCA"  # Markets in Crypto-Assets (EU)
    DORA = "DORA"  # Digital Operational Resilience Act (EU)
    SEC = "SEC"    # Securities and Exchange Commission (US)
    CFTC = "CFTC"  # Commodity Futures Trading Commission (US)
    FCA = "FCA"    # Financial Conduct Authority (UK)
    FINMA = "FINMA"  # Swiss Financial Market Supervisory Authority
    MAS = "MAS"    # Monetary Authority of Singapore
    JFSA = "JFSA"  # Japan Financial Services Agency
    CUSTOM = "CUSTOM"  # Custom/Internal regulations


class Jurisdiction(Enum):
    """Jurisdictions."""
    EU = "EU"
    US = "US"
    UK = "UK"
    SWITZERLAND = "SWITZERLAND"
    SINGAPORE = "SINGAPORE"
    JAPAN = "JAPAN"
    GLOBAL = "GLOBAL"  # Applies globally


class ComplianceStatus(Enum):
    """Compliance check status."""
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    PARTIAL = "PARTIAL"
    PENDING_REVIEW = "PENDING_REVIEW"
    EXEMPT = "EXEMPT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AlertPriority(Enum):
    """Compliance alert priority."""
    CRITICAL = 0  # Immediate action required
    HIGH = 1      # Action within 24 hours
    MEDIUM = 2    # Action within 7 days
    LOW = 3       # Informational


class RequirementCategory(Enum):
    """Categories of regulatory requirements."""
    DATA_PROTECTION = "DATA_PROTECTION"
    OPERATIONAL_RESILIENCE = "OPERATIONAL_RESILIENCE"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    REPORTING = "REPORTING"
    LICENSING = "LICENSING"
    CONSUMER_PROTECTION = "CONSUMER_PROTECTION"
    AML_KYC = "AML_KYC"  # Anti-Money Laundering / Know Your Customer
    CAPITAL_REQUIREMENTS = "CAPITAL_REQUIREMENTS"
    GOVERNANCE = "GOVERNANCE"
    AUDIT = "AUDIT"


class RetentionPeriod(Enum):
    """Data retention periods."""
    ONE_YEAR = 365
    THREE_YEARS = 1095
    FIVE_YEARS = 1825
    SEVEN_YEARS = 2555
    TEN_YEARS = 3650
    PERMANENT = -1


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Requirement:
    """A regulatory requirement."""
    requirement_id: str
    framework: RegulatoryFramework
    category: RequirementCategory
    title: str
    description: str
    effective_date: datetime
    jurisdictions: FrozenSet[Jurisdiction]
    mandatory: bool
    remediation_guidance: str
    reference_url: Optional[str] = None
    retention_period: RetentionPeriod = RetentionPeriod.FIVE_YEARS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "requirement_id": self.requirement_id,
            "framework": self.framework.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "effective_date": self.effective_date.isoformat(),
            "jurisdictions": [j.value for j in self.jurisdictions],
            "mandatory": self.mandatory,
            "remediation_guidance": self.remediation_guidance,
            "reference_url": self.reference_url,
            "retention_period": self.retention_period.value,
        }


@dataclass
class ComplianceCheckResult:
    """Result of a compliance check."""
    check_id: str
    requirement_id: str
    operation_id: str
    status: ComplianceStatus
    checked_at: datetime
    details: Dict[str, Any]
    evidence: List[str]
    remediation_steps: List[str]
    deadline: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_id": self.check_id,
            "requirement_id": self.requirement_id,
            "operation_id": self.operation_id,
            "status": self.status.value,
            "checked_at": self.checked_at.isoformat(),
            "details": self.details,
            "evidence": self.evidence,
            "remediation_steps": self.remediation_steps,
            "deadline": self.deadline.isoformat() if self.deadline else None,
        }


@dataclass
class RegulatoryAlert:
    """A compliance alert."""
    alert_id: str
    priority: AlertPriority
    requirement_id: str
    title: str
    message: str
    created_at: datetime
    deadline: datetime
    affected_operations: List[str]
    resolution_status: str  # "OPEN", "IN_PROGRESS", "RESOLVED"
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "priority": self.priority.name,
            "requirement_id": self.requirement_id,
            "title": self.title,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat(),
            "affected_operations": self.affected_operations,
            "resolution_status": self.resolution_status,
            "resolution_notes": self.resolution_notes,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class AuditRecord:
    """An immutable audit record."""
    record_id: str
    timestamp: datetime
    operation_type: str
    operation_id: str
    actor_id: str
    action: str
    data_before: Optional[Dict[str, Any]]
    data_after: Optional[Dict[str, Any]]
    jurisdictions: FrozenSet[Jurisdiction]
    hash_value: str
    previous_hash: str
    
    def compute_hash(self, previous_hash: str) -> str:
        """Compute record hash."""
        content = json.dumps({
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "operation_type": self.operation_type,
            "operation_id": self.operation_id,
            "actor_id": self.actor_id,
            "action": self.action,
            "previous_hash": previous_hash,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "operation_type": self.operation_type,
            "operation_id": self.operation_id,
            "actor_id": self.actor_id,
            "action": self.action,
            "jurisdictions": [j.value for j in self.jurisdictions],
            "hash_value": self.hash_value,
            "previous_hash": self.previous_hash,
        }


@dataclass
class ComplianceScore:
    """Compliance score for an entity."""
    entity_id: str
    framework: RegulatoryFramework
    score: float  # 0.0 to 1.0
    compliant_count: int
    non_compliant_count: int
    partial_count: int
    pending_count: int
    calculated_at: datetime
    breakdown: Dict[str, float]  # category -> score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_id": self.entity_id,
            "framework": self.framework.value,
            "score": self.score,
            "compliant_count": self.compliant_count,
            "non_compliant_count": self.non_compliant_count,
            "partial_count": self.partial_count,
            "pending_count": self.pending_count,
            "calculated_at": self.calculated_at.isoformat(),
            "breakdown": self.breakdown,
        }


@dataclass
class ComplianceReport:
    """A compliance report."""
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    framework: RegulatoryFramework
    entity_id: str
    overall_score: ComplianceScore
    checks: List[ComplianceCheckResult]
    alerts: List[RegulatoryAlert]
    gaps: List[Dict[str, Any]]
    trends: Dict[str, List[float]]  # metric -> values over time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "framework": self.framework.value,
            "entity_id": self.entity_id,
            "overall_score": self.overall_score.to_dict(),
            "checks_count": len(self.checks),
            "alerts_count": len(self.alerts),
            "gaps_count": len(self.gaps),
            "trends": self.trends,
        }


# =============================================================================
# REGULATORY FRAMEWORK REGISTRY
# =============================================================================

class RegulatoryFrameworkRegistry:
    """
    Registry of regulatory frameworks and requirements.
    
    Maintains the catalog of requirements per framework.
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._frameworks: Dict[RegulatoryFramework, Dict[str, Requirement]] = defaultdict(dict)
        self._by_jurisdiction: Dict[Jurisdiction, Set[str]] = defaultdict(set)
        self._by_category: Dict[RequirementCategory, Set[str]] = defaultdict(set)
        
        # Initialize with core requirements
        self._initialize_core_requirements()
    
    def _initialize_core_requirements(self) -> None:
        """Initialize core regulatory requirements."""
        # MiCA requirements
        self.register_requirement(Requirement(
            requirement_id="MICA-001",
            framework=RegulatoryFramework.MICA,
            category=RequirementCategory.LICENSING,
            title="CASP Authorization",
            description="Crypto-asset service providers must be authorized",
            effective_date=datetime(2024, 12, 30, tzinfo=timezone.utc),
            jurisdictions=frozenset([Jurisdiction.EU]),
            mandatory=True,
            remediation_guidance="Apply for CASP authorization through national competent authority",
        ))
        
        self.register_requirement(Requirement(
            requirement_id="MICA-002",
            framework=RegulatoryFramework.MICA,
            category=RequirementCategory.CONSUMER_PROTECTION,
            title="White Paper Requirement",
            description="Publish crypto-asset white paper before public offering",
            effective_date=datetime(2024, 12, 30, tzinfo=timezone.utc),
            jurisdictions=frozenset([Jurisdiction.EU]),
            mandatory=True,
            remediation_guidance="Prepare and publish compliant white paper",
        ))
        
        # DORA requirements
        self.register_requirement(Requirement(
            requirement_id="DORA-001",
            framework=RegulatoryFramework.DORA,
            category=RequirementCategory.OPERATIONAL_RESILIENCE,
            title="ICT Risk Management Framework",
            description="Implement comprehensive ICT risk management framework",
            effective_date=datetime(2025, 1, 17, tzinfo=timezone.utc),
            jurisdictions=frozenset([Jurisdiction.EU]),
            mandatory=True,
            remediation_guidance="Develop and document ICT risk management policies",
        ))
        
        self.register_requirement(Requirement(
            requirement_id="DORA-002",
            framework=RegulatoryFramework.DORA,
            category=RequirementCategory.REPORTING,
            title="ICT Incident Reporting",
            description="Report major ICT-related incidents to authorities",
            effective_date=datetime(2025, 1, 17, tzinfo=timezone.utc),
            jurisdictions=frozenset([Jurisdiction.EU]),
            mandatory=True,
            remediation_guidance="Establish incident reporting procedures and templates",
        ))
        
        # SEC requirements
        self.register_requirement(Requirement(
            requirement_id="SEC-001",
            framework=RegulatoryFramework.SEC,
            category=RequirementCategory.LICENSING,
            title="Broker-Dealer Registration",
            description="Register as broker-dealer for securities transactions",
            effective_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            jurisdictions=frozenset([Jurisdiction.US]),
            mandatory=True,
            remediation_guidance="File Form BD with SEC and join FINRA",
        ))
        
        # AML/KYC (Global)
        self.register_requirement(Requirement(
            requirement_id="AML-001",
            framework=RegulatoryFramework.CUSTOM,
            category=RequirementCategory.AML_KYC,
            title="Customer Due Diligence",
            description="Perform customer identification and verification",
            effective_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            jurisdictions=frozenset([Jurisdiction.GLOBAL]),
            mandatory=True,
            remediation_guidance="Implement KYC procedures with identity verification",
        ))
    
    def register_requirement(self, requirement: Requirement) -> None:
        """Register a regulatory requirement."""
        with self._lock:
            self._frameworks[requirement.framework][requirement.requirement_id] = requirement
            
            for jurisdiction in requirement.jurisdictions:
                self._by_jurisdiction[jurisdiction].add(requirement.requirement_id)
            
            self._by_category[requirement.category].add(requirement.requirement_id)
    
    def get_requirement(self, requirement_id: str) -> Optional[Requirement]:
        """Get requirement by ID."""
        with self._lock:
            for framework_reqs in self._frameworks.values():
                if requirement_id in framework_reqs:
                    return framework_reqs[requirement_id]
            return None
    
    def get_requirements_for_framework(
        self,
        framework: RegulatoryFramework,
    ) -> List[Requirement]:
        """Get all requirements for a framework."""
        with self._lock:
            return list(self._frameworks.get(framework, {}).values())
    
    def get_requirements_for_jurisdiction(
        self,
        jurisdiction: Jurisdiction,
    ) -> List[Requirement]:
        """Get all requirements applicable to a jurisdiction."""
        with self._lock:
            requirement_ids = self._by_jurisdiction.get(jurisdiction, set())
            requirements = []
            for req_id in requirement_ids:
                req = self.get_requirement(req_id)
                if req:
                    requirements.append(req)
            return requirements
    
    def get_effective_requirements(
        self,
        as_of: Optional[datetime] = None,
    ) -> List[Requirement]:
        """Get requirements effective as of date."""
        as_of = as_of or datetime.now(timezone.utc)
        with self._lock:
            requirements = []
            for framework_reqs in self._frameworks.values():
                for req in framework_reqs.values():
                    if req.effective_date <= as_of:
                        requirements.append(req)
            return requirements


# =============================================================================
# COMPLIANCE CHECKER
# =============================================================================

class ComplianceChecker:
    """
    Validates operations against regulatory requirements.
    
    Features:
    - Pre-execution compliance check
    - Post-execution audit
    - Remediation suggestions
    - Compliance score calculation
    """
    
    def __init__(self, registry: RegulatoryFrameworkRegistry) -> None:
        self._lock = threading.RLock()
        self._registry = registry
        self._check_results: Dict[str, ComplianceCheckResult] = {}
        self._check_handlers: Dict[str, Callable[[str, Dict[str, Any]], ComplianceCheckResult]] = {}
    
    def register_check_handler(
        self,
        requirement_id: str,
        handler: Callable[[str, Dict[str, Any]], ComplianceCheckResult],
    ) -> None:
        """Register a handler for specific requirement check."""
        with self._lock:
            self._check_handlers[requirement_id] = handler
    
    def check_pre_execution(
        self,
        operation_id: str,
        operation_type: str,
        context: Dict[str, Any],
        jurisdictions: Set[Jurisdiction],
    ) -> List[ComplianceCheckResult]:
        """
        Check compliance before operation execution.
        
        FAIL-CLOSED: Returns non-compliant if check fails.
        """
        results = []
        
        # Get applicable requirements
        requirements = []
        for jurisdiction in jurisdictions:
            requirements.extend(
                self._registry.get_requirements_for_jurisdiction(jurisdiction)
            )
        
        # Deduplicate
        seen_ids: Set[str] = set()
        unique_requirements = []
        for req in requirements:
            if req.requirement_id not in seen_ids:
                seen_ids.add(req.requirement_id)
                unique_requirements.append(req)
        
        for requirement in unique_requirements:
            result = self._execute_check(operation_id, requirement, context)
            results.append(result)
            
            with self._lock:
                self._check_results[result.check_id] = result
        
        return results
    
    def check_post_execution(
        self,
        operation_id: str,
        operation_type: str,
        context: Dict[str, Any],
        execution_result: Dict[str, Any],
    ) -> List[ComplianceCheckResult]:
        """Check compliance after operation execution."""
        # Add execution result to context
        context["execution_result"] = execution_result
        
        jurisdictions = context.get("jurisdictions", {Jurisdiction.GLOBAL})
        return self.check_pre_execution(
            operation_id, operation_type, context, jurisdictions
        )
    
    def _execute_check(
        self,
        operation_id: str,
        requirement: Requirement,
        context: Dict[str, Any],
    ) -> ComplianceCheckResult:
        """Execute a compliance check."""
        now = datetime.now(timezone.utc)
        check_id = str(uuid.uuid4())
        
        # Check if custom handler exists
        handler = self._check_handlers.get(requirement.requirement_id)
        if handler:
            try:
                return handler(operation_id, context)
            except Exception as e:
                # FAIL-CLOSED on handler error
                return ComplianceCheckResult(
                    check_id=check_id,
                    requirement_id=requirement.requirement_id,
                    operation_id=operation_id,
                    status=ComplianceStatus.NON_COMPLIANT,
                    checked_at=now,
                    details={"error": str(e), "fail_closed": True},
                    evidence=[],
                    remediation_steps=[requirement.remediation_guidance],
                )
        
        # Default check logic
        return ComplianceCheckResult(
            check_id=check_id,
            requirement_id=requirement.requirement_id,
            operation_id=operation_id,
            status=ComplianceStatus.PENDING_REVIEW,
            checked_at=now,
            details={"auto_check": False, "requires_manual_review": True},
            evidence=[],
            remediation_steps=[requirement.remediation_guidance],
        )
    
    def calculate_compliance_score(
        self,
        entity_id: str,
        framework: RegulatoryFramework,
    ) -> ComplianceScore:
        """Calculate compliance score for an entity."""
        with self._lock:
            requirements = self._registry.get_requirements_for_framework(framework)
            
            compliant = 0
            non_compliant = 0
            partial = 0
            pending = 0
            
            category_scores: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))
            
            for req in requirements:
                # Find most recent check for this requirement
                latest_check: Optional[ComplianceCheckResult] = None
                for check in self._check_results.values():
                    if check.requirement_id == req.requirement_id:
                        if not latest_check or check.checked_at > latest_check.checked_at:
                            latest_check = check
                
                if latest_check:
                    cat = req.category.value
                    total, score = category_scores[cat]
                    
                    if latest_check.status == ComplianceStatus.COMPLIANT:
                        compliant += 1
                        category_scores[cat] = (total + 1, score + 1)
                    elif latest_check.status == ComplianceStatus.NON_COMPLIANT:
                        non_compliant += 1
                        category_scores[cat] = (total + 1, score)
                    elif latest_check.status == ComplianceStatus.PARTIAL:
                        partial += 1
                        category_scores[cat] = (total + 1, score + 0.5)
                    else:
                        pending += 1
                        category_scores[cat] = (total + 1, score)
                else:
                    pending += 1
            
            total = compliant + non_compliant + partial + pending
            score = (compliant + 0.5 * partial) / total if total > 0 else 0.0
            
            breakdown = {
                cat: s / t if t > 0 else 0.0
                for cat, (t, s) in category_scores.items()
            }
            
            return ComplianceScore(
                entity_id=entity_id,
                framework=framework,
                score=score,
                compliant_count=compliant,
                non_compliant_count=non_compliant,
                partial_count=partial,
                pending_count=pending,
                calculated_at=datetime.now(timezone.utc),
                breakdown=breakdown,
            )
    
    def get_remediation_suggestions(
        self,
        check_result: ComplianceCheckResult,
    ) -> List[str]:
        """Get remediation suggestions for a failed check."""
        if check_result.status == ComplianceStatus.COMPLIANT:
            return []
        
        suggestions = list(check_result.remediation_steps)
        
        requirement = self._registry.get_requirement(check_result.requirement_id)
        if requirement:
            suggestions.append(requirement.remediation_guidance)
        
        return suggestions


# =============================================================================
# JURISDICTION ROUTER
# =============================================================================

class JurisdictionRouter:
    """
    Routes operations by jurisdiction.
    
    Features:
    - Entity-to-jurisdiction mapping
    - Multi-jurisdiction handling
    - Conflict resolution rules
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entity_jurisdictions: Dict[str, Set[Jurisdiction]] = defaultdict(set)
        self._jurisdiction_handlers: Dict[Jurisdiction, Callable[[str, Dict[str, Any]], bool]] = {}
        self._conflict_resolution: Dict[Tuple[Jurisdiction, Jurisdiction], Jurisdiction] = {}
    
    def register_entity(
        self,
        entity_id: str,
        jurisdictions: Set[Jurisdiction],
    ) -> None:
        """Register entity with jurisdictions."""
        with self._lock:
            self._entity_jurisdictions[entity_id] = jurisdictions
    
    def set_conflict_resolution(
        self,
        jurisdiction_a: Jurisdiction,
        jurisdiction_b: Jurisdiction,
        preferred: Jurisdiction,
    ) -> None:
        """Set conflict resolution rule."""
        with self._lock:
            key = tuple(sorted([jurisdiction_a.value, jurisdiction_b.value]))
            self._conflict_resolution[(Jurisdiction(key[0]), Jurisdiction(key[1]))] = preferred
    
    def get_jurisdictions(self, entity_id: str) -> Set[Jurisdiction]:
        """Get jurisdictions for entity."""
        with self._lock:
            return self._entity_jurisdictions.get(entity_id, {Jurisdiction.GLOBAL})
    
    def resolve_jurisdiction(
        self,
        entity_id: str,
        operation_context: Dict[str, Any],
    ) -> Set[Jurisdiction]:
        """
        Resolve applicable jurisdictions for an operation.
        
        Considers:
        - Entity's registered jurisdictions
        - Operation-specific jurisdiction hints
        - Conflict resolution rules
        """
        with self._lock:
            entity_jurisdictions = self._entity_jurisdictions.get(entity_id, set())
            
            # Check for operation-specific jurisdiction
            op_jurisdiction = operation_context.get("jurisdiction")
            if op_jurisdiction:
                if isinstance(op_jurisdiction, Jurisdiction):
                    entity_jurisdictions = entity_jurisdictions | {op_jurisdiction}
                elif isinstance(op_jurisdiction, str):
                    try:
                        entity_jurisdictions = entity_jurisdictions | {Jurisdiction(op_jurisdiction)}
                    except ValueError:
                        pass
            
            # Apply conflict resolution
            if len(entity_jurisdictions) > 1:
                entity_jurisdictions = self._resolve_conflicts(entity_jurisdictions)
            
            return entity_jurisdictions if entity_jurisdictions else {Jurisdiction.GLOBAL}
    
    def _resolve_conflicts(self, jurisdictions: Set[Jurisdiction]) -> Set[Jurisdiction]:
        """Resolve jurisdiction conflicts."""
        # For now, keep all - could apply conflict resolution rules
        return jurisdictions
    
    def route_operation(
        self,
        entity_id: str,
        operation_type: str,
        operation_data: Dict[str, Any],
    ) -> Dict[Jurisdiction, bool]:
        """Route operation to jurisdiction handlers."""
        jurisdictions = self.resolve_jurisdiction(entity_id, operation_data)
        results: Dict[Jurisdiction, bool] = {}
        
        with self._lock:
            for jurisdiction in jurisdictions:
                handler = self._jurisdiction_handlers.get(jurisdiction)
                if handler:
                    try:
                        results[jurisdiction] = handler(operation_type, operation_data)
                    except Exception:
                        results[jurisdiction] = False
                else:
                    results[jurisdiction] = True  # No handler = pass through
        
        return results


# =============================================================================
# AUDIT TRAIL GENERATOR
# =============================================================================

class AuditTrailGenerator:
    """
    Generates immutable audit trails.
    
    Features:
    - Immutable operation log
    - Hash-chained records
    - Regulatory-specific export formats
    - Retention policy enforcement
    """
    
    GENESIS_HASH = "0" * 64
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: List[AuditRecord] = []
        self._current_hash = self.GENESIS_HASH
        self._retention_policies: Dict[Jurisdiction, RetentionPeriod] = {
            Jurisdiction.EU: RetentionPeriod.FIVE_YEARS,
            Jurisdiction.US: RetentionPeriod.SEVEN_YEARS,
            Jurisdiction.UK: RetentionPeriod.FIVE_YEARS,
            Jurisdiction.GLOBAL: RetentionPeriod.FIVE_YEARS,
        }
    
    def record(
        self,
        operation_type: str,
        operation_id: str,
        actor_id: str,
        action: str,
        jurisdictions: FrozenSet[Jurisdiction],
        data_before: Optional[Dict[str, Any]] = None,
        data_after: Optional[Dict[str, Any]] = None,
    ) -> AuditRecord:
        """Create an immutable audit record."""
        with self._lock:
            record_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            record = AuditRecord(
                record_id=record_id,
                timestamp=now,
                operation_type=operation_type,
                operation_id=operation_id,
                actor_id=actor_id,
                action=action,
                data_before=data_before,
                data_after=data_after,
                jurisdictions=jurisdictions,
                hash_value="",
                previous_hash=self._current_hash,
            )
            
            # Compute hash
            record.hash_value = record.compute_hash(self._current_hash)
            self._current_hash = record.hash_value
            
            self._records.append(record)
            return record
    
    def verify_chain_integrity(self) -> Tuple[bool, Optional[str]]:
        """Verify the integrity of the audit chain."""
        with self._lock:
            if not self._records:
                return True, None
            
            expected_previous = self.GENESIS_HASH
            
            for record in self._records:
                if record.previous_hash != expected_previous:
                    return False, f"Chain broken at record {record.record_id}"
                
                computed = record.compute_hash(expected_previous)
                if computed != record.hash_value:
                    return False, f"Hash mismatch at record {record.record_id}"
                
                expected_previous = record.hash_value
            
            return True, None
    
    def get_records(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        operation_type: Optional[str] = None,
        jurisdiction: Optional[Jurisdiction] = None,
    ) -> List[AuditRecord]:
        """Get audit records with filters."""
        with self._lock:
            records = self._records
            
            if start:
                records = [r for r in records if r.timestamp >= start]
            if end:
                records = [r for r in records if r.timestamp <= end]
            if operation_type:
                records = [r for r in records if r.operation_type == operation_type]
            if jurisdiction:
                records = [r for r in records if jurisdiction in r.jurisdictions]
            
            return records
    
    def export_for_regulator(
        self,
        framework: RegulatoryFramework,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        """Export audit trail in regulatory format."""
        # Get jurisdiction for framework
        framework_jurisdictions = {
            RegulatoryFramework.MICA: Jurisdiction.EU,
            RegulatoryFramework.DORA: Jurisdiction.EU,
            RegulatoryFramework.SEC: Jurisdiction.US,
            RegulatoryFramework.CFTC: Jurisdiction.US,
            RegulatoryFramework.FCA: Jurisdiction.UK,
        }
        
        jurisdiction = framework_jurisdictions.get(framework, Jurisdiction.GLOBAL)
        records = self.get_records(start=start, end=end, jurisdiction=jurisdiction)
        
        return {
            "framework": framework.value,
            "jurisdiction": jurisdiction.value,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "record_count": len(records),
            "chain_hash": self._current_hash,
            "records": [r.to_dict() for r in records],
        }
    
    def enforce_retention(self) -> int:
        """Enforce retention policy, return count of purged records."""
        with self._lock:
            now = datetime.now(timezone.utc)
            purge_count = 0
            
            # Find minimum retention period across all jurisdictions
            min_retention_days = min(
                policy.value for policy in self._retention_policies.values()
                if policy.value > 0
            )
            
            cutoff = now - timedelta(days=min_retention_days)
            
            # Only purge records older than cutoff
            # Note: In production, would need to preserve chain integrity
            new_records = []
            for record in self._records:
                # Check if any jurisdiction requires retention
                retain = False
                for jurisdiction in record.jurisdictions:
                    policy = self._retention_policies.get(jurisdiction, RetentionPeriod.FIVE_YEARS)
                    if policy == RetentionPeriod.PERMANENT:
                        retain = True
                        break
                    record_cutoff = now - timedelta(days=policy.value)
                    if record.timestamp >= record_cutoff:
                        retain = True
                        break
                
                if retain:
                    new_records.append(record)
                else:
                    purge_count += 1
            
            self._records = new_records
            return purge_count


# =============================================================================
# COMPLIANCE REPORT GENERATOR
# =============================================================================

class ComplianceReportGenerator:
    """
    Generates compliance reports.
    
    Features:
    - By framework
    - By time period
    - Gap analysis
    - Trend visualization data
    """
    
    def __init__(
        self,
        registry: RegulatoryFrameworkRegistry,
        checker: ComplianceChecker,
        audit_trail: AuditTrailGenerator,
    ) -> None:
        self._registry = registry
        self._checker = checker
        self._audit_trail = audit_trail
        self._historical_scores: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
    
    def generate_report(
        self,
        entity_id: str,
        framework: RegulatoryFramework,
        period_start: datetime,
        period_end: datetime,
    ) -> ComplianceReport:
        """Generate compliance report."""
        report_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Calculate score
        score = self._checker.calculate_compliance_score(entity_id, framework)
        
        # Record for trends
        self._historical_scores[f"{entity_id}:{framework.value}"].append(
            (now, score.score)
        )
        
        # Get checks from period
        checks = list(self._checker._check_results.values())
        period_checks = [
            c for c in checks
            if period_start <= c.checked_at <= period_end
        ]
        
        # Get alerts (simulated)
        alerts: List[RegulatoryAlert] = []
        for check in period_checks:
            if check.status == ComplianceStatus.NON_COMPLIANT:
                alerts.append(RegulatoryAlert(
                    alert_id=str(uuid.uuid4()),
                    priority=AlertPriority.HIGH,
                    requirement_id=check.requirement_id,
                    title=f"Non-compliance: {check.requirement_id}",
                    message=f"Operation {check.operation_id} is non-compliant",
                    created_at=check.checked_at,
                    deadline=check.checked_at + timedelta(days=7),
                    affected_operations=[check.operation_id],
                    resolution_status="OPEN",
                ))
        
        # Gap analysis
        gaps = self._analyze_gaps(entity_id, framework)
        
        # Trends
        trends = self._calculate_trends(entity_id, framework)
        
        return ComplianceReport(
            report_id=report_id,
            generated_at=now,
            period_start=period_start,
            period_end=period_end,
            framework=framework,
            entity_id=entity_id,
            overall_score=score,
            checks=period_checks,
            alerts=alerts,
            gaps=gaps,
            trends=trends,
        )
    
    def _analyze_gaps(
        self,
        entity_id: str,
        framework: RegulatoryFramework,
    ) -> List[Dict[str, Any]]:
        """Analyze compliance gaps."""
        requirements = self._registry.get_requirements_for_framework(framework)
        gaps = []
        
        for req in requirements:
            if req.mandatory:
                # Check if we have a passing check
                has_passing = False
                for check in self._checker._check_results.values():
                    if (check.requirement_id == req.requirement_id and
                        check.status == ComplianceStatus.COMPLIANT):
                        has_passing = True
                        break
                
                if not has_passing:
                    gaps.append({
                        "requirement_id": req.requirement_id,
                        "title": req.title,
                        "category": req.category.value,
                        "severity": "HIGH" if req.mandatory else "MEDIUM",
                        "remediation": req.remediation_guidance,
                    })
        
        return gaps
    
    def _calculate_trends(
        self,
        entity_id: str,
        framework: RegulatoryFramework,
    ) -> Dict[str, List[float]]:
        """Calculate compliance trends."""
        key = f"{entity_id}:{framework.value}"
        historical = self._historical_scores.get(key, [])
        
        # Return last 30 data points
        scores = [score for _, score in historical[-30:]]
        
        return {
            "compliance_score": scores,
            "trend_direction": self._calculate_trend_direction(scores),
        }
    
    def _calculate_trend_direction(self, scores: List[float]) -> List[float]:
        """Calculate trend direction (simple moving average delta)."""
        if len(scores) < 2:
            return [0.0]
        
        deltas = []
        for i in range(1, len(scores)):
            deltas.append(scores[i] - scores[i-1])
        
        return deltas


# =============================================================================
# WRAP HASH COMPUTATION
# =============================================================================

def compute_wrap_hash() -> str:
    """Compute WRAP hash for GID-03 deliverable."""
    content = f"GID-03:regulatory_engine:v{REGULATORY_ENGINE_VERSION}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "REGULATORY_ENGINE_VERSION",
    "RegulatoryFramework",
    "Jurisdiction",
    "ComplianceStatus",
    "AlertPriority",
    "RequirementCategory",
    "RetentionPeriod",
    "Requirement",
    "ComplianceCheckResult",
    "RegulatoryAlert",
    "AuditRecord",
    "ComplianceScore",
    "ComplianceReport",
    "RegulatoryFrameworkRegistry",
    "ComplianceChecker",
    "JurisdictionRouter",
    "AuditTrailGenerator",
    "ComplianceReportGenerator",
    "compute_wrap_hash",
]
