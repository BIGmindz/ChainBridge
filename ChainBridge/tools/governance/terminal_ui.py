#!/usr/bin/env python3
"""
Terminal Governance UI — Canonical Rendering Layer

══════════════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-01 — CODY (BACKEND ENGINEER)
PAC-CODY-P30-TERMINAL-GOVERNANCE-UI-STANDARD-IMPLEMENTATION-01
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
══════════════════════════════════════════════════════════════════════════════

AGENT_ACTIVATION_ACK:
  agent_name: CODY
  gid: GID-01
  color: BLUE
  icon: 🔵
  role: Senior Backend Engineer
  execution_lane: BACKEND
  authority: Benson (GID-00)
  mode: EXECUTABLE

RUNTIME_ACTIVATION_ACK:
  runtime_name: terminal_ui
  gid: N/A
  authority: DELEGATED
  execution_lane: UI_RENDERING
  mode: READ_ONLY
  executes_for_agent: CODY (GID-01)

══════════════════════════════════════════════════════════════════════════════

This module provides the canonical terminal UI rendering layer for governance
output. It uses the Rich library for consistent, accessible terminal output.

CRITICAL CONSTRAINTS:
- NO agent persona colors (🔵🔴🟢🟡🟣 reserved for agents)
- NO governance state mutation
- NO network calls
- Deterministic output for CI compatibility
- Performance budget: <50ms per render

System Glyph Set (non-agent, system-only):
  PASS   ▰✔▰   (green accent, not agent green)
  FAIL   ▰✖▰   (red accent, not agent red)
  WARN   ▰⚠▰   (yellow accent)
  SKIP   ▰↷▰   (dim/grey)
  LEGACY ▰⧗▰   (amber/orange)
  REVIEW ▰◼▰   (cyan accent)

Authority: PAC-CODY-P30-TERMINAL-GOVERNANCE-UI-STANDARD-IMPLEMENTATION-01
Mode: READ_ONLY
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
import sys

# Rich imports with graceful fallback
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.style import Style
    from rich.box import ROUNDED, HEAVY, DOUBLE
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None


# =============================================================================
# CANONICAL SYSTEM GLYPH SET
# =============================================================================
# These glyphs are RESERVED for system UI only.
# Agent persona colors (🔵🔴🟢🟡🟣🟠🩷⬜🟦) are FORBIDDEN in system output.

class SystemGlyph(Enum):
    """Canonical system glyphs for governance UI. Non-agent colors only."""
    PASS = "▰✔▰"
    FAIL = "▰✖▰"
    WARN = "▰⚠▰"
    SKIP = "▰↷▰"
    LEGACY = "▰⧗▰"
    REVIEW = "▰◼▰"
    INFO = "▰ℹ▰"
    LOCK = "▰🔒▰"
    GATE = "▰⛊▰"
    CHECK = "▰◉▰"


class SystemColor:
    """System UI colors - distinct from agent persona colors."""
    # These are terminal color names, NOT agent identity colors
    PASS = "bright_green"
    FAIL = "bright_red"
    WARN = "bright_yellow"
    SKIP = "dim"
    LEGACY = "dark_orange"
    REVIEW = "bright_cyan"
    INFO = "bright_blue"
    HEADER = "bold bright_white"
    BORDER = "bright_black"
    MUTED = "dim white"
    ACCENT = "magenta"  # System accent, not agent magenta


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class GateStatus(Enum):
    """Status of a governance gate check."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"
    LEGACY = "legacy"
    REVIEW = "review"


@dataclass
class GateResult:
    """Result of a single gate check."""
    gate_id: str
    gate_name: str
    status: GateStatus
    message: str
    details: Optional[str] = None
    hint: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class GovernanceReport:
    """Complete governance validation report for UI rendering."""
    mode: str  # e.g., "PAG-01 AUDIT", "CI VALIDATION"
    source: str  # e.g., file path or "repository"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    gates: List[GateResult] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Check if all gates passed."""
        return all(g.status in (GateStatus.PASS, GateStatus.SKIP) for g in self.gates)

    @property
    def total_gates(self) -> int:
        return len(self.gates)

    @property
    def passed_count(self) -> int:
        return sum(1 for g in self.gates if g.status == GateStatus.PASS)

    @property
    def failed_count(self) -> int:
        return sum(1 for g in self.gates if g.status == GateStatus.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for g in self.gates if g.status == GateStatus.WARN)


