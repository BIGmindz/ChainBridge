#!/usr/bin/env python3
"""
CI-Safe Terminal Renderer for Governance Output
PAC-DAN-P30-TERMINAL-GOVERNANCE-UI-CI-INTEGRATION-01

High-visibility terminal UI for governance validation in CI/CD pipelines.
Auto-detects CI environment and falls back to plain text when needed.

Features:
  - Rich terminal output (PASS/WARN/FAIL/SKIP/REVIEW)
  - Distinct governance iconography (non-agent colors)
  - Auto-detect CI environment (GitHub Actions, GitLab, local)
  - Fallback to plain text for limited terminals
  - Toggle flags: --ui, --ui-compact, --no-ui

Usage:
    from ci_renderer import CIRenderer, GovState

    renderer = CIRenderer(mode="auto")
    renderer.start_run("gate_pack.py validation")
    renderer.result("PAC-DAN-P30", GovState.PASS)
    renderer.end_run()
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict


class GovState(Enum):
    """Governance validation states with distinct visual identity."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"
    LEGACY = "LEGACY"
    REVIEW = "REVIEW"


class OutputMode(Enum):
    """Terminal output modes."""
    RICH = "rich"           # Full color + symbols
    COMPACT = "compact"     # Condensed color output
    PLAIN = "plain"         # No color, ASCII only
    AUTO = "auto"           # Auto-detect


@dataclass
class ValidationResult:
    """Single validation result entry."""
    artifact_id: str
    state: GovState
    errors: List[str] = field(default_factory=list)
    note: str = ""
    file_path: Optional[str] = None


# High-contrast symbols - DISTINCT from agent identity colors
# These use governance-specific iconography
SYMBOLS_RICH = {
    GovState.PASS:   ("▰✔▰", "\033[92m"),   # Bright green - success
    GovState.FAIL:   ("▰✖▰", "\033[91m"),   # Bright red - failure
    GovState.WARN:   ("▰⚡▰", "\033[93m"),   # Yellow - warning
    GovState.SKIP:   ("▰↷▰", "\033[96m"),   # Cyan - skipped
    GovState.LEGACY: ("▰⧗▰", "\033[33m"),   # Dark yellow - legacy
    GovState.REVIEW: ("▰⚠▰", "\033[95m"),   # Magenta - needs review
}

SYMBOLS_COMPACT = {
    GovState.PASS:   ("✓", "\033[92m"),
    GovState.FAIL:   ("✗", "\033[91m"),
    GovState.WARN:   ("!", "\033[93m"),
    GovState.SKIP:   ("~", "\033[96m"),
    GovState.LEGACY: ("◇", "\033[33m"),
    GovState.REVIEW: ("?", "\033[95m"),
}

SYMBOLS_PLAIN = {
    GovState.PASS:   ("[PASS]", ""),
    GovState.FAIL:   ("[FAIL]", ""),
    GovState.WARN:   ("[WARN]", ""),
    GovState.SKIP:   ("[SKIP]", ""),
    GovState.LEGACY: ("[LEGACY]", ""),
    GovState.REVIEW: ("[REVIEW]", ""),
}

# ANSI codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
UNDERLINE = "\033[4m"


def detect_ci_environment() -> Dict[str, any]:
    """Detect CI environment and terminal capabilities."""
    env = {
        "is_ci": False,
        "ci_name": None,
        "supports_color": True,
        "supports_unicode": True,
    }

    # GitHub Actions
    if os.environ.get("GITHUB_ACTIONS") == "true":
        env["is_ci"] = True
        env["ci_name"] = "GitHub Actions"
        env["supports_color"] = True  # GitHub Actions supports ANSI
        env["supports_unicode"] = True
        return env

    # GitLab CI
    if os.environ.get("GITLAB_CI") == "true":
        env["is_ci"] = True
        env["ci_name"] = "GitLab CI"
        env["supports_color"] = True
        env["supports_unicode"] = True
        return env

    # Jenkins
    if os.environ.get("JENKINS_URL"):
        env["is_ci"] = True
        env["ci_name"] = "Jenkins"
        # Jenkins color support varies
        env["supports_color"] = os.environ.get("TERM") != "dumb"
        env["supports_unicode"] = True
        return env

    # CircleCI
    if os.environ.get("CIRCLECI") == "true":
        env["is_ci"] = True
        env["ci_name"] = "CircleCI"
        env["supports_color"] = True
        env["supports_unicode"] = True
        return env

    # Generic CI detection
    if os.environ.get("CI") == "true":
        env["is_ci"] = True
        env["ci_name"] = "Generic CI"
        env["supports_color"] = os.environ.get("TERM") != "dumb"
        return env

    # Local terminal detection
    if sys.stdout.isatty():
        env["supports_color"] = True
        # Check for Windows cmd.exe limitations
        if os.name == "nt" and "ANSICON" not in os.environ:
            env["supports_color"] = os.environ.get("WT_SESSION") is not None
    else:
        # Piped output
        env["supports_color"] = False

    return env


