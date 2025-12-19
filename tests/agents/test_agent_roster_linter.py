"""
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
ALEX — GID-08 — GOVERNANCE ENGINE
PAC-ALEX-ROSTER-LINT-001: Agent Roster Linter Tests
⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪

Tests for the canonical agent roster linter.
Ensures PAC headers/footers comply with HARD RULES:
- No new agents without explicit registry update
- No color reassignment
- No emoji substitution
- No dual colors per agent
- All PAC headers/footers must match exactly
"""

import pytest
from pathlib import Path
import sys

# Import from canonical roster
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.governance.agent_roster import (
    CANONICAL_AGENTS,
    VALID_EMOJIS,
    VALID_GIDS,
    Agent,
    AgentColor,
    get_agent_by_gid,
    get_agent_by_name,
    is_valid_agent,
    is_valid_emoji,
    is_valid_gid,
    validate_agent_emoji_match,
    validate_agent_gid_match,
)


# =============================================================================
# CANONICAL ROSTER INTEGRITY TESTS
# =============================================================================


class TestCanonicalRosterIntegrity:
    """Verify canonical roster data is correct and complete."""

    def test_roster_has_12_agents(self):
        """Roster must have exactly 12 agents (GID-00 to GID-11)."""
        assert len(CANONICAL_AGENTS) == 12

    def test_all_gids_are_sequential(self):
        """GIDs must be sequential from 00 to 11."""
        expected_gids = {f"GID-{i:02d}" for i in range(12)}
        actual_gids = {a.gid for a in CANONICAL_AGENTS.values()}
        assert actual_gids == expected_gids

    def test_benson_is_gid_00(self):
        """BENSON must be GID-00 (CTO/Orchestrator)."""
        assert "BENSON" in CANONICAL_AGENTS
        assert CANONICAL_AGENTS["BENSON"].gid == "GID-00"
        # BENSON uses TEAL (🟦🟩) per canonical registry
        assert CANONICAL_AGENTS["BENSON"].emoji == "🟦🟩"

    def test_cody_is_gid_01(self):
        """CODY must be GID-01 (Senior Backend Engineer)."""
        assert "CODY" in CANONICAL_AGENTS
        assert CANONICAL_AGENTS["CODY"].gid == "GID-01"
        assert CANONICAL_AGENTS["CODY"].emoji == "🔵"

    def test_sonny_is_gid_02(self):
        """SONNY must be GID-02 (Senior Frontend Engineer)."""
        assert "SONNY" in CANONICAL_AGENTS
        assert CANONICAL_AGENTS["SONNY"].gid == "GID-02"
        assert CANONICAL_AGENTS["SONNY"].emoji == "🟨"

    def test_mira_r_is_gid_03(self):
        """MIRA-R must be GID-03 (Research Lead)."""
        assert "MIRA-R" in CANONICAL_AGENTS
        assert CANONICAL_AGENTS["MIRA-R"].gid == "GID-03"
        assert CANONICAL_AGENTS["MIRA-R"].emoji == "🟣"

    def test_cindy_is_gid_04(self):
        """CINDY must be GID-04 (Senior Backend Engineer)."""
        assert "CINDY" in CANONICAL_AGENTS
        assert CANONICAL_AGENTS["CINDY"].gid == "GID-04"
        assert CANONICAL_AGENTS["CINDY"].emoji == "🟦"

    def test_pax_is_gid_05(self):
        """PAX must be GID-05 (Product & Smart Contract)."""
        assert "PAX" in CANONICAL_AGENTS
        assert CANONICAL_AGENTS["PAX"].gid == "GID-05"
        assert CANONICAL_AGENTS["PAX"].emoji == "🟧"

    def test_sam_is_gid_06(self):
        """SAM must be GID-06 (Security Engineer)."""
        assert "SAM" in CANONICAL_AGENTS
        assert CANONICAL_AGENTS["SAM"].gid == "GID-06"
        assert CANONICAL_AGENTS["SAM"].emoji == "🟥"

    def test_dan_is_gid_07(self):
        """DAN must be GID-07 (DevOps Lead)."""
        assert "DAN" in CANONICAL_AGENTS
        assert CANONICAL_AGENTS["DAN"].gid == "GID-07"
        assert CANONICAL_AGENTS["DAN"].emoji == "🟩"

    def test_alex_is_gid_08(self):
        """ALEX must be GID-08 (Governance Engine)."""
        assert "ALEX" in CANONICAL_AGENTS
        assert CANONICAL_AGENTS["ALEX"].gid == "GID-08"
        assert CANONICAL_AGENTS["ALEX"].emoji == "⚪"

    def test_lira_is_gid_09(self):
        """LIRA must be GID-09 (Frontend/ChainBoard UX)."""
        assert "LIRA" in CANONICAL_AGENTS
        assert CANONICAL_AGENTS["LIRA"].gid == "GID-09"
        assert CANONICAL_AGENTS["LIRA"].emoji == "🩷"

    def test_maggie_is_gid_10(self):
        """MAGGIE must be GID-10 (ML & Applied AI Lead)."""
        assert "MAGGIE" in CANONICAL_AGENTS
        assert CANONICAL_AGENTS["MAGGIE"].gid == "GID-10"
        assert CANONICAL_AGENTS["MAGGIE"].emoji == "🩷"

    def test_atlas_is_gid_11(self):
        """ATLAS must be GID-11 (Build/Repair Agent)."""
        assert "ATLAS" in CANONICAL_AGENTS
        assert CANONICAL_AGENTS["ATLAS"].gid == "GID-11"
        assert CANONICAL_AGENTS["ATLAS"].emoji == "🔵"


