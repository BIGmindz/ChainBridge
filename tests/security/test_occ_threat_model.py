# ═══════════════════════════════════════════════════════════════════════════════
# P25 Test Suite — Threat Model & Security Tests
# PAC-BENSON-P25: PARALLEL PLATFORM EXPANSION & OPERATOR-GRADE EXECUTION
# Agent: DAN (GID-07) — CI/CD & Test Scaling
# ═══════════════════════════════════════════════════════════════════════════════

"""
Test suite for OCC Threat Model and Security.

Tests cover:
- Threat vector registration
- Mitigation tracking
- Input sanitization
- Threat assessment generation

EXECUTION MODE: PARALLEL
LANE: CI/CD (GID-07)
"""

import pytest

from core.security.occ_threat_model import (
    ThreatCategory,
    ThreatSeverity,
    MitigationStatus,
    AttackSurface,
    ThreatVector,
    Mitigation,
    ThreatAssessment,
    ThreatModelRegistry,
    InputSanitizer,
    THREAT_UI_XSS_001,
    THREAT_API_002,
    MIT_XSS_001,
    MIT_API_002,
)


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT VECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestThreatVector:
    """Tests for ThreatVector."""

    def test_threat_vector_creation(self) -> None:
        """Test creating a threat vector."""
        threat = ThreatVector(
            vector_id="THREAT-TEST-001",
            name="Test Threat",
            description="A test threat",
            category=ThreatCategory.TAMPERING,
            severity=ThreatSeverity.MEDIUM,
            attack_surface=AttackSurface.OCC_UI,
            attack_complexity="LOW",
            prerequisites=("Test prerequisite",),
            impact="Test impact",
            likelihood="LOW",
        )
        assert threat.vector_id == "THREAT-TEST-001"
        assert threat.category == ThreatCategory.TAMPERING

    def test_threat_immutability(self) -> None:
        """Test that threats are immutable."""
        with pytest.raises(AttributeError):
            THREAT_UI_XSS_001.severity = ThreatSeverity.LOW  # type: ignore


