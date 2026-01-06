"""
Trust Reporter — Trust-Grade Reporting with Legal Boundaries

PAC Reference: PAC-JEFFREY-P49
Agent: ALEX (GID-08), SONNY (GID-02)

Generates trust reports for verified APIs with explicit legal disclaimers.
Reports verification results WITHOUT making certification claims.

LEGAL BOUNDARIES (ALEX-ENFORCED):
- ❌ NO "certified" language
- ❌ NO "secure" guarantees
- ❌ NO liability acceptance
- ❌ NO compliance claims (SOC2, HIPAA, etc.)

This is VERIFICATION reporting, not CERTIFICATION.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import hashlib


class TrustGrade(Enum):
    """Trust grade levels (NOT certification levels)."""
    VERIFIED_EXCELLENT = "VERIFIED_EXCELLENT"   # 90+
    VERIFIED_GOOD = "VERIFIED_GOOD"             # 80-89
    VERIFIED_ACCEPTABLE = "VERIFIED_ACCEPTABLE" # 70-79
    NEEDS_ATTENTION = "NEEDS_ATTENTION"         # 60-69
    HIGH_RISK = "HIGH_RISK"                     # <60


class ReportFormat(Enum):
    """Output format for reports."""
    JSON = "JSON"
    MARKDOWN = "MARKDOWN"
    HTML = "HTML"
    PDF = "PDF"


@dataclass
class LegalDisclaimer:
    """
    Legal disclaimer attached to all reports.
    
    MANDATORY — cannot be removed or modified.
    """
    disclaimer_id: str = "CHAINVERIFY-LEGAL-001"
    version: str = "1.0.0"
    
    NOT_CERTIFICATION: str = (
        "This report is a VERIFICATION report, NOT a certification. "
        "ChainVerify does not certify, guarantee, or warrant the security, "
        "reliability, or fitness for purpose of any API or system."
    )
    
    NOT_SECURITY_GUARANTEE: str = (
        "Verification scores reflect observed behavior during automated testing only. "
        "They do NOT guarantee protection against security vulnerabilities, data breaches, "
        "or system failures."
    )
    
    NOT_COMPLIANCE: str = (
        "This report does NOT constitute compliance with any regulatory framework "
        "including but not limited to SOC2, HIPAA, PCI-DSS, GDPR, or ISO 27001."
    )
    
    LIABILITY_LIMITATION: str = (
        "ChainVerify and its operators accept NO LIABILITY for any damages, losses, "
        "or consequences arising from reliance on this report or the verified API."
    )
    
    SCOPE_LIMITATION: str = (
        "Testing was performed against a specific API version at a specific point in time. "
        "Results may not reflect current API behavior or behavior under different conditions."
    )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "disclaimer_id": self.disclaimer_id,
            "version": self.version,
            "statements": {
                "not_certification": self.NOT_CERTIFICATION,
                "not_security_guarantee": self.NOT_SECURITY_GUARANTEE,
                "not_compliance": self.NOT_COMPLIANCE,
                "liability_limitation": self.LIABILITY_LIMITATION,
                "scope_limitation": self.SCOPE_LIMITATION,
            },
        }
    
    def as_markdown(self) -> str:
        """Render disclaimer as markdown."""
        return f"""## Legal Disclaimer

**IMPORTANT: READ BEFORE RELYING ON THIS REPORT**

### Not a Certification
{self.NOT_CERTIFICATION}

### No Security Guarantee
{self.NOT_SECURITY_GUARANTEE}

### No Compliance Claims
{self.NOT_COMPLIANCE}

### Limitation of Liability
{self.LIABILITY_LIMITATION}

### Scope Limitation
{self.SCOPE_LIMITATION}

