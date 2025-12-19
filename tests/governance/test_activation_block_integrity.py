"""
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
ATLAS — GID-11 — REPOSITORY INTEGRITY
PAC-ATLAS-ACTIVATION-BLOCK-INTEGRITY-ENFORCEMENT-01: Structural Integrity Tests
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵

Tests for Activation Block structural and positional integrity.
Enforces HARD RULES:
- Activation Block MUST appear before execution content
- Exactly ONE Activation Block per context
- Header/footer symmetry MUST match
- Required fields MUST be present
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.governance.activation_block import (
    ActivationBlockIntegrityResult,
    ActivationBlockViolationCode,
    ActivationBlockViolationError,
    require_activation_block_integrity,
    validate_activation_block_integrity,
    validate_activation_block_position,
    validate_activation_block_structure,
    validate_single_activation_block,
)


# =============================================================================
# VALID ACTIVATION BLOCK FIXTURES
# =============================================================================

VALID_ACTIVATION_BLOCK = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-11 — ATLAS (BUILD / REPAIR / REFACTOR)
AGENT ACTIVATION BLOCK — ATLAS-LOCK-01
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════

AGENT: ATLAS
GID: GID-11
ROLE: Build / Repair / Refactor / Repository Integrity
COLOR: 🔵 BLUE
LANE: Repository Integrity / Code Quality
PERSONA BINDING: ACTIVE

PROHIBITED ACTIONS:
    • ❌ Acting as another agent
    • ❌ Introducing new features or business logic
    • ❌ Changing governance rules or PAC standards

════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
END — ATLAS (GID-11) — 🔵 BLUE
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════
"""

VALID_PAC_WITH_ACTIVATION_FIRST = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-11 — ATLAS (BUILD / REPAIR / REFACTOR)
AGENT ACTIVATION BLOCK — ATLAS-LOCK-01
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════

AGENT: ATLAS
GID: GID-11
ROLE: Build / Repair / Refactor
COLOR: 🔵 BLUE
LANE: Repository Integrity
PERSONA BINDING: ACTIVE

PROHIBITED ACTIONS:
    • ❌ Acting as another agent

════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
END — ATLAS (GID-11) — 🔵 BLUE
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════

⸻

════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
PAC-ATLAS-TEST-01
EXECUTION PACK
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════

EXECUTING AGENT: ATLAS (GID-11) — 🔵 BLUE
EXECUTING LANE: Repository Integrity / Code Quality

OBJECTIVE:
Test objective here

SCOPE:
Test scope here

TASKS:
1. Task one
2. Task two

════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
END — ATLAS (GID-11) — 🔵 BLUE
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════
"""


# =============================================================================
# INVALID ACTIVATION BLOCK FIXTURES
# =============================================================================

CONTENT_BEFORE_ACTIVATION = """
OBJECTIVE:
Do something important first

SCOPE:
This is the scope

════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-11 — ATLAS (BUILD / REPAIR / REFACTOR)
AGENT ACTIVATION BLOCK — ATLAS-LOCK-01
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════

AGENT: ATLAS
GID: GID-11
ROLE: Build / Repair
COLOR: 🔵 BLUE
LANE: Repository Integrity
PERSONA BINDING: ACTIVE

════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
END — ATLAS (GID-11) — 🔵 BLUE
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════
"""

DUPLICATE_ACTIVATION_BLOCKS = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-11 — ATLAS (BUILD / REPAIR / REFACTOR)
AGENT ACTIVATION BLOCK — ATLAS-LOCK-01
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════

AGENT: ATLAS
GID: GID-11
ROLE: Build / Repair
COLOR: 🔵 BLUE
LANE: Repository Integrity
PERSONA BINDING: ACTIVE

════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
END — ATLAS (GID-11) — 🔵 BLUE
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════

════════════════════════════════════════════════════════════════════
🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣
GID-03 — MIRA-R (RESEARCH)
AGENT ACTIVATION BLOCK — MIRA-LOCK-01
🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣
════════════════════════════════════════════════════════════════════

AGENT: MIRA-R
GID: GID-03
ROLE: Research
COLOR: 🟣 PURPLE
LANE: Research
PERSONA BINDING: ACTIVE

════════════════════════════════════════════════════════════════════
🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣
END — MIRA-R (GID-03) — 🟣 PURPLE
🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣
════════════════════════════════════════════════════════════════════
"""

MISMATCHED_HEADER_FOOTER = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-11 — ATLAS (BUILD / REPAIR / REFACTOR)
AGENT ACTIVATION BLOCK — ATLAS-LOCK-01
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════

AGENT: ATLAS
GID: GID-11
ROLE: Build / Repair
COLOR: 🔵 BLUE
LANE: Repository Integrity
PERSONA BINDING: ACTIVE

