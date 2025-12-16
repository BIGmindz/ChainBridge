"""
PAC-DAN-GATEKEEPER-02: Gatekeeper identity + proof tests.

Validates the new gatekeeper tool that enforces a single canonical registry
and rejects forbidden aliases ("DANA") in any agent packet.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "agent_outputs"
GATEKEEPER_SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "gatekeeper" / "check_agent_output.py"
REGISTRY_PATH = Path(__file__).parent.parent.parent / "ChainBridge" / "docs" / "governance" / "AGENT_REGISTRY.json"


def run_gatekeeper(fixture_name: str) -> tuple[int, str, str]:
    fixture_path = FIXTURES_DIR / fixture_name
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")

    result = subprocess.run(
        [sys.executable, str(GATEKEEPER_SCRIPT), str(fixture_path)],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


class TestGatekeeperPassFail:
    def test_valid_dan_packet_passes(self):
        exit_code, stdout, _ = run_gatekeeper("valid_dan_packet.txt")
        assert exit_code == 0, stdout
        assert "PASS" in stdout

    def test_wrong_gid_fails(self):
        exit_code, stdout, _ = run_gatekeeper("invalid_dan_wrong_gid.txt")
        assert exit_code == 1
        assert "Identity mismatch" in stdout

    def test_wrong_color_fails(self):
        exit_code, stdout, _ = run_gatekeeper("invalid_wrong_color.txt")
        assert exit_code == 1
        assert "Emoji mismatch" in stdout

    def test_contains_forbidden_alias_dana_fails(self):
        exit_code, stdout, _ = run_gatekeeper("invalid_contains_dana.txt")
        assert exit_code == 1
        assert "Forbidden alias" in stdout

    def test_missing_required_fields_fails(self):
        exit_code, stdout, _ = run_gatekeeper("invalid_missing_fields.txt")
        assert exit_code == 1
        assert "Missing required field" in stdout or "Proof missing" in stdout


class TestRegistry:
    def test_registry_single_source_of_truth(self):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        assert "agents" in data
        dan = data["agents"].get("DAN")
        assert dan is not None
        assert dan.get("gid") == "GID-07"
        assert dan.get("emoji") == "🟠"

    def test_forbidden_aliases_include_dana(self):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        aliases = {alias.upper() for alias in data.get("forbidden_aliases", [])}
        assert "DANA" in aliases
