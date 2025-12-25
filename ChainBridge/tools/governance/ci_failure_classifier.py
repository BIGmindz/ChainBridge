#!/usr/bin/env python3
"""
CI Failure Classifier — Governance Failure Taxonomy & Auto-Remediation
PAC-DAN-P44-GOVERNANCE-CI-FAILURE-VISIBILITY-AUTO-REMEDIATION-01

Standardized CI failure classification with zero silent failures.
All failures are classified, visible, and actionable.

Failure Classes:
  - CONFIG: Configuration/structure errors (missing blocks, invalid fields)
  - REGRESSION: Performance regression detected
  - DRIFT: Semantic drift from calibration envelope
  - SEQUENTIAL: PAC/WRAP sequencing violations
  - RUNTIME: Runtime validation failures

Usage:
    from ci_failure_classifier import FailureClassifier, FailureClass
    
    classifier = FailureClassifier()
    result = classifier.classify("GS_094")
    print(result.remediation_hint)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class FailureClass(Enum):
    """CI failure classification taxonomy."""
    CONFIG = "CONFIG"           # Configuration/structure errors
    REGRESSION = "REGRESSION"   # Performance regression
    DRIFT = "DRIFT"             # Semantic drift
    SEQUENTIAL = "SEQUENTIAL"   # PAC/WRAP sequencing
    RUNTIME = "RUNTIME"         # Runtime validation
    UNKNOWN = "UNKNOWN"         # Unclassified (FAIL_CLOSED)


class FailureSeverity(Enum):
    """Failure severity levels."""
    CRITICAL = "CRITICAL"   # Blocks all progress
    HIGH = "HIGH"           # Requires immediate attention
    MEDIUM = "MEDIUM"       # Should be fixed soon
    LOW = "LOW"             # Informational


@dataclass
class ClassifiedFailure:
    """A classified CI failure with remediation guidance."""
    error_code: str
    failure_class: FailureClass
    severity: FailureSeverity
    description: str
    remediation_hint: str
    agent_action: str  # Machine-readable action for agents
    documentation_ref: Optional[str] = None
    related_codes: List[str] = field(default_factory=list)


@dataclass
class FailureSummary:
    """Aggregate failure summary for CI run."""
    total_failures: int = 0
    by_class: Dict[FailureClass, int] = field(default_factory=dict)
    by_severity: Dict[FailureSeverity, int] = field(default_factory=dict)
    failures: List[ClassifiedFailure] = field(default_factory=list)
    passed: int = 0
    skipped: int = 0
    
    def add_failure(self, failure: ClassifiedFailure) -> None:
        """Add a failure to the summary."""
        self.total_failures += 1
        self.failures.append(failure)
        self.by_class[failure.failure_class] = self.by_class.get(failure.failure_class, 0) + 1
        self.by_severity[failure.severity] = self.by_severity.get(failure.severity, 0) + 1
    
    @property
    def has_blocking_failures(self) -> bool:
        """Check if any failures are blocking."""
        return self.by_severity.get(FailureSeverity.CRITICAL, 0) > 0
    
    @property
    def exit_code(self) -> int:
        """Determine exit code based on failures."""
        if self.by_severity.get(FailureSeverity.CRITICAL, 0) > 0:
            return 2  # Critical failure
        elif self.total_failures > 0:
            return 1  # Non-critical failures
        return 0  # Success


# Error code to failure class mapping
ERROR_CLASS_MAP: Dict[str, FailureClass] = {
    # CONFIG class - Structure/configuration errors
    "G0_001": FailureClass.CONFIG,
    "G0_002": FailureClass.CONFIG,
    "G0_005": FailureClass.CONFIG,
    "G0_006": FailureClass.CONFIG,
    "G0_008": FailureClass.CONFIG,
    "G0_009": FailureClass.CONFIG,
    "G0_010": FailureClass.CONFIG,
    "G0_011": FailureClass.CONFIG,
    "G0_012": FailureClass.CONFIG,
    "G0_020": FailureClass.CONFIG,
    "G0_021": FailureClass.CONFIG,
    "G0_022": FailureClass.CONFIG,
    "G0_023": FailureClass.CONFIG,
    "G0_024": FailureClass.CONFIG,
    "G0_040": FailureClass.CONFIG,
    "G0_041": FailureClass.CONFIG,
    "G0_042": FailureClass.CONFIG,
    "G0_043": FailureClass.CONFIG,
    "G0_044": FailureClass.CONFIG,
    "G0_045": FailureClass.CONFIG,
    "G0_046": FailureClass.CONFIG,
    "RG_001": FailureClass.CONFIG,
    "RG_002": FailureClass.CONFIG,
    "RG_003": FailureClass.CONFIG,
    "RG_004": FailureClass.CONFIG,
    "RG_005": FailureClass.CONFIG,
    "RG_006": FailureClass.CONFIG,
    "RG_007": FailureClass.CONFIG,
    "BSRG_001": FailureClass.CONFIG,
    "BSRG_002": FailureClass.CONFIG,
    "BSRG_003": FailureClass.CONFIG,
    "BSRG_004": FailureClass.CONFIG,
    "BSRG_005": FailureClass.CONFIG,
    "BSRG_006": FailureClass.CONFIG,
    "BSRG_007": FailureClass.CONFIG,
    "BSRG_008": FailureClass.CONFIG,
    "BSRG_009": FailureClass.CONFIG,
    "BSRG_010": FailureClass.CONFIG,
    "BSRG_011": FailureClass.CONFIG,
    "BSRG_012": FailureClass.CONFIG,
    
    # REGRESSION class - Performance regression
    "GS_094": FailureClass.REGRESSION,
    "GS_115": FailureClass.REGRESSION,
    
    # DRIFT class - Semantic drift
    "GS_095": FailureClass.DRIFT,
    "GS_060": FailureClass.DRIFT,
    "GS_061": FailureClass.DRIFT,
    "GS_062": FailureClass.DRIFT,
    "GS_063": FailureClass.DRIFT,
    "GS_030": FailureClass.DRIFT,
    "GS_031": FailureClass.DRIFT,
    "GS_032": FailureClass.DRIFT,
    
    # SEQUENTIAL class - PAC/WRAP sequencing
    "GS_096": FailureClass.SEQUENTIAL,
    "GS_097": FailureClass.SEQUENTIAL,
    "GS_098": FailureClass.SEQUENTIAL,
    "GS_099": FailureClass.SEQUENTIAL,
    "GS_110": FailureClass.SEQUENTIAL,
    "GS_111": FailureClass.SEQUENTIAL,
    "GS_112": FailureClass.SEQUENTIAL,
    "GS_113": FailureClass.SEQUENTIAL,
    "GS_114": FailureClass.SEQUENTIAL,
    
    # RUNTIME class - Runtime validation
    "G0_003": FailureClass.RUNTIME,
    "G0_004": FailureClass.RUNTIME,
    "G0_007": FailureClass.RUNTIME,
    "G0_050": FailureClass.RUNTIME,
    "G0_051": FailureClass.RUNTIME,
    "G0_052": FailureClass.RUNTIME,
    "WRP_001": FailureClass.RUNTIME,
    "WRP_002": FailureClass.RUNTIME,
    "WRP_003": FailureClass.RUNTIME,
    "WRP_004": FailureClass.RUNTIME,
    "WRP_005": FailureClass.RUNTIME,
    "WRP_006": FailureClass.RUNTIME,
    "WRP_007": FailureClass.RUNTIME,
    "WRP_008": FailureClass.RUNTIME,
    "WRP_009": FailureClass.RUNTIME,
    "WRP_010": FailureClass.RUNTIME,
    "WRP_011": FailureClass.RUNTIME,
    "GS_090": FailureClass.RUNTIME,
    "GS_091": FailureClass.RUNTIME,
    "GS_092": FailureClass.RUNTIME,
    "GS_093": FailureClass.RUNTIME,
}

# Remediation hints by error code
REMEDIATION_HINTS: Dict[str, Dict[str, str]] = {
    # CONFIG class
    "G0_001": {
        "hint": "Add the missing required block to the artifact. Check CANONICAL_CORRECTION_PACK_TEMPLATE.md for required blocks.",
        "action": "ADD_MISSING_BLOCK",
    },
    "G0_002": {
        "hint": "Reorder blocks to match canonical template. Runtime activation must come before agent activation.",
        "action": "REORDER_BLOCKS",
    },
    "G0_005": {
        "hint": "Correct the invalid field value. Check AGENT_REGISTRY.json for valid values.",
        "action": "FIX_FIELD_VALUE",
    },
    "G0_006": {
        "hint": "Add the missing required field to the YAML block.",
        "action": "ADD_MISSING_FIELD",
    },
    "RG_001": {
        "hint": "Add REVIEW_GATE section with gate_id: REVIEW-GATE-v1.1",
        "action": "ADD_REVIEW_GATE",
    },
    "RG_002": {
        "hint": "Move GOLD_STANDARD_CHECKLIST to be the terminal (last) section.",
        "action": "MOVE_CHECKLIST_TERMINAL",
    },
    "BSRG_001": {
        "hint": "Add BENSON_SELF_REVIEW_GATE section before GOLD_STANDARD_CHECKLIST.",
        "action": "ADD_BSRG",
    },
    "BSRG_007": {
        "hint": "Ensure all checklist_results items are set to PASS.",
        "action": "FIX_BSRG_CHECKLIST",
    },
    
    # REGRESSION class
    "GS_094": {
        "hint": "Performance regression detected. Review baseline in GOVERNANCE_AGENT_BASELINES.md. Either improve performance or update baseline with justification.",
        "action": "REVIEW_BASELINE_OR_OPTIMIZE",
    },
    "GS_115": {
        "hint": "Illegal PAC state transition. Check PAC lifecycle and ensure valid state progression.",
        "action": "FIX_STATE_TRANSITION",
    },
    
    # DRIFT class
    "GS_095": {
        "hint": "Semantic drift detected. Agent output has deviated from calibration envelope. Review and recalibrate or escalate.",
        "action": "RECALIBRATE_OR_ESCALATE",
    },
    "GS_060": {
        "hint": "Overhelpfulness detected. Artifact contains unauthorized changes. Revert to authorized scope.",
        "action": "REVERT_TO_AUTHORIZED_SCOPE",
    },
    "GS_031": {
        "hint": "Agent color does not match registry. Check AGENT_REGISTRY.json and use canonical color.",
        "action": "FIX_AGENT_COLOR",
    },
    
    # SEQUENTIAL class
    "GS_096": {
        "hint": "PAC sequence violation. PAC numbers must be globally monotonic. Check ledger for next valid number.",
        "action": "USE_NEXT_PAC_NUMBER",
    },
    "GS_110": {
        "hint": "Previous PAC has no corresponding WRAP. Create and commit WRAP for prior PAC before proceeding.",
        "action": "CREATE_MISSING_WRAP",
    },
    "GS_111": {
        "hint": "Prior WRAP not accepted. Ensure previous WRAP is recorded in ledger with ACCEPTED status.",
        "action": "ACCEPT_PRIOR_WRAP",
    },
    "GS_114": {
        "hint": "WRAP does not cryptographically bind to PAC. Regenerate WRAP with correct PAC reference.",
        "action": "REGENERATE_WRAP",
    },
    
    # RUNTIME class
    "G0_003": {
        "hint": "Invalid GID format. GID must match pattern GID-XX (e.g., GID-07).",
        "action": "FIX_GID_FORMAT",
    },
    "G0_004": {
        "hint": "Registry mismatch. Agent attributes do not match AGENT_REGISTRY.json. Verify and correct.",
        "action": "FIX_REGISTRY_MISMATCH",
    },
    "WRP_001": {
        "hint": "WRAP missing WRAP_INGESTION_PREAMBLE. Add preamble as first block.",
        "action": "ADD_WRAP_PREAMBLE",
    },
    "GS_090": {
        "hint": "Non-executing agent cannot emit PACs. Only executing agents (mode: EXECUTABLE) can create PACs.",
        "action": "CHECK_AGENT_MODE",
    },
}

# Severity mapping
ERROR_SEVERITY_MAP: Dict[str, FailureSeverity] = {
    # CRITICAL - blocks all progress
    "GS_094": FailureSeverity.CRITICAL,
    "GS_095": FailureSeverity.CRITICAL,
    "GS_096": FailureSeverity.CRITICAL,
    "GS_110": FailureSeverity.CRITICAL,
    "GS_111": FailureSeverity.CRITICAL,
    "GS_114": FailureSeverity.CRITICAL,
    "GS_115": FailureSeverity.CRITICAL,
    "GS_090": FailureSeverity.CRITICAL,
    "GS_091": FailureSeverity.CRITICAL,
    
    # HIGH - requires immediate attention
    "G0_001": FailureSeverity.HIGH,
    "G0_002": FailureSeverity.HIGH,
    "RG_001": FailureSeverity.HIGH,
    "BSRG_001": FailureSeverity.HIGH,
    "WRP_001": FailureSeverity.HIGH,
    "GS_060": FailureSeverity.HIGH,
    
    # MEDIUM - should be fixed soon
    "G0_005": FailureSeverity.MEDIUM,
    "G0_006": FailureSeverity.MEDIUM,
    "RG_002": FailureSeverity.MEDIUM,
    "BSRG_007": FailureSeverity.MEDIUM,
    "GS_031": FailureSeverity.MEDIUM,
}


class FailureClassifier:
    """
    CI failure classifier with remediation hints.
    
    Classifies governance errors into failure categories and provides
    actionable remediation guidance.
    """
    
    def __init__(self):
        """Initialize classifier."""
        self._class_map = ERROR_CLASS_MAP.copy()
        self._remediation_hints = REMEDIATION_HINTS.copy()
        self._severity_map = ERROR_SEVERITY_MAP.copy()
    
    def classify(self, error_code: str, description: str = "") -> ClassifiedFailure:
        """
        Classify an error code into a failure category.
        
        Args:
            error_code: The error code (e.g., "GS_094", "G0_001")
            description: Optional error description
            
        Returns:
            ClassifiedFailure with remediation guidance
        """
        # Normalize error code
        code = self._normalize_code(error_code)
        
        # Get failure class (UNKNOWN if not mapped - FAIL_CLOSED)
        failure_class = self._class_map.get(code, FailureClass.UNKNOWN)
        
        # Get severity
        severity = self._severity_map.get(code, FailureSeverity.MEDIUM)
        
        # Get remediation hint
        hint_data = self._remediation_hints.get(code, {
            "hint": f"Unknown error code {code}. Check governance documentation or escalate to BENSON.",
            "action": "ESCALATE_TO_BENSON",
        })
        
        return ClassifiedFailure(
            error_code=code,
            failure_class=failure_class,
            severity=severity,
            description=description or f"Error {code}",
            remediation_hint=hint_data["hint"],
            agent_action=hint_data["action"],
            documentation_ref=self._get_doc_ref(code),
            related_codes=self._get_related_codes(code),
        )
    
    def classify_multiple(self, error_codes: List[str]) -> FailureSummary:
        """
        Classify multiple error codes and produce a summary.
        
        Args:
            error_codes: List of error codes
            
        Returns:
            FailureSummary with all classified failures
        """
        summary = FailureSummary()
        
        for code in error_codes:
            failure = self.classify(code)
            summary.add_failure(failure)
        
        return summary
    
    def _normalize_code(self, code: str) -> str:
        """Normalize error code format."""
        # Extract code from bracketed format: [G0_001] or plain G0_001
        # Pattern matches: G0_001, GS_094, RG_001, BSRG_001, WRP_001
        match = re.search(r'\[?([A-Z]+\d*_\d+)\]?', code.upper())
        if match:
            return match.group(1)
        # Fallback for codes without underscore
        match = re.search(r'\[?([A-Z]+\d+)\]?', code.upper())
        if match:
            return match.group(1)
        return code.upper().strip()
    
    def _get_doc_ref(self, code: str) -> Optional[str]:
        """Get documentation reference for error code."""
        if code.startswith("G0_"):
            return "docs/governance/CANONICAL_CORRECTION_PACK_TEMPLATE.md"
        elif code.startswith("RG_"):
            return "docs/governance/pacs/PAC-BENSON-G0-REVIEW-GATE-V1-1-IMPLEMENTATION-01.md"
        elif code.startswith("BSRG_"):
            return "docs/governance/pacs/PAC-ATLAS-P21-BSRG-PARSER-AND-LEDGER-IMMUTABILITY-01.md"
        elif code.startswith("GS_"):
            return "docs/governance/GOVERNANCE_CI_FAILURE_VISIBILITY.md"
        elif code.startswith("WRP_"):
            return "docs/governance/pacs/PAC-BENSON-P28-CANONICAL-WRAP-SCHEMA-ENFORCEMENT-01.md"
        return None
    
    def _get_related_codes(self, code: str) -> List[str]:
        """Get related error codes."""
        related = []
        prefix = code.split("_")[0] if "_" in code else code[:2]
        
        for other_code in self._class_map:
            if other_code != code and other_code.startswith(prefix):
                related.append(other_code)
        
        return related[:3]  # Limit to 3 related codes


def format_failure_summary(summary: FailureSummary, use_color: bool = True) -> str:
    """
    Format a failure summary for CI output.
    
    Args:
        summary: The failure summary to format
        use_color: Whether to use ANSI colors
        
    Returns:
        Formatted string for CI output
    """
    RESET = "\033[0m" if use_color else ""
    BOLD = "\033[1m" if use_color else ""
    RED = "\033[91m" if use_color else ""
    YELLOW = "\033[93m" if use_color else ""
    GREEN = "\033[92m" if use_color else ""
    CYAN = "\033[96m" if use_color else ""
    
    lines = []
    width = 80
    
    # Header
    lines.append("")
    lines.append("═" * width)
    lines.append(f"{BOLD}CI FAILURE SUMMARY{RESET}")
    lines.append("═" * width)
    
    # Counts by class
    lines.append(f"\n{BOLD}By Failure Class:{RESET}")
    for fc in FailureClass:
        count = summary.by_class.get(fc, 0)
        if count > 0:
            color = RED if fc == FailureClass.UNKNOWN else CYAN
            lines.append(f"  {color}[{fc.value}]{RESET}: {count}")
    
    # Counts by severity
    lines.append(f"\n{BOLD}By Severity:{RESET}")
    for sev in FailureSeverity:
        count = summary.by_severity.get(sev, 0)
        if count > 0:
            color = RED if sev == FailureSeverity.CRITICAL else YELLOW if sev == FailureSeverity.HIGH else ""
            lines.append(f"  {color}[{sev.value}]{RESET}: {count}")
    
    # Individual failures with remediation
    if summary.failures:
        lines.append(f"\n{BOLD}Failures & Remediation:{RESET}")
        lines.append("-" * width)
        
        for i, failure in enumerate(summary.failures, 1):
            color = RED if failure.severity == FailureSeverity.CRITICAL else YELLOW
            lines.append(f"\n{color}{i}. [{failure.error_code}] {failure.failure_class.value}{RESET}")
            lines.append(f"   Severity: {failure.severity.value}")
            lines.append(f"   {BOLD}Remediation:{RESET} {failure.remediation_hint}")
            lines.append(f"   {CYAN}Agent Action:{RESET} {failure.agent_action}")
            if failure.documentation_ref:
                lines.append(f"   Reference: {failure.documentation_ref}")
    
    # Final status
    lines.append("")
    lines.append("═" * width)
    
    if summary.has_blocking_failures:
        lines.append(f"{RED}{BOLD}❌ CI BLOCKED — Critical failures detected{RESET}")
        lines.append(f"{RED}Exit code: {summary.exit_code}{RESET}")
    elif summary.total_failures > 0:
        lines.append(f"{YELLOW}{BOLD}⚠ CI FAILED — {summary.total_failures} failure(s) detected{RESET}")
        lines.append(f"{YELLOW}Exit code: {summary.exit_code}{RESET}")
    else:
        lines.append(f"{GREEN}{BOLD}✓ CI PASSED — No failures detected{RESET}")
    
    lines.append("═" * width)
    
    return "\n".join(lines)


def format_failure_json(summary: FailureSummary) -> dict:
    """
    Format failure summary as JSON for machine consumption.
    
    Args:
        summary: The failure summary
        
    Returns:
        Dict suitable for JSON serialization
    """
    return {
        "status": "BLOCKED" if summary.has_blocking_failures else "FAILED" if summary.total_failures > 0 else "PASSED",
        "exit_code": summary.exit_code,
        "total_failures": summary.total_failures,
        "by_class": {fc.value: count for fc, count in summary.by_class.items()},
        "by_severity": {sev.value: count for sev, count in summary.by_severity.items()},
        "failures": [
            {
                "error_code": f.error_code,
                "class": f.failure_class.value,
                "severity": f.severity.value,
                "remediation_hint": f.remediation_hint,
                "agent_action": f.agent_action,
                "documentation_ref": f.documentation_ref,
            }
            for f in summary.failures
        ],
    }


# Demo / self-test
if __name__ == "__main__":
    classifier = FailureClassifier()
    
    # Test classification
    test_codes = [
        "G0_001",
        "GS_094",
        "GS_095",
        "GS_110",
        "BSRG_001",
        "UNKNOWN_CODE",
    ]
    
    print("Testing CI Failure Classifier")
    print("=" * 60)
    
    summary = classifier.classify_multiple(test_codes)
    print(format_failure_summary(summary))
    
    print("\nJSON Output:")
    import json
    print(json.dumps(format_failure_json(summary), indent=2))
