"""
Tests for PAC-BENSON-P37 Metrics Enforcement.

Authority: PAC-BENSON-P37-AGENT-PERFORMANCE-METRICS-BASELINE-AND-ENFORCEMENT-01

Tests:
- GS_080: Missing METRICS block detection
- GS_081: Missing required field detection
- GS_082: Invalid value detection
- GS_083: execution_time_ms type validation
- GS_084: quality_score range validation
- GS_085: scope_compliance boolean validation
- Legacy grandfathering
- Metrics extraction
"""

import pytest
import sys
from pathlib import Path

# Add tools/governance to path
TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools" / "governance"
sys.path.insert(0, str(TOOLS_DIR))

from gate_pack import (
    ErrorCode,
    ValidationResult,
    is_executable_artifact,
    extract_metrics_block,
    validate_metrics_block,
)
from metrics_extractor import MetricsExtractor, MetricsRecord


class TestGS080MissingMetricsBlock:
    """Test GS_080: Missing METRICS block in EXECUTABLE artifact."""

    def test_executable_without_metrics_raises_gs080(self):
        """Executable artifact without METRICS block should fail."""
        content = """# PAC-TEST-P40-EXECUTABLE-01

AGENT_ACTIVATION_ACK:
  gid: GID-001
  agent_name: ATLAS
  execution_lane: GOVERNANCE

TASKS:
- [ ] Task 1: Do something

FILES:
- file1.py
"""
        errors = validate_metrics_block(content)
        gs080_errors = [e for e in errors if e.code == ErrorCode.GS_080]
        assert len(gs080_errors) == 1
        assert "Missing METRICS block" in gs080_errors[0].message

    def test_non_executable_without_metrics_passes(self):
        """Non-executable artifact without METRICS block should pass."""
        content = """# GOVERNANCE_SCHEMA.md

This is a doctrinal document, not an executable artifact.

## Section 1
Some content here.
"""
        errors = validate_metrics_block(content)
        gs080_errors = [e for e in errors if e.code == ErrorCode.GS_080]
        assert len(gs080_errors) == 0

    def test_executable_with_metrics_passes(self):
        """Executable artifact with valid METRICS block should pass GS_080."""
        content = """# PAC-TEST-P40-EXECUTABLE-01

TASKS:
- [x] Task 1: Do something

FILES:
- file1.py

METRICS:
  execution_time_ms: 5000
  tasks_completed: 1
  tasks_total: 1
  quality_score: 0.95
  scope_compliance: true
"""
        errors = validate_metrics_block(content)
        gs080_errors = [e for e in errors if e.code == ErrorCode.GS_080]
        assert len(gs080_errors) == 0


class TestGS081MissingRequiredField:
    """Test GS_081: METRICS block missing required field."""

    def test_missing_execution_time_raises_gs081(self):
        """METRICS without execution_time_ms should fail."""
        content = """# PAC-TEST-P40-MISSING-FIELD-01

TASKS:
- [x] Task 1

METRICS:
  tasks_completed: 1
  tasks_total: 1
  quality_score: 0.95
  scope_compliance: true
"""
        errors = validate_metrics_block(content)
        gs081_errors = [e for e in errors if e.code == ErrorCode.GS_081]
        assert len(gs081_errors) == 1
        assert "execution_time_ms" in gs081_errors[0].message

    def test_missing_quality_score_raises_gs081(self):
        """METRICS without quality_score should fail."""
        content = """# PAC-TEST-P40-MISSING-QUALITY-01

TASKS:
- [x] Task 1

METRICS:
  execution_time_ms: 5000
  tasks_completed: 1
  tasks_total: 1
  scope_compliance: true
"""
        errors = validate_metrics_block(content)
        gs081_errors = [e for e in errors if e.code == ErrorCode.GS_081]
        assert len(gs081_errors) == 1
        assert "quality_score" in gs081_errors[0].message

    def test_all_required_fields_present_passes(self):
        """METRICS with all required fields should pass GS_081."""
        content = """# PAC-TEST-P40-ALL-FIELDS-01

TASKS:
- [x] Task 1

METRICS:
  execution_time_ms: 5000
  tasks_completed: 1
  tasks_total: 1
  quality_score: 0.95
  scope_compliance: true
"""
        errors = validate_metrics_block(content)
        gs081_errors = [e for e in errors if e.code == ErrorCode.GS_081]
        assert len(gs081_errors) == 0


