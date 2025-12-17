"""Pytest configuration for governance tests."""

from pathlib import Path

import pytest

from core.governance.drcp import reset_denial_registry


@pytest.fixture(autouse=True)
def reset_drcp_registry():
    """Reset the DRCP denial registry before each test.

    This prevents test isolation issues where denials from one test
    affect subsequent tests (RETRY_AFTER_DENY_FORBIDDEN).
    """
    reset_denial_registry()
    yield
    reset_denial_registry()


@pytest.fixture
def manifests_dir():
    """Return the path to the manifests directory."""
    return Path(__file__).parent.parent.parent / "manifests"


@pytest.fixture
def temp_manifests_dir(tmp_path):
    """Create a temporary manifests directory with valid ACMs for testing."""
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    return manifests


@pytest.fixture
def sample_cody_manifest(temp_manifests_dir):
    """Create a sample Cody manifest for testing."""
    content = """# Agent Capability Manifest — Cody (GID-01)
# Version: 1.0.0
# Status: GOVERNANCE-LOCKED

agent_id: "Cody"
gid: "GID-01"
role: "Senior Backend Engineer"
color: "Blue 🔵"
version: "1.0.0"

constraints:
  - "MUST NOT modify frontend/UI code"

capabilities:
  read:
    - "backend source code"
    - "API specifications"
    - "test suites (backend)"

  propose:
    - "backend code changes"
    - "API endpoint modifications"

  execute:
    - "local test runs"
    - "code formatting"
    - "lint fixes"

  block: []

  escalate:
    - "security implications"
    - "production deployment requests"

escalation_triggers:
  - "Change affects security"

invariants:
  - "All backend changes must have corresponding tests"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# END OF ACM — GOVERNANCE LOCKED
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    manifest_path = temp_manifests_dir / "GID-01_Cody.yaml"
    manifest_path.write_text(content)
    return manifest_path


@pytest.fixture
def sample_sam_manifest(temp_manifests_dir):
    """Create a sample Sam manifest for testing (with BLOCK authority)."""
    content = """# Agent Capability Manifest — Sam (GID-06)
# Version: 1.0.0
# Status: GOVERNANCE-LOCKED

agent_id: "Sam"
gid: "GID-06"
role: "Security & Threat Engineer"
color: "Dark Red 🔴"
version: "1.0.0"

constraints:
  - "MUST NOT approve insecure shortcuts"

capabilities:
  read:
    - "all source code (security audit)"
    - "authentication and authorization logic"

  propose:
    - "security hardening measures"

  execute: []

  block:
    - "insecure code changes"
    - "fail-open configurations"
    - "authentication bypasses"

  escalate:
    - "security posture degradation"

escalation_triggers:
  - "Security posture is degraded"

invariants:
  - "Security is never traded for convenience"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# END OF ACM — GOVERNANCE LOCKED
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    manifest_path = temp_manifests_dir / "GID-06_Sam.yaml"
    manifest_path.write_text(content)
    return manifest_path


@pytest.fixture
def sample_alex_manifest(temp_manifests_dir):
    """Create a sample ALEX manifest for testing (with BLOCK authority)."""
    content = """# Agent Capability Manifest — ALEX (GID-08)
# Version: 1.0.0
# Status: GOVERNANCE-LOCKED

agent_id: "ALEX"
gid: "GID-08"
role: "Governance & Alignment Engine"
color: "Grey ⚪"
version: "1.0.0"

constraints:
  - "MUST NOT write application code"

capabilities:
  read:
    - "all agent outputs"
    - "governance rules and policies"

  propose:
    - "governance policy clarifications"

  execute: []

  block:
    - "governance violations"
    - "identity drift"

  escalate:
    - "unresolvable governance conflicts"

escalation_triggers:
  - "Standards are violated"

invariants:
  - "Observe, validate, and block — never execute"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# END OF ACM — GOVERNANCE LOCKED
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    manifest_path = temp_manifests_dir / "GID-08_ALEX.yaml"
    manifest_path.write_text(content)
    return manifest_path
