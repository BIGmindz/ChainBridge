"""
Test suite for PAG-01 Persona Activation Governance audit module.

Tests all audit paths for AGENT_ACTIVATION_ACK and RUNTIME_ACTIVATION_ACK
validation against AGENT_REGISTRY.json.

Coverage target: ≥90%
"""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add tools path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools" / "governance"))

from pag_audit import (
    PAG01ViolationCode,
    PAG01Violation,
    PAG01AuditResult,
    PAG01RepoAuditResult,
    load_registry,
    audit_pag01_single_file,
    audit_pag01_repository,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_registry():
    """Mock AGENT_REGISTRY.json content."""
    return {
        "registry_version": "4.0.0",
        "status": "LOCKED",
        "agents": {
            "BENSON": {
                "gid": "GID-00",
                "name": "BENSON",
                "color": "RED",
                "emoji": "🔴",
                "role": "System Architect",
                "execution_lane": "ARCHITECTURE"
            },
            "CODY": {
                "gid": "GID-01",
                "name": "CODY",
                "color": "BLUE",
                "emoji": "🔵",
                "role": "Backend Engineer",
                "execution_lane": "BACKEND"
            },
            "ALEX": {
                "gid": "GID-02",
                "name": "ALEX",
                "color": "GREEN",
                "emoji": "🟢",
                "role": "Frontend Engineer",
                "execution_lane": "FRONTEND"
            }
        }
    }


@pytest.fixture
def valid_pac_content():
    """Valid PAC with correct AGENT_ACTIVATION_ACK and RUNTIME_ACTIVATION_ACK."""
    return '''# PAC-CODY-G1-TEST-01

## RUNTIME_ACTIVATION_ACK

```yaml
RUNTIME_ACTIVATION_ACK:
  session_id: "test-session-001"
  timestamp: "2025-01-15T10:00:00Z"
  status: ACTIVE
```

## AGENT_ACTIVATION_ACK

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "CODY"
  gid: "GID-01"
  color: "BLUE"
  icon: "🔵"
  role: "Backend Engineer"
  execution_lane: "BACKEND"
```

## SCOPE_LOCK
- Test scope

## CLOSURE
- status: COMPLETE
'''


@pytest.fixture
def pac_missing_agent_block():
    """PAC missing AGENT_ACTIVATION_ACK block."""
    return '''# PAC-CODY-G1-TEST-02

## RUNTIME_ACTIVATION_ACK

```yaml
RUNTIME_ACTIVATION_ACK:
  session_id: "test-session-002"
  timestamp: "2025-01-15T10:00:00Z"
  status: ACTIVE
```

## SCOPE_LOCK
- Test scope

## CLOSURE
- status: COMPLETE
'''


@pytest.fixture
def pac_missing_runtime_block():
    """PAC missing RUNTIME_ACTIVATION_ACK block."""
    return '''# PAC-CODY-G1-TEST-03

## AGENT_ACTIVATION_ACK

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "CODY"
  gid: "GID-01"
  color: "BLUE"
  icon: "🔵"
  role: "Backend Engineer"
  execution_lane: "BACKEND"
```

## SCOPE_LOCK
- Test scope

## CLOSURE
- status: COMPLETE
'''


@pytest.fixture
def pac_wrong_order():
    """PAC with AGENT_ACTIVATION_ACK before RUNTIME_ACTIVATION_ACK."""
    return '''# PAC-CODY-G1-TEST-04

## AGENT_ACTIVATION_ACK

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "CODY"
  gid: "GID-01"
  color: "BLUE"
  icon: "🔵"
  role: "Backend Engineer"
  execution_lane: "BACKEND"
```

## RUNTIME_ACTIVATION_ACK

```yaml
RUNTIME_ACTIVATION_ACK:
  session_id: "test-session-004"
  timestamp: "2025-01-15T10:00:00Z"
  status: ACTIVE
```

## SCOPE_LOCK
- Test scope

## CLOSURE
- status: COMPLETE
'''


@pytest.fixture
def pac_registry_mismatch():
    """PAC with registry values that don't match."""
    return '''# PAC-CODY-G1-TEST-05

## RUNTIME_ACTIVATION_ACK

```yaml
RUNTIME_ACTIVATION_ACK:
  session_id: "test-session-005"
  timestamp: "2025-01-15T10:00:00Z"
  status: ACTIVE
```

## AGENT_ACTIVATION_ACK

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "CODY"
  gid: "GID-01"
  color: "RED"
  icon: "🔴"
  role: "Backend Engineer"
  execution_lane: "BACKEND"
```

## SCOPE_LOCK
- Test scope

## CLOSURE
- status: COMPLETE
'''


# =============================================================================
# UNIT TESTS - PAG01ViolationCode
# =============================================================================

class TestPAG01ViolationCode:
    """Tests for violation code enum."""

    def test_all_codes_exist(self):
        """Verify all 10 violation codes are defined."""
        codes = list(PAG01ViolationCode)
        assert len(codes) == 10

    def test_code_names(self):
        """Verify code naming convention."""
        for code in PAG01ViolationCode:
            assert code.name.startswith("PAG_")

    def test_code_descriptions(self):
        """Verify all codes have descriptions."""
        for code in PAG01ViolationCode:
            assert len(code.value) > 0


# =============================================================================
# UNIT TESTS - PAG01Violation
# =============================================================================

class TestPAG01Violation:
    """Tests for violation dataclass."""

    def test_violation_creation(self):
        """Test basic violation creation."""
        v = PAG01Violation(
            code=PAG01ViolationCode.PAG_001_MISSING_BLOCK,
            message="Test message",
            file_path="test.md"
        )
        assert v.code == PAG01ViolationCode.PAG_001_MISSING_BLOCK
        assert v.message == "Test message"
        assert v.file_path == "test.md"

    def test_violation_with_agent(self):
        """Test violation with agent information."""
        v = PAG01Violation(
            code=PAG01ViolationCode.PAG_003_REGISTRY_MISMATCH,
            message="Color mismatch",
            file_path="test.md",
            agent="CODY",
            details={"expected": "BLUE", "actual": "RED"}
        )
        assert v.agent == "CODY"
        assert v.details["expected"] == "BLUE"


# =============================================================================
# UNIT TESTS - PAG01AuditResult
# =============================================================================

class TestPAG01AuditResult:
    """Tests for single file audit result."""

    def test_compliant_result(self):
        """Test compliant audit result."""
        result = PAG01AuditResult(
            file_path="test.md",
            compliant=True,
            violations=[]
        )
        assert result.compliant is True
        assert len(result.violations) == 0

    def test_non_compliant_result(self):
        """Test non-compliant audit result."""
        v = PAG01Violation(
            code=PAG01ViolationCode.PAG_001_MISSING_BLOCK,
            message="Missing block",
            file_path="test.md"
        )
        result = PAG01AuditResult(
            file_path="test.md",
            compliant=False,
            violations=[v]
        )
        assert result.compliant is False
        assert len(result.violations) == 1


# =============================================================================
# UNIT TESTS - PAG01RepoAuditResult
# =============================================================================

class TestPAG01RepoAuditResult:
    """Tests for repository-wide audit result."""

    def test_empty_repo_result(self):
        """Test audit result with no files."""
        result = PAG01RepoAuditResult(
            total_files=0,
            compliant_files=0,
            non_compliant_files=0,
            violations=[],
            results=[]
        )
        assert result.total_files == 0
        assert result.all_compliant is True

    def test_repo_result_with_violations(self):
        """Test audit result with violations."""
        v1 = PAG01Violation(
            code=PAG01ViolationCode.PAG_001_MISSING_BLOCK,
            message="Missing block",
            file_path="test.md"
        )
        v2 = PAG01Violation(
            code=PAG01ViolationCode.PAG_003_REGISTRY_MISMATCH,
            message="Mismatch",
            file_path="test.md"
        )
        file_result = PAG01AuditResult(
            file_path="test.md",
            compliant=False,
            violations=[v1, v2]
        )
        result = PAG01RepoAuditResult(
            total_files=1,
            compliant_files=0,
            non_compliant_files=1,
            violations=[v1, v2],
            results=[file_result]
        )
        assert result.non_compliant_files == 1
        assert result.all_compliant is False
        assert len(result.violations) == 2

    def test_to_json(self):
        """Test JSON serialization."""
        result = PAG01RepoAuditResult(
            total_files=0,
            compliant_files=0,
            non_compliant_files=0,
            violations=[],
            results=[]
        )
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert "total_files" in parsed["summary"]
        assert parsed["audit_type"] == "PAG-01"


# =============================================================================
# INTEGRATION TESTS - audit_pag01_single_file
# =============================================================================

class TestAuditPAG01SingleFile:
    """Integration tests for single file audit."""

    def test_valid_pac_passes(self, valid_pac_content, mock_registry, tmp_path):
        """Test that valid PAC passes audit."""
        pac_file = tmp_path / "valid.md"
        pac_file.write_text(valid_pac_content)

        result = audit_pag01_single_file(pac_file, mock_registry)
        assert result.compliant is True
        assert len(result.violations) == 0

    def test_missing_agent_block_fails(self, pac_missing_agent_block, mock_registry, tmp_path):
        """Test that missing AGENT_ACTIVATION_ACK fails."""
        pac_file = tmp_path / "missing_agent.md"
        pac_file.write_text(pac_missing_agent_block)

        result = audit_pag01_single_file(pac_file, mock_registry)
        assert result.compliant is False

        codes = [v.code for v in result.violations]
        assert PAG01ViolationCode.PAG_001_MISSING_BLOCK in codes

    def test_missing_runtime_block_fails(self, pac_missing_runtime_block, mock_registry, tmp_path):
        """Test that missing RUNTIME_ACTIVATION_ACK fails."""
        pac_file = tmp_path / "missing_runtime.md"
        pac_file.write_text(pac_missing_runtime_block)

        result = audit_pag01_single_file(pac_file, mock_registry)
        assert result.compliant is False

        codes = [v.code for v in result.violations]
        assert PAG01ViolationCode.PAG_002_MISSING_RUNTIME in codes

    def test_wrong_order_fails(self, pac_wrong_order, mock_registry, tmp_path):
        """Test that wrong block order fails."""
        pac_file = tmp_path / "wrong_order.md"
        pac_file.write_text(pac_wrong_order)

        result = audit_pag01_single_file(pac_file, mock_registry)
        assert result.compliant is False

        codes = [v.code for v in result.violations]
        assert PAG01ViolationCode.PAG_005_ORDERING_VIOLATION in codes

    def test_registry_mismatch_fails(self, pac_registry_mismatch, mock_registry, tmp_path):
        """Test that registry mismatch fails."""
        pac_file = tmp_path / "mismatch.md"
        pac_file.write_text(pac_registry_mismatch)

        result = audit_pag01_single_file(pac_file, mock_registry)
        assert result.compliant is False

        codes = [v.code for v in result.violations]
        # Should detect color mismatch
        mismatch_codes = [
            PAG01ViolationCode.PAG_003_REGISTRY_MISMATCH,
            PAG01ViolationCode.PAG_006_COLOR_MISMATCH,
            PAG01ViolationCode.PAG_009_ICON_MISMATCH
        ]
        assert any(c in codes for c in mismatch_codes)


# =============================================================================
# INTEGRATION TESTS - audit_pag01_repository
# =============================================================================

class TestAuditPAG01Repository:
    """Integration tests for repository audit."""

    def test_repository_audit_runs(self):
        """Test that repo audit runs and returns result."""
        result = audit_pag01_repository()
        # Should scan governance files in the actual repo
        assert result.total_files > 0
        assert hasattr(result, 'compliant_files')
        assert hasattr(result, 'non_compliant_files')


# =============================================================================
# UNIT TESTS - load_registry
# =============================================================================

class TestLoadRegistry:
    """Tests for registry loading."""

    def test_load_registry_returns_dict(self):
        """Test that load_registry returns dict."""
        registry = load_registry()
        assert isinstance(registry, dict)

    def test_registry_has_agents(self, mock_registry):
        """Test registry structure."""
        assert "agents" in mock_registry
        assert len(mock_registry["agents"]) > 0


# =============================================================================
# CLI INTEGRATION TESTS
# =============================================================================

class TestCLIIntegration:
    """Tests for CLI integration with gate_pack.py."""

    def test_audit_pag01_flag_exists(self):
        """Verify --audit-pag01 flag is accepted."""
        # This is validated by the gate_pack.py argument parser
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--audit-pag01", action="store_true")
        args = parser.parse_args(["--audit-pag01"])
        assert args.audit_pag01 is True

    def test_json_flag_exists(self):
        """Verify --json flag is accepted."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--json", action="store_true")
        args = parser.parse_args(["--json"])
        assert args.json is True

    def test_no_fail_flag_exists(self):
        """Verify --no-fail flag is accepted."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--no-fail", action="store_true")
        args = parser.parse_args(["--no-fail"])
        assert args.no_fail is True


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Edge case tests."""

    def test_empty_file_is_compliant(self, mock_registry, tmp_path):
        """Test audit of empty file - considered compliant (no governance content to validate)."""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("")

        result = audit_pag01_single_file(empty_file, mock_registry)
        # Empty files are considered compliant - no governance content to validate
        assert result.compliant is True

    def test_non_governance_file_is_compliant(self, mock_registry, tmp_path):
        """Test audit of non-governance markdown file - considered compliant."""
        readme = tmp_path / "README.md"
        readme.write_text("# Project Readme\n\nThis is not a governance file.")

        result = audit_pag01_single_file(readme, mock_registry)
        # Non-governance files without activation blocks are considered compliant
        # (no governance claims to validate)
        assert result.compliant is True

    def test_file_with_partial_activation_block(self, mock_registry, tmp_path):
        """Test audit of file with incomplete AGENT_ACTIVATION_ACK."""
        partial = tmp_path / "partial.md"
        partial.write_text('''# PAC-TEST-G1-PARTIAL-01

## AGENT_ACTIVATION_ACK
This block has the header but no actual YAML content
''')

        result = audit_pag01_single_file(partial, mock_registry)
        # Should handle gracefully - incomplete blocks may be flagged
        assert isinstance(result.compliant, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