class CIRenderer:
    """
    CI-safe terminal renderer for governance output.

    Automatically detects environment capabilities and adjusts output.
    """

    def __init__(self, mode: str = "auto"):
        """
        Initialize renderer.

        Args:
            mode: Output mode - "rich", "compact", "plain", or "auto"
        """
        self.env = detect_ci_environment()
        self.results: List[ValidationResult] = []
        self._run_title: Optional[str] = None

        # Determine effective mode
        if mode == "auto":
            if not self.env["supports_color"]:
                self._mode = OutputMode.PLAIN
            elif self.env["is_ci"]:
                self._mode = OutputMode.RICH  # CI typically has full support
            else:
                self._mode = OutputMode.RICH
        else:
            self._mode = OutputMode(mode)

        # Select symbol set
        if self._mode == OutputMode.PLAIN:
            self._symbols = SYMBOLS_PLAIN
            self._use_color = False
        elif self._mode == OutputMode.COMPACT:
            self._symbols = SYMBOLS_COMPACT
            self._use_color = True
        else:
            self._symbols = SYMBOLS_RICH
            self._use_color = True

    @property
    def mode(self) -> OutputMode:
        """Current output mode."""
        return self._mode

    def _color(self, text: str, color_code: str) -> str:
        """Apply color if supported."""
        if self._use_color and color_code:
            return f"{color_code}{text}{RESET}"
        return text

    def _bold(self, text: str) -> str:
        """Apply bold if supported."""
        if self._use_color:
            return f"{BOLD}{text}{RESET}"
        return text

    def _dim(self, text: str) -> str:
        """Apply dim if supported."""
        if self._use_color:
            return f"{DIM}{text}{RESET}"
        return text

    def start_run(self, title: str = "Governance Validation") -> None:
        """Print run header."""
        self._run_title = title
        self.results = []

        width = 80
        if self._mode == OutputMode.PLAIN:
            print()
            print("=" * width)
            print(f">>> {title.upper()} <<<")
            print("=" * width)
        else:
            border = "═" * width
            print()
            print(f"{BOLD}▶▶▶ {title.upper()} ◀◀◀{RESET}")
            print(border)

        # CI environment notice
        if self.env["is_ci"]:
            ci_name = self.env["ci_name"] or "CI"
            print(self._dim(f"Environment: {ci_name} | Mode: {self._mode.value}"))
            print()

    def result(
        self,
        artifact_id: str,
        state: GovState,
        errors: List[str] = None,
        note: str = "",
        file_path: str = None
    ) -> None:
        """Record and display a validation result."""
        result = ValidationResult(
            artifact_id=artifact_id,
            state=state,
            errors=errors or [],
            note=note,
            file_path=file_path
        )
        self.results.append(result)

        symbol, color = self._symbols[state]
        colored_symbol = self._color(symbol, color)

        note_str = f" — {note}" if note else ""
        note_display = self._dim(note_str) if note_str else ""

        print(f"{colored_symbol} {artifact_id}{note_display}")

        # Show errors for failures
        if state == GovState.FAIL and result.errors:
            for error in result.errors[:5]:  # Limit to 5 errors
                print(f"    {self._color('│', color)} {error}")

    def end_run(self) -> Dict[str, int]:
        """Print run summary and return counts."""
        counts = {state: 0 for state in GovState}
        for r in self.results:
            counts[r.state] += 1

        total = len(self.results)
        passed = counts[GovState.PASS]
        failed = counts[GovState.FAIL]

        width = 80
        if self._mode == OutputMode.PLAIN:
            print()
            print("-" * width)
            print("SUMMARY")
            print("-" * width)
        else:
            print()
            print("─" * width)
            print(f"{BOLD}SUMMARY{RESET}")

        # State counts
        labels = {
            GovState.PASS: "PASSED",
            GovState.FAIL: "FAILED",
            GovState.WARN: "WARNINGS",
            GovState.SKIP: "SKIPPED",
            GovState.LEGACY: "LEGACY",
            GovState.REVIEW: "REVIEW",
        }

        for state in GovState:
            if counts[state] > 0:
                symbol, color = self._symbols[state]
                colored_symbol = self._color(symbol, color)
                print(f"{colored_symbol} {counts[state]} {labels[state]}")

        # Final status line
        print()
        if failed == 0:
            status_symbol, status_color = self._symbols[GovState.PASS]
            status = self._color(f"{status_symbol} ALL VALIDATIONS PASSED ({passed}/{total})", status_color)
        else:
            status_symbol, status_color = self._symbols[GovState.FAIL]
            status = self._color(f"{status_symbol} VALIDATION FAILED ({failed} errors)", status_color)

        print(self._bold(status))

        if self._mode != OutputMode.PLAIN:
            print("═" * width)
        else:
            print("=" * width)

        return {state.value: counts[state] for state in GovState}

    def single_result(self, artifact_id: str, state: GovState, errors: List[str] = None) -> None:
        """Display a single result without run context (for inline validation)."""
        symbol, color = self._symbols[state]
        colored_symbol = self._color(symbol, color)
        print(f"{colored_symbol} {artifact_id}")

        if state == GovState.FAIL and errors:
            for error in errors[:3]:
                print(f"    {self._color('│', color)} {error}")

    def end_run_with_failure_classification(self, error_codes: List[str] = None) -> Dict[str, any]:
        """
        Print run summary with failure classification and remediation hints.

        PAC-DAN-P44: Integrates ci_failure_classifier for zero silent failures.

        Args:
            error_codes: Optional list of error codes to classify

        Returns:
            Dict with counts and failure summary
        """
        from ci_failure_classifier import (
            FailureClassifier,
            format_failure_summary,
            format_failure_json
        )

        # First do standard summary
        counts = self.end_run()

        # If we have error codes, add classified failure summary
        if error_codes:
            classifier = FailureClassifier()
            summary = classifier.classify_multiple(error_codes)

            # Print failure classification
            print(format_failure_summary(summary, use_color=self._use_color))

            return {
                "counts": counts,
                "failure_summary": format_failure_json(summary),
                "exit_code": summary.exit_code,
            }

        return {"counts": counts, "exit_code": 1 if counts.get("FAIL", 0) > 0 else 0}


