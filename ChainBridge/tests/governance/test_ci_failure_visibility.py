#!/usr/bin/env python3
"""
Tests for CI Failure Visibility System
PAC-DAN-P44-GOVERNANCE-CI-FAILURE-VISIBILITY-AUTO-REMEDIATION-01

Tests:
  - Failure classification accuracy
  - Remediation hint generation
  - Severity assignment
  - Summary formatting
  - Zero silent failures guarantee
"""

import pytest
import sys
from pathlib import Path

# Add tools/governance to path
TOOLS_DIR = Path(__file__).parent.parent.parent / "tools" / "governance"
sys.path.insert(0, str(TOOLS_DIR))

from ci_failure_classifier import (
    FailureClassifier,
    FailureClass,
    FailureSeverity,
    FailureSummary,
    ClassifiedFailure,
    format_failure_summary,
    format_failure_json,
)


class TestFailureClassifier:
    """Test FailureClassifier classification accuracy."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return FailureClassifier()

    # CONFIG class tests
    def test_classify_config_g0_001(self, classifier):
        """G0_001 should be classified as CONFIG."""
        result = classifier.classify("G0_001")
        assert result.failure_class == FailureClass.CONFIG
        assert result.error_code == "G0_001"

    def test_classify_config_rg_001(self, classifier):
        """RG_001 should be classified as CONFIG."""
        result = classifier.classify("RG_001")
        assert result.failure_class == FailureClass.CONFIG

    def test_classify_config_bsrg_001(self, classifier):
        """BSRG_001 should be classified as CONFIG."""
        result = classifier.classify("BSRG_001")
        assert result.failure_class == FailureClass.CONFIG

    # REGRESSION class tests
    def test_classify_regression_gs_094(self, classifier):
        """GS_094 should be classified as REGRESSION."""
        result = classifier.classify("GS_094")
        assert result.failure_class == FailureClass.REGRESSION
        assert result.severity == FailureSeverity.CRITICAL

    def test_classify_regression_gs_115(self, classifier):
        """GS_115 should be classified as REGRESSION."""
        result = classifier.classify("GS_115")
        assert result.failure_class == FailureClass.REGRESSION

    # DRIFT class tests
    def test_classify_drift_gs_095(self, classifier):
        """GS_095 should be classified as DRIFT."""
        result = classifier.classify("GS_095")
        assert result.failure_class == FailureClass.DRIFT
        assert result.severity == FailureSeverity.CRITICAL

    def test_classify_drift_gs_060(self, classifier):
        """GS_060 should be classified as DRIFT."""
        result = classifier.classify("GS_060")
        assert result.failure_class == FailureClass.DRIFT

    # SEQUENTIAL class tests
    def test_classify_sequential_gs_096(self, classifier):
        """GS_096 should be classified as SEQUENTIAL."""
        result = classifier.classify("GS_096")
        assert result.failure_class == FailureClass.SEQUENTIAL
        assert result.severity == FailureSeverity.CRITICAL

    def test_classify_sequential_gs_110(self, classifier):
        """GS_110 should be classified as SEQUENTIAL."""
        result = classifier.classify("GS_110")
        assert result.failure_class == FailureClass.SEQUENTIAL

    def test_classify_sequential_gs_111(self, classifier):
        """GS_111 should be classified as SEQUENTIAL."""
        result = classifier.classify("GS_111")
        assert result.failure_class == FailureClass.SEQUENTIAL
        assert result.severity == FailureSeverity.CRITICAL

    # RUNTIME class tests
    def test_classify_runtime_g0_003(self, classifier):
        """G0_003 should be classified as RUNTIME."""
        result = classifier.classify("G0_003")
        assert result.failure_class == FailureClass.RUNTIME

    def test_classify_runtime_wrp_001(self, classifier):
        """WRP_001 should be classified as RUNTIME."""
        result = classifier.classify("WRP_001")
        assert result.failure_class == FailureClass.RUNTIME

    def test_classify_runtime_gs_090(self, classifier):
        """GS_090 should be classified as RUNTIME."""
        result = classifier.classify("GS_090")
        assert result.failure_class == FailureClass.RUNTIME
        assert result.severity == FailureSeverity.CRITICAL


class TestUnknownErrors:
    """Test FAIL_CLOSED behavior for unknown errors."""

    @pytest.fixture
    def classifier(self):
        return FailureClassifier()

    def test_unknown_error_classified_as_unknown(self, classifier):
        """Unknown errors should be classified as UNKNOWN."""
        result = classifier.classify("FAKE_ERROR_999")
        assert result.failure_class == FailureClass.UNKNOWN

    def test_unknown_error_has_remediation(self, classifier):
        """Unknown errors should have remediation hint."""
        result = classifier.classify("UNKNOWN_CODE")
        assert result.remediation_hint is not None
        assert "BENSON" in result.remediation_hint

    def test_unknown_error_action_is_escalate(self, classifier):
        """Unknown errors should have ESCALATE_TO_BENSON action."""
        result = classifier.classify("NOT_A_REAL_CODE")
        assert result.agent_action == "ESCALATE_TO_BENSON"

    def test_zero_silent_failures(self, classifier):
        """No error code should result in None or empty result."""
        test_codes = [
            "G0_001", "GS_094", "UNKNOWN", "", "random_text", "123"
        ]
        for code in test_codes:
            result = classifier.classify(code)
            assert result is not None
            assert result.failure_class is not None
            assert result.remediation_hint is not None


class TestRemediationHints:
    """Test remediation hint generation."""

    @pytest.fixture
    def classifier(self):
        return FailureClassifier()

    def test_g0_001_remediation(self, classifier):
        """G0_001 should have block addition hint."""
        result = classifier.classify("G0_001")
        assert "block" in result.remediation_hint.lower()
        assert result.agent_action == "ADD_MISSING_BLOCK"

    def test_gs_094_remediation(self, classifier):
        """GS_094 should reference baseline."""
        result = classifier.classify("GS_094")
        assert "baseline" in result.remediation_hint.lower()

    def test_gs_110_remediation(self, classifier):
        """GS_110 should reference WRAP creation."""
        result = classifier.classify("GS_110")
        assert "WRAP" in result.remediation_hint
        assert result.agent_action == "CREATE_MISSING_WRAP"

    def test_documentation_ref_present(self, classifier):
        """Known errors should have documentation reference."""
        result = classifier.classify("G0_001")
        assert result.documentation_ref is not None


class TestFailureSummary:
    """Test FailureSummary aggregation."""

    @pytest.fixture
    def classifier(self):
        return FailureClassifier()

    def test_summary_counts_by_class(self, classifier):
        """Summary should count failures by class."""
        codes = ["G0_001", "G0_002", "GS_094", "GS_110"]
        summary = classifier.classify_multiple(codes)

        assert summary.by_class[FailureClass.CONFIG] == 2
        assert summary.by_class[FailureClass.REGRESSION] == 1
        assert summary.by_class[FailureClass.SEQUENTIAL] == 1

    def test_summary_counts_by_severity(self, classifier):
        """Summary should count failures by severity."""
        codes = ["GS_094", "GS_095", "G0_005"]
        summary = classifier.classify_multiple(codes)

        assert summary.by_severity[FailureSeverity.CRITICAL] == 2
        assert summary.by_severity[FailureSeverity.MEDIUM] == 1

    def test_summary_total(self, classifier):
        """Summary should track total failures."""
        codes = ["G0_001", "GS_094", "GS_110"]
        summary = classifier.classify_multiple(codes)

        assert summary.total_failures == 3

    def test_summary_blocking_detection(self, classifier):
        """Summary should detect blocking failures."""
        # With critical
        codes_critical = ["GS_094", "G0_001"]
        summary_critical = classifier.classify_multiple(codes_critical)
        assert summary_critical.has_blocking_failures is True

        # Without critical
        codes_non_critical = ["G0_005", "G0_006"]
        summary_non_critical = classifier.classify_multiple(codes_non_critical)
        assert summary_non_critical.has_blocking_failures is False

    def test_summary_exit_code(self, classifier):
        """Summary should provide correct exit code."""
        # Critical → exit 2
        summary_critical = classifier.classify_multiple(["GS_094"])
        assert summary_critical.exit_code == 2

        # Non-critical failures → exit 1
        summary_failures = classifier.classify_multiple(["G0_005"])
        assert summary_failures.exit_code == 1

        # No failures → exit 0
        empty_summary = FailureSummary()
        assert empty_summary.exit_code == 0


class TestOutputFormatting:
    """Test output formatting functions."""

    @pytest.fixture
    def classifier(self):
        return FailureClassifier()

    def test_format_failure_summary_contains_header(self, classifier):
        """Formatted summary should contain header."""
        summary = classifier.classify_multiple(["G0_001"])
        output = format_failure_summary(summary, use_color=False)

        assert "CI FAILURE SUMMARY" in output

    def test_format_failure_summary_contains_remediation(self, classifier):
        """Formatted summary should contain remediation hints."""
        summary = classifier.classify_multiple(["G0_001"])
        output = format_failure_summary(summary, use_color=False)

        assert "Remediation" in output

    def test_format_failure_summary_shows_blocked(self, classifier):
        """Formatted summary should show BLOCKED for critical."""
        summary = classifier.classify_multiple(["GS_094"])
        output = format_failure_summary(summary, use_color=False)

        assert "BLOCKED" in output

    def test_format_failure_json_structure(self, classifier):
        """JSON output should have required structure."""
        summary = classifier.classify_multiple(["G0_001", "GS_094"])
        json_output = format_failure_json(summary)

        assert "status" in json_output
        assert "exit_code" in json_output
        assert "total_failures" in json_output
        assert "by_class" in json_output
        assert "by_severity" in json_output
        assert "failures" in json_output

    def test_format_failure_json_failures_complete(self, classifier):
        """JSON failures should have all required fields."""
        summary = classifier.classify_multiple(["G0_001"])
        json_output = format_failure_json(summary)

        failure = json_output["failures"][0]
        assert "error_code" in failure
        assert "class" in failure
        assert "severity" in failure
        assert "remediation_hint" in failure
        assert "agent_action" in failure


class TestCodeNormalization:
    """Test error code normalization."""

    @pytest.fixture
    def classifier(self):
        return FailureClassifier()

    def test_normalize_bracketed_code(self, classifier):
        """Should handle bracketed codes: [G0_001]."""
        result = classifier.classify("[G0_001]")
        assert result.error_code == "G0_001"
        assert result.failure_class == FailureClass.CONFIG

    def test_normalize_lowercase(self, classifier):
        """Should handle lowercase codes."""
        result = classifier.classify("g0_001")
        assert result.error_code == "G0_001"

    def test_normalize_with_message(self, classifier):
        """Should extract code from message format."""
        result = classifier.classify("[G0_001] Missing required block")
        assert result.error_code == "G0_001"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def classifier(self):
        return FailureClassifier()

    def test_empty_error_list(self, classifier):
        """Should handle empty error list."""
        summary = classifier.classify_multiple([])
        assert summary.total_failures == 0
        assert summary.exit_code == 0

    def test_duplicate_errors(self, classifier):
        """Should count duplicate errors separately."""
        summary = classifier.classify_multiple(["G0_001", "G0_001", "G0_001"])
        assert summary.total_failures == 3
        assert summary.by_class[FailureClass.CONFIG] == 3

    def test_all_failure_classes_covered(self, classifier):
        """Each failure class should have at least one mapped code."""
        codes_by_class = {
            FailureClass.CONFIG: "G0_001",
            FailureClass.REGRESSION: "GS_094",
            FailureClass.DRIFT: "GS_095",
            FailureClass.SEQUENTIAL: "GS_110",
            FailureClass.RUNTIME: "WRP_001",
        }

        for expected_class, code in codes_by_class.items():
            result = classifier.classify(code)
            assert result.failure_class == expected_class, f"{code} should be {expected_class}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