---
*Disclaimer ID: {self.disclaimer_id} | Version: {self.version}*
"""


@dataclass
class VerificationSummary:
    """Executive summary of verification results."""
    api_name: str
    verification_date: datetime
    trust_grade: TrustGrade
    final_score: float
    tests_executed: int
    pass_rate: float
    safety_compliance: float
    key_findings: list[str]
    recommendations: list[str]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "api_name": self.api_name,
            "verification_date": self.verification_date.isoformat(),
            "trust_grade": self.trust_grade.value,
            "final_score": round(self.final_score, 2),
            "tests_executed": self.tests_executed,
            "pass_rate": round(self.pass_rate, 2),
            "safety_compliance": round(self.safety_compliance, 2),
            "key_findings": self.key_findings,
            "recommendations": self.recommendations,
        }


@dataclass
class VerificationReport:
    """
    Complete verification report for an API.
    
    STRUCTURE:
    1. Legal disclaimer (MANDATORY, FIRST)
    2. Executive summary
    3. Detailed scores
    4. Findings and recommendations
    5. Technical appendix
    """
    report_id: str
    tenant_id: str
    api_id: str
    api_title: str
    disclaimer: LegalDisclaimer
    summary: VerificationSummary
    detailed_scores: dict[str, Any]
    dimension_breakdown: list[dict[str, Any]]
    findings: list[dict[str, str]]
    recommendations: list[dict[str, str]]
    generated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None  # Reports expire after 90 days
    
    def __post_init__(self):
        if self.expires_at is None:
            # Reports expire after 90 days
            from datetime import timedelta
            self.expires_at = self.generated_at + timedelta(days=90)
    
    @property
    def is_expired(self) -> bool:
        """Check if report has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "tenant_id": self.tenant_id,
            "api_id": self.api_id,
            "api_title": self.api_title,
            "disclaimer": self.disclaimer.to_dict(),
            "summary": self.summary.to_dict(),
            "detailed_scores": self.detailed_scores,
            "dimension_breakdown": self.dimension_breakdown,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
        }
    
    def to_markdown(self) -> str:
        """Render report as markdown."""
        md = f"""# ChainVerify Verification Report

**Report ID:** {self.report_id}  
**API:** {self.api_title}  
**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M UTC')}  
**Expires:** {self.expires_at.strftime('%Y-%m-%d') if self.expires_at else 'N/A'}

---

{self.disclaimer.as_markdown()}

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Trust Grade** | {self.summary.trust_grade.value} |
| **Final Score** | {self.summary.final_score:.1f}/100 |
| **Tests Executed** | {self.summary.tests_executed:,} |
| **Pass Rate** | {self.summary.pass_rate:.1f}% |
| **Safety Compliance** | {self.summary.safety_compliance:.1f}% |

### Key Findings

"""
        for finding in self.summary.key_findings:
            md += f"- {finding}\n"
        
        md += "\n### Recommendations\n\n"
        for rec in self.summary.recommendations:
            md += f"- {rec}\n"
        
        md += f"""
---

## Detailed Scores

| Component | Score | Weight |
|-----------|-------|--------|
| Base Test Pass Rate | {self.detailed_scores.get('base', 0):.1f} | 40% |
| Chaos Coverage Index | {self.detailed_scores.get('cci', 0):.1f} | 35% |
| Safety Compliance | {self.detailed_scores.get('safety', 0):.1f} | 25% |

---

## Chaos Dimension Coverage

| Dimension | Tests | Passed | Coverage |
|-----------|-------|--------|----------|
"""
        for dim in self.dimension_breakdown:
            md += f"| {dim['dimension']} | {dim['tests_executed']} | {dim['tests_passed']} | {dim['coverage_percentage']:.1f}% |\n"
        
        md += f"""
---

## Findings

"""
        for i, finding in enumerate(self.findings, 1):
            md += f"### Finding {i}: {finding.get('title', 'Untitled')}\n\n"
            md += f"**Severity:** {finding.get('severity', 'Unknown')}\n\n"
            md += f"{finding.get('description', '')}\n\n"
        
        md += """
---

*This report was generated by ChainVerify — Infinite Test as a Service*

**REMINDER:** This is a VERIFICATION report, NOT a certification. See Legal Disclaimer above.
"""
        return md