def create_renderer_from_args(args) -> CIRenderer:
    """
    Create renderer based on CLI arguments.

    Expected args attributes:
        --ui: Enable rich mode
        --ui-compact: Enable compact mode
        --no-ui: Force plain mode
    """
    if getattr(args, "no_ui", False):
        return CIRenderer(mode="plain")
    elif getattr(args, "ui_compact", False):
        return CIRenderer(mode="compact")
    elif getattr(args, "ui", False):
        return CIRenderer(mode="rich")
    else:
        return CIRenderer(mode="auto")


# Demo / self-test
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CI Renderer Demo")
    parser.add_argument("--ui", action="store_true", help="Enable rich UI mode")
    parser.add_argument("--ui-compact", action="store_true", help="Enable compact UI mode")
    parser.add_argument("--no-ui", action="store_true", help="Force plain text mode")
    args = parser.parse_args()

    renderer = create_renderer_from_args(args)

    print(f"Detected environment: {renderer.env}")
    print(f"Using mode: {renderer.mode.value}")
    print()

    renderer.start_run("PAG-01 Persona Activation Audit (Demo)")

    renderer.result("PAC-DAN-P30-TERMINAL-GOVERNANCE-UI-CI-INTEGRATION-01", GovState.PASS)
    renderer.result("PAC-ATLAS-P29-GOVERNANCE-TERMINAL-UI-DEMO-EXECUTION-01", GovState.PASS)
    renderer.result("PAC-ALEX-P25-PAG01-PERSONA-ACTIVATION-CORRECTION-01", GovState.PASS)
    renderer.result("WRAP-SONNY-P28", GovState.SKIP, note="report-only artifact")
    renderer.result("WRAP-SAM-G1", GovState.LEGACY, note="legacy exemption")
    renderer.result(
        "PAC-SAM-P21",
        GovState.FAIL,
        errors=["[G0_001] Missing required block: AGENT_ACTIVATION_ACK", "[G0_003] Invalid GID format"],
        note="requires correction"
    )
    renderer.result("PAC-MAGGIE-P24", GovState.REVIEW, note="requires human review")
    renderer.result("PAC-CODY-P27", GovState.WARN, note="non-blocking issue detected")

    counts = renderer.end_run()

    # Exit with error code if failures
    sys.exit(1 if counts.get("FAIL", 0) > 0 else 0)
