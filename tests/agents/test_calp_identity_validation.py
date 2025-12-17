"""
CALP v1 Agent Identity Validation Tests

Tests the ChainBridge Agent Launch Pack (CALP) canonical definitions.
Ensures GID assignments, colors, and roles are consistent across all registry files.

PAC-ALEX-GOV-023: CALP Boot Protocol Enforcement
"""

import json
from pathlib import Path

import pytest

# Paths to registry files
ROOT = Path(__file__).parent.parent.parent
CONFIG_AGENTS_PATH = ROOT / "config" / "agents.json"
AGENT_REGISTRY_PATH = ROOT / "docs" / "governance" / "AGENT_REGISTRY.json"
ALEX_RULES_PATH = ROOT / ".github" / "ALEX_RULES.json"


# CALP v1 Canonical Agent Definitions
CALP_V1_CANONICAL = {
    "BENSON": {"gid": "GID-00", "color": "TEAL", "role": "Orchestrator"},
    "CODY": {"gid": "GID-01", "color": "BLUE", "role": "Backend Engineering"},
    "SONNY": {"gid": "GID-02", "color": "YELLOW", "role": "Frontend Engineering"},
    "MIRA_R": {"gid": "GID-03", "color": "PURPLE", "role": "Research"},
    "CINDY": {"gid": "GID-04", "color": "TEAL", "role": "Backend Expansion"},
    "PAX": {"gid": "GID-05", "color": "ORANGE", "role": "Product Strategy"},
    "SAM": {"gid": "GID-06", "color": "DARK RED", "role": "Security"},
    "DAN": {"gid": "GID-07", "color": "GREEN", "role": "DevOps"},
    "ALEX": {"gid": "GID-08", "color": "GREY", "role": "Governance"},
    "LIRA": {"gid": "GID-09", "color": "PINK", "role": "UX"},
    "MAGGIE": {"gid": "GID-10", "color": "PINK", "role": "ML & Risk"},
    "ATLAS": {"gid": "GID-11", "color": "BLUE", "role": "Build & Repair"},
}

# Expected GID range
EXPECTED_GIDS = [f"GID-{i:02d}" for i in range(12)]

# Forbidden aliases
FORBIDDEN_ALIASES = ["DANA"]


class TestCALPAgentRegistry:
    """Tests for config/agents.json CALP compliance."""

    @pytest.fixture
    def agents_config(self):
        """Load config/agents.json."""
        with open(CONFIG_AGENTS_PATH) as f:
            return json.load(f)

    def test_calp_version_present(self, agents_config):
        """CALP version must be declared."""
        assert "calp_version" in agents_config
        assert agents_config["calp_version"] == "1.0.0"

    def test_all_canonical_agents_present(self, agents_config):
        """All 12 canonical agents must be defined."""
        agents = agents_config.get("agents", {})
        for agent_name in CALP_V1_CANONICAL:
            assert agent_name in agents, f"Missing agent: {agent_name}"

    def test_gid_assignments_match_canonical(self, agents_config):
        """GID assignments must match CALP v1 canonical."""
        agents = agents_config.get("agents", {})
        for agent_name, expected in CALP_V1_CANONICAL.items():
            actual_gid = agents.get(agent_name, {}).get("gid")
            assert actual_gid == expected["gid"], f"{agent_name}: expected GID {expected['gid']}, got {actual_gid}"

    def test_color_assignments_match_canonical(self, agents_config):
        """Color assignments must match CALP v1 canonical."""
        agents = agents_config.get("agents", {})
        for agent_name, expected in CALP_V1_CANONICAL.items():
            actual_color = agents.get(agent_name, {}).get("color")
            assert actual_color == expected["color"], f"{agent_name}: expected color {expected['color']}, got {actual_color}"

    def test_role_short_matches_canonical(self, agents_config):
        """Role short must match CALP v1 canonical role."""
        agents = agents_config.get("agents", {})
        for agent_name, expected in CALP_V1_CANONICAL.items():
            actual_role = agents.get(agent_name, {}).get("role_short")
            assert actual_role == expected["role"], f"{agent_name}: expected role '{expected['role']}', got '{actual_role}'"

    def test_gid_index_complete(self, agents_config):
        """GID index must map all 12 GIDs."""
        gid_index = agents_config.get("gid_index", {})
        for gid in EXPECTED_GIDS:
            assert gid in gid_index, f"Missing GID in index: {gid}"

    def test_gid_index_bidirectional(self, agents_config):
        """GID index must be consistent with agent definitions."""
        agents = agents_config.get("agents", {})
        gid_index = agents_config.get("gid_index", {})

        for gid, agent_name in gid_index.items():
            agent_def = agents.get(agent_name, {})
            assert agent_def.get("gid") == gid, f"GID index mismatch: {gid} -> {agent_name} but agent has {agent_def.get('gid')}"

    def test_no_duplicate_gids(self, agents_config):
        """No two agents can share a GID."""
        agents = agents_config.get("agents", {})
        gids = [a.get("gid") for a in agents.values()]
        assert len(gids) == len(set(gids)), "Duplicate GIDs detected"

    def test_forbidden_aliases_defined(self, agents_config):
        """Forbidden aliases must be defined."""
        forbidden = agents_config.get("forbidden_aliases", [])
        for alias in FORBIDDEN_ALIASES:
            assert alias in forbidden, f"Missing forbidden alias: {alias}"

    def test_no_forbidden_agents(self, agents_config):
        """No forbidden aliases in agent list."""
        agents = agents_config.get("agents", {})
        for alias in FORBIDDEN_ALIASES:
            assert alias not in agents, f"Forbidden alias in agents: {alias}"