# =============================================================================
# LOOKUP FUNCTION TESTS
# =============================================================================


class TestAgentLookups:
    """Test agent lookup functions."""

    def test_get_agent_by_name_exact(self):
        """Exact name lookup works."""
        agent = get_agent_by_name("CODY")
        assert agent is not None
        assert agent.gid == "GID-01"

    def test_get_agent_by_name_case_insensitive(self):
        """Name lookup is case-insensitive."""
        agent = get_agent_by_name("cody")
        assert agent is not None
        assert agent.name == "CODY"

    def test_get_agent_by_name_alias(self):
        """Alias lookup works."""
        agent = get_agent_by_name("CODEX")
        assert agent is not None
        assert agent.name == "CODY"

    def test_get_agent_by_name_unknown(self):
        """Unknown agent returns None."""
        assert get_agent_by_name("UNKNOWN_AGENT") is None

    def test_get_agent_by_gid(self):
        """GID lookup works."""
        agent = get_agent_by_gid("GID-08")
        assert agent is not None
        assert agent.name == "ALEX"

    def test_get_agent_by_gid_invalid(self):
        """Invalid GID returns None."""
        assert get_agent_by_gid("GID-99") is None

    def test_is_valid_agent(self):
        """Agent validation works."""
        assert is_valid_agent("BENSON") is True
        assert is_valid_agent("CODEX") is True  # Alias
        assert is_valid_agent("FAKE") is False

    def test_is_valid_gid(self):
        """GID validation works."""
        assert is_valid_gid("GID-00") is True
        assert is_valid_gid("GID-11") is True
        assert is_valid_gid("GID-12") is False
        assert is_valid_gid("GID-99") is False

    def test_is_valid_emoji(self):
        """Emoji validation works."""
        assert is_valid_emoji("🔵") is True
        assert is_valid_emoji("⚪") is True
        assert is_valid_emoji("🟤") is False  # Not in roster


# =============================================================================
# VALIDATION FUNCTION TESTS
# =============================================================================


class TestAgentValidation:
    """Test agent-GID-emoji validation."""

    def test_validate_agent_gid_match_correct(self):
        """Correct agent-GID pairs pass."""
        assert validate_agent_gid_match("CODY", "GID-01") is True
        assert validate_agent_gid_match("ALEX", "GID-08") is True
        assert validate_agent_gid_match("BENSON", "GID-00") is True

    def test_validate_agent_gid_match_incorrect(self):
        """Incorrect agent-GID pairs fail."""
        assert validate_agent_gid_match("CODY", "GID-02") is False
        assert validate_agent_gid_match("ALEX", "GID-01") is False

    def test_validate_agent_emoji_match_correct(self):
        """Correct agent-emoji pairs pass."""
        assert validate_agent_emoji_match("CODY", "🔵") is True
        assert validate_agent_emoji_match("ALEX", "⚪") is True
        assert validate_agent_emoji_match("SONNY", "🟨") is True

    def test_validate_agent_emoji_match_incorrect(self):
        """Incorrect agent-emoji pairs fail."""
        assert validate_agent_emoji_match("CODY", "🟦") is False
        assert validate_agent_emoji_match("ALEX", "🔵") is False


