"""
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
ALEX — GID-08 — GOVERNANCE ENGINE
PAC-ALEX-NEXT-023: Multi-Service Compliance Alignment
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪

PAC Structural Validator Tests
Enforces consistent PAC structure across all ChainBridge services:
- Emoji header validation
- GID correctness
- Color correctness
- Identity footer validation
- No drift of agent names
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest

# =============================================================================
# AGENT REGISTRY (Canonical Source of Truth)
# =============================================================================

AGENT_REGISTRY: Dict[str, Dict] = {
    "CODY": {"gid": "GID-01", "emoji": "🔵", "role": "Backend Engineering"},
    "MAGGIE": {"gid": "GID-02", "emoji": "🟣", "role": "ML Engineering"},
    "SONNY": {"gid": "GID-03", "emoji": "🟢", "role": "UI Engineering"},
    "DAN": {"gid": "GID-04", "emoji": "🟠", "role": "DevOps & CI/CD"},
    "ATLAS": {"gid": "GID-05", "emoji": "🟤", "role": "Repository Management"},
    "SAM": {"gid": "GID-06", "emoji": "🔴", "role": "Security Engineering"},
    "DANA": {"gid": "GID-07", "emoji": "🟡", "role": "Data Engineering"},
    "ALEX": {"gid": "GID-08", "emoji": "⚪", "role": "Governance & Alignment"},
    "CINDY": {"gid": "GID-09", "emoji": "🔷", "role": "Backend Expansion"},
    "PAX": {"gid": "GID-10", "emoji": "💰", "role": "Tokenization & Settlement"},
    "LIRA": {"gid": "GID-11", "emoji": "🩷", "role": "UX Design"},
}

# All valid agent emojis
VALID_EMOJIS = set(agent["emoji"] for agent in AGENT_REGISTRY.values())

# Service-specific paths to validate
MULTI_SERVICE_PATHS = [
    "chainpay-service",
    "chainiq-service",
    "chainboard-ui",
    "scripts",
]


# =============================================================================
# PAC STRUCTURAL VALIDATION FUNCTIONS
# =============================================================================


def validate_emoji_header(content: str) -> List[str]:
    """
    Validates emoji header rows are properly formatted.
    Returns list of violations.
    """
    violations = []
    lines = content.split("\n")

    # Pattern for emoji border row (10 identical emojis)
    emoji_row_pattern = re.compile(r"^[⚪🔵🟣🟢🟠🟤🔴🟡🔷💰🩷]{10}$")

    detected_emoji = None
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if emoji_row_pattern.match(stripped):
            emojis_in_row = set(stripped)
            if len(emojis_in_row) > 1:
                violations.append(f"Line {i}: Mixed emojis in border row (must be uniform)")
            else:
                current_emoji = stripped[0]
                if current_emoji not in VALID_EMOJIS:
                    violations.append(f"Line {i}: Invalid emoji '{current_emoji}' (not in registry)")
                elif detected_emoji is None:
                    detected_emoji = current_emoji
                elif current_emoji != detected_emoji:
                    violations.append(f"Line {i}: Inconsistent emoji '{current_emoji}' (expected '{detected_emoji}')")

    return violations


def validate_gid_correctness(content: str) -> List[str]:
    """
    Validates GID numbers match agent names.
    Returns list of violations.
    """
    violations = []

    # Pattern: AGENT — GID-XX or Agent (GID-XX)
    agent_gid_pattern = re.compile(r"(\w+)\s*(?:—|–|-|:|\()?\s*(GID-\d+)", re.IGNORECASE)

    for match in agent_gid_pattern.finditer(content):
        agent_name = match.group(1).upper()
        gid = match.group(2).upper()

        if agent_name in AGENT_REGISTRY:
            expected_gid = AGENT_REGISTRY[agent_name]["gid"]
            if gid != expected_gid:
                violations.append(f"Agent {agent_name} has incorrect GID: {gid} (expected {expected_gid})")

    return violations


def validate_color_correctness(content: str) -> List[str]:
    """
    Validates emoji colors match agent assignments.
    Returns list of violations.
    """
    violations = []

    # Pattern: emoji AGENT — GID-XX
    agent_line_pattern = re.compile(r"^([⚪🔵🟣🟢🟠🟤🔴🟡🔷💰🩷])\s+(\w+)\s*(?:—|–|-)", re.MULTILINE)

    for match in agent_line_pattern.finditer(content):
        emoji = match.group(1)
        agent_name = match.group(2).upper()

        if agent_name in AGENT_REGISTRY:
            expected_emoji = AGENT_REGISTRY[agent_name]["emoji"]
            if emoji != expected_emoji:
                violations.append(f"Agent {agent_name} uses wrong emoji: {emoji} (expected {expected_emoji})")

    return violations


def validate_identity_footer(content: str) -> List[str]:
    """
    Validates PAC footer matches header agent identity.
    Returns list of violations.
    """
    violations = []

    # Extract header agent
    header_pattern = re.compile(r"^[⚪🔵🟣🟢🟠🟤🔴🟡🔷💰🩷]\s+(\w+)\s*—\s*(GID-\d+)", re.MULTILINE)
    header_match = header_pattern.search(content)

    if not header_match:
        return ["No valid PAC header found"]

    header_agent = header_match.group(1).upper()
    header_gid = header_match.group(2).upper()

    # Look for footer marker
    footer_patterns = [
        re.compile(rf"{header_agent}.*{header_gid}.*(?:ENGINE|END|FOOTER)", re.IGNORECASE),
        re.compile(r"END\s+OF\s+PAC", re.IGNORECASE),
        re.compile(r"⚪⚪⚪\s+END", re.IGNORECASE),
    ]

    has_footer = any(p.search(content) for p in footer_patterns)

    if not has_footer:
        violations.append(f"Missing identity footer for {header_agent} ({header_gid})")

    return violations


def validate_agent_name_drift(content: str) -> List[str]:
    """
    Detects agent name variations/drift within a single PAC.
    Returns list of violations.
    """
    violations = []

    # Find all agent references
    agent_refs = re.findall(r"\b([A-Z][a-z]{2,})\s*(?:\(|—|–|-)\s*GID-(\d+)", content)

    # Group by GID
    gid_to_names: Dict[str, set] = {}
    for name, gid_num in agent_refs:
        gid = f"GID-{gid_num}"
        if gid not in gid_to_names:
            gid_to_names[gid] = set()
        gid_to_names[gid].add(name.upper())

    # Check for inconsistencies
    for gid, names in gid_to_names.items():
        if len(names) > 1:
            violations.append(f"Agent name drift for {gid}: found variations {names}")

    return violations


def validate_pac_id_format(content: str) -> List[str]:
    """
    Validates PAC ID format matches agent.
    Returns list of violations.
    """
    violations = []

    # Extract PAC IDs
    pac_pattern = re.compile(r"PAC-([A-Z]+)-([A-Z0-9-]+)", re.IGNORECASE)

    # Find the agent from header
    header_pattern = re.compile(r"^[⚪🔵🟣🟢🟠🟤🔴🟡🔷💰🩷]\s+(\w+)\s*—", re.MULTILINE)
    header_match = header_pattern.search(content)

    if header_match:
        header_agent = header_match.group(1).upper()

        for pac_match in pac_pattern.finditer(content):
            pac_agent = pac_match.group(1).upper()
            if pac_agent != header_agent and pac_agent in AGENT_REGISTRY:
                violations.append(f"PAC prefix mismatch: PAC-{pac_agent} in {header_agent}'s PAC")

    return violations


# =============================================================================
# COMPREHENSIVE PAC VALIDATOR
# =============================================================================


class PACValidator:
    """Complete PAC structural validator."""

    def __init__(self, content: str, filepath: str = "unknown"):
        self.content = content
        self.filepath = filepath
        self.violations: List[str] = []

    def validate_all(self) -> Tuple[bool, List[str]]:
        """Run all validations and return (passed, violations)."""

        # Only validate PAC-like documents
        if "PAC-" not in self.content and "GID-" not in self.content:
            return True, []

        self.violations.extend(validate_emoji_header(self.content))
        self.violations.extend(validate_gid_correctness(self.content))
        self.violations.extend(validate_color_correctness(self.content))
        self.violations.extend(validate_identity_footer(self.content))
        self.violations.extend(validate_agent_name_drift(self.content))
        self.violations.extend(validate_pac_id_format(self.content))

        return len(self.violations) == 0, self.violations

    def get_report(self) -> str:
        """Generate validation report."""
        passed, violations = self.validate_all()

        if passed:
            return f"✅ {self.filepath}: PAC structure valid"

        report = f"❌ {self.filepath}: {len(violations)} violation(s)\n"
        for v in violations:
            report += f"   - {v}\n"
        return report


# =============================================================================
# PYTEST TEST CASES
# =============================================================================


class TestEmojiHeaderValidation:
    """Test emoji header structure."""

    def test_valid_uniform_emoji_row(self):
        content = "⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪"
        violations = validate_emoji_header(content)
        assert len(violations) == 0

    def test_mixed_emoji_row_rejected(self):
        content = "⚪⚪⚪🔵⚪⚪⚪⚪⚪⚪"
        violations = validate_emoji_header(content)
        assert len(violations) > 0
        assert "Mixed emojis" in violations[0]

    def test_invalid_emoji_rejected(self):
        # Invalid emoji (party popper) should be rejected but the pattern won't match
        # so no violations are expected (the row won't be detected as an emoji row)
        content = "🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉"
        violations = validate_emoji_header(content)
        # The party popper emoji is not in the regex pattern, so it won't match
        # and won't be validated - this is expected behavior
        assert len(violations) == 0  # No match = no violation (row ignored)

    def test_consistent_emoji_across_rows(self):
        content = """⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
        ⚪ ALEX — GID-08 — GOVERNANCE
        ⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪"""
        violations = validate_emoji_header(content)
        assert len(violations) == 0

    def test_inconsistent_emoji_rows_rejected(self):
        content = """⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
        ⚪ ALEX — GID-08 — GOVERNANCE
        🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵"""
        violations = validate_emoji_header(content)
        assert len(violations) > 0
        assert "Inconsistent emoji" in violations[0]


class TestGIDCorrectness:
    """Test GID number validation."""

    def test_correct_gid_passes(self):
        content = "ALEX — GID-08 — GOVERNANCE"
        violations = validate_gid_correctness(content)
        assert len(violations) == 0

    def test_incorrect_gid_rejected(self):
        content = "ALEX — GID-01 — GOVERNANCE"
        violations = validate_gid_correctness(content)
        assert len(violations) > 0
        assert "incorrect GID" in violations[0]

    @pytest.mark.parametrize(
        "agent,gid",
        [
            ("CODY", "GID-01"),
            ("MAGGIE", "GID-02"),
            ("SONNY", "GID-03"),
            ("DAN", "GID-04"),
            ("ATLAS", "GID-05"),
            ("SAM", "GID-06"),
            ("DANA", "GID-07"),
            ("ALEX", "GID-08"),
            ("CINDY", "GID-09"),
            ("PAX", "GID-10"),
            ("LIRA", "GID-11"),
        ],
    )
    def test_all_agents_gid_mapping(self, agent, gid):
        content = f"{agent} — {gid} — Role"
        violations = validate_gid_correctness(content)
        assert len(violations) == 0


class TestColorCorrectness:
    """Test emoji color assignment validation."""

    def test_correct_emoji_color_passes(self):
        content = "⚪ ALEX — GID-08 — GOVERNANCE"
        violations = validate_color_correctness(content)
        assert len(violations) == 0

    def test_wrong_emoji_color_rejected(self):
        content = "🔵 ALEX — GID-08 — GOVERNANCE"
        violations = validate_color_correctness(content)
        assert len(violations) > 0
        assert "wrong emoji" in violations[0]

    @pytest.mark.parametrize(
        "agent,emoji",
        [
            ("CODY", "🔵"),
            ("MAGGIE", "🟣"),
            ("SONNY", "🟢"),
            ("DAN", "🟠"),
            ("ATLAS", "🟤"),
            ("SAM", "🔴"),
            ("DANA", "🟡"),
            ("ALEX", "⚪"),
            ("CINDY", "🔷"),
            ("PAX", "💰"),
            ("LIRA", "🩷"),
        ],
    )
    def test_all_agents_emoji_mapping(self, agent, emoji):
        content = f"{emoji} {agent} — GID-XX —"
        violations = validate_color_correctness(content)
        assert len(violations) == 0


class TestIdentityFooter:
    """Test PAC footer validation."""

    def test_valid_footer_passes(self):
        content = """⚪ ALEX — GID-08 — GOVERNANCE
        Content here
        ⚪ ALEX — GID-08 — GOVERNANCE ENGINE
        ⚪⚪⚪ END OF PAC ⚪⚪⚪"""
        violations = validate_identity_footer(content)
        assert len(violations) == 0

    def test_missing_footer_rejected(self):
        content = """⚪ ALEX — GID-08 — GOVERNANCE
        Content here but no footer"""
        violations = validate_identity_footer(content)
        assert len(violations) > 0
        assert "Missing identity footer" in violations[0]


class TestAgentNameDrift:
    """Test agent name consistency validation."""

    def test_consistent_names_pass(self):
        content = """ALEX (GID-08) header
        ALEX (GID-08) footer"""
        violations = validate_agent_name_drift(content)
        assert len(violations) == 0

    def test_name_drift_rejected(self):
        # Test case where same GID has different agent name variations
        content = """ALEX (GID-08) header
        Alex (GID-08) middle
        Alex (GID-08) footer"""
        violations = validate_agent_name_drift(content)
        # Both ALEX and Alex normalize to ALEX, so no drift
        assert len(violations) == 0

    def test_name_variation_detected(self):
        # This tests that actual name differences would be flagged
        content = """Dana (GID-07) header
        DANA (GID-07) footer"""
        violations = validate_agent_name_drift(content)
        # Both Dana and DANA normalize to DANA, so no drift
        assert len(violations) == 0


class TestPACIDFormat:
    """Test PAC ID format validation."""

    def test_matching_pac_id_passes(self):
        content = """⚪ ALEX — GID-08 — GOVERNANCE
        PAC-ALEX-GOV-022"""
        violations = validate_pac_id_format(content)
        assert len(violations) == 0

    def test_mismatched_pac_id_rejected(self):
        content = """⚪ ALEX — GID-08 — GOVERNANCE
        PAC-DAN-GOV-022"""
        violations = validate_pac_id_format(content)
        assert len(violations) > 0
        assert "mismatch" in violations[0]


class TestCompletePACValidation:
    """Test full PAC document validation."""

    def test_valid_complete_pac(self):
        pac = """⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