# =============================================================================
# TERMINAL UI RENDERER
# =============================================================================

class GovernanceTerminalUI:
    """
    Canonical terminal UI renderer for governance output.

    Uses Rich library for consistent, accessible rendering.
    All output is read-only and deterministic.
    """

    def __init__(self, force_terminal: bool = False, no_color: bool = False):
        """
        Initialize the terminal UI renderer.

        Args:
            force_terminal: Force terminal output even if not a TTY
            no_color: Disable color output (for CI/logs)
        """
        self.no_color = no_color

        if RICH_AVAILABLE:
            self.console = Console(
                force_terminal=force_terminal,
                no_color=no_color,
                highlight=False,
                markup=True,
            )
        else:
            self.console = None

    def _get_status_style(self, status: GateStatus) -> tuple:
        """Get glyph and style for a gate status."""
        mapping = {
            GateStatus.PASS: (SystemGlyph.PASS.value, SystemColor.PASS),
            GateStatus.FAIL: (SystemGlyph.FAIL.value, SystemColor.FAIL),
            GateStatus.WARN: (SystemGlyph.WARN.value, SystemColor.WARN),
            GateStatus.SKIP: (SystemGlyph.SKIP.value, SystemColor.SKIP),
            GateStatus.LEGACY: (SystemGlyph.LEGACY.value, SystemColor.LEGACY),
            GateStatus.REVIEW: (SystemGlyph.REVIEW.value, SystemColor.REVIEW),
        }
        return mapping.get(status, (SystemGlyph.INFO.value, SystemColor.MUTED))

    def render_header(self, report: GovernanceReport) -> None:
        """Render the governance report header."""
        if not self.console:
            self._fallback_header(report)
            return

        # Build header content
        header_text = Text()
        header_text.append("GOVERNANCE GATE ENGINE", style=SystemColor.HEADER)
        header_text.append("\n")
        header_text.append(f"Mode: ", style=SystemColor.MUTED)
        header_text.append(f"{report.mode}", style=SystemColor.ACCENT)
        header_text.append(f"  │  ", style=SystemColor.BORDER)
        header_text.append(f"Source: ", style=SystemColor.MUTED)
        header_text.append(f"{report.source}", style=SystemColor.INFO)
        header_text.append(f"\n")
        header_text.append(f"Timestamp: ", style=SystemColor.MUTED)
        header_text.append(f"{report.timestamp}", style=SystemColor.MUTED)

        panel = Panel(
            header_text,
            box=DOUBLE,
            border_style=SystemColor.BORDER,
            padding=(0, 2),
        )
        self.console.print(panel)

    def render_gates(self, report: GovernanceReport) -> None:
        """Render the gate-by-gate checklist."""
        if not self.console:
            self._fallback_gates(report)
            return

        table = Table(
            show_header=True,
            header_style=SystemColor.HEADER,
            box=box.ROUNDED,
            border_style=SystemColor.BORDER,
            padding=(0, 1),
            expand=True,
        )

        table.add_column("", width=5, justify="center")  # Status glyph
        table.add_column("Gate", style=SystemColor.MUTED, min_width=20)
        table.add_column("Result", min_width=30)
        table.add_column("Details", style=SystemColor.MUTED)

        for gate in report.gates:
            glyph, style = self._get_status_style(gate.status)

            # Status cell
            status_text = Text(glyph, style=style)

            # Gate name
            gate_text = Text(gate.gate_name)

            # Result message
            result_text = Text(gate.message, style=style)

            # Details (truncated if needed)
            details = gate.details or ""
            if len(details) > 40:
                details = details[:37] + "..."
            details_text = Text(details)

            table.add_row(status_text, gate_text, result_text, details_text)

            # Add hint row if present and gate failed
            if gate.hint and gate.status == GateStatus.FAIL:
                hint_text = Text(f"  └─ Hint: {gate.hint}", style=SystemColor.WARN)
                table.add_row("", "", hint_text, "")

        self.console.print(table)

    def render_summary(self, report: GovernanceReport) -> None:
        """Render the summary footer."""
        if not self.console:
            self._fallback_summary(report)
            return

        # Determine overall status
        if report.passed:
            overall_glyph = SystemGlyph.PASS.value
            overall_style = SystemColor.PASS
            overall_text = "ALL GATES PASSED"
        elif report.failed_count > 0:
            overall_glyph = SystemGlyph.FAIL.value
            overall_style = SystemColor.FAIL
            overall_text = f"{report.failed_count} GATE(S) FAILED"
        else:
            overall_glyph = SystemGlyph.WARN.value
            overall_style = SystemColor.WARN
            overall_text = "REVIEW REQUIRED"

        # Build summary text
        summary = Text()
        summary.append(f"\n{overall_glyph} ", style=overall_style)
        summary.append(overall_text, style=f"bold {overall_style}")
        summary.append(f"\n\n")
        summary.append(f"Total: {report.total_gates}", style=SystemColor.MUTED)
        summary.append(f"  │  ", style=SystemColor.BORDER)
        summary.append(f"Pass: {report.passed_count}", style=SystemColor.PASS)
        summary.append(f"  │  ", style=SystemColor.BORDER)
        summary.append(f"Fail: {report.failed_count}", style=SystemColor.FAIL)
        summary.append(f"  │  ", style=SystemColor.BORDER)
        summary.append(f"Warn: {report.warn_count}", style=SystemColor.WARN)

        panel = Panel(
            summary,
            box=ROUNDED,
            border_style=overall_style,
            padding=(0, 2),
        )
        self.console.print(panel)

    def render_report(self, report: GovernanceReport) -> None:
        """Render a complete governance report."""
        self.render_header(report)
        self.console.print() if self.console else print()
        self.render_gates(report)
        self.render_summary(report)

    def render_violation(
        self,
        code: str,
        message: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        hint: Optional[str] = None,
    ) -> None:
        """Render a single violation with actionable hint."""
        if not self.console:
            self._fallback_violation(code, message, file_path, line_number, hint)
            return

        # Build violation text
        text = Text()
        text.append(f"{SystemGlyph.FAIL.value} ", style=SystemColor.FAIL)
        text.append(f"[{code}] ", style=f"bold {SystemColor.FAIL}")
        text.append(message, style=SystemColor.FAIL)

        if file_path:
            text.append(f"\n   File: ", style=SystemColor.MUTED)
            text.append(file_path, style=SystemColor.INFO)
            if line_number:
                text.append(f":{line_number}", style=SystemColor.INFO)

        if hint:
            text.append(f"\n   {SystemGlyph.INFO.value} ", style=SystemColor.WARN)
            text.append(hint, style=SystemColor.WARN)

        self.console.print(text)

    def render_success(self, message: str) -> None:
        """Render a success message."""
        if self.console:
            text = Text()
            text.append(f"{SystemGlyph.PASS.value} ", style=SystemColor.PASS)
            text.append(message, style=SystemColor.PASS)
            self.console.print(text)
        else:
            print(f"{SystemGlyph.PASS.value} {message}")

    def render_banner(self, title: str, style: str = "info") -> None:
        """Render a section banner."""
        styles = {
            "info": SystemColor.INFO,
            "pass": SystemColor.PASS,
            "fail": SystemColor.FAIL,
            "warn": SystemColor.WARN,
        }
        color = styles.get(style, SystemColor.INFO)

        if self.console:
            self.console.print()
            self.console.rule(title, style=color)
            self.console.print()
        else:
            print(f"\n{'=' * 60}")
            print(f" {title}")
            print(f"{'=' * 60}\n")

    # =========================================================================
    # FALLBACK RENDERERS (when Rich is not available)
    # =========================================================================

    def _fallback_header(self, report: GovernanceReport) -> None:
        """Plain text header fallback."""
        print("=" * 60)
        print("GOVERNANCE GATE ENGINE")
        print(f"Mode: {report.mode}  |  Source: {report.source}")
        print(f"Timestamp: {report.timestamp}")
        print("=" * 60)

    def _fallback_gates(self, report: GovernanceReport) -> None:
        """Plain text gates fallback."""
        for gate in report.gates:
            glyph, _ = self._get_status_style(gate.status)
            print(f"{glyph} {gate.gate_name}: {gate.message}")
            if gate.hint and gate.status == GateStatus.FAIL:
                print(f"   └─ Hint: {gate.hint}")

    def _fallback_summary(self, report: GovernanceReport) -> None:
        """Plain text summary fallback."""
        print("-" * 60)
        if report.passed:
            print(f"{SystemGlyph.PASS.value} ALL GATES PASSED")
        else:
            print(f"{SystemGlyph.FAIL.value} {report.failed_count} GATE(S) FAILED")
        print(f"Total: {report.total_gates} | Pass: {report.passed_count} | Fail: {report.failed_count}")
        print("-" * 60)

    def _fallback_violation(
        self,
        code: str,
        message: str,
        file_path: Optional[str],
        line_number: Optional[int],
        hint: Optional[str],
    ) -> None:
        """Plain text violation fallback."""
        print(f"{SystemGlyph.FAIL.value} [{code}] {message}")
        if file_path:
            loc = f"{file_path}:{line_number}" if line_number else file_path
            print(f"   File: {loc}")
        if hint:
            print(f"   Hint: {hint}")