class TestGS083ExecutionTimeValidation:
    """Test GS_083: execution_time_ms must be numeric."""

    def test_string_execution_time_raises_gs083(self):
        """Non-numeric execution_time_ms should fail."""
        content = """# PAC-TEST-P40-BAD-TIME-01

TASKS:
- [x] Task 1

METRICS:
  execution_time_ms: "five thousand"
  tasks_completed: 1
  tasks_total: 1
  quality_score: 0.95
  scope_compliance: true
"""
        errors = validate_metrics_block(content)
        gs083_errors = [e for e in errors if e.code == ErrorCode.GS_083]
        assert len(gs083_errors) == 1

    def test_numeric_execution_time_passes(self):
        """Numeric execution_time_ms should pass."""
        content = """# PAC-TEST-P40-GOOD-TIME-01

TASKS:
- [x] Task 1

METRICS:
  execution_time_ms: 5000
  tasks_completed: 1
  tasks_total: 1
  quality_score: 0.95
  scope_compliance: true
"""
        errors = validate_metrics_block(content)
        gs083_errors = [e for e in errors if e.code == ErrorCode.GS_083]
        assert len(gs083_errors) == 0


class TestGS084QualityScoreRange:
    """Test GS_084: quality_score out of valid range (0.0-1.0)."""

    def test_quality_score_above_1_raises_gs084(self):
        """quality_score > 1.0 should fail."""
        content = """# PAC-TEST-P40-BAD-SCORE-01

TASKS:
- [x] Task 1

METRICS:
  execution_time_ms: 5000
  tasks_completed: 1
  tasks_total: 1
  quality_score: 1.5
  scope_compliance: true
"""
        errors = validate_metrics_block(content)
        gs084_errors = [e for e in errors if e.code == ErrorCode.GS_084]
        assert len(gs084_errors) == 1

    def test_quality_score_below_0_raises_gs084(self):
        """quality_score < 0.0 should fail."""
        content = """# PAC-TEST-P40-NEGATIVE-SCORE-01

TASKS:
- [x] Task 1

METRICS:
  execution_time_ms: 5000
  tasks_completed: 1
  tasks_total: 1
  quality_score: -0.5
  scope_compliance: true
"""
        errors = validate_metrics_block(content)
        gs084_errors = [e for e in errors if e.code == ErrorCode.GS_084]
        assert len(gs084_errors) == 1

    def test_quality_score_in_range_passes(self):
        """quality_score in [0.0, 1.0] should pass."""
        content = """# PAC-TEST-P40-GOOD-SCORE-01

TASKS:
- [x] Task 1

METRICS:
  execution_time_ms: 5000
  tasks_completed: 1
  tasks_total: 1
  quality_score: 0.95
  scope_compliance: true
"""
        errors = validate_metrics_block(content)
        gs084_errors = [e for e in errors if e.code == ErrorCode.GS_084]
        assert len(gs084_errors) == 0


class TestGS085ScopeComplianceBoolean:
    """Test GS_085: scope_compliance must be boolean."""

    def test_string_scope_compliance_raises_gs085(self):
        """Non-boolean scope_compliance should fail."""
        content = """# PAC-TEST-P40-BAD-SCOPE-01

TASKS:
- [x] Task 1

METRICS:
  execution_time_ms: 5000
  tasks_completed: 1
  tasks_total: 1
  quality_score: 0.95
  scope_compliance: "yes"
"""
        errors = validate_metrics_block(content)
        gs085_errors = [e for e in errors if e.code == ErrorCode.GS_085]
        assert len(gs085_errors) == 1

    def test_boolean_scope_compliance_passes(self):
        """Boolean scope_compliance should pass."""
        content = """# PAC-TEST-P40-GOOD-SCOPE-01

TASKS:
- [x] Task 1

METRICS:
  execution_time_ms: 5000
  tasks_completed: 1
  tasks_total: 1
  quality_score: 0.95
  scope_compliance: true
"""
        errors = validate_metrics_block(content)
        gs085_errors = [e for e in errors if e.code == ErrorCode.GS_085]
        assert len(gs085_errors) == 0


class TestLegacyGrandfathering:
    """Test legacy artifact grandfathering."""

    def test_pre_p37_artifact_grandfathered(self):
        """Artifacts before P37 enforcement should be grandfathered."""
        content = """# PAC-BENSON-P20-LEGACY-ARTIFACT-01

Created: 2025-05-01

## TASKS
- [x] Task 1

## FILES
- file1.py
"""
        errors = validate_metrics_block(content)
        # Should have no GS_080 errors due to grandfathering
        gs080_errors = [e for e in errors if e.code == ErrorCode.GS_080]
        # Note: Grandfathering is based on PAC number (P01-P36)
        # P20 should be grandfathered
        assert len(gs080_errors) == 0