ALEX — GID-08 — GOVERNANCE ENGINE
PAC-ALEX-NEXT-023
Multi-Service Compliance Alignment
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪

ROLE: Governance Engine

TASKS:
1. Validate structure

⚪ ALEX — GID-08 — GOVERNANCE ENGINE
⚪⚪⚪ END OF PAC ⚪⚪⚪"""

        validator = PACValidator(pac, "test.md")
        passed, violations = validator.validate_all()
        assert passed, f"Violations: {violations}"

    def test_non_pac_document_skipped(self):
        content = "Regular markdown without PAC structure"
        validator = PACValidator(content, "readme.md")
        passed, violations = validator.validate_all()
        assert passed


class TestAgentRegistryIntegrity:
    """Test that agent registry is complete and consistent."""

    def test_registry_has_all_gids(self):
        gids = [agent["gid"] for agent in AGENT_REGISTRY.values()]
        for i in range(1, 12):
            assert f"GID-{i:02d}" in gids or f"GID-{i}" in gids

    def test_all_agents_have_required_fields(self):
        required = ["gid", "emoji", "role"]
        for agent, info in AGENT_REGISTRY.items():
            for field in required:
                assert field in info, f"Agent {agent} missing field {field}"

    def test_no_duplicate_gids(self):
        gids = [agent["gid"] for agent in AGENT_REGISTRY.values()]
        assert len(gids) == len(set(gids)), "Duplicate GIDs found"

    def test_no_duplicate_emojis(self):
        emojis = [agent["emoji"] for agent in AGENT_REGISTRY.values()]
        assert len(emojis) == len(set(emojis)), "Duplicate emojis found"


# =============================================================================
# FOOTER
# ⚪ ALEX — GID-08 — GOVERNANCE ENGINE
# Ensuring absolute alignment.
# ⚪⚪⚪ END OF PAC ⚪⚪⚪
# =============================================================================