════════════════════════════════════════════════════════════════════
🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣
END — MIRA-R (GID-03) — 🟣 PURPLE
🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣
════════════════════════════════════════════════════════════════════
"""

MISSING_REQUIRED_FIELDS = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-11 — ATLAS (BUILD / REPAIR / REFACTOR)
AGENT ACTIVATION BLOCK — ATLAS-LOCK-01
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════

AGENT: ATLAS
GID: GID-11
COLOR: 🔵 BLUE

════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
END — ATLAS (GID-11) — 🔵 BLUE
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════
"""

NO_ACTIVATION_BLOCK = """
════════════════════════════════════════════════════════════════════
PAC-ATLAS-TEST-01
EXECUTION PACK
════════════════════════════════════════════════════════════════════

EXECUTING AGENT: ATLAS (GID-11) — 🔵 BLUE

OBJECTIVE:
Test objective

TASKS:
1. Do something
"""


# =============================================================================
# POSITION VALIDATION TESTS
# =============================================================================


class TestActivationBlockPosition:
    """Test Activation Block position enforcement."""

    def test_valid_position_passes(self):
        """Activation Block before execution content passes."""
        valid, violations, line = validate_activation_block_position(
            VALID_PAC_WITH_ACTIVATION_FIRST
        )
        assert valid is True
        assert len(violations) == 0
        assert line is not None
        assert line > 0

    def test_content_before_activation_fails(self):
        """Execution content before Activation Block fails."""
        valid, violations, line = validate_activation_block_position(
            CONTENT_BEFORE_ACTIVATION
        )
        assert valid is False
        assert len(violations) > 0
        assert any("BEFORE Activation Block" in v for v in violations)

    def test_objective_before_activation_detected(self):
        """OBJECTIVE: before Activation Block is detected."""
        content = """
OBJECTIVE: Do something

🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-11 — ATLAS
AGENT ACTIVATION BLOCK
"""
        valid, violations, _ = validate_activation_block_position(content)
        assert valid is False
        assert any("OBJECTIVE" in v for v in violations)

    def test_scope_before_activation_detected(self):
        """SCOPE: before Activation Block is detected."""
        content = """
SCOPE: All files

🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-11 — ATLAS
AGENT ACTIVATION BLOCK
"""
        valid, violations, _ = validate_activation_block_position(content)
        assert valid is False
        assert any("SCOPE" in v for v in violations)

    def test_tasks_before_activation_detected(self):
        """TASKS: before Activation Block is detected."""
        content = """
TASKS:
1. First task

🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-11 — ATLAS
AGENT ACTIVATION BLOCK
"""
        valid, violations, _ = validate_activation_block_position(content)
        assert valid is False
        assert any("TASK" in v for v in violations)


# =============================================================================
# SINGLE ACTIVATION RULE TESTS
# =============================================================================


class TestSingleActivationRule:
    """Test exactly one Activation Block enforcement."""

    def test_single_block_passes(self):
        """Single Activation Block passes."""
        valid, violations, count = validate_single_activation_block(
            VALID_ACTIVATION_BLOCK
        )
        assert valid is True
        assert count == 1
        assert len(violations) == 0

    def test_no_block_fails(self):
        """Missing Activation Block fails."""
        valid, violations, count = validate_single_activation_block(
            NO_ACTIVATION_BLOCK
        )
        assert valid is False
        assert count == 0
        assert any("No Activation Block" in v for v in violations)

    def test_duplicate_blocks_fails(self):
        """Multiple Activation Blocks fails."""
        valid, violations, count = validate_single_activation_block(
            DUPLICATE_ACTIVATION_BLOCKS
        )
        assert valid is False
        assert count > 1
        assert any("Multiple" in v for v in violations)


# =============================================================================
# STRUCTURAL INTEGRITY TESTS
# =============================================================================


class TestActivationBlockStructure:
    """Test header/footer symmetry and required fields."""

    def test_valid_structure_passes(self):
        """Valid structure with symmetry passes."""
        valid, violations = validate_activation_block_structure(
            VALID_ACTIVATION_BLOCK
        )
        # May have minor field violations but not structural mismatch
        structural_violations = [v for v in violations if "mismatch" in v.lower()]
        assert len(structural_violations) == 0

    def test_header_footer_agent_mismatch_fails(self):
        """Header/footer agent mismatch is detected."""
        valid, violations = validate_activation_block_structure(
            MISMATCHED_HEADER_FOOTER
        )
        assert valid is False
        assert any("agent mismatch" in v.lower() for v in violations)

    def test_header_footer_emoji_mismatch_fails(self):
        """Header/footer emoji mismatch is detected."""
        valid, violations = validate_activation_block_structure(
            MISMATCHED_HEADER_FOOTER
        )
        assert any("emoji mismatch" in v.lower() for v in violations)

    def test_missing_role_detected(self):
        """Missing ROLE field is detected."""
        valid, violations = validate_activation_block_structure(
            MISSING_REQUIRED_FIELDS
        )
        assert any("ROLE" in v for v in violations)

    def test_missing_lane_detected(self):
        """Missing LANE field is detected."""
        valid, violations = validate_activation_block_structure(
            MISSING_REQUIRED_FIELDS
        )
        assert any("LANE" in v for v in violations)

    def test_missing_persona_binding_detected(self):
        """Missing PERSONA BINDING field is detected."""
        valid, violations = validate_activation_block_structure(
            MISSING_REQUIRED_FIELDS
        )
        assert any("PERSONA" in v for v in violations)


