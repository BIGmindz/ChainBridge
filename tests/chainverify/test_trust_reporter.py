"""
ChainVerify Tests — Trust Reporter

PAC Reference: PAC-JEFFREY-P49
"""

import pytest
from dataclasses import dataclass, field
from datetime import datetime

from core.chainverify.trust_reporter import (
    TrustReporter,
    TrustGrade,
    VerificationReport,
    VerificationSummary,
    LegalDisclaimer,
    ReportFormat,
    get_trust_reporter,
    reset_trust_reporter,
)
from core.chainverify.cci_scorer import ScoreGrade, ChaosDimension, DimensionCoverage


@dataclass
class MockVerificationScore:
    """Mock verification score for testing."""
    api_id: str = "api_123"
    api_title: str = "Test API"
    base_score: float = 85.0
    cci_score: float = 75.0
    safety_score: float = 90.0
    final_score: float = 82.5
    grade: ScoreGrade = ScoreGrade.B
    dimension_coverage: list = field(default_factory=list)
    total_tests: int = 100
    passed_tests: int = 85
    failed_tests: int = 10
    blocked_tests: int = 5
    edge_cases_handled: int = 20
    
    def __post_init__(self):
        if not self.dimension_coverage:
            self.dimension_coverage = [
                DimensionCoverage(ChaosDimension.AUTH, 10, 8, 80.0),
                DimensionCoverage(ChaosDimension.STATE, 5, 4, 80.0),
            ]


@dataclass
class MockExecutionBatch:
    """Mock execution batch for testing."""
    batch_id: str = "batch_001"
    tenant_id: str = "tenant_123"
    total_tests: int = 100
    passed_tests: int = 85
    failed_tests: int = 10
    blocked_tests: int = 5
    total_violations: int = 2
    execution_time_ms: float = 5000.0
    results: list = field(default_factory=list)


class TestTrustGrade:
    """Test trust grade enumeration."""
    
    def test_all_grades_defined(self):
        expected = {
            "VERIFIED_EXCELLENT", "VERIFIED_GOOD", "VERIFIED_ACCEPTABLE",
            "NEEDS_ATTENTION", "HIGH_RISK"
        }
        actual = {g.value for g in TrustGrade}
        assert actual == expected


class TestReportFormat:
    """Test report format enumeration."""
    
    def test_all_formats_defined(self):
        expected = {"JSON", "MARKDOWN", "HTML", "PDF"}
        actual = {f.value for f in ReportFormat}
        assert actual == expected


class TestLegalDisclaimer:
    """Test legal disclaimer."""
    
    def test_disclaimer_content(self):
        disclaimer = LegalDisclaimer()
        
        # Must contain key terms
        assert "NOT" in disclaimer.NOT_CERTIFICATION
        assert "certification" in disclaimer.NOT_CERTIFICATION.lower()
        assert "guarantee" in disclaimer.NOT_SECURITY_GUARANTEE.lower()
        assert "compliance" in disclaimer.NOT_COMPLIANCE.lower()
        assert "liability" in disclaimer.LIABILITY_LIMITATION.lower()
    
    def test_to_dict(self):
        disclaimer = LegalDisclaimer()
        d = disclaimer.to_dict()
        
        assert "disclaimer_id" in d
        assert "statements" in d
        assert "not_certification" in d["statements"]
    
    def test_as_markdown(self):
        disclaimer = LegalDisclaimer()
        md = disclaimer.as_markdown()
        
        assert "## Legal Disclaimer" in md
        assert "NOT a certification" in md
        assert "LIMITATION" in md.upper()


class TestVerificationSummary:
    """Test verification summary dataclass."""
    
    def test_create_summary(self):
        summary = VerificationSummary(
            api_name="Test API",
            verification_date=datetime.utcnow(),
            trust_grade=TrustGrade.VERIFIED_GOOD,
            final_score=82.5,
            tests_executed=100,
            pass_rate=85.0,
            safety_compliance=95.0,
            key_findings=["Finding 1", "Finding 2"],
            recommendations=["Rec 1"]
        )
        
        assert summary.trust_grade == TrustGrade.VERIFIED_GOOD
        assert len(summary.key_findings) == 2
    
    def test_to_dict(self):
        summary = VerificationSummary(
            api_name="Test API",
            verification_date=datetime.utcnow(),
            trust_grade=TrustGrade.VERIFIED_EXCELLENT,
            final_score=95.0,
            tests_executed=100,
            pass_rate=95.0,
            safety_compliance=100.0,
            key_findings=[],
            recommendations=[]
        )
        
        d = summary.to_dict()
        assert d["trust_grade"] == "VERIFIED_EXCELLENT"


