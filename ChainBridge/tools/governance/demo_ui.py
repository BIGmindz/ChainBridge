#!/usr/bin/env python3
"""
Governance Terminal UI Demo
PAC-ATLAS-P29-GOVERNANCE-TERMINAL-UI-DEMO-EXECUTION-01

Terminal-only governance visualization demo.
No governance logic is modified. Output-only demonstration.

Usage:
    python tools/governance/demo_ui.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from typing import List


class GovState(Enum):
    """Governance validation states."""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    LEGACY = "LEGACY"
    REVIEW = "REVIEW"


@dataclass
class GovResult:
    """Single governance result entry."""
    artifact_id: str
    state: GovState
    note: str = ""


# High-contrast symbols that don't conflict with agent identity colors
SYMBOLS = {
    GovState.PASS:   ("▰✔▰", "\033[92m"),   # Bright green
    GovState.FAIL:   ("▰✖▰", "\033[91m"),   # Bright red
    GovState.SKIP:   ("▰↷▰", "\033[96m"),   # Cyan
    GovState.LEGACY: ("▰⧗▰", "\033[93m"),   # Yellow
    GovState.REVIEW: ("▰⚠▰", "\033[95m"),   # Magenta
}
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def render_result(result: GovResult) -> str:
    """Render a single governance result line."""
    symbol, color = SYMBOLS[result.state]
    note_str = f" — {result.note}" if result.note else ""
    return f"{color}{symbol}{RESET} {result.artifact_id}{DIM}{note_str}{RESET}"


def render_summary(results: List[GovResult]) -> str:
    """Render summary counts."""
    counts = {state: 0 for state in GovState}
    for r in results:
        counts[r.state] += 1
    
    lines = [f"{BOLD}SUMMARY{RESET}"]
    labels = {
        GovState.PASS: "PASSED",
        GovState.FAIL: "FAILED",
        GovState.SKIP: "SKIPPED",
        GovState.LEGACY: "LEGACY",
        GovState.REVIEW: "REVIEW",
    }
    for state in GovState:
        if counts[state] > 0:
            symbol, color = SYMBOLS[state]
            lines.append(f"{color}{symbol}{RESET} {counts[state]} {labels[state]}")
    return "\n".join(lines)


def render_demo() -> None:
    """Render the full governance UI demo."""
    # Demo data
    results = [
        GovResult("PAC-ALEX-P26-PAG01-GOVERNANCE-ADOPTION-AND-ENFORCEMENT-01", GovState.PASS),
        GovResult("PAC-CODY-P25-PAG01-PERSONA-ACTIVATION-CORRECTION-01", GovState.PASS),
        GovResult("WRAP-SONNY-P28", GovState.SKIP, "report-only artifact"),
        GovResult("WRAP-SAM-G1", GovState.LEGACY, "legacy exemption"),
        GovResult("PAC-SAM-P21", GovState.FAIL, "missing AGENT_ACTIVATION_ACK"),
        GovResult("PAC-MAGGIE-P24", GovState.REVIEW, "requires human review"),
    ]
    
    width = 80
    border = "═" * width
    
    print()
    print(f"{BOLD}▶▶▶ PAG-01 PERSONA ACTIVATION AUDIT (DEMO) ◀◀◀{RESET}")
    print(border)
    
    for result in results:
        print(render_result(result))
    
    print()
    print(render_summary(results))
    print(border)
    print(f"{BOLD}◀◀◀ END ◀◀◀{RESET}")
    print()


def main() -> int:
    """Main entry point."""
    print()
    print(f"{DIM}╭────────────────────────────────────────────────────────────╮{RESET}")
    print(f"{DIM}│{RESET} {BOLD}ChainBridge Governance Terminal UI Demo{RESET}                    {DIM}│{RESET}")
    print(f"{DIM}│{RESET} PAC-ATLAS-P29 | Agent: ATLAS (GID-05) | 🔵 BLUE            {DIM}│{RESET}")
    print(f"{DIM}│{RESET} Mode: DEMO_ONLY | No governance mutation                   {DIM}│{RESET}")
    print(f"{DIM}╰────────────────────────────────────────────────────────────╯{RESET}")
    
    render_demo()
    
    print(f"{DIM}Legend:{RESET}")
    for state in GovState:
        symbol, color = SYMBOLS[state]
        print(f"  {color}{symbol}{RESET} = {state.value}")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