class TestAgentRegistryConsistency:
    """Tests for docs/governance/AGENT_REGISTRY.json consistency."""

    @pytest.fixture
    def agent_registry(self):
        """Load AGENT_REGISTRY.json."""
        with open(AGENT_REGISTRY_PATH) as f:
            return json.load(f)

    def test_calp_version_present(self, agent_registry):
        """CALP version must be declared."""
        assert "calp_version" in agent_registry
        assert agent_registry["calp_version"] == "1.0.0"

    def test_all_canonical_agents_present(self, agent_registry):
        """All 12 canonical agents must be defined."""
        agents = agent_registry.get("agents", {})
        for agent_name in CALP_V1_CANONICAL:
            assert agent_name in agents, f"Missing agent: {agent_name}"

    def test_gid_assignments_match_canonical(self, agent_registry):
        """GID assignments must match CALP v1 canonical."""
        agents = agent_registry.get("agents", {})
        for agent_name, expected in CALP_V1_CANONICAL.items():
            actual_gid = agents.get(agent_name, {}).get("gid")
            assert actual_gid == expected["gid"], f"{agent_name}: expected GID {expected['gid']}, got {actual_gid}"


class TestALEXRulesCALPCompliance:
    """Tests for ALEX_RULES.json CALP rule compliance."""

    @pytest.fixture
    def alex_rules(self):
        """Load ALEX_RULES.json."""
        with open(ALEX_RULES_PATH) as f:
            return json.load(f)

    def test_calp_rule_exists(self, alex_rules):
        """Rule 23 (CALP Boot Protocol) must exist."""
        rules = alex_rules.get("hard_constraints", {})
        assert "rule_23" in rules, "Missing rule_23 (CALP Boot Protocol)"

    def test_calp_rule_severity_critical(self, alex_rules):
        """CALP rule must be CRITICAL severity."""
        rule = alex_rules.get("hard_constraints", {}).get("rule_23", {})
        assert rule.get("severity") == "CRITICAL"

    def test_calp_rule_enforcement_fatal(self, alex_rules):
        """CALP rule must enforce FATAL_ERROR."""
        rule = alex_rules.get("hard_constraints", {}).get("rule_23", {})
        assert rule.get("enforcement") == "FATAL_ERROR"

    def test_calp_canonical_agents_in_rule(self, alex_rules):
        """CALP canonical agents must be defined in rule."""
        rule = alex_rules.get("hard_constraints", {}).get("rule_23", {})
        canonical = rule.get("canonical_agents", {})

        for agent_name, expected in CALP_V1_CANONICAL.items():
            assert agent_name in canonical, f"Missing agent in rule: {agent_name}"
            assert canonical[agent_name]["gid"] == expected["gid"]
            assert canonical[agent_name]["color"] == expected["color"]
            assert canonical[agent_name]["role"] == expected["role"]

    def test_calp_references_in_docs(self, alex_rules):
        """CALP v1 must be referenced in documentation."""
        refs = alex_rules.get("references", {}).get("documentation", [])
        assert "docs/governance/CALP_v1.md" in refs

    def test_agents_json_in_registries(self, alex_rules):
        """config/agents.json must be in registries."""
        refs = alex_rules.get("references", {}).get("registries", [])
        assert "config/agents.json" in refs