class TestVerificationReport:
    """Test verification report dataclass."""
    
    def test_create_report(self):
        summary = VerificationSummary(
            api_name="Test",
            verification_date=datetime.utcnow(),
            trust_grade=TrustGrade.VERIFIED_GOOD,
            final_score=80.0,
            tests_executed=100,
            pass_rate=80.0,
            safety_compliance=95.0,
            key_findings=[],
            recommendations=[]
        )
        
        report = VerificationReport(
            report_id="rpt_001",
            tenant_id="tenant_123",
            api_id="api_123",
            api_title="Test API",
            disclaimer=LegalDisclaimer(),
            summary=summary,
            detailed_scores={"base": 80.0},
            dimension_breakdown=[],
            findings=[],
            recommendations=[]
        )
        
        assert report.report_id == "rpt_001"
        assert not report.is_expired
    
    def test_report_expiration(self):
        from datetime import timedelta
        
        summary = VerificationSummary(
            api_name="Test",
            verification_date=datetime.utcnow(),
            trust_grade=TrustGrade.VERIFIED_GOOD,
            final_score=80.0,
            tests_executed=100,
            pass_rate=80.0,
            safety_compliance=95.0,
            key_findings=[],
            recommendations=[]
        )
        
        # Create an already expired report
        past = datetime.utcnow() - timedelta(days=100)
        report = VerificationReport(
            report_id="rpt_old",
            tenant_id="tenant_123",
            api_id="api_123",
            api_title="Test API",
            disclaimer=LegalDisclaimer(),
            summary=summary,
            detailed_scores={},
            dimension_breakdown=[],
            findings=[],
            recommendations=[],
            generated_at=past,
            expires_at=past + timedelta(days=90)
        )
        
        assert report.is_expired
    
    def test_to_markdown(self):
        summary = VerificationSummary(
            api_name="Test",
            verification_date=datetime.utcnow(),
            trust_grade=TrustGrade.VERIFIED_GOOD,
            final_score=80.0,
            tests_executed=100,
            pass_rate=80.0,
            safety_compliance=95.0,
            key_findings=["Test finding"],
            recommendations=["Test rec"]
        )
        
        report = VerificationReport(
            report_id="rpt_001",
            tenant_id="tenant_123",
            api_id="api_123",
            api_title="Test API",
            disclaimer=LegalDisclaimer(),
            summary=summary,
            detailed_scores={"base": 80.0, "cci": 75.0, "safety": 90.0},
            dimension_breakdown=[{"dimension": "AUTH", "tests_executed": 10, "tests_passed": 8, "coverage_percentage": 80.0}],
            findings=[{"title": "Finding 1", "severity": "MEDIUM", "description": "Test"}],
            recommendations=[{"title": "Rec 1", "priority": "LOW", "description": "Test"}]
        )
        
        md = report.to_markdown()
        
        assert "# ChainVerify Verification Report" in md
        assert "Legal Disclaimer" in md
        assert "Executive Summary" in md
        assert "VERIFIED_GOOD" in md


class TestTrustReporter:
    """Test trust reporter."""
    
    def setup_method(self):
        reset_trust_reporter()
    
    def test_generate_report(self):
        reporter = TrustReporter()
        
        score = MockVerificationScore()
        batch = MockExecutionBatch()
        
        report = reporter.generate_report(
            tenant_id="tenant_123",
            verification_score=score,
            execution_batch=batch
        )
        
        assert report.api_id == "api_123"
        assert report.disclaimer is not None
        assert report.summary is not None
    
    def test_trust_grade_mapping(self):
        reporter = TrustReporter()
        
        assert reporter._score_to_trust_grade(95) == TrustGrade.VERIFIED_EXCELLENT
        assert reporter._score_to_trust_grade(85) == TrustGrade.VERIFIED_GOOD
        assert reporter._score_to_trust_grade(75) == TrustGrade.VERIFIED_ACCEPTABLE
        assert reporter._score_to_trust_grade(65) == TrustGrade.NEEDS_ATTENTION
        assert reporter._score_to_trust_grade(50) == TrustGrade.HIGH_RISK
    
    def test_generate_findings(self):
        reporter = TrustReporter()
        
        # Low pass rate
        score = MockVerificationScore(
            passed_tests=50,
            total_tests=100,
            final_score=50.0
        )
        batch = MockExecutionBatch(total_violations=5)
        
        findings = reporter._generate_findings(score, batch)
        
        assert len(findings) > 0
        assert any("Pass Rate" in f["title"] for f in findings)
    
    def test_generate_recommendations(self):
        reporter = TrustReporter()
        
        score = MockVerificationScore(
            cci_score=50.0,
            safety_score=80.0,
            final_score=55.0
        )
        
        recommendations = reporter._generate_recommendations(
            score,
            TrustGrade.HIGH_RISK
        )
        
        assert len(recommendations) > 0
        assert any("Immediate" in r["title"] or "Critical" in r.get("priority", "") for r in recommendations)
    
    def test_get_report(self):
        reporter = TrustReporter()
        
        score = MockVerificationScore()
        batch = MockExecutionBatch()
        
        report = reporter.generate_report("tenant", score, batch)
        
        retrieved = reporter.get_report(report.report_id)
        assert retrieved is not None
        assert retrieved.report_id == report.report_id


class TestLanguageValidation:
    """Test forbidden language validation."""
    
    def test_detect_forbidden_terms(self):
        reporter = TrustReporter()
        
        # Should detect "certified"
        violations = reporter.validate_language("This API is certified secure")
        assert "certified" in violations
        
        # Should detect "guarantee"
        violations = reporter.validate_language("We guarantee security")
        assert "guarantee" in violations or "guaranteed" in violations
    
    def test_clean_text_passes(self):
        reporter = TrustReporter()
        
        clean = "This API has been verified through automated testing"
        violations = reporter.validate_language(clean)
        
        assert len(violations) == 0
    
    def test_multiple_violations(self):
        reporter = TrustReporter()
        
        text = "This certified API is guaranteed to be SOC2 compliant"
        violations = reporter.validate_language(text)
        
        assert len(violations) >= 2


class TestGlobalFunctions:
    """Test module-level convenience functions."""
    
    def setup_method(self):
        reset_trust_reporter()
    
    def test_get_singleton(self):
        r1 = get_trust_reporter()
        r2 = get_trust_reporter()
        assert r1 is r2
    
    def test_reset_clears_state(self):
        reporter = get_trust_reporter()
        reporter._generated_reports["test"] = None
        
        reset_trust_reporter()
        
        new_reporter = get_trust_reporter()
        assert len(new_reporter._generated_reports) == 0
