#!/usr/bin/env python3
"""
PAC Linter — Agent Roster Enforcement
════════════════════════════════════════════════════════════════════════════════

Validates PAC (Protocol Acknowledgment Certificate) files against the
canonical agent roster. Enforces HARD RULES:

- No new agents without explicit registry update
- No color reassignment
- No emoji substitution
- No dual colors per agent
- All PAC headers/footers must match exactly

Usage:
    python tools/pac_linter.py                    # Lint all PAC files
    python tools/pac_linter.py path/to/file.py   # Lint specific file
    python tools/pac_linter.py --check           # CI mode (exit 1 on failure)

PAC Reference: PAC-ALEX-LINTER-001
Effective Date: 2025-12-19

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

# Import canonical roster
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.governance.agent_roster import (
    CANONICAL_AGENTS,
    EMOJI_TO_COLOR,
    VALID_AGENT_LEVELS,
    VALID_EMOJIS,
    VALID_GIDS,
    get_agent_by_name,
    get_agent_color,
    get_agent_level,
    is_deprecated_agent,
    is_teal_allowed,
)


class ViolationSeverity(Enum):
    """Violation severity levels."""

    ERROR = "ERROR"      # Blocks merge
    WARNING = "WARNING"  # Requires review
    INFO = "INFO"        # Informational


@dataclass
class LintViolation:
    """A single lint violation."""

    file: Path
    line: int
    severity: ViolationSeverity
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line} [{self.severity.value}] {self.rule}: {self.message}"


# ═══════════════════════════════════════════════════════════════════════════════
# LINT RULES
# ═══════════════════════════════════════════════════════════════════════════════

# Pattern for emoji border rows (10 identical emojis)
EMOJI_BORDER_PATTERN = re.compile(r"^[⚪🔵🟣🟨🟦🟧🟥🟩🩷]{10}$")

# Pattern for agent header: emoji AGENT — GID-XX
AGENT_HEADER_PATTERN = re.compile(
    r"^([⚪🔵🟣🟨🟦🟧🟥🟩🩷])\s+(\w+(?:-\w+)?)\s*(?:—|–|-|/)\s*(GID-\d+)",
    re.IGNORECASE
)

# Pattern for any GID reference
GID_REFERENCE_PATTERN = re.compile(r"\b(GID-\d+)\b", re.IGNORECASE)

# Pattern for agent name + GID combo anywhere
AGENT_GID_COMBO_PATTERN = re.compile(
    r"\b(\w+(?:-\w+)?)\s*(?:—|–|-|:|\(|/)\s*(GID-\d+)",
    re.IGNORECASE
)


def lint_emoji_border_consistency(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-emoji-border-consistency
    Emoji border rows must use uniform, valid emojis.
    """
    violations = []
    lines = content.split("\n")

    detected_emoji: Optional[str] = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Check if this looks like an emoji border
        if len(stripped) >= 10 and all(c in "⚪🔵🟣🟨🟦🟧🟥🟩🩷" for c in stripped):
            emojis_in_row = set(stripped)

            # Rule: Must be uniform (single emoji type)
            if len(emojis_in_row) > 1:
                violations.append(LintViolation(
                    file=file_path,
                    line=i,
                    severity=ViolationSeverity.ERROR,
                    rule="pac-emoji-border-consistency",
                    message=f"Mixed emojis in border row: {emojis_in_row}. Must be uniform.",
                ))
            else:
                current_emoji = stripped[0]

                # Rule: Must be a valid registered emoji
                if current_emoji not in VALID_EMOJIS:
                    violations.append(LintViolation(
                        file=file_path,
                        line=i,
                        severity=ViolationSeverity.ERROR,
                        rule="pac-emoji-not-registered",
                        message=f"Emoji '{current_emoji}' is not in canonical agent roster.",
                    ))

                # Track for consistency within file
                if detected_emoji is None:
                    detected_emoji = current_emoji
                elif current_emoji != detected_emoji:
                    violations.append(LintViolation(
                        file=file_path,
                        line=i,
                        severity=ViolationSeverity.ERROR,
                        rule="pac-emoji-border-consistency",
                        message=f"Inconsistent emoji '{current_emoji}' (file uses '{detected_emoji}').",
                    ))

    return violations


# Test files with intentional invalid GIDs for testing guard behavior
TEST_FILES_WITH_INVALID_GIDS = {
    "test_pdo_guards.py",
    "test_lane_enforcement.py",
    "test_settlement_guards.py",
}