# =============================================================================
# DEMO MODE
# =============================================================================

def run_demo() -> None:
    """Run a demonstration of the terminal UI."""
    ui = GovernanceTerminalUI()

    # Create sample report
    report = GovernanceReport(
        mode="PAG-01 COMPLIANCE AUDIT",
        source="docs/governance/",
        gates=[
            GateResult(
                gate_id="PAG_001",
                gate_name="AGENT_ACTIVATION_ACK Present",
                status=GateStatus.PASS,
                message="Block found and valid",
                details="48 files compliant",
            ),
            GateResult(
                gate_id="PAG_002",
                gate_name="RUNTIME_ACTIVATION_ACK Present",
                status=GateStatus.PASS,
                message="Block found and valid",
                details="48 files compliant",
            ),
            GateResult(
                gate_id="PAG_003",
                gate_name="Registry Binding",
                status=GateStatus.WARN,
                message="2 files have mismatched colors",
                details="WRAP-ATLAS-A12, GOLD_STANDARD_WRAP_TEMPLATE",
                hint="Run: python tools/governance/pag_audit.py --verbose",
            ),
            GateResult(
                gate_id="PAG_005",
                gate_name="Block Ordering",
                status=GateStatus.PASS,
                message="Runtime precedes Agent in all files",
            ),
            GateResult(
                gate_id="LEGACY_001",
                gate_name="Legacy File Detection",
                status=GateStatus.LEGACY,
                message="32 pre-PAG-01 files detected",
                details="Locks, templates, policies",
                hint="These files predate PAG-01 and are exempt",
            ),
            GateResult(
                gate_id="GS_030",
                gate_name="Gold Standard Compliance",
                status=GateStatus.FAIL,
                message="TRAINING_SIGNAL missing",
                details="PAC-ALEX-G2-GLOBAL-AGENT-LEARNING-LEDGER-01.md",
                hint="Add TRAINING_SIGNAL block per Gold Standard template",
            ),
        ],
    )

    ui.render_banner("GOVERNANCE TERMINAL UI DEMO", style="info")
    ui.render_report(report)

    print("\n")
    ui.render_banner("INDIVIDUAL VIOLATION RENDERING", style="warn")

    ui.render_violation(
        code="PAG_006_COLOR_MISMATCH",
        message="Agent color does not match registry",
        file_path="docs/governance/WRAP-ATLAS-A12-GOVERNANCE-CORRECTION-01.md",
        line_number=15,
        hint="Expected: BLUE, Found: BUILD / STATE ENGINE",
    )

    print("\n")
    ui.render_success("Demonstration complete. No governance state was mutated.")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Terminal Governance UI — Canonical Rendering Layer"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration of terminal UI components",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color output",
    )
    parser.add_argument(
        "--check-rich",
        action="store_true",
        help="Check if Rich library is available",
    )

    args = parser.parse_args()

    if args.check_rich:
        if RICH_AVAILABLE:
            print(f"{SystemGlyph.PASS.value} Rich library is available")
            sys.exit(0)
        else:
            print(f"{SystemGlyph.FAIL.value} Rich library not installed")
            print("Install with: pip install rich")
            sys.exit(1)

    if args.demo:
        run_demo()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()


# =============================================================================
# END — CODY (GID-01) — 🔵 BLUE
# =============================================================================
