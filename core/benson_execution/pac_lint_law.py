# ═══════════════════════════════════════════════════════════════════════════════
# BensonExecution — PAC Lint Law V1
# PAC-BENSON-EXEC-C01: BENSON EXECUTION GENESIS & IDENTITY INSTANTIATION
# Agent: Benson Execution (GID-00-EXEC) — Deterministic Execution Engine
# ═══════════════════════════════════════════════════════════════════════════════

"""
PAC Lint Law V1 — Canonical Lint Enforcement

PURPOSE:
    Enforce PAC_LINT_LAW_V1 rules mechanically.
    No interpretation. No soft validation. Deterministic pass/fail.

LINT RULES (BLOCK-LEVEL):
    LINT-001: METADATA block must exist and contain all required fields
    LINT-002: pac_id must match canonical format
    LINT-003: pac_version must be semantic version
    LINT-004: classification must be valid enum
    LINT-005: governance_tier must be valid enum
    LINT-006: issuer_gid must match GID format
    LINT-007: issued_at must be ISO8601 timestamp
    LINT-008: fail_closed must be true for LAW tier
    LINT-009: All numbered blocks must be present (BLOCK 0-19)
    LINT-010: No duplicate block numbers
    LINT-011: FINAL_STATE_DECLARATION must exist
    LINT-012: LEDGER_COMMIT_AND_ATTESTATION must exist

ENFORCEMENT:
    - Any violation → HARD REJECT
    - No warnings (only errors)
    - Fail-closed behavior
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# LINT RULE IDENTIFIERS
# ═══════════════════════════════════════════════════════════════════════════════

class LintRuleID(Enum):
    """Canonical lint rule identifiers."""
    
    LINT_001 = "LINT-001"  # METADATA block required
    LINT_002 = "LINT-002"  # pac_id format
    LINT_003 = "LINT-003"  # pac_version semantic
    LINT_004 = "LINT-004"  # classification valid
    LINT_005 = "LINT-005"  # governance_tier valid
    LINT_006 = "LINT-006"  # issuer_gid format
    LINT_007 = "LINT-007"  # issued_at ISO8601
    LINT_008 = "LINT_008"  # fail_closed for LAW tier
    LINT_009 = "LINT-009"  # All blocks present
    LINT_010 = "LINT-010"  # No duplicate blocks
    LINT_011 = "LINT-011"  # FINAL_STATE_DECLARATION required
    LINT_012 = "LINT-012"  # LEDGER_COMMIT required
    LINT_013 = "LINT-013"  # Block ordering
    LINT_014 = "LINT-014"  # Required block fields


# ═══════════════════════════════════════════════════════════════════════════════
# PAC CLASSIFICATION & GOVERNANCE TIERS
# ═══════════════════════════════════════════════════════════════════════════════

class PACClassification(Enum):
    """Valid PAC classifications."""
    
    CONSTITUTIONAL = "CONSTITUTIONAL"
    OPERATIONAL = "OPERATIONAL"
    TACTICAL = "TACTICAL"
    DIAGNOSTIC = "DIAGNOSTIC"


class GovernanceTier(Enum):
    """Valid governance tiers (enforcement level)."""
    
    LAW = "LAW"          # Immutable, no exceptions
    POLICY = "POLICY"    # Configurable but enforced
    GUIDELINE = "GUIDELINE"  # Recommended but flexible


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL PAC BLOCK DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

REQUIRED_BLOCKS: FrozenSet[int] = frozenset(range(20))  # BLOCK 0-19

BLOCK_NAMES: Dict[int, str] = {
    0: "METADATA",
    1: "PAC_ADMISSION_CHECK",
    2: "RUNTIME_ACTIVATION_ACK",
    3: "GOVERNANCE_MODE_DECLARATION",
    4: "AGENT_ACTIVATION_ACK",
    5: "EXECUTION_LANE",
    6: "CONTEXT",
    7: "GOAL_STATE",
    8: "CONSTRAINTS_AND_GUARDRAILS",
    9: "INVARIANTS_ENFORCED",
    10: "TASKS_AND_PLAN",
    11: "FILE_AND_CODE_TARGETS",
    12: "INTERFACES_AND_CONTRACTS",
    13: "SECURITY_AND_THREAT_MODEL",
    14: "TESTING_AND_VERIFICATION",
    15: "QA_AND_ACCEPTANCE_CRITERIA",
    16: "WRAP_REQUIREMENT",
    17: "FAILURE_AND_ROLLBACK",
    18: "FINAL_STATE_DECLARATION",
    19: "LEDGER_COMMIT_AND_ATTESTATION",
}

# Fields required in METADATA (BLOCK 0)
METADATA_REQUIRED_FIELDS: FrozenSet[str] = frozenset([
    "pac_id",
    "pac_version",
    "classification",
    "governance_tier",
    "issuer_gid",
    "issuer_role",
    "issued_at",
    "scope",
    "fail_closed",
    "schema_version",
])


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

# PAC ID: PAC-<AGENT>-<TYPE>-<ID> e.g., PAC-BENSON-EXEC-C01
PAC_ID_PATTERN = re.compile(
    r"^PAC-[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$"
)

# Semantic version: MAJOR.MINOR.PATCH
SEMVER_PATTERN = re.compile(
    r"^\d+\.\d+\.\d+$"
)

# GID format: GID-XX or GID-XX-YYY
GID_PATTERN = re.compile(
    r"^GID-\d{2}(-[A-Z]+)?$"
)

# ISO8601 timestamp
ISO8601_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$"
)

# Schema version format
SCHEMA_VERSION_PATTERN = re.compile(
    r"^CHAINBRIDGE_PAC_SCHEMA_v\d+\.\d+\.\d+$"
)


# ═══════════════════════════════════════════════════════════════════════════════
# LINT VIOLATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LintViolation:
    """
    Immutable record of a lint rule violation.
    
    Attributes:
        rule_id: The canonical lint rule that was violated
        message: Human-readable description of the violation
        block_number: Which block contained the violation (if applicable)
        field_name: Which field was invalid (if applicable)
        expected: What was expected
        actual: What was found
    """
    
    rule_id: LintRuleID
    message: str
    block_number: Optional[int] = None
    field_name: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    
    def __str__(self) -> str:
        parts = [f"[{self.rule_id.value}] {self.message}"]
        if self.block_number is not None:
            parts.append(f"(BLOCK {self.block_number})")
        if self.field_name:
            parts.append(f"field='{self.field_name}'")
        if self.expected:
            parts.append(f"expected='{self.expected}'")
        if self.actual:
            parts.append(f"actual='{self.actual}'")
        return " ".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# LINT RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LintResult:
    """
    Immutable result of PAC lint enforcement.
    
    Attributes:
        passed: True if PAC passed all lint rules
        pac_id: The PAC ID that was linted
        violations: List of violations (empty if passed)
        rules_checked: Set of rule IDs that were checked
        lint_timestamp: When lint was performed
    """
    
    passed: bool
    pac_id: str
    violations: Tuple[LintViolation, ...] = field(default_factory=tuple)
    rules_checked: FrozenSet[LintRuleID] = field(
        default_factory=lambda: frozenset(LintRuleID)
    )
    lint_timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    
    @property
    def violation_count(self) -> int:
        return len(self.violations)
    
    @property
    def is_hard_reject(self) -> bool:
        """Any violation means hard reject."""
        return not self.passed


# ═══════════════════════════════════════════════════════════════════════════════
# PAC LINT LAW V1
# ═══════════════════════════════════════════════════════════════════════════════

class PACLintLaw:
    """
    PAC Lint Law V1 — Deterministic lint enforcement.
    
    This is a stateless, deterministic enforcement engine.
    No learning. No interpretation. No soft validation.
    
    Usage:
        lint_law = PACLintLaw()
        result = lint_law.enforce(pac_document)
        if not result.passed:
            # HARD REJECT
            for violation in result.violations:
                print(violation)
    """
    
    VERSION = "1.0.0"
    LAW_ID = "PAC_LINT_LAW_V1"
    
    def enforce(self, pac: Dict[str, Any]) -> LintResult:
        """
        Enforce all lint rules against a PAC document.
        
        Args:
            pac: The PAC document as a dictionary
            
        Returns:
            LintResult with pass/fail and any violations
        """
        violations: List[LintViolation] = []
        pac_id = pac.get("metadata", {}).get("pac_id", "UNKNOWN")
        
        # Run all lint rules in fixed order
        violations.extend(self._lint_001_metadata_block(pac))
        violations.extend(self._lint_002_pac_id_format(pac))
        violations.extend(self._lint_003_pac_version(pac))
        violations.extend(self._lint_004_classification(pac))
        violations.extend(self._lint_005_governance_tier(pac))
        violations.extend(self._lint_006_issuer_gid(pac))
        violations.extend(self._lint_007_issued_at(pac))
        violations.extend(self._lint_008_fail_closed_law_tier(pac))
        violations.extend(self._lint_009_all_blocks_present(pac))
        violations.extend(self._lint_010_no_duplicate_blocks(pac))
        violations.extend(self._lint_011_final_state(pac))
        violations.extend(self._lint_012_ledger_commit(pac))
        
        return LintResult(
            passed=len(violations) == 0,
            pac_id=pac_id,
            violations=tuple(violations),
            rules_checked=frozenset(LintRuleID),
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LINT RULES — DETERMINISTIC ENFORCEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _lint_001_metadata_block(self, pac: Dict[str, Any]) -> List[LintViolation]:
        """LINT-001: METADATA block must exist with all required fields."""
        violations = []
        
        metadata = pac.get("metadata")
        if metadata is None:
            violations.append(LintViolation(
                rule_id=LintRuleID.LINT_001,
                message="METADATA block is missing",
                block_number=0,
            ))
            return violations  # Can't check fields if block missing
        
        if not isinstance(metadata, dict):
            violations.append(LintViolation(
                rule_id=LintRuleID.LINT_001,
                message="METADATA block must be a dictionary",
                block_number=0,
                expected="dict",
                actual=type(metadata).__name__,
            ))
            return violations
        
        # Check required fields
        for field_name in METADATA_REQUIRED_FIELDS:
            if field_name not in metadata:
                violations.append(LintViolation(
                    rule_id=LintRuleID.LINT_001,
                    message=f"METADATA missing required field: {field_name}",
                    block_number=0,
                    field_name=field_name,
                ))
        
        return violations
    
    def _lint_002_pac_id_format(self, pac: Dict[str, Any]) -> List[LintViolation]:
        """LINT-002: pac_id must match canonical format."""
        violations = []
        
        pac_id = pac.get("metadata", {}).get("pac_id")
        if pac_id is None:
            return violations  # Handled by LINT-001
        
        if not PAC_ID_PATTERN.match(pac_id):
            violations.append(LintViolation(
                rule_id=LintRuleID.LINT_002,
                message="pac_id does not match canonical format",
                block_number=0,
                field_name="pac_id",
                expected="PAC-<AGENT>-<TYPE>-<ID>",
                actual=pac_id,
            ))
        
        return violations
    
    def _lint_003_pac_version(self, pac: Dict[str, Any]) -> List[LintViolation]:
        """LINT-003: pac_version must be semantic version."""
        violations = []
        
        version = pac.get("metadata", {}).get("pac_version")
        if version is None:
            return violations  # Handled by LINT-001
        
        if not SEMVER_PATTERN.match(str(version)):
            violations.append(LintViolation(
                rule_id=LintRuleID.LINT_003,
                message="pac_version must be semantic version (MAJOR.MINOR.PATCH)",
                block_number=0,
                field_name="pac_version",
                expected="X.Y.Z",
                actual=str(version),
            ))
        
        return violations
    
    def _lint_004_classification(self, pac: Dict[str, Any]) -> List[LintViolation]:
        """LINT-004: classification must be valid enum."""
        violations = []
        
        classification = pac.get("metadata", {}).get("classification")
        if classification is None:
            return violations  # Handled by LINT-001
        
        valid_values = {c.value for c in PACClassification}
        if classification not in valid_values:
            violations.append(LintViolation(
                rule_id=LintRuleID.LINT_004,
                message="classification must be valid enum value",
                block_number=0,
                field_name="classification",
                expected=str(valid_values),
                actual=classification,
            ))
        
        return violations
    
    def _lint_005_governance_tier(self, pac: Dict[str, Any]) -> List[LintViolation]:
        """LINT-005: governance_tier must be valid enum."""
        violations = []
        
        tier = pac.get("metadata", {}).get("governance_tier")
        if tier is None:
            return violations  # Handled by LINT-001
        
        valid_values = {t.value for t in GovernanceTier}
        if tier not in valid_values:
            violations.append(LintViolation(
                rule_id=LintRuleID.LINT_005,
                message="governance_tier must be valid enum value",
                block_number=0,
                field_name="governance_tier",
                expected=str(valid_values),
                actual=tier,
            ))
        
        return violations
    
    def _lint_006_issuer_gid(self, pac: Dict[str, Any]) -> List[LintViolation]:
        """LINT-006: issuer_gid must match GID format."""
        violations = []
        
        gid = pac.get("metadata", {}).get("issuer_gid")
        if gid is None:
            return violations  # Handled by LINT-001
        
        if not GID_PATTERN.match(gid):
            violations.append(LintViolation(
                rule_id=LintRuleID.LINT_006,
                message="issuer_gid must match GID format",
                block_number=0,
                field_name="issuer_gid",
                expected="GID-XX or GID-XX-YYY",
                actual=gid,
            ))
        
        return violations
    
    def _lint_007_issued_at(self, pac: Dict[str, Any]) -> List[LintViolation]:
        """LINT-007: issued_at must be ISO8601 timestamp."""
        violations = []
        
        issued_at = pac.get("metadata", {}).get("issued_at")
        if issued_at is None:
            return violations  # Handled by LINT-001
        
        if not ISO8601_PATTERN.match(issued_at):
            violations.append(LintViolation(
                rule_id=LintRuleID.LINT_007,
                message="issued_at must be ISO8601 timestamp",
                block_number=0,
                field_name="issued_at",
                expected="YYYY-MM-DDTHH:MM:SSZ",
                actual=issued_at,
            ))
        
        return violations
    
    def _lint_008_fail_closed_law_tier(self, pac: Dict[str, Any]) -> List[LintViolation]:
        """LINT-008: fail_closed must be true for LAW tier."""
        violations = []
        
        metadata = pac.get("metadata", {})
        tier = metadata.get("governance_tier")
        fail_closed = metadata.get("fail_closed")
        
        if tier == GovernanceTier.LAW.value and fail_closed is not True:
            violations.append(LintViolation(
                rule_id=LintRuleID.LINT_008,
                message="fail_closed must be true for LAW governance tier",
                block_number=0,
                field_name="fail_closed",
                expected="true",
                actual=str(fail_closed),
            ))
        
        return violations
    
    def _lint_009_all_blocks_present(self, pac: Dict[str, Any]) -> List[LintViolation]:
        """LINT-009: All numbered blocks (0-19) must be present."""
        violations = []
        
        blocks = pac.get("blocks", {})
        if not isinstance(blocks, dict):
            violations.append(LintViolation(
                rule_id=LintRuleID.LINT_009,
                message="'blocks' must be a dictionary",
                expected="dict",
                actual=type(blocks).__name__,
            ))
            return violations
        
        # Check for missing blocks
        present_blocks = set()
        for key in blocks.keys():
            try:
                block_num = int(key)
                present_blocks.add(block_num)
            except (ValueError, TypeError):
                # Non-numeric keys are allowed (named blocks)
                continue
        
        missing = REQUIRED_BLOCKS - present_blocks
        for block_num in sorted(missing):
            block_name = BLOCK_NAMES.get(block_num, "UNKNOWN")
            violations.append(LintViolation(
                rule_id=LintRuleID.LINT_009,
                message=f"Missing required BLOCK {block_num}: {block_name}",
                block_number=block_num,
            ))
        
        return violations
    
    def _lint_010_no_duplicate_blocks(self, pac: Dict[str, Any]) -> List[LintViolation]:
        """LINT-010: No duplicate block numbers."""
        # In a dict, keys are unique by definition
        # This rule catches if multiple block entries reference same number
        # (e.g., "0" and 0 as separate keys)
        violations = []
        
        blocks = pac.get("blocks", {})
        if not isinstance(blocks, dict):
            return violations  # Handled by LINT-009
        
        seen_numbers: Set[int] = set()
        for key in blocks.keys():
            try:
                block_num = int(key)
                if block_num in seen_numbers:
                    violations.append(LintViolation(
                        rule_id=LintRuleID.LINT_010,
                        message=f"Duplicate block number: {block_num}",
                        block_number=block_num,
                    ))
                seen_numbers.add(block_num)
            except (ValueError, TypeError):
                pass
        
        return violations
    
    def _lint_011_final_state(self, pac: Dict[str, Any]) -> List[LintViolation]:
        """LINT-011: FINAL_STATE_DECLARATION (BLOCK 18) must exist."""
        violations = []
        
        blocks = pac.get("blocks", {})
        final_state = blocks.get("18") or blocks.get(18)
        
        if final_state is None:
            violations.append(LintViolation(
                rule_id=LintRuleID.LINT_011,
                message="FINAL_STATE_DECLARATION (BLOCK 18) is required",
                block_number=18,
            ))
            return violations
        
        # Check required fields in FINAL_STATE_DECLARATION
        required_fields = {"execution_blocking", "promotion_eligible"}
        if isinstance(final_state, dict):
            missing = required_fields - set(final_state.keys())
            for field_name in missing:
                violations.append(LintViolation(
                    rule_id=LintRuleID.LINT_011,
                    message=f"FINAL_STATE_DECLARATION missing field: {field_name}",
                    block_number=18,
                    field_name=field_name,
                ))
        
        return violations
    
    def _lint_012_ledger_commit(self, pac: Dict[str, Any]) -> List[LintViolation]:
        """LINT-012: LEDGER_COMMIT_AND_ATTESTATION (BLOCK 19) must exist."""
        violations = []
        
        blocks = pac.get("blocks", {})
        ledger_commit = blocks.get("19") or blocks.get(19)
        
        if ledger_commit is None:
            violations.append(LintViolation(
                rule_id=LintRuleID.LINT_012,
                message="LEDGER_COMMIT_AND_ATTESTATION (BLOCK 19) is required",
                block_number=19,
            ))
            return violations
        
        # Check required attestation fields
        required_fields = {"ordering_attested", "immutability_attested"}
        if isinstance(ledger_commit, dict):
            missing = required_fields - set(ledger_commit.keys())
            for field_name in missing:
                violations.append(LintViolation(
                    rule_id=LintRuleID.LINT_012,
                    message=f"LEDGER_COMMIT missing field: {field_name}",
                    block_number=19,
                    field_name=field_name,
                ))
        
        return violations


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_LINT_LAW_INSTANCE: Optional[PACLintLaw] = None


def get_pac_lint_law() -> PACLintLaw:
    """Get the singleton PACLintLaw instance."""
    global _LINT_LAW_INSTANCE
    if _LINT_LAW_INSTANCE is None:
        _LINT_LAW_INSTANCE = PACLintLaw()
    return _LINT_LAW_INSTANCE