def lint_gid_validity(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-gid-valid
    All GID references must exist in the canonical roster.
    """
    violations = []

    # Skip GID validation for test files with intentional invalid GIDs
    if file_path.name in TEST_FILES_WITH_INVALID_GIDS:
        return violations

    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        for match in GID_REFERENCE_PATTERN.finditer(line):
            gid = match.group(1).upper()
            if gid not in VALID_GIDS:
                violations.append(LintViolation(
                    file=file_path,
                    line=i,
                    severity=ViolationSeverity.ERROR,
                    rule="pac-gid-valid",
                    message=f"Unknown GID '{gid}'. Not in canonical roster (GID-00 to GID-11).",
                ))

    return violations


def lint_agent_gid_match(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-agent-gid-match
    Agent names must match their canonical GIDs.
    """
    violations = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        for match in AGENT_GID_COMBO_PATTERN.finditer(line):
            agent_name = match.group(1).upper()
            gid = match.group(2).upper()

            # Skip if agent name is not recognized (could be something else)
            agent = get_agent_by_name(agent_name)
            if agent is None:
                continue

            if agent.gid != gid:
                violations.append(LintViolation(
                    file=file_path,
                    line=i,
                    severity=ViolationSeverity.ERROR,
                    rule="pac-agent-gid-match",
                    message=f"Agent '{agent_name}' has incorrect GID '{gid}'. Expected '{agent.gid}'.",
                ))

    return violations


def lint_agent_emoji_match(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-agent-emoji-match
    Agent emojis must match their canonical assignments.
    """
    violations = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        match = AGENT_HEADER_PATTERN.search(line)
        if match:
            emoji = match.group(1)
            agent_name = match.group(2).upper()

            agent = get_agent_by_name(agent_name)
            if agent is None:
                violations.append(LintViolation(
                    file=file_path,
                    line=i,
                    severity=ViolationSeverity.ERROR,
                    rule="pac-agent-unknown",
                    message=f"Unknown agent '{agent_name}'. Not in canonical roster.",
                ))
            elif agent.emoji != emoji:
                violations.append(LintViolation(
                    file=file_path,
                    line=i,
                    severity=ViolationSeverity.ERROR,
                    rule="pac-agent-emoji-match",
                    message=f"Agent '{agent_name}' uses wrong emoji '{emoji}'. Expected '{agent.emoji}'.",
                ))

    return violations


def lint_pac_header_footer_match(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-header-footer-match
    PAC headers and footers must match agent identity.
    """
    violations = []

    # Find header
    header_match = AGENT_HEADER_PATTERN.search(content)
    if not header_match:
        # No PAC header found - not a PAC file, skip
        return violations

    header_agent = header_match.group(2).upper()
    header_gid = header_match.group(3).upper()

    # Look for proper footer
    footer_patterns = [
        re.compile(r"END\s+OF\s+PAC", re.IGNORECASE),
        re.compile(rf"{header_agent}.*ENGINE", re.IGNORECASE),
        re.compile(r"[⚪🔵🟣🟨🟦🟧🟥🟩🩷]{10}\s*$"),
    ]

    has_proper_footer = any(p.search(content) for p in footer_patterns)

    if not has_proper_footer:
        violations.append(LintViolation(
            file=file_path,
            line=len(content.split("\n")),
            severity=ViolationSeverity.WARNING,
            rule="pac-header-footer-match",
            message=f"PAC for {header_agent} ({header_gid}) missing proper footer.",
        ))

    return violations


def lint_no_duplicate_gid_assignment(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-no-duplicate-gid
    Each GID can only be assigned to one agent in a file.
    """
    violations = []

    gid_to_agents: dict[str, set[str]] = {}

    for match in AGENT_GID_COMBO_PATTERN.finditer(content):
        agent_name = match.group(1).upper()
        gid = match.group(2).upper()

        if gid not in gid_to_agents:
            gid_to_agents[gid] = set()
        gid_to_agents[gid].add(agent_name)

    for gid, agents in gid_to_agents.items():
        # Filter to known agents only
        known_agents = {a for a in agents if get_agent_by_name(a) is not None}
        if len(known_agents) > 1:
            violations.append(LintViolation(
                file=file_path,
                line=1,
                severity=ViolationSeverity.ERROR,
                rule="pac-no-duplicate-gid",
                message=f"GID '{gid}' assigned to multiple agents: {known_agents}.",
            ))

    return violations


# ═══════════════════════════════════════════════════════════════════════════════
# COLOR GATEWAY ENFORCEMENT — PAC-BENSON-COLOR-GATEWAY-ENFORCEMENT-CODE-01
# ═══════════════════════════════════════════════════════════════════════════════

# Pattern for EXECUTING AGENT line
EXECUTING_AGENT_PATTERN = re.compile(
    r"EXECUTING\s+AGENT[:\s]+(\w+(?:-\w+)?)\s*(?:\(|—|–|-|/)?\s*(GID-\d+)?",
    re.IGNORECASE
)

# Pattern for EXECUTING COLOR line - matches emoji + color name on same line
EXECUTING_COLOR_PATTERN = re.compile(
    r"EXECUTING\s+COLOR[:\s]+([🟦🟩🔷🔵🟡🟨🟣🟠🟧🔴🟥🟢⚪🩷💗]+)?\s*((?:TEAL|BLUE|YELLOW|PURPLE|ORANGE|DARK\s*RED|GREEN|WHITE|GREY|PINK))\b",
    re.IGNORECASE
)

# Pattern for PAC header with GID
PAC_HEADER_GID_PATTERN = re.compile(
    r"(GID-\d+)\s*(?:—|–|-|/)\s*(\w+(?:-\w+)?)",
    re.IGNORECASE
)

# Pattern for color declaration in header
PAC_HEADER_COLOR_PATTERN = re.compile(
    r"([🟦🟩🔷🔵🟡🟨🟣🟠🟧🔴🟥🟢⚪🩷💗]+)\s*(\w+(?:\s+\w+)?)\s*(?:—|–|-|/)",
    re.IGNORECASE
)


def lint_pac_has_required_fields(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-color-gateway-required-fields
    PACs must have: EXECUTING AGENT, GID, and EXECUTING COLOR.
    """
    violations = []

    # Check if this looks like a PAC file
    if "PAC-" not in content and "GID-" not in content:
        return violations  # Not a PAC file

    # Check for EXECUTING AGENT
    has_executing_agent = EXECUTING_AGENT_PATTERN.search(content) is not None

    # Check for EXECUTING COLOR
    has_executing_color = EXECUTING_COLOR_PATTERN.search(content) is not None

    # Check for GID in header
    has_gid_header = PAC_HEADER_GID_PATTERN.search(content) is not None

    # Only flag if it looks like a PAC but is missing fields
    pac_indicators = [
        "EXECUTING AGENT",
        "EXECUTING COLOR",
        "END OF PAC",
        "════════",
    ]

    is_pac = any(ind in content for ind in pac_indicators)

    if is_pac:
        if not has_executing_agent:
            violations.append(LintViolation(
                file=file_path,
                line=1,
                severity=ViolationSeverity.ERROR,
                rule="pac-color-gateway-required-fields",
                message="PAC missing required field: EXECUTING AGENT",
            ))

        if not has_executing_color:
            violations.append(LintViolation(
                file=file_path,
                line=1,
                severity=ViolationSeverity.ERROR,
                rule="pac-color-gateway-required-fields",
                message="PAC missing required field: EXECUTING COLOR",
            ))

        if not has_gid_header:
            violations.append(LintViolation(
                file=file_path,
                line=1,
                severity=ViolationSeverity.ERROR,
                rule="pac-color-gateway-required-fields",
                message="PAC missing required field: GID in header",
            ))

    return violations


def lint_agent_color_consistency(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-color-gateway-agent-color-match
    Agent must use their canonical color.
    """
    violations = []
    lines = content.split("\n")

    # Extract executing agent and color
    agent_match = EXECUTING_AGENT_PATTERN.search(content)
    color_match = EXECUTING_COLOR_PATTERN.search(content)

    if not agent_match or not color_match:
        return violations  # Can't validate without both

    agent_name = agent_match.group(1).upper()
    declared_color = color_match.group(2).strip().upper() if color_match.group(2) else None

    if not declared_color:
        return violations

    # Get canonical color for agent
    canonical_color = get_agent_color(agent_name)

    if canonical_color is None:
        # Agent not in roster - already caught by other rules
        return violations

    if canonical_color.upper() != declared_color:
        # Find the line number for the color declaration
        line_num = 1
        for i, line in enumerate(lines, 1):
            if "EXECUTING COLOR" in line.upper():
                line_num = i
                break

        violations.append(LintViolation(
            file=file_path,
            line=line_num,
            severity=ViolationSeverity.ERROR,
            rule="pac-color-gateway-agent-color-match",
            message=f"Agent {agent_name} declared color '{declared_color}' but canonical is '{canonical_color}'",
        ))

    return violations


def lint_teal_reserved(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-color-gateway-teal-reserved
    TEAL color is reserved for GID-00 (Benson) ONLY.
    """
    violations = []
    lines = content.split("\n")

    # Check for TEAL usage
    color_match = EXECUTING_COLOR_PATTERN.search(content)
    if not color_match:
        return violations

    declared_color = color_match.group(2).strip().upper() if color_match.group(2) else None

    if declared_color != "TEAL":
        return violations  # Not using TEAL

    # Find the GID
    agent_match = EXECUTING_AGENT_PATTERN.search(content)
    gid_match = PAC_HEADER_GID_PATTERN.search(content)

    gid = None
    if agent_match and agent_match.group(2):
        gid = agent_match.group(2).upper()
    elif gid_match:
        gid = gid_match.group(1).upper()

    if gid is None:
        return violations  # Can't validate without GID

    if not is_teal_allowed(gid):
        # Find line number for color declaration
        line_num = 1
        for i, line in enumerate(lines, 1):
            if "EXECUTING COLOR" in line.upper() or "TEAL" in line.upper():
                line_num = i
                break

        agent_name = agent_match.group(1) if agent_match else "unknown"
        violations.append(LintViolation(
            file=file_path,
            line=line_num,
            severity=ViolationSeverity.ERROR,
            rule="pac-color-gateway-teal-reserved",
            message=f"TEAL color reserved for GID-00 (Benson). Agent {agent_name} ({gid}) cannot use TEAL.",
        ))

    return violations


def lint_emoji_color_match(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-color-gateway-emoji-color-match
    Emoji must match declared color.
    """
    violations = []
    lines = content.split("\n")

    color_match = EXECUTING_COLOR_PATTERN.search(content)
    if not color_match:
        return violations

    emoji = color_match.group(1)
    declared_color = color_match.group(2).strip().upper() if color_match.group(2) else None

    if not emoji or not declared_color:
        return violations

    emoji_color = EMOJI_TO_COLOR.get(emoji)

    if emoji_color and emoji_color.upper() != declared_color:
        # Find line number
        line_num = 1
        for i, line in enumerate(lines, 1):
            if "EXECUTING COLOR" in line.upper():
                line_num = i
                break

        violations.append(LintViolation(
            file=file_path,
            line=line_num,
            severity=ViolationSeverity.ERROR,
            rule="pac-color-gateway-emoji-color-match",
            message=f"Emoji {emoji} is '{emoji_color}' but declared color is '{declared_color}'",
        ))

    return violations


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT LEVEL ENFORCEMENT — PAC-ATLAS-AGENT-REGISTRY-ENFORCEMENT-01
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# END BANNER ENFORCEMENT — PAC-BENSON-CODY-END-BANNER-LINT-ENFORCEMENT-01
# ═══════════════════════════════════════════════════════════════════════════════

# Pattern for END banner line: END — AGENT (GID) — EMOJI COLOR
END_BANNER_PATTERN = re.compile(
    r"END\s*(?:—|–|-|/)\s*(\w+(?:-\w+)?)\s*\((GID-\d+)\)\s*(?:—|–|-|/)\s*([🟦🟩🔷🔵🟡🟨🟣🟠🟧🔴🟥🟢⚪🩷💗]+)?\s*(\w+(?:\s+\w+)?)?",
    re.IGNORECASE
)

# Alternative pattern: just "END — AGENT" or "END — AGENT (GID)"
END_BANNER_SIMPLE_PATTERN = re.compile(
    r"END\s*(?:—|–|-|/)\s*(\w+(?:-\w+)?)\s*(?:\((GID-\d+)\))?",
    re.IGNORECASE
)

# Pattern for emoji border ending a PAC (10 identical emojis at end)
END_EMOJI_BORDER_PATTERN = re.compile(
    r"^[⚪🔵🟣🟨🟦🟧🟥🟩🩷💗]{10}$"
)


def lint_end_banner_present(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-end-banner-present
    All PACs MUST have an END banner.
    """
    violations = []

    # Check if this looks like a PAC file
    pac_indicators = [
        "PAC-",
        "EXECUTING AGENT",
        "EXECUTING COLOR",
        "════════",
    ]

    is_pac = any(ind in content for ind in pac_indicators)

    if not is_pac:
        return violations  # Not a PAC file

    # Look for END banner
    has_end_banner = (
        END_BANNER_PATTERN.search(content) is not None or
        END_BANNER_SIMPLE_PATTERN.search(content) is not None
    )

    if not has_end_banner:
        violations.append(LintViolation(
            file=file_path,
            line=len(content.split("\n")),
            severity=ViolationSeverity.ERROR,
            rule="pac-end-banner-present",
            message="PAC missing required END banner (format: END — AGENT (GID) — EMOJI COLOR)",
        ))

    return violations


def lint_end_banner_agent_match(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-end-banner-agent-match
    END banner agent name must match EXECUTING AGENT.
    """
    violations = []
    lines = content.split("\n")

    # Get executing agent
    exec_agent_match = EXECUTING_AGENT_PATTERN.search(content)
    if not exec_agent_match:
        return violations  # Can't validate without executing agent

    executing_agent = exec_agent_match.group(1).upper()

    # Find END banner
    end_match = END_BANNER_PATTERN.search(content)
    if not end_match:
        end_match = END_BANNER_SIMPLE_PATTERN.search(content)

    if not end_match:
        return violations  # Missing END banner caught by other rule

    end_agent = end_match.group(1).upper()

    if end_agent != executing_agent:
        # Find line number
        line_num = len(lines)
        for i, line in enumerate(lines, 1):
            if "END" in line and end_agent.lower() in line.lower():
                line_num = i
                break

        violations.append(LintViolation(
            file=file_path,
            line=line_num,
            severity=ViolationSeverity.ERROR,
            rule="pac-end-banner-agent-match",
            message=f"END banner agent '{end_agent}' does not match EXECUTING AGENT '{executing_agent}'",
        ))

    return violations


def lint_end_banner_gid_match(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-end-banner-gid-match
    END banner GID must match agent's canonical GID.
    """
    violations = []
    lines = content.split("\n")

    # Find END banner with GID
    end_match = END_BANNER_PATTERN.search(content)
    if not end_match:
        end_match = END_BANNER_SIMPLE_PATTERN.search(content)

    if not end_match or not end_match.group(2):
        return violations  # No GID in END banner or no banner

    end_agent = end_match.group(1).upper()
    end_gid = end_match.group(2).upper()

    # Get canonical GID for agent
    agent = get_agent_by_name(end_agent)
    if agent is None:
        return violations  # Unknown agent caught by other rule

    if agent.gid != end_gid:
        # Find line number
        line_num = len(lines)
        for i, line in enumerate(lines, 1):
            if "END" in line and end_agent.lower() in line.lower():
                line_num = i
                break

        violations.append(LintViolation(
            file=file_path,
            line=line_num,
            severity=ViolationSeverity.ERROR,
            rule="pac-end-banner-gid-match",
            message=f"END banner GID '{end_gid}' does not match canonical GID '{agent.gid}' for {end_agent}",
        ))

    return violations


def lint_end_banner_color_match(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-end-banner-color-match
    END banner emoji/color must match agent's canonical color.
    """
    violations = []
    lines = content.split("\n")

    # Find END banner with color info
    end_match = END_BANNER_PATTERN.search(content)
    if not end_match:
        return violations  # No full END banner

    end_agent = end_match.group(1).upper()
    end_emoji = end_match.group(3)  # May be None
    end_color = end_match.group(4).strip().upper() if end_match.group(4) else None

    # Get canonical agent info
    agent = get_agent_by_name(end_agent)
    if agent is None:
        return violations  # Unknown agent caught by other rule

    # Validate emoji matches agent
    if end_emoji and end_emoji != agent.emoji:
        # Find line number
        line_num = len(lines)
        for i, line in enumerate(lines, 1):
            if "END" in line and end_agent.lower() in line.lower():
                line_num = i
                break

        violations.append(LintViolation(
            file=file_path,
            line=line_num,
            severity=ViolationSeverity.ERROR,
            rule="pac-end-banner-color-match",
            message=f"END banner emoji '{end_emoji}' does not match canonical emoji '{agent.emoji}' for {end_agent}",
        ))

    # Validate color matches agent's canonical color
    if end_color and end_color != agent.color.upper():
        # Handle "DARK RED" vs "DARK_RED" normalization
        normalized_end_color = end_color.replace(" ", "_")
        normalized_canonical = agent.color.upper().replace(" ", "_")

        if normalized_end_color != normalized_canonical:
            # Find line number
            line_num = len(lines)
            for i, line in enumerate(lines, 1):
                if "END" in line and end_agent.lower() in line.lower():
                    line_num = i
                    break

            violations.append(LintViolation(
                file=file_path,
                line=line_num,
                severity=ViolationSeverity.ERROR,
                rule="pac-end-banner-color-match",
                message=f"END banner color '{end_color}' does not match canonical color '{agent.color}' for {end_agent}",
            ))

    return violations


# ═══════════════════════════════════════════════════════════════════════════════
# GOLD STANDARD CHECKLIST ENFORCEMENT — PAC-BENSON-P74-GOLD-STANDARD-CHECKLIST-01
# ═══════════════════════════════════════════════════════════════════════════════

# Canonical Gold Standard Checklist items (13 items, immutable)
# PAC-BENSON-P74: These are the exact items required for POSITIVE_CLOSURE
GOLD_STANDARD_CHECKLIST_ITEMS = [
    "Canonical PAC template used",
    "All gateways (G0–G7) executed in order",
    "Execution lane explicitly declared",
    "Agent activation acknowledged (PAG-01)",
    "Runtime activation acknowledged",
    "Constraints & guardrails declared",
    "Tasks scoped and non-expansive",
    "File scope explicitly bounded",
    "Fail-closed posture enforced",
    "WRAP requirement declared",
    "BER requirement declared (if applicable)",
    "Human review gate declared (if applicable)",
    "Ledger mutation explicitly attested",
]

GOLD_STANDARD_CHECKLIST_COUNT = 13  # Canonical count, immutable

# Pattern for GOLD_STANDARD_CHECKLIST header
GOLD_STANDARD_CHECKLIST_HEADER_PATTERN = re.compile(
    r"(?:GOLD[_\s-]?STANDARD[_\s-]?CHECKLIST|Gold\s+Standard\s+Checklist)",
    re.IGNORECASE
)

# Pattern for CHECKLIST_STATUS: PASS (13/13)
CHECKLIST_STATUS_PATTERN = re.compile(
    r"CHECKLIST[_\s-]?STATUS\s*:\s*(?:PASS|✅)\s*\(?\s*(\d+)\s*/\s*(\d+)\s*\)?",
    re.IGNORECASE
)

# Pattern for checked checkbox items [✓] or [x] or [X]
CHECKLIST_ITEM_CHECKED_PATTERN = re.compile(
    r"^\s*\[(?:✓|x|X|✅)\]\s*(.+)$",
    re.MULTILINE
)

# Pattern for any checkbox item (checked or unchecked)
CHECKLIST_ITEM_ANY_PATTERN = re.compile(
    r"^\s*\[(?:✓|x|X|✅|\s|✗|❌)?\]\s*(.+)$",
    re.MULTILINE
)


def lint_gold_standard_checklist_present(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-gold-standard-checklist-present
    All PACs MUST have a Gold Standard Checklist section.

    PAC-BENSON-P74: The checklist is a mandatory terminal artifact.
    No PAC can achieve POSITIVE_CLOSURE without it.
    """
    violations = []

    # Check if this looks like a PAC file
    if "PAC-" not in content.upper():
        return violations

    # Check for Gold Standard Checklist header
    has_checklist_header = GOLD_STANDARD_CHECKLIST_HEADER_PATTERN.search(content) is not None

    if not has_checklist_header:
        # Find appropriate line number (end of file or near POSITIVE_CLOSURE)
        lines = content.split("\n")
        line_num = len(lines)

        for i, line in enumerate(lines, 1):
            if "POSITIVE_CLOSURE" in line.upper() or "END" in line.upper():
                line_num = i
                break

        violations.append(LintViolation(
            file=file_path,
            line=line_num,
            severity=ViolationSeverity.ERROR,
            rule="pac-gold-standard-checklist-present",
            message="PAC missing GOLD_STANDARD_CHECKLIST section. Required for POSITIVE_CLOSURE.",
        ))

    return violations


def lint_gold_standard_checklist_status(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-gold-standard-checklist-status
    Checklist must have CHECKLIST_STATUS: PASS (13/13) for POSITIVE_CLOSURE.

    PAC-BENSON-P74: PASS (13/13) is the ONLY valid closure state.
    """
    violations = []

    # Check if this looks like a PAC file
    if "PAC-" not in content.upper():
        return violations

    # If no checklist header, skip (caught by other rule)
    if not GOLD_STANDARD_CHECKLIST_HEADER_PATTERN.search(content):
        return violations

    lines = content.split("\n")

    # Look for CHECKLIST_STATUS
    status_match = CHECKLIST_STATUS_PATTERN.search(content)

    if not status_match:
        # Find checklist section line
        line_num = len(lines)
        for i, line in enumerate(lines, 1):
            if GOLD_STANDARD_CHECKLIST_HEADER_PATTERN.search(line):
                line_num = i
                break

        violations.append(LintViolation(
            file=file_path,
            line=line_num,
            severity=ViolationSeverity.ERROR,
            rule="pac-gold-standard-checklist-status",
            message="GOLD_STANDARD_CHECKLIST missing CHECKLIST_STATUS. Required: PASS (13/13).",
        ))
        return violations

    # Validate pass count
    passed_count = int(status_match.group(1))
    total_count = int(status_match.group(2))

    # Find line number of status
    line_num = len(lines)
    for i, line in enumerate(lines, 1):
        if CHECKLIST_STATUS_PATTERN.search(line):
            line_num = i
            break

    # Must be 13/13
    if total_count != GOLD_STANDARD_CHECKLIST_COUNT:
        violations.append(LintViolation(
            file=file_path,
            line=line_num,
            severity=ViolationSeverity.ERROR,
            rule="pac-gold-standard-checklist-status",
            message=f"CHECKLIST_STATUS has {total_count} total items, expected {GOLD_STANDARD_CHECKLIST_COUNT}.",
        ))

    if passed_count != GOLD_STANDARD_CHECKLIST_COUNT:
        violations.append(LintViolation(
            file=file_path,
            line=line_num,
            severity=ViolationSeverity.ERROR,
            rule="pac-gold-standard-checklist-status",
            message=f"CHECKLIST_STATUS shows {passed_count}/{total_count}. PASS ({GOLD_STANDARD_CHECKLIST_COUNT}/{GOLD_STANDARD_CHECKLIST_COUNT}) required for POSITIVE_CLOSURE.",
        ))

    return violations


def lint_gold_standard_checklist_items(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-gold-standard-checklist-items
    All 13 canonical checklist items must be present and checked.

    PAC-BENSON-P74: Checklist items are immutable learning substrate.
    """
    violations = []

    # Check if this looks like a PAC file
    if "PAC-" not in content.upper():
        return violations

    # If no checklist header, skip (caught by other rule)
    if not GOLD_STANDARD_CHECKLIST_HEADER_PATTERN.search(content):
        return violations

    lines = content.split("\n")

    # Find checklist section
    checklist_start = -1
    checklist_end = -1

    for i, line in enumerate(lines):
        if GOLD_STANDARD_CHECKLIST_HEADER_PATTERN.search(line):
            checklist_start = i
        elif checklist_start >= 0 and ("═" in line or "CHECKLIST_STATUS" in line.upper()):
            checklist_end = i
            break

    if checklist_start < 0:
        return violations

    if checklist_end < 0:
        checklist_end = len(lines)

    # Extract checklist section
    checklist_section = "\n".join(lines[checklist_start:checklist_end])

    # Find all checked items
    checked_items = CHECKLIST_ITEM_CHECKED_PATTERN.findall(checklist_section)
    checked_items_normalized = [item.strip().lower() for item in checked_items]

    # Verify all canonical items are present and checked
    for canonical_item in GOLD_STANDARD_CHECKLIST_ITEMS:
        item_normalized = canonical_item.lower()

        # Check if this canonical item is present (with some flexibility)
        item_found = False
        for checked in checked_items_normalized:
            # Allow some variation in wording
            if (item_normalized in checked or
                checked in item_normalized or
                _checklist_item_matches(canonical_item, checked)):
                item_found = True
                break

        if not item_found:
            violations.append(LintViolation(
                file=file_path,
                line=checklist_start + 1,
                severity=ViolationSeverity.ERROR,
                rule="pac-gold-standard-checklist-items",
                message=f"Missing or unchecked checklist item: '{canonical_item}'",
            ))

    return violations


def _checklist_item_matches(canonical: str, actual: str) -> bool:
    """
    Check if actual checklist item matches canonical item.
    Allows for minor wording variations while enforcing key concepts.
    """
    canonical_lower = canonical.lower()
    actual_lower = actual.lower()

    # Key phrase matching for each canonical item
    key_phrases = {
        "canonical pac template used": ["canonical", "pac", "template"],
        "all gateways (g0–g7) executed in order": ["gateway", "g0", "g7", "order"],
        "execution lane explicitly declared": ["execution", "lane", "declared"],
        "agent activation acknowledged (pag-01)": ["agent", "activation", "pag-01"],
        "runtime activation acknowledged": ["runtime", "activation"],
        "constraints & guardrails declared": ["constraint", "guardrail"],
        "tasks scoped and non-expansive": ["task", "scope", "non-expansive"],
        "file scope explicitly bounded": ["file", "scope", "bound"],
        "fail-closed posture enforced": ["fail", "closed"],
        "wrap requirement declared": ["wrap", "requirement", "declared"],
        "ber requirement declared (if applicable)": ["ber", "requirement"],
        "human review gate declared (if applicable)": ["human", "review", "gate"],
        "ledger mutation explicitly attested": ["ledger", "mutation", "attest"],
    }

    if canonical_lower in key_phrases:
        required_phrases = key_phrases[canonical_lower]
        matches = sum(1 for phrase in required_phrases if phrase in actual_lower)
        # Require at least 2/3 of key phrases to match
        return matches >= (len(required_phrases) * 2 // 3)

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVATION BLOCK ENFORCEMENT — PAC-BENSON-ACTIVATION-BLOCK-IMPLEMENTATION-01
# ═══════════════════════════════════════════════════════════════════════════════

# Pattern for Activation Block marker
ACTIVATION_BLOCK_PATTERN = re.compile(
    r"I\.\s*EXECUTING\s+AGENT\s*\(MANDATORY\)|ACTIVATION\s+BLOCK|IDENTITY\s+BINDING",
    re.IGNORECASE
)

# Pattern for prohibited actions section
PROHIBITED_SECTION_PATTERN = re.compile(
    r"(?:PROHIBITED|FORBIDDEN|NOT\s+ALLOWED|MUST\s+NOT|❌\s*)",
    re.IGNORECASE
)

# Pattern for persona binding statement
PERSONA_BINDING_CHECK_PATTERN = re.compile(
    r"(?:I\s+am\s+\w+|This\s+is\s+\w+|Operating\s+as|Executing\s+as|PERSONA|BINDING)",
    re.IGNORECASE
)


def lint_activation_block_present(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-activation-block-present
    All PACs MUST have an Activation Block with EXECUTING AGENT.

    Required elements:
    - EXECUTING AGENT header with (MANDATORY) marker
    - Agent name
    - GID
    - Color/lane
    """
    violations = []

    # Check if this looks like a PAC file
    pac_indicators = [
        "PAC-",
        "════════",
        "OBJECTIVE",
        "SCOPE",
    ]

    is_pac = any(ind in content for ind in pac_indicators)

    if not is_pac:
        return violations  # Not a PAC file

    # Check for EXECUTING AGENT
    agent_match = EXECUTING_AGENT_PATTERN.search(content)
    if not agent_match:
        violations.append(LintViolation(
            file=file_path,
            line=1,
            severity=ViolationSeverity.ERROR,
            rule="pac-activation-block-present",
            message="PAC is missing EXECUTING AGENT. No execution without identity.",
        ))
        return violations

    # Check for GID
    gid_match = GID_REFERENCE_PATTERN.search(content)
    if not gid_match:
        violations.append(LintViolation(
            file=file_path,
            line=1,
            severity=ViolationSeverity.ERROR,
            rule="pac-activation-block-present",
            message="PAC is missing GID. Identity incomplete.",
        ))

    # Check for EXECUTING COLOR
    color_pattern = re.compile(r"EXECUTING\s+COLOR", re.IGNORECASE)
    if not color_pattern.search(content):
        violations.append(LintViolation(
            file=file_path,
            line=1,
            severity=ViolationSeverity.ERROR,
            rule="pac-activation-block-present",
            message="PAC is missing EXECUTING COLOR. Lane assignment required.",
        ))

    return violations


def lint_activation_block_prohibited_actions(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-activation-block-prohibited
    PACs SHOULD declare prohibited actions for the executing agent.

    This catches identity drift and unauthorized behavior.
    """
    violations = []

    # Check if this looks like a PAC file with Activation Block
    if "EXECUTING AGENT" not in content.upper():
        return violations

    # Check for prohibited actions section
    has_prohibited = PROHIBITED_SECTION_PATTERN.search(content)

    if not has_prohibited:
        lines = content.split("\n")
        line_num = 1
        for i, line in enumerate(lines, 1):
            if "EXECUTING AGENT" in line.upper():
                line_num = i
                break

        violations.append(LintViolation(
            file=file_path,
            line=line_num,
            severity=ViolationSeverity.WARNING,
            rule="pac-activation-block-prohibited",
            message="PAC should declare prohibited actions for executing agent",
        ))

    return violations


def lint_activation_block_no_proxy(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-activation-block-no-proxy
    PACs MUST NOT use proxy execution or "acting as" patterns.

    FORBIDDEN:
    - "Acting as X"
    - "On behalf of X"
    - "Proxy for X"
    - "Impersonating X"
    """
    violations = []

    # Proxy patterns that are FORBIDDEN
    proxy_patterns = [
        r"acting\s+as\s+\w+",
        r"on\s+behalf\s+of\s+\w+",
        r"proxy\s+(?:for|execution)",
        r"impersonating\s+\w+",
        r"pretending\s+to\s+be",
        r"assuming\s+identity",
    ]

    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        for pattern in proxy_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append(LintViolation(
                    file=file_path,
                    line=i,
                    severity=ViolationSeverity.ERROR,
                    rule="pac-activation-block-no-proxy",
                    message="FORBIDDEN: Proxy execution detected. No 'acting as' or delegation allowed.",
                ))
                break  # Only one violation per line

    return violations


def lint_activation_block_identity_consistency(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-activation-block-identity-consistent
    Activation Block identity (agent/GID/color) must be internally consistent.

    All references to the executing agent must match the declared identity.
    """
    violations = []

    # Extract declared identity
    agent_match = EXECUTING_AGENT_PATTERN.search(content)
    if not agent_match:
        return violations

    declared_agent = agent_match.group(1).upper()
    agent = get_agent_by_name(declared_agent)

    if agent is None:
        return violations  # Caught by other rules

    # Check all GID references in the file match the declared agent
    lines = content.split("\n")
    gid_references = list(GID_REFERENCE_PATTERN.finditer(content))

    for gid_match in gid_references:
        gid = gid_match.group(1).upper()
        # Find which line this is on
        pos = gid_match.start()
        line_num = content[:pos].count("\n") + 1
        line = lines[line_num - 1] if line_num <= len(lines) else ""

        # Check if this GID is in context with the agent name
        if declared_agent.lower() in line.lower():
            if gid != agent.gid:
                violations.append(LintViolation(
                    file=file_path,
                    line=line_num,
                    severity=ViolationSeverity.ERROR,
                    rule="pac-activation-block-identity-consistent",
                    message=f"Identity inconsistency: {declared_agent} referenced with {gid}, expected {agent.gid}",
                ))

    return violations


def lint_activation_block_registry_validation(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-activation-block-registry-valid
    Activation Block must validate against canonical agent registry.

    HARD FAIL enforcement:
    - Agent must exist in registry
    - GID must match canonical
    - Color must match canonical
    - Emoji must match canonical
    - Role must match (partial match allowed)

    PAC Reference: PAC-DAN-ACTIVATION-GATE-ENFORCEMENT-01
    """
    violations = []

    # Check if this looks like a PAC file
    if "EXECUTING AGENT" not in content.upper():
        return violations

    # Import here to avoid circular imports
    try:
        from core.governance.activation_block import (
            check_activation_block_presence,
            validate_activation_block_fields,
        )
    except ImportError:
        return violations  # Module not available

    # Step 1: Check presence
    has_block, missing = check_activation_block_presence(content)
    if not has_block:
        for element in missing:
            violations.append(LintViolation(
                file=file_path,
                line=1,
                severity=ViolationSeverity.ERROR,
                rule="pac-activation-block-registry-valid",
                message=f"Activation Block missing: {element}",
            ))
        return violations

    # Step 2: Validate fields against registry
    is_valid, errors = validate_activation_block_fields(content)
    if not is_valid:
        for error in errors:
            violations.append(LintViolation(
                file=file_path,
                line=1,
                severity=ViolationSeverity.ERROR,
                rule="pac-activation-block-registry-valid",
                message=f"Registry validation failed: {error}",
            ))

    return violations


def lint_activation_block_lane_match(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-activation-block-lane-match
    LANE declaration (if present) must match the agent's color lane.

    Color → Lane mapping is canonical and immutable.
    """
    violations = []

    # Check if this looks like a PAC file
    if "EXECUTING AGENT" not in content.upper():
        return violations

    # Look for LANE declaration (LANE: VALUE or LANE — VALUE)
    # Case-sensitive to avoid matching docstrings like "lane: description"
    lane_pattern = re.compile(r"(?<!\w)LANE\s*[:\-—]\s*([^\n/]+)")
    lane_match = lane_pattern.search(content)

    if not lane_match:
        return violations  # No lane declared, skip

    declared_lane = lane_match.group(1).strip()

    # Get executing agent
    agent_match = EXECUTING_AGENT_PATTERN.search(content)
    if not agent_match:
        return violations

    declared_agent = agent_match.group(1).upper()
    agent = get_agent_by_name(declared_agent)

    if agent is None:
        return violations  # Caught by other rules

    # Get expected lane for agent's color
    from core.governance.agent_roster import get_lane_for_color
    expected_lane = get_lane_for_color(agent.color)

    if expected_lane:
        # Normalize for comparison
        declared_normalized = declared_lane.upper().replace(" ", "_").replace("-", "_")
        expected_normalized = expected_lane.upper().replace(" ", "_").replace("-", "_")

        # Also allow color name as lane (e.g., "GREEN" for DevOps lane)
        color_normalized = agent.color.upper().replace(" ", "_")

        if declared_normalized != expected_normalized and declared_normalized != color_normalized:
            # Find line number
            lines = content.split("\n")
            line_num = 1
            for i, line in enumerate(lines, 1):
                if "LANE" in line.upper() and declared_lane.upper() in line.upper():
                    line_num = i
                    break

            violations.append(LintViolation(
                file=file_path,
                line=line_num,
                severity=ViolationSeverity.ERROR,
                rule="pac-activation-block-lane-match",
                message=f"Lane '{declared_lane}' does not match agent {declared_agent}'s color lane '{expected_lane}'",
            ))

    return violations


def lint_agent_level_valid(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-agent-level-valid
    EXECUTING AGENT must have a valid agent_level (L0-L3) in registry.
    """
    violations = []
    lines = content.split("\n")

    # Check if this looks like a PAC file
    if "PAC-" not in content and "EXECUTING AGENT" not in content:
        return violations

    agent_match = EXECUTING_AGENT_PATTERN.search(content)
    if not agent_match:
        return violations

    agent_name = agent_match.group(1).upper()

    # Get agent level from registry
    level = get_agent_level(agent_name)

    if level is None:
        # Agent not in registry - caught by other rules
        return violations

    if level not in VALID_AGENT_LEVELS:
        # Find line number
        line_num = 1
        for i, line in enumerate(lines, 1):
            if "EXECUTING AGENT" in line.upper():
                line_num = i
                break

        violations.append(LintViolation(
            file=file_path,
            line=line_num,
            severity=ViolationSeverity.ERROR,
            rule="pac-agent-level-valid",
            message=f"Agent {agent_name} has invalid level '{level}' (expected L0-L3)",
        ))

    return violations


def lint_deprecated_agent(content: str, file_path: Path) -> List[LintViolation]:
    """
    RULE: pac-deprecated-agent
    PACs cannot reference unknown or deprecated agents.
    """
    violations = []
    lines = content.split("\n")

    # Check if this looks like a PAC file
    if "PAC-" not in content and "EXECUTING AGENT" not in content:
        return violations

    agent_match = EXECUTING_AGENT_PATTERN.search(content)
    if not agent_match:
        return violations

    agent_name = agent_match.group(1).upper()

    if is_deprecated_agent(agent_name):
        # Find line number
        line_num = 1
        for i, line in enumerate(lines, 1):
            if "EXECUTING AGENT" in line.upper():
                line_num = i
                break

        violations.append(LintViolation(
            file=file_path,
            line=line_num,
            severity=ViolationSeverity.ERROR,
            rule="pac-deprecated-agent",
            message=f"Agent '{agent_name}' is unknown or deprecated - not in registry",
        ))

    return violations


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN LINTER
# ═══════════════════════════════════════════════════════════════════════════════


ALL_LINT_RULES = [
    # Original roster rules
    lint_emoji_border_consistency,
    lint_gid_validity,
    lint_agent_gid_match,
    lint_agent_emoji_match,
    lint_pac_header_footer_match,
    lint_no_duplicate_gid_assignment,
    # Color Gateway Enforcement (PAC-BENSON-COLOR-GATEWAY-ENFORCEMENT-CODE-01)
    lint_pac_has_required_fields,
    lint_agent_color_consistency,
    lint_teal_reserved,
    lint_emoji_color_match,
    # END Banner Enforcement (PAC-BENSON-CODY-END-BANNER-LINT-ENFORCEMENT-01)
    lint_end_banner_present,
    lint_end_banner_agent_match,
    lint_end_banner_gid_match,
    lint_end_banner_color_match,
    # Gold Standard Checklist Enforcement (PAC-BENSON-P74-GOLD-STANDARD-CHECKLIST-01)
    lint_gold_standard_checklist_present,
    lint_gold_standard_checklist_status,
    lint_gold_standard_checklist_items,
    # Activation Block Enforcement (PAC-BENSON-ACTIVATION-BLOCK-IMPLEMENTATION-01)
    lint_activation_block_present,
    lint_activation_block_prohibited_actions,
    lint_activation_block_no_proxy,
    lint_activation_block_identity_consistency,
    # Activation Gate Enforcement (PAC-DAN-ACTIVATION-GATE-ENFORCEMENT-01)
    lint_activation_block_registry_validation,
    lint_activation_block_lane_match,
    # Agent Level Enforcement (PAC-ATLAS-AGENT-REGISTRY-ENFORCEMENT-01)
    lint_agent_level_valid,
    lint_deprecated_agent,
]


def lint_file(file_path: Path) -> List[LintViolation]:
    """Run all lint rules on a single file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return [LintViolation(
            file=file_path,
            line=0,
            severity=ViolationSeverity.ERROR,
            rule="file-read-error",
            message=str(e),
        )]

    violations = []
    for rule in ALL_LINT_RULES:
        violations.extend(rule(content, file_path))

    return violations


def find_pac_files(root: Path, exclude_tests: bool = False, pac_only: bool = False) -> List[Path]:
    """Find all files that might contain PAC headers.

    Args:
        root: Root directory to search
        exclude_tests: If True, exclude test files with intentional violations
        pac_only: If True, only search canonical PAC paths (docs/governance/pacs/*.md)
                  PAC-BENSON-P73: This is the recommended mode for CI/pre-commit.
    """
    pac_files = []

    # P73: Canonical PAC paths only mode - restrict to markdown PAC files
    if pac_only:
        # Search only canonical PAC directories
        pac_dirs = [
            root / "docs" / "governance" / "pacs",
            root / "ChainBridge" / "docs" / "governance" / "pacs",
        ]
        for pac_dir in pac_dirs:
            if pac_dir.exists():
                for md_file in pac_dir.glob("PAC-*.md"):
                    pac_files.append(md_file)
        return pac_files

    # Patterns that indicate PAC content
    pac_indicators = [
        "PAC-",
        "GID-",
        "🔵🔵🔵",
        "⚪⚪⚪",
        "🟦🟦🟦",
        "🟨🟨🟨",
        "🟣🟣🟣",
        "🟧🟧🟧",
        "🟥🟥🟥",
        "🟩🟩🟩",
        "🩷🩷🩷",
    ]

    # Files that intentionally contain invalid data for testing
    test_exclusions = {
        "test_agent_roster_linter.py",
        "test_pac_structural_validator.py",
        "test_forbidden_regions.py",
        "test_gameday_diggi_forbidden_verb.py",
        "test_gameday_forged_gid.py",
        "test_gameday_governance_drift.py",
        "test_decision_envelope.py",
        "test_acm_evaluator.py",
        "test_acm_loader.py",
        "test_alex_middleware.py",
        "test_diggi_corrections.py",
        "test_diggi_envelope_handler.py",
        "test_drcp.py",
        "test_intent_schema.py",
        # P73: Additional test file exclusions for governance tests
        "test_negative_paths.py",
        "test_execution_result_contract.py",
        "test_execution_telemetry.py",
        "test_orchestrator_discipline.py",
    }

    # P73: Directories to exclude from Python file scanning
    excluded_dirs = {
        "__pycache__", "venv", ".venv", "node_modules", "build", "dist",
        ".git", ".tox", ".pytest_cache", ".mypy_cache", "htmlcov",
    }

    for py_file in root.rglob("*.py"):
        # Skip venv, cache, etc.
        if any(part.startswith(".") or part in excluded_dirs
               for part in py_file.parts):
            continue

        # Skip test files with intentional violations
        if exclude_tests and py_file.name in test_exclusions:
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            if any(indicator in content for indicator in pac_indicators):
                pac_files.append(py_file)
        except Exception:
            continue

    return pac_files


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PAC Linter - Validate agent roster compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/pac_linter.py                    # Lint all PAC files
  python tools/pac_linter.py path/to/file.py   # Lint specific file
  python tools/pac_linter.py --check           # CI mode (exit 1 on failure)
  python tools/pac_linter.py --pac-only        # Only lint canonical PAC markdown files
  python tools/pac_linter.py --roster          # Print canonical roster
        """
    )
    parser.add_argument("files", nargs="*", help="Specific files to lint")
    parser.add_argument("--check", action="store_true", help="CI mode: exit 1 on any error")
    parser.add_argument("--roster", action="store_true", help="Print canonical agent roster")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--include-tests", action="store_true", help="Include test files with intentional violations")
    parser.add_argument("--pac-only", action="store_true",
                        help="P73: Only lint canonical PAC markdown files in docs/governance/pacs/")

    args = parser.parse_args()

    if args.roster:
        print("=" * 60)
        print("CHAINBRIDGE AGENT ROSTER — CANONICAL")
        print("=" * 60)
        for agent in sorted(CANONICAL_AGENTS.values(), key=lambda a: int(a.gid.split("-")[1])):
            aliases = f" (aliases: {', '.join(agent.aliases)})" if agent.aliases else ""
            print(f"{agent.emoji} {agent.name:10} {agent.gid}  {agent.role}{aliases}")
        print("=" * 60)
        print(f"Total agents: {len(CANONICAL_AGENTS)}")
        return 0

    # Determine files to lint
    root = Path(__file__).parent.parent

    # P73: Define canonical PAC path pattern
    PAC_PATH_PATTERN = re.compile(r"docs/governance/pacs/PAC-.*\.md$")

    if args.files:
        files = [Path(f) for f in args.files]
        # P73: When --pac-only is set, filter out non-PAC files even when explicitly passed
        if args.pac_only:
            original_count = len(files)
            files = [f for f in files if PAC_PATH_PATTERN.search(str(f))]
            if args.verbose and original_count != len(files):
                print(f"P73: Filtered {original_count - len(files)} non-PAC files (--pac-only mode)")
    else:
        files = find_pac_files(root, exclude_tests=not args.include_tests, pac_only=args.pac_only)

    if args.verbose:
        print(f"Linting {len(files)} files...")

    # Run linter
    all_violations: List[LintViolation] = []

    for file_path in files:
        violations = lint_file(file_path)
        all_violations.extend(violations)

    # Report results
    errors = [v for v in all_violations if v.severity == ViolationSeverity.ERROR]
    warnings = [v for v in all_violations if v.severity == ViolationSeverity.WARNING]

    if all_violations:
        print("\n🔴 PAC LINT VIOLATIONS")
        print("=" * 60)

        for v in sorted(all_violations, key=lambda x: (str(x.file), x.line)):
            severity_icon = "❌" if v.severity == ViolationSeverity.ERROR else "⚠️"
            print(f"{severity_icon} {v}")

        print("=" * 60)
        print(f"Errors: {len(errors)} | Warnings: {len(warnings)}")
    else:
        print("✅ PAC lint passed - no violations found")

    if args.check and errors:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