class TestIsExecutableArtifact:
    """Test is_executable_artifact() detection."""

    def test_artifact_with_tasks_is_executable(self):
        """Artifact with TASKS: block is executable."""
        content = """# PAC-TEST-P40-EXEC-01

TASKS:
- [ ] Task 1
"""
        assert is_executable_artifact(content) is True

    def test_artifact_with_files_is_executable(self):
        """Artifact with FILES: block is executable."""
        content = """# PAC-TEST-P40-FILES-01

FILES:
- file1.py
"""
        assert is_executable_artifact(content) is True

    def test_wrap_with_execution_summary_is_executable(self):
        """WRAP with EXECUTION_SUMMARY is executable."""
        content = """# WRAP-BENSON-G40-FEATURE-01

EXECUTION_SUMMARY:
Status: DONE
"""
        assert is_executable_artifact(content) is True

    def test_schema_doc_is_not_executable(self):
        """Schema documentation is not executable."""
        content = """# GOVERNANCE_SCHEMA.md

This is doctrinal content only.
"""
        assert is_executable_artifact(content) is False

    def test_registry_is_not_executable(self):
        """Registry document is not executable."""
        content = """# AGENT_REGISTRY

Agent definitions here.
"""
        assert is_executable_artifact(content) is False


class TestExtractMetricsBlock:
    """Test extract_metrics_block() parsing."""

    def test_extract_yaml_code_block(self):
        """Extract METRICS from inline YAML format."""
        content = """# Artifact

METRICS:
  execution_time_ms: 5000
  quality_score: 0.95
  tasks_completed: 1
  tasks_total: 1
  scope_compliance: true
"""
        metrics = extract_metrics_block(content)
        assert metrics is not None
        assert metrics.get("execution_time_ms") == 5000
        assert metrics.get("quality_score") == 0.95

    def test_extract_inline_yaml(self):
        """Extract METRICS from inline YAML."""
        content = """# Artifact

METRICS:
  execution_time_ms: 5000
  quality_score: 0.95
"""
        metrics = extract_metrics_block(content)
        assert metrics is not None
        assert metrics.get("execution_time_ms") == 5000

    def test_no_metrics_returns_none(self):
        """No METRICS block returns None."""
        content = """# Artifact

No metrics here.
"""
        metrics = extract_metrics_block(content)
        assert metrics is None


class TestMetricsExtractor:
    """Test MetricsExtractor class."""

    def test_extract_full_record(self):
        """Extract complete metrics record from content."""
        content = """# PAC-BENSON-P40-TEST-01

AGENT_ACTIVATION_ACK:
  gid: GID-002
  agent_name: BENSON
  execution_lane: GOVERNANCE

TASKS:
- [x] Task 1

METRICS:
  execution_time_ms: 4500
  tasks_completed: 1
  tasks_total: 1
  quality_score: 0.96
  scope_compliance: true
"""
        extractor = MetricsExtractor()
        record = extractor.extract_from_content(content)

        assert record is not None
        assert record.artifact_id == "PAC-BENSON-P40-TEST-01"
        assert record.agent_gid == "GID-002"
        assert record.agent_name == "BENSON"
        assert record.execution_time_ms == 4500
        assert record.quality_score == 0.96
        assert record.scope_compliance is True

    def test_compute_agent_baseline(self):
        """Compute baseline from multiple records."""
        extractor = MetricsExtractor()

        # Add multiple records
        extractor.records = [
            MetricsRecord(
                artifact_id="PAC-1",
                agent_gid="GID-001",
                agent_name="ATLAS",
                execution_lane="GOVERNANCE",
                timestamp="2025-06-16T00:00:00Z",
                execution_time_ms=3000,
                tasks_completed=5,
                tasks_total=5,
                quality_score=0.95,
                scope_compliance=True,
            ),
            MetricsRecord(
                artifact_id="PAC-2",
                agent_gid="GID-001",
                agent_name="ATLAS",
                execution_lane="GOVERNANCE",
                timestamp="2025-06-16T01:00:00Z",
                execution_time_ms=4000,
                tasks_completed=3,
                tasks_total=4,
                quality_score=0.98,
                scope_compliance=True,
            ),
        ]

        baseline = extractor.compute_agent_baseline("GID-001")

        assert baseline is not None
        assert baseline.agent_gid == "GID-001"
        assert baseline.avg_execution_time_ms == 3500.0
        assert baseline.avg_quality_score == 0.965
        assert baseline.scope_compliance_rate == 1.0
        assert baseline.total_executions == 2

    def test_to_ledger_format(self):
        """Convert record to ledger format."""
        extractor = MetricsExtractor()
        record = MetricsRecord(
            artifact_id="PAC-TEST-01",
            agent_gid="GID-001",
            agent_name="ATLAS",
            execution_lane="GOVERNANCE",
            timestamp="2025-06-16T00:00:00Z",
            execution_time_ms=3000,
            tasks_completed=5,
            tasks_total=5,
            quality_score=0.95,
            scope_compliance=True,
            files_created=2,
        )

        ledger = extractor.to_ledger_format(record)

        assert ledger["artifact_id"] == "PAC-TEST-01"
        assert ledger["metrics"]["execution_time_ms"] == 3000
        assert ledger["optional_metrics"]["files_created"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