class TestCrossRegistryConsistency:
    """Tests for consistency across all registry files."""

    @pytest.fixture
    def all_registries(self):
        """Load all registry files."""
        with open(CONFIG_AGENTS_PATH) as f:
            config_agents = json.load(f)
        with open(AGENT_REGISTRY_PATH) as f:
            agent_registry = json.load(f)
        with open(ALEX_RULES_PATH) as f:
            alex_rules = json.load(f)

        return {
            "config_agents": config_agents,
            "agent_registry": agent_registry,
            "alex_rules": alex_rules,
        }

    def test_gids_consistent_across_registries(self, all_registries):
        """GID assignments must be identical across all registries."""
        config = all_registries["config_agents"].get("agents", {})
        registry = all_registries["agent_registry"].get("agents", {})
        rule = all_registries["alex_rules"].get("hard_constraints", {}).get("rule_23", {}).get("canonical_agents", {})

        for agent_name in CALP_V1_CANONICAL:
            config_gid = config.get(agent_name, {}).get("gid")
            registry_gid = registry.get(agent_name, {}).get("gid")
            rule_gid = rule.get(agent_name, {}).get("gid")

            assert (
                config_gid == registry_gid == rule_gid
            ), f"{agent_name} GID mismatch: config={config_gid}, registry={registry_gid}, rule={rule_gid}"

    def test_colors_consistent_across_registries(self, all_registries):
        """Color assignments must be identical across all registries."""
        config = all_registries["config_agents"].get("agents", {})
        registry = all_registries["agent_registry"].get("agents", {})
        rule = all_registries["alex_rules"].get("hard_constraints", {}).get("rule_23", {}).get("canonical_agents", {})

        for agent_name in CALP_V1_CANONICAL:
            config_color = config.get(agent_name, {}).get("color")
            registry_color = registry.get(agent_name, {}).get("color")
            rule_color = rule.get(agent_name, {}).get("color")

            assert (
                config_color == registry_color == rule_color
            ), f"{agent_name} color mismatch: config={config_color}, registry={registry_color}, rule={rule_color}"


class TestCALPBootProtocol:
    """Tests for CALP boot protocol requirements."""

    @pytest.fixture
    def agents_config(self):
        """Load config/agents.json."""
        with open(CONFIG_AGENTS_PATH) as f:
            return json.load(f)

    def test_boot_protocol_defined(self, agents_config):
        """Boot protocol must be defined."""
        assert "boot_protocol" in agents_config
        protocol = agents_config["boot_protocol"]
        assert protocol.get("name") == "CALP"
        assert protocol.get("version") == "1.0.0"

    def test_boot_steps_defined(self, agents_config):
        """Boot protocol steps must be defined."""
        protocol = agents_config.get("boot_protocol", {})
        steps = protocol.get("steps", [])
        assert len(steps) >= 5, "Boot protocol must have at least 5 steps"

    def test_fatal_conditions_defined(self, agents_config):
        """Fatal conditions must be defined."""
        protocol = agents_config.get("boot_protocol", {})
        fatal = protocol.get("fatal_conditions", [])
        assert "Cannot identify GID" in fatal
        assert "GID mismatch" in fatal

    def test_execution_order_defined(self, agents_config):
        """Execution order must be defined."""
        execution = agents_config.get("execution_order", [])
        assert len(execution) >= 4, "Execution order must have at least 4 steps"

    def test_load_response_for_all_agents(self, agents_config):
        """Each agent must have a load_response definition."""
        agents = agents_config.get("agents", {})
        for agent_name, agent_def in agents.items():
            assert "load_response" in agent_def, f"{agent_name} missing load_response"
            response = agent_def["load_response"]
            assert "agent" in response
            assert "gid" in response
            assert "color" in response
            assert "role" in response