class TrustReporter:
    """
    Generates trust reports from verification scores.
    
    LEGAL COMPLIANCE:
    - Every report includes mandatory disclaimer
    - No certification language used
    - Clear scope limitations stated
    """
    
    # Keywords that MUST NOT appear in reports
    FORBIDDEN_TERMS = [
        "certified",
        "certification",
        "guarantee",
        "guaranteed",
        "warrant",
        "warranty",
        "secure",
        "security certified",
        "compliant with",
        "meets requirements",
        "SOC2 compliant",
        "HIPAA compliant",
        "PCI compliant",
    ]
    
    def __init__(self):
        self._generated_reports: dict[str, VerificationReport] = {}
    
    def generate_report(
        self,
        tenant_id: str,
        verification_score: Any,  # VerificationScore
        execution_batch: Any,     # ExecutionBatch
    ) -> VerificationReport:
        """
        Generate a verification report.
        
        Args:
            tenant_id: Tenant requesting the report
            verification_score: Score from CCI scorer
            execution_batch: Raw execution results
            
        Returns:
            VerificationReport with all sections
        """
        # Generate report ID
        report_id = hashlib.sha256(
            f"{tenant_id}:{verification_score.api_id}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Map score to trust grade
        trust_grade = self._score_to_trust_grade(verification_score.final_score)
        
        # Generate findings
        findings = self._generate_findings(verification_score, execution_batch)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            verification_score,
            trust_grade
        )
        
        # Build summary
        summary = VerificationSummary(
            api_name=verification_score.api_title,
            verification_date=datetime.utcnow(),
            trust_grade=trust_grade,
            final_score=verification_score.final_score,
            tests_executed=verification_score.total_tests,
            pass_rate=(verification_score.passed_tests / max(1, verification_score.total_tests)) * 100,
            safety_compliance=verification_score.safety_score,
            key_findings=[f["title"] for f in findings[:3]],
            recommendations=[r["title"] for r in recommendations[:3]],
        )
        
        # Build report
        report = VerificationReport(
            report_id=report_id,
            tenant_id=tenant_id,
            api_id=verification_score.api_id,
            api_title=verification_score.api_title,
            disclaimer=LegalDisclaimer(),
            summary=summary,
            detailed_scores={
                "base": verification_score.base_score,
                "cci": verification_score.cci_score,
                "safety": verification_score.safety_score,
                "final": verification_score.final_score,
            },
            dimension_breakdown=[d.to_dict() for d in verification_score.dimension_coverage],
            findings=findings,
            recommendations=recommendations,
        )
        
        # Cache report
        self._generated_reports[report_id] = report
        
        return report
    
    def get_report(self, report_id: str) -> VerificationReport | None:
        """Retrieve a generated report."""
        return self._generated_reports.get(report_id)
    
    def validate_language(self, text: str) -> list[str]:
        """
        Check text for forbidden certification language.
        
        Returns list of forbidden terms found.
        """
        text_lower = text.lower()
        violations = []
        
        for term in self.FORBIDDEN_TERMS:
            if term.lower() in text_lower:
                violations.append(term)
        
        return violations
    
    def _score_to_trust_grade(self, score: float) -> TrustGrade:
        """Convert numeric score to trust grade."""
        if score >= 90:
            return TrustGrade.VERIFIED_EXCELLENT
        elif score >= 80:
            return TrustGrade.VERIFIED_GOOD
        elif score >= 70:
            return TrustGrade.VERIFIED_ACCEPTABLE
        elif score >= 60:
            return TrustGrade.NEEDS_ATTENTION
        else:
            return TrustGrade.HIGH_RISK
    
    def _generate_findings(
        self,
        score: Any,
        batch: Any,
    ) -> list[dict[str, str]]:
        """Generate findings from verification results."""
        findings = []
        
        # Check for low pass rate
        if score.passed_tests < score.total_tests * 0.8:
            findings.append({
                "title": "Below Target Pass Rate",
                "severity": "HIGH",
                "description": (
                    f"Only {score.passed_tests}/{score.total_tests} tests passed "
                    f"({(score.passed_tests/score.total_tests)*100:.1f}%). "
                    "Review failed tests for potential issues."
                ),
            })
        
        # Check for safety violations
        if batch.total_violations > 0:
            findings.append({
                "title": "Safety Boundary Violations Detected",
                "severity": "MEDIUM",
                "description": (
                    f"{batch.total_violations} tests triggered safety boundaries. "
                    "These may indicate unexpected API behavior or test configuration issues."
                ),
            })
        
        # Check for low CCI coverage
        if score.cci_score < 50:
            findings.append({
                "title": "Limited Chaos Dimension Coverage",
                "severity": "MEDIUM",
                "description": (
                    f"CCI score of {score.cci_score:.1f} indicates limited coverage "
                    "of chaos scenarios. Consider expanding test suite."
                ),
            })
        
        # Check individual dimensions
        for dim in score.dimension_coverage:
            if dim.tests_executed == 0:
                findings.append({
                    "title": f"No {dim.dimension.value} Testing",
                    "severity": "LOW",
                    "description": (
                        f"No tests executed for {dim.dimension.value} dimension. "
                        "Consider adding chaos scenarios for this dimension."
                    ),
                })
        
        # If all good
        if not findings:
            findings.append({
                "title": "No Critical Issues Found",
                "severity": "INFO",
                "description": "Verification completed without identifying critical issues.",
            })
        
        return findings
    
    def _generate_recommendations(
        self,
        score: Any,
        grade: TrustGrade,
    ) -> list[dict[str, str]]:
        """Generate recommendations based on verification results."""
        recommendations = []
        
        if grade == TrustGrade.HIGH_RISK:
            recommendations.append({
                "title": "Immediate Review Required",
                "priority": "CRITICAL",
                "description": (
                    "Score indicates significant issues. Recommend immediate "
                    "review of API implementation and error handling."
                ),
            })
        
        if score.cci_score < 70:
            recommendations.append({
                "title": "Expand Chaos Testing",
                "priority": "HIGH",
                "description": (
                    "Add more chaos scenario tests to improve resilience coverage. "
                    "Focus on AUTH and STATE dimensions."
                ),
            })
        
        if score.safety_score < 90:
            recommendations.append({
                "title": "Review Input Validation",
                "priority": "MEDIUM",
                "description": (
                    "Some fuzz tests triggered unexpected behavior. "
                    "Review input validation and sanitization."
                ),
            })
        
        # Standard recommendations
        recommendations.append({
            "title": "Schedule Regular Verification",
            "priority": "LOW",
            "description": (
                "Run verification after each major release to track quality over time."
            ),
        })
        
        return recommendations


# Module-level singleton
_trust_reporter: TrustReporter | None = None


def get_trust_reporter() -> TrustReporter:
    """Get the singleton reporter."""
    global _trust_reporter
    if _trust_reporter is None:
        _trust_reporter = TrustReporter()
    return _trust_reporter


def reset_trust_reporter() -> None:
    """Reset the singleton (for testing)."""
    global _trust_reporter
    _trust_reporter = None


def generate_trust_report(
    tenant_id: str,
    verification_score: Any,
    execution_batch: Any,
) -> VerificationReport:
    """Convenience function to generate a trust report."""
    return get_trust_reporter().generate_report(
        tenant_id,
        verification_score,
        execution_batch
    )
