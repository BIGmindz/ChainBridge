#!/usr/bin/env python3
"""
Governance Terminal UI Demo
PAC-ATLAS-P29 + PAC-ATLAS-P31 (Operator Enhancement)

Terminal-only governance visualization demo with operator-focused cues.
No governance logic is modified. Output-only demonstration.

Usage:
    python tools/governance/demo_ui.py           # Default rich mode
    python tools/governance/demo_ui.py --ui      # Rich mode (explicit)
    python tools/governance/demo_ui.py --ui-compact  # Compact mode
    python tools/governance/demo_ui.py --no-ui   # Plain ASCII (CI fallback)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class UIMode(Enum):
    """UI rendering modes."""
    RICH = "rich"
    COMPACT = "compact"
    PLAIN = "plain"


class GovState(Enum):
    """Governance validation states."""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    LEGACY = "LEGACY"
    REVIEW = "REVIEW"
    WARN = "WARN"


@dataclass
class GovResult:
    """Single governance result entry."""
    artifact_id: str
    state: GovState
    note: str = ""
    next_action: str = ""


# High-contrast symbols that don't conflict with agent identity colors
# Rich mode: Unicode glyphs with ANSI colors
SYMBOLS_RICH = {
    GovState.PASS:   ("▰✔▰", "\033[92m"),   # Bright green
    GovState.FAIL:   ("▰✖▰", "\033[91m"),   # Bright red
    GovState.SKIP:   ("▰↷▰", "\033[96m"),   # Cyan
    GovState.LEGACY: ("▰⧗▰", "\033[93m"),   # Yellow
    GovState.REVIEW: ("▰⚠▰", "\033[95m"),   # Magenta
    GovState.WARN:   ("▰⚡▰", "\033[93m"),   # Yellow
}

# Compact mode: Smaller glyphs
SYMBOLS_COMPACT = {
    GovState.PASS:   ("✓", "\033[92m"),
    GovState.FAIL:   ("✗", "\033[91m"),
    GovState.SKIP:   ("↷", "\033[96m"),
    GovState.LEGACY: ("⧗", "\033[93m"),
    GovState.REVIEW: ("⚠", "\033[95m"),
    GovState.WARN:   ("⚡", "\033[93m"),
}

# Plain mode: ASCII only (CI fallback)
SYMBOLS_PLAIN = {
    GovState.PASS:   ("[PASS]", ""),
    GovState.FAIL:   ("[FAIL]", ""),
    GovState.SKIP:   ("[SKIP]", ""),
    GovState.LEGACY: ("[LEGACY]", ""),
    GovState.REVIEW: ("[REVIEW]", ""),
    GovState.WARN:   ("[WARN]", ""),
}

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def detect_ci() -> bool:
    """Detect if running in CI environment."""
    ci_vars = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "CIRCLECI"]
    return any(os.environ.get(var) for var in ci_vars)


def get_symbols(mode: UIMode) -> dict:
    """Get symbol set for UI mode."""
    if mode == UIMode.RICH:
        return SYMBOLS_RICH
    elif mode == UIMode.COMPACT:
        return SYMBOLS_COMPACT
    return SYMBOLS_PLAIN


def get_colors(mode: UIMode) -> tuple:
    """Get color codes for UI mode."""
    if mode == UIMode.PLAIN:
        return "", "", ""  # No colors
    return RESET, BOLD, DIM


class DemoRenderer:
    """Governance demo renderer with multiple UI modes."""

    def __init__(self, mode: UIMode):
        self.mode = mode
        self.symbols = get_symbols(mode)
        self.reset, self.bold, self.dim = get_colors(mode)
        self.start_time: Optional[float] = None

    def render_result(self, result: GovResult) -> str:
        """Render a single governance result line."""
        symbol, color = self.symbols[result.state]
        note_str = f" — {result.note}" if result.note else ""
        if self.mode == UIMode.PLAIN:
            return f"{symbol} {result.artifact_id}{note_str}"
        return f"{color}{symbol}{self.reset} {result.artifact_id}{self.dim}{note_str}{self.reset}"

    def render_summary(self, results: List[GovResult]) -> str:
        """Render summary counts."""
        counts = {state: 0 for state in GovState}
        for r in results:
            counts[r.state] += 1

        lines = [f"{self.bold}SUMMARY{self.reset}" if self.mode != UIMode.PLAIN else "SUMMARY"]
        labels = {
            GovState.PASS: "PASSED",
            GovState.FAIL: "FAILED",
            GovState.SKIP: "SKIPPED",
            GovState.LEGACY: "LEGACY",
            GovState.REVIEW: "REVIEW",
            GovState.WARN: "WARNINGS",
        }
        for state in GovState:
            if counts[state] > 0:
                symbol, color = self.symbols[state]
                if self.mode == UIMode.PLAIN:
                    lines.append(f"{symbol} {counts[state]} {labels[state]}")
                else:
                    lines.append(f"{color}{symbol}{self.reset} {counts[state]} {labels[state]}")
        return "\n".join(lines)

    def render_next_actions(self, results: List[GovResult]) -> str:
        """Render next action hints for failures."""
        actions = []
        for r in results:
            if r.state in (GovState.FAIL, GovState.REVIEW) and r.next_action:
                actions.append(f"  → {r.artifact_id}: {r.next_action}")
        
        if not actions:
            return ""
        
        header = f"{self.bold}NEXT ACTIONS{self.reset}" if self.mode != UIMode.PLAIN else "NEXT ACTIONS"
        return header + "\n" + "\n".join(actions)

    def render_banner_start(self, title: str) -> str:
        """Render start banner."""
        self.start_time = time.time()
        width = 80
        if self.mode == UIMode.PLAIN:
            return f"{'=' * width}\n>>> {title} <<<\n{'=' * width}"
        border = "═" * width
        return f"\n{self.bold}▶▶▶ {title} ◀◀◀{self.reset}\n{border}"

    def render_banner_end(self, has_failures: bool) -> str:
        """Render end banner with timing."""
        width = 80
        elapsed = time.time() - self.start_time if self.start_time else 0
        elapsed_str = f"Elapsed: {elapsed:.2f}s"
        
        if self.mode == UIMode.PLAIN:
            status = "FAILURES DETECTED" if has_failures else "ALL CHECKS PASSED"
            return f"{'=' * width}\n<<< END | {status} | {elapsed_str} >>>\n{'=' * width}"
        
        border = "═" * width
        if has_failures:
            status = f"\033[91m✖ FAILURES DETECTED{self.reset}"
        else:
            status = f"\033[92m✓ ALL CHECKS PASSED{self.reset}"
        return f"{border}\n{self.bold}◀◀◀ END{self.reset} | {status} | {self.dim}{elapsed_str}{self.reset}\n"

    def render_header(self) -> str:
        """Render demo header box."""
        if self.mode == UIMode.PLAIN:
            return (
                "+------------------------------------------------------------+\n"
                "| ChainBridge Governance Terminal UI Demo                    |\n"
                "| PAC-ATLAS-P31 | Agent: ATLAS (GID-05) | BLUE               |\n"
                "| Mode: DEMO_ONLY | No governance mutation                   |\n"
                "+------------------------------------------------------------+"
            )
        return (
            f"{self.dim}╭────────────────────────────────────────────────────────────╮{self.reset}\n"
            f"{self.dim}│{self.reset} {self.bold}ChainBridge Governance Terminal UI Demo{self.reset}                    {self.dim}│{self.reset}\n"
            f"{self.dim}│{self.reset} PAC-ATLAS-P31 | Agent: ATLAS (GID-05) | 🔵 BLUE            {self.dim}│{self.reset}\n"
            f"{self.dim}│{self.reset} Mode: DEMO_ONLY | No governance mutation                   {self.dim}│{self.reset}\n"
            f"{self.dim}╰────────────────────────────────────────────────────────────╯{self.reset}"
        )

    def render_legend(self) -> str:
        """Render symbol legend."""
        lines = [f"{self.dim}Legend:{self.reset}" if self.mode != UIMode.PLAIN else "Legend:"]
        for state in GovState:
            symbol, color = self.symbols[state]
            if self.mode == UIMode.PLAIN:
                lines.append(f"  {symbol} = {state.value}")
            else:
                lines.append(f"  {color}{symbol}{self.reset} = {state.value}")
        return "\n".join(lines)


def get_demo_results() -> List[GovResult]:
    """Get demo data with next action hints."""
    return [
        GovResult(
            "PAC-ALEX-P26-PAG01-GOVERNANCE-ADOPTION-AND-ENFORCEMENT-01",
            GovState.PASS
        ),
        GovResult(
            "PAC-CODY-P25-PAG01-PERSONA-ACTIVATION-CORRECTION-01",
            GovState.PASS
        ),
        GovResult(
            "WRAP-SONNY-P28",
            GovState.SKIP,
            "report-only artifact"
        ),
        GovResult(
            "WRAP-SAM-G1",
            GovState.LEGACY,
            "legacy exemption"
        ),
        GovResult(
            "PAC-SAM-P21",
            GovState.FAIL,
            "missing AGENT_ACTIVATION_ACK",
            "Add AGENT_ACTIVATION_ACK block with canonical schema"
        ),
        GovResult(
            "PAC-MAGGIE-P24",
            GovState.REVIEW,
            "requires human review",
            "Escalate to governance owner for sign-off"
        ),
    ]


def run_demo(mode: UIMode) -> int:
    """Run the governance demo."""
    renderer = DemoRenderer(mode)
    results = get_demo_results()
    has_failures = any(r.state == GovState.FAIL for r in results)

    print()
    print(renderer.render_header())
    print(renderer.render_banner_start("PAG-01 PERSONA ACTIVATION AUDIT (DEMO)"))

    for result in results:
        print(renderer.render_result(result))

    print()
    print(renderer.render_summary(results))

    next_actions = renderer.render_next_actions(results)
    if next_actions:
        print()
        print(next_actions)

    print(renderer.render_banner_end(has_failures))
    print(renderer.render_legend())
    print()

    return 1 if has_failures else 0


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="ChainBridge Governance Terminal UI Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
UI Modes:
  --ui          Rich mode with Unicode glyphs and colors (default)
  --ui-compact  Compact mode with smaller symbols
  --no-ui       Plain ASCII mode for CI environments

Examples:
  python tools/governance/demo_ui.py
  python tools/governance/demo_ui.py --ui-compact
  python tools/governance/demo_ui.py --no-ui
        """
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--ui", action="store_true", help="Rich UI mode (default)")
    group.add_argument("--ui-compact", action="store_true", help="Compact UI mode")
    group.add_argument("--no-ui", action="store_true", help="Plain ASCII mode (CI fallback)")
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Determine UI mode
    if args.no_ui or detect_ci():
        mode = UIMode.PLAIN
    elif args.ui_compact:
        mode = UIMode.COMPACT
    else:
        mode = UIMode.RICH

    return run_demo(mode)


if __name__ == "__main__":
    sys.exit(main())
