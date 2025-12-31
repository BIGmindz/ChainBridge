# ═══════════════════════════════════════════════════════════════════════════════
# UI Invariants — Frontend Governance Rules
# PAC-BENSON-P23-C: Parallel Platform Hardening (Corrective)
#
# Defines and enforces UI invariants for the ChainBoard platform:
# - INV-UI-001: No optimistic state rendering
# - INV-UI-002: Read-only display enforcement
# - INV-UI-003: Input sanitization
# - INV-UI-004: Accessibility compliance
#
# Author: ALEX (GID-08) — Governance Enforcer
# Accessibility Review: LIRA (GID-09)
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

class UIInvariantSeverity(str, Enum):
    """Severity levels for UI invariants."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class UIInvariant:
    """Definition of a UI governance invariant."""
    invariant_id: str
    name: str
    description: str
    severity: UIInvariantSeverity
    enforcement: str
    validation_patterns: List[str] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# UI INVARIANT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

UI_INVARIANTS: List[UIInvariant] = [
    UIInvariant(
        invariant_id="INV-UI-001",
        name="No Optimistic State Rendering",
        description="UI must not render optimistic state before server confirmation",
        severity=UIInvariantSeverity.CRITICAL,
        enforcement="BLOCK_PR",
        blocked_patterns=[
            r"setOptimistic\w*\(",
            r"optimisticUpdate",
            r"useOptimistic",
            r"\.mutate\s*\(",  # React Query optimistic mutations
        ],
        validation_patterns=[
            r"await\s+fetch",
            r"\.then\s*\(",
            r"useQuery",
        ],
    ),
    UIInvariant(
        invariant_id="INV-UI-002",
        name="Read-Only Display Enforcement",
        description="OCC components must be read-only with no mutation controls",
        severity=UIInvariantSeverity.CRITICAL,
        enforcement="BLOCK_PR",
        blocked_patterns=[
            r"<button[^>]*onClick[^>]*>.*Edit",
            r"<button[^>]*onClick[^>]*>.*Delete",
            r"<button[^>]*onClick[^>]*>.*Modify",
            r"<input[^>]*type=['\"]text['\"]",
            r"<textarea",
            r"contentEditable",
        ],
        validation_patterns=[
            r"readonly",
            r"disabled",
            r"aria-readonly",
        ],
    ),
    UIInvariant(
        invariant_id="INV-UI-003",
        name="Input Sanitization",
        description="All user inputs must be sanitized before rendering",
        severity=UIInvariantSeverity.HIGH,
        enforcement="BLOCK_PR",
        blocked_patterns=[
            r"dangerouslySetInnerHTML",
            r"innerHTML\s*=",
            r"\.html\s*\(",
            r"document\.write",
            r"eval\s*\(",
        ],
        validation_patterns=[
            r"sanitize\w*\(",
            r"escape\w*\(",
            r"DOMPurify",
        ],
    ),
    UIInvariant(
        invariant_id="INV-UI-004",
        name="Accessibility Compliance",
        description="All interactive elements must have proper ARIA attributes",
        severity=UIInvariantSeverity.HIGH,
        enforcement="WARNING",
        validation_patterns=[
            r"aria-label",
            r"aria-labelledby",
            r"aria-describedby",
            r"role=",
            r"tabIndex",
            r"sr-only",
        ],
        blocked_patterns=[
            r"<img[^>]*(?!alt=)",  # Images without alt
        ],
    ),
    UIInvariant(
        invariant_id="INV-UI-005",
        name="No Hidden Execution Paths",
        description="All actions must be visible and traceable",
        severity=UIInvariantSeverity.CRITICAL,
        enforcement="BLOCK_PR",
        blocked_patterns=[
            r"display:\s*none.*onClick",
            r"visibility:\s*hidden.*onClick",
            r"opacity:\s*0.*onClick",
        ],
    ),
    UIInvariant(
        invariant_id="INV-UI-006",
        name="State Loading Indicators",
        description="All async operations must show loading state",
        severity=UIInvariantSeverity.MEDIUM,
        enforcement="WARNING",
        validation_patterns=[
            r"isLoading",
            r"loading",
            r"isPending",
            r"isFetching",
            r"Spinner",
            r"LoadingIndicator",
        ],
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT CHECKER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class InvariantViolation:
    """Record of an invariant violation."""
    invariant_id: str
    file_path: str
    line_number: int
    matched_pattern: str
    context: str
    severity: UIInvariantSeverity
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class UIInvariantChecker:
    """
    Checks UI code for invariant violations.
    
    Used by ALEX for governance enforcement and DAN for CI checks.
    """
    
    def __init__(self, invariants: Optional[List[UIInvariant]] = None):
        self.invariants = invariants or UI_INVARIANTS
        self._compiled_patterns: dict = {}
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for performance."""
        for inv in self.invariants:
            self._compiled_patterns[inv.invariant_id] = {
                "blocked": [re.compile(p, re.IGNORECASE) for p in inv.blocked_patterns],
                "validation": [re.compile(p, re.IGNORECASE) for p in inv.validation_patterns],
            }
    
    def check_file(self, file_path: Path) -> List[InvariantViolation]:
        """Check a single file for invariant violations."""
        violations: List[InvariantViolation] = []
        
        if not file_path.exists():
            return violations
        
        # Only check TypeScript/React files
        if file_path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            return violations
        
        content = file_path.read_text()
        lines = content.split("\n")
        
        for inv in self.invariants:
            patterns = self._compiled_patterns[inv.invariant_id]
            
            for pattern in patterns["blocked"]:
                for i, line in enumerate(lines, 1):
                    if pattern.search(line):
                        violations.append(InvariantViolation(
                            invariant_id=inv.invariant_id,
                            file_path=str(file_path),
                            line_number=i,
                            matched_pattern=pattern.pattern,
                            context=line.strip()[:100],
                            severity=inv.severity,
                        ))
        
        return violations
    
    def check_directory(self, directory: Path, extensions: Optional[Set[str]] = None) -> List[InvariantViolation]:
        """Check all files in a directory for violations."""
        extensions = extensions or {".ts", ".tsx", ".js", ".jsx"}
        violations: List[InvariantViolation] = []
        
        for file_path in directory.rglob("*"):
            if file_path.suffix in extensions and file_path.is_file():
                violations.extend(self.check_file(file_path))
        
        return violations
    
    def get_summary(self, violations: List[InvariantViolation]) -> dict:
        """Generate summary of violations."""
        by_severity: dict = {s.value: 0 for s in UIInvariantSeverity}
        by_invariant: dict = {}
        
        for v in violations:
            by_severity[v.severity.value] += 1
            by_invariant[v.invariant_id] = by_invariant.get(v.invariant_id, 0) + 1
        
        return {
            "total": len(violations),
            "by_severity": by_severity,
            "by_invariant": by_invariant,
            "blocking": by_severity["critical"] + by_severity["high"],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "UIInvariantSeverity",
    "UIInvariant",
    "UI_INVARIANTS",
    "InvariantViolation",
    "UIInvariantChecker",
]