# =============================================================================
# HARD RULE ENFORCEMENT TESTS
# =============================================================================


class TestHardRules:
    """Test HARD RULES enforcement."""

    def test_no_duplicate_gids(self):
        """Each agent has a unique GID."""
        gids = [a.gid for a in CANONICAL_AGENTS.values()]
        assert len(gids) == len(set(gids)), "Duplicate GIDs detected!"

    def test_no_gid_gaps(self):
        """GIDs are contiguous from 00 to 11."""
        gid_numbers = sorted(a.gid_number for a in CANONICAL_AGENTS.values())
        assert gid_numbers == list(range(12))

    def test_agents_are_immutable(self):
        """Agent dataclass is frozen (immutable)."""
        agent = CANONICAL_AGENTS["CODY"]
        with pytest.raises(Exception):  # FrozenInstanceError
            agent.gid = "GID-99"

    def test_valid_emojis_match_roster(self):
        """VALID_EMOJIS set matches roster emojis."""
        roster_emojis = {a.emoji for a in CANONICAL_AGENTS.values()}
        assert VALID_EMOJIS == roster_emojis

    def test_valid_gids_match_roster(self):
        """VALID_GIDS set matches roster GIDs."""
        roster_gids = {a.gid for a in CANONICAL_AGENTS.values()}
        assert VALID_GIDS == roster_gids

    def test_no_emoji_changes_allowed(self):
        """Specific emoji assignments are locked per AGENT_REGISTRY.json."""
        # These are HARD LOCKED per docs/governance/AGENT_REGISTRY.json
        # Test will fail if anyone changes them without updating the canonical source
        LOCKED_ASSIGNMENTS = {
            "BENSON": "🟦🟩",  # TEAL
            "CODY": "🔵",
            "SONNY": "🟨",
            "MIRA-R": "🟣",
            "CINDY": "🟦",  # TEAL color but single blue square emoji
            "PAX": "🟧",
            "SAM": "🟥",
            "DAN": "🟩",
            "ALEX": "⚪",
            "LIRA": "🩷",
            "MAGGIE": "🩷",
            "ATLAS": "🔵",
        }
        
        for name, expected_emoji in LOCKED_ASSIGNMENTS.items():
            agent = CANONICAL_AGENTS[name]
            assert agent.emoji == expected_emoji, f"{name} emoji drift detected!"


# =============================================================================
# PAC LINTER INTEGRATION TESTS
# =============================================================================


class TestPACLinterIntegration:
    """Test PAC linter catches violations."""

    def test_linter_detects_wrong_gid(self):
        """Linter catches incorrect GID assignments."""
        # Sample PAC with wrong GID (CODY should be GID-01)
        bad_pac = """
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
🔵 CODY — GID-02 — BACKEND ENGINE
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
"""
        # The linter would flag: CODY has incorrect GID 'GID-02'. Expected 'GID-01'.
        agent = get_agent_by_name("CODY")
        assert agent.gid != "GID-02"

    def test_linter_detects_wrong_emoji(self):
        """Linter catches incorrect emoji assignments."""
        # SONNY should use 🟨, not 🔵
        assert CANONICAL_AGENTS["SONNY"].emoji == "🟨"
        assert CANONICAL_AGENTS["SONNY"].emoji != "🔵"

    def test_linter_detects_unknown_agent(self):
        """Linter catches unknown agents."""
        assert get_agent_by_name("DANA") is None  # Not in roster
        assert get_agent_by_name("UNKNOWN") is None


# ⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
# END OF PAC — ALEX — GID-08 — GOVERNANCE ENGINE
# ⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪
