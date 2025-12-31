# ═══════════════════════════════════════════════════════════════════════════════
# OCC Invariants Tests — PAC-BENSON-P22-C
#
# Tests for INV-OCC-004, INV-OCC-005, INV-OCC-006.
# Validates governance rules in ALEX_RULES.json.
#
# Authors:
# - ALEX (GID-08) — Governance Enforcer
# - DAN (GID-07) — CI/Testing Lead
# ═══════════════════════════════════════════════════════════════════════════════

import json
import pytest
from pathlib import Path


@pytest.fixture
def alex_rules():
    """Load ALEX_RULES.json."""
    rules_path = Path(__file__).parent.parent.parent / ".github" / "ALEX_RULES.json"
    with open(rules_path) as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════════════════
# INV-OCC-004: Timeline Completeness
# ═══════════════════════════════════════════════════════════════════════════════

class TestINVOCC004TimelineCompleteness:
    """Test INV-OCC-004 governance rule."""

    def test_rule_24_exists(self, alex_rules):
        """Rule 24 (INV-OCC-004) exists in ALEX_RULES."""
        assert "rule_24" in alex_rules["hard_constraints"]
        rule = alex_rules["hard_constraints"]["rule_24"]
        assert "INV-OCC-004" in rule["name"]

    def test_rule_24_requirements(self, alex_rules):
        """Rule 24 has timeline completeness requirements."""
        rule = alex_rules["hard_constraints"]["rule_24"]
        assert len(rule["requirements"]) >= 7
        
        # Check key requirements exist
        req_text = " ".join(rule["requirements"]).lower()
        assert "lifecycle" in req_text
        assert "timeline" in req_text
        assert "agent" in req_text

    def test_rule_24_validation_states(self, alex_rules):
        """Rule 24 defines valid timeline states."""
        rule = alex_rules["hard_constraints"]["rule_24"]
        states = rule["validation"]["timeline_states"]
        
        expected_states = [
            "ADMISSION",
            "RUNTIME_ACTIVATION",
            "AGENT_ACTIVATION",
            "EXECUTING",
            "WRAP_COLLECTION",
            "REVIEW_GATE",
            "BER_ISSUED",
            "SETTLED",
            "FAILED",
            "CANCELLED",
        ]
        
        for state in expected_states:
            assert state in states

    def test_rule_24_enforcement(self, alex_rules):
        """Rule 24 has proper enforcement."""
        rule = alex_rules["hard_constraints"]["rule_24"]
        assert rule["enforcement"] == "RUNTIME_CHECK"
        assert rule["severity"] == "HIGH"


# ═══════════════════════════════════════════════════════════════════════════════
# INV-OCC-005: Evidence Immutability
# ═══════════════════════════════════════════════════════════════════════════════

class TestINVOCC005EvidenceImmutability:
    """Test INV-OCC-005 governance rule."""

    def test_rule_25_exists(self, alex_rules):
        """Rule 25 (INV-OCC-005) exists in ALEX_RULES."""
        assert "rule_25" in alex_rules["hard_constraints"]
        rule = alex_rules["hard_constraints"]["rule_25"]
        assert "INV-OCC-005" in rule["name"]

    def test_rule_25_read_only_requirements(self, alex_rules):
        """Rule 25 enforces READ-ONLY operations."""
        rule = alex_rules["hard_constraints"]["rule_25"]
        req_text = " ".join(rule["requirements"]).lower()
        
        assert "read-only" in req_text or "read only" in req_text
        assert "405" in req_text
        assert "immutable" in req_text

    def test_rule_25_blocked_operations(self, alex_rules):
        """Rule 25 blocks mutation methods."""
        rule = alex_rules["hard_constraints"]["rule_25"]
        blocked = rule["blocked_operations"]
        
        assert "/occ/timeline/*" in blocked["endpoints"]
        assert "/occ/agents/*" in blocked["endpoints"]
        assert "/occ/diff/*" in blocked["endpoints"]
        
        assert "POST" in blocked["methods"]
        assert "PUT" in blocked["methods"]
        assert "PATCH" in blocked["methods"]
        assert "DELETE" in blocked["methods"]

    def test_rule_25_enforcement(self, alex_rules):
        """Rule 25 has CRITICAL enforcement."""
        rule = alex_rules["hard_constraints"]["rule_25"]
        assert rule["enforcement"] == "BLOCK_REQUEST"
        assert rule["severity"] == "CRITICAL"


# ═══════════════════════════════════════════════════════════════════════════════
# INV-OCC-006: No Hidden Transitions
# ═══════════════════════════════════════════════════════════════════════════════

class TestINVOCC006NoHiddenTransitions:
    """Test INV-OCC-006 governance rule."""

    def test_rule_26_exists(self, alex_rules):
        """Rule 26 (INV-OCC-006) exists in ALEX_RULES."""
        assert "rule_26" in alex_rules["hard_constraints"]
        rule = alex_rules["hard_constraints"]["rule_26"]
        assert "INV-OCC-006" in rule["name"]

    def test_rule_26_visibility_requirements(self, alex_rules):
        """Rule 26 requires visibility for all transitions."""
        rule = alex_rules["hard_constraints"]["rule_26"]
        req_text = " ".join(rule["requirements"]).lower()
        
        assert "visible" in req_text or "recorded" in req_text
        assert "transition" in req_text or "activation" in req_text

    def test_rule_26_event_categories(self, alex_rules):
        """Rule 26 defines event categories."""
        rule = alex_rules["hard_constraints"]["rule_26"]
        categories = rule["validation"]["timeline_event_categories"]
        
        expected_categories = [
            "pac_lifecycle",
            "agent_activation",
            "execution",
            "decision",
            "wrap",
            "review_gate",
            "ber",
            "governance",
            "error",
        ]
        
        for cat in expected_categories:
            assert cat in categories

    def test_rule_26_diff_change_types(self, alex_rules):
        """Rule 26 defines diff change types."""
        rule = alex_rules["hard_constraints"]["rule_26"]
        change_types = rule["validation"]["diff_change_types"]
        
        expected_types = ["added", "removed", "modified", "unchanged"]
        for ct in expected_types:
            assert ct in change_types

    def test_rule_26_enforcement(self, alex_rules):
        """Rule 26 has proper enforcement."""
        rule = alex_rules["hard_constraints"]["rule_26"]
        assert rule["enforcement"] == "RUNTIME_CHECK"
        assert rule["severity"] == "HIGH"


# ═══════════════════════════════════════════════════════════════════════════════
# ALEX_RULES.json Structure Validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestALEXRulesStructure:
    """Test ALEX_RULES.json overall structure."""

    def test_occ_rules_have_pac_reference(self, alex_rules):
        """OCC rules reference PAC-BENSON-P22-C."""
        for rule_id in ["rule_24", "rule_25", "rule_26"]:
            rule = alex_rules["hard_constraints"][rule_id]
            assert rule["pac_ref"] == "PAC-BENSON-P22-C"

    def test_occ_rules_have_governance_doc(self, alex_rules):
        """OCC rules reference governance documentation."""
        for rule_id in ["rule_24", "rule_25", "rule_26"]:
            rule = alex_rules["hard_constraints"][rule_id]
            assert rule["governance_doc"] == "docs/governance/OCC_INVARIANTS.md"

    def test_changelog_includes_p22c(self, alex_rules):
        """Changelog includes PAC-BENSON-P22-C entry."""
        changelog = alex_rules["changelog"]
        p22c_entry = None
        for entry in changelog:
            if "PAC-BENSON-P22-C" in entry.get("changes", ""):
                p22c_entry = entry
                break
        
        assert p22c_entry is not None
        assert "OCC Invariants" in p22c_entry["changes"]
        assert "INV-OCC-004" in p22c_entry["changes"]
        assert "INV-OCC-005" in p22c_entry["changes"]
        assert "INV-OCC-006" in p22c_entry["changes"]