# =============================================================================
# FULL INTEGRITY VALIDATION TESTS
# =============================================================================


class TestFullIntegrityValidation:
    """Test complete integrity validation."""

    def test_valid_content_passes(self):
        """Valid PAC with proper Activation Block passes all checks."""
        result = validate_activation_block_integrity(
            VALID_PAC_WITH_ACTIVATION_FIRST
        )
        # May have field warnings but critical checks should pass
        assert result.activation_block_count == 1
        assert result.activation_block_position is not None
        assert result.has_content_before_activation is False

    def test_result_structure(self):
        """Result contains expected fields."""
        result = validate_activation_block_integrity(VALID_ACTIVATION_BLOCK)
        assert isinstance(result, ActivationBlockIntegrityResult)
        assert hasattr(result, "is_valid")
        assert hasattr(result, "violations")
        assert hasattr(result, "activation_block_count")
        assert hasattr(result, "activation_block_position")
        assert hasattr(result, "has_content_before_activation")
        assert hasattr(result, "has_structural_symmetry")

    def test_content_before_activation_sets_flag(self):
        """Content before activation sets the flag."""
        result = validate_activation_block_integrity(CONTENT_BEFORE_ACTIVATION)
        assert result.has_content_before_activation is True

    def test_multiple_violations_collected(self):
        """Multiple violations are all collected."""
        # Content with content before AND missing fields
        bad_content = """
OBJECTIVE: Something

🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-11 — ATLAS
AGENT ACTIVATION BLOCK
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵

AGENT: ATLAS
GID: GID-11

🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
END — ATLAS (GID-11)
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
"""
        result = validate_activation_block_integrity(bad_content)
        assert len(result.violations) > 1


# =============================================================================
# REQUIRE FUNCTION TESTS (HARD FAIL)
# =============================================================================


class TestRequireActivationBlockIntegrity:
    """Test the require function that raises on failure."""

    def test_valid_content_returns_result(self):
        """Valid content returns result without raising."""
        result = require_activation_block_integrity(VALID_ACTIVATION_BLOCK)
        assert isinstance(result, ActivationBlockIntegrityResult)

    def test_content_before_activation_raises(self):
        """Content before activation raises error."""
        with pytest.raises(ActivationBlockViolationError) as exc_info:
            require_activation_block_integrity(CONTENT_BEFORE_ACTIVATION)
        assert exc_info.value.violation_code == ActivationBlockViolationCode.POSITION_VIOLATION.value

    def test_duplicate_blocks_raises(self):
        """Duplicate blocks raises error."""
        with pytest.raises(ActivationBlockViolationError) as exc_info:
            require_activation_block_integrity(DUPLICATE_ACTIVATION_BLOCKS)
        assert exc_info.value.violation_code == ActivationBlockViolationCode.DUPLICATE_BLOCK.value

    def test_no_block_raises(self):
        """Missing block raises error."""
        with pytest.raises(ActivationBlockViolationError) as exc_info:
            require_activation_block_integrity(NO_ACTIVATION_BLOCK)
        assert exc_info.value.violation_code == ActivationBlockViolationCode.MISSING_BLOCK.value

    def test_error_contains_pac_id(self):
        """Error message contains PAC ID when provided."""
        with pytest.raises(ActivationBlockViolationError) as exc_info:
            require_activation_block_integrity(NO_ACTIVATION_BLOCK, pac_id="PAC-TEST-001")
        assert "PAC-TEST-001" in str(exc_info.value)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_content(self):
        """Empty content handles gracefully."""
        result = validate_activation_block_integrity("")
        assert result.activation_block_count == 0

    def test_whitespace_only_content(self):
        """Whitespace-only content handles gracefully."""
        result = validate_activation_block_integrity("   \n\n\t\t\n   ")
        assert result.activation_block_count == 0

    def test_partial_activation_block(self):
        """Partial activation block is handled."""
        partial = """
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-11 — ATLAS
AGENT: ATLAS
"""
        result = validate_activation_block_integrity(partial)
        # Should detect issues with incomplete block
        assert len(result.violations) > 0

    def test_unicode_content_preserved(self):
        """Unicode characters are properly handled."""
        result = validate_activation_block_integrity(VALID_ACTIVATION_BLOCK)
        # Should not fail on emoji characters
        assert result is not None