class TestMitigation:
    """Tests for Mitigation."""

    def test_mitigation_creation(self) -> None:
        """Test creating a mitigation."""
        mitigation = Mitigation(
            mitigation_id="MIT-TEST-001",
            name="Test Mitigation",
            description="A test mitigation",
            implementation="Test implementation",
            status=MitigationStatus.IMPLEMENTED,
            validates_invariant="INV-TEST-001",
        )
        assert mitigation.mitigation_id == "MIT-TEST-001"
        assert mitigation.status == MitigationStatus.IMPLEMENTED

    def test_mitigation_immutability(self) -> None:
        """Test that mitigations are immutable."""
        with pytest.raises(AttributeError):
            MIT_XSS_001.status = MitigationStatus.PLANNED  # type: ignore


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT MODEL REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestThreatModelRegistry:
    """Tests for ThreatModelRegistry."""

    def test_registry_singleton(self) -> None:
        """Test that registry is a singleton."""
        reg1 = ThreatModelRegistry()
        reg2 = ThreatModelRegistry()
        assert reg1 is reg2

    def test_registry_has_threats(self) -> None:
        """Test that registry has default threats."""
        registry = ThreatModelRegistry()
        assert registry.count() >= 10

    def test_get_threat_by_id(self) -> None:
        """Test getting threat by ID."""
        registry = ThreatModelRegistry()
        threat = registry.get_threat("THREAT-UI-XSS-001")
        assert threat is not None
        assert threat.name == "Stored XSS in Decision Cards"

    def test_get_threats_by_category(self) -> None:
        """Test filtering threats by category."""
        registry = ThreatModelRegistry()
        tampering = registry.get_threats_by_category(ThreatCategory.TAMPERING)
        assert len(tampering) >= 2
        assert all(t.category == ThreatCategory.TAMPERING for t in tampering)

    def test_get_threats_by_severity(self) -> None:
        """Test filtering threats by severity."""
        registry = ThreatModelRegistry()
        high = registry.get_threats_by_severity(ThreatSeverity.HIGH)
        assert len(high) >= 3
        assert all(t.severity == ThreatSeverity.HIGH for t in high)

    def test_get_threats_by_surface(self) -> None:
        """Test filtering threats by attack surface."""
        registry = ThreatModelRegistry()
        ui_threats = registry.get_threats_by_surface(AttackSurface.OCC_UI)
        assert len(ui_threats) >= 2
        assert all(t.attack_surface == AttackSurface.OCC_UI for t in ui_threats)

    def test_get_critical_threats(self) -> None:
        """Test getting critical threats."""
        registry = ThreatModelRegistry()
        critical = registry.get_critical_threats()
        assert len(critical) >= 4
        assert all(
            t.severity in (ThreatSeverity.CRITICAL, ThreatSeverity.HIGH)
            for t in critical
        )

    def test_get_mitigations_by_invariant(self) -> None:
        """Test getting mitigations by invariant."""
        registry = ThreatModelRegistry()
        mitigations = registry.get_mitigations_by_invariant("INV-SEC-UI-001")
        assert len(mitigations) >= 2

    def test_get_assessment(self) -> None:
        """Test getting threat assessment."""
        registry = ThreatModelRegistry()
        assessment = registry.get_assessment("THREAT-UI-XSS-001")
        assert assessment is not None
        assert len(assessment.mitigations) >= 2
        assert assessment.residual_risk == "LOW"

    def test_generate_report(self) -> None:
        """Test generating threat model report."""
        registry = ThreatModelRegistry()
        report = registry.generate_report()
        assert report["total_threats"] >= 10
        assert report["total_mitigations"] >= 10
        assert "by_severity" in report
        assert "by_category" in report
        assert "residual_risk_summary" in report


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT SANITIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestInputSanitizer:
    """Tests for InputSanitizer."""

    def test_escape_html_basic(self) -> None:
        """Test basic HTML escaping."""
        result = InputSanitizer.escape_html("<script>alert('xss')</script>")
        assert "<" not in result
        assert ">" not in result
        assert "&lt;" in result
        assert "&gt;" in result

    def test_escape_html_quotes(self) -> None:
        """Test quote escaping."""
        result = InputSanitizer.escape_html('onclick="alert(1)"')
        assert '"' not in result
        assert "&quot;" in result

    def test_detect_xss_script_tag(self) -> None:
        """Test XSS detection for script tags."""
        assert InputSanitizer.detect_xss("<script>evil()</script>")
        assert InputSanitizer.detect_xss("<SCRIPT>evil()</SCRIPT>")

    def test_detect_xss_javascript_url(self) -> None:
        """Test XSS detection for javascript: URLs."""
        assert InputSanitizer.detect_xss("javascript:alert(1)")
        assert InputSanitizer.detect_xss("JAVASCRIPT:alert(1)")

    def test_detect_xss_event_handlers(self) -> None:
        """Test XSS detection for event handlers."""
        assert InputSanitizer.detect_xss('onerror="alert(1)"')
        assert InputSanitizer.detect_xss("onclick=alert(1)")
        assert InputSanitizer.detect_xss("onload = alert(1)")

    def test_detect_xss_clean_input(self) -> None:
        """Test that clean input is not flagged."""
        assert not InputSanitizer.detect_xss("Hello, world!")
        assert not InputSanitizer.detect_xss("PAC-BENSON-P25")
        assert not InputSanitizer.detect_xss("Normal decision summary text")

    def test_sanitize_for_display(self) -> None:
        """Test full sanitization for display."""
        malicious = '<script>alert("xss")</script>'
        sanitized = InputSanitizer.sanitize_for_display(malicious)
        assert "<script>" not in sanitized
        assert "&lt;script&gt;" in sanitized

    def test_validate_identifier_valid(self) -> None:
        """Test valid identifier validation."""
        assert InputSanitizer.validate_identifier("PAC-BENSON-P25")
        assert InputSanitizer.validate_identifier("GID_01")
        assert InputSanitizer.validate_identifier("agent123")

    def test_validate_identifier_invalid(self) -> None:
        """Test invalid identifier validation."""
        assert not InputSanitizer.validate_identifier("<script>")
        assert not InputSanitizer.validate_identifier("user@domain")
        assert not InputSanitizer.validate_identifier("a b c")


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT ASSESSMENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestThreatAssessment:
    """Tests for ThreatAssessment."""

    def test_assessment_creation(self) -> None:
        """Test creating a threat assessment."""
        assessment = ThreatAssessment(
            vector=THREAT_UI_XSS_001,
            mitigations=[MIT_XSS_001],
            residual_risk="LOW",
        )
        assert assessment.vector.vector_id == "THREAT-UI-XSS-001"
        assert len(assessment.mitigations) == 1
        assert assessment.residual_risk == "LOW"

    def test_assessment_has_assessor(self) -> None:
        """Test that assessment has assessor field."""
        assessment = ThreatAssessment(
            vector=THREAT_API_002,
            mitigations=[MIT_API_002],
            residual_risk="LOW",
        )
        assert assessment.assessor == "SAM (GID-06)"


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSecurityInvariants:
    """Tests for security invariant validation."""

    def test_inv_sec_ui_001_input_sanitization(self) -> None:
        """INV-SEC-UI-001: All user input must be sanitized before display."""
        # Verify that mitigations exist for this invariant
        registry = ThreatModelRegistry()
        mitigations = registry.get_mitigations_by_invariant("INV-SEC-UI-001")
        assert len(mitigations) >= 2
        # Verify all are implemented
        assert all(m.status == MitigationStatus.IMPLEMENTED for m in mitigations)

    def test_inv_sec_ui_002_no_client_mutation(self) -> None:
        """INV-SEC-UI-002: No client-side mutation of control plane state."""
        registry = ThreatModelRegistry()
        mitigations = registry.get_mitigations_by_invariant("INV-SEC-UI-002")
        assert len(mitigations) >= 1

    def test_inv_sec_ui_003_authentication(self) -> None:
        """INV-SEC-UI-003: All API calls require authentication."""
        registry = ThreatModelRegistry()
        mitigations = registry.get_mitigations_by_invariant("INV-SEC-UI-003")
        assert len(mitigations) >= 2

    def test_inv_sec_ui_004_rate_limiting(self) -> None:
        """INV-SEC-UI-004: Rate limiting enforced on all endpoints."""
        registry = ThreatModelRegistry()
        mitigations = registry.get_mitigations_by_invariant("INV-SEC-UI-004")
        assert len(mitigations) >= 1

    def test_inv_sec_ui_005_audit_logging(self) -> None:
        """INV-SEC-UI-005: Audit logging for all security-relevant actions."""
        registry = ThreatModelRegistry()
        mitigations = registry.get_mitigations_by_invariant("INV-SEC-UI-005")
        assert len(mitigations) >= 1
