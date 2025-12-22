"""
# ═══════════════════════════════════════════════════════════════════════════════
# 🟢 DAN (GID-07) ACTIVATION BLOCK — CI Gate Tests
# ═══════════════════════════════════════════════════════════════════════════════
# PAC: PAC-DAN-ACTIVATION-GATE-CI-ENFORCEMENT-01
# Lane: 🟢 GREEN — DevOps / CI-CD
# Status: ACTIVE
# ═══════════════════════════════════════════════════════════════════════════════

Tests for CI Activation Gate enforcement.

Tests:
- Missing activation block → DENIED_ACTIVATION_MISSING
- Malformed activation block → DENIED_ACTIVATION_MALFORMED
- Duplicate activation block → DENIED_ACTIVATION_DUPLICATE
- Misordered activation block → DENIED_ACTIVATION_MISORDERED
- Valid activation block → PASS
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Path to the CI gate script
GATE_SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "ci" / "activation_gate.py"


class TestActivationGateDenialCodes:
    """Test structured denial codes for CI visibility."""

    def test_missing_activation_in_pac_file_returns_denied_missing(self, tmp_path: Path):
        """PAC-like file without EXECUTING AGENT returns DENIED_ACTIVATION_MISSING."""
        test_file = tmp_path / "pac_no_agent.py"
        # File has PAC header but no EXECUTING AGENT
        test_file.write_text('''"""
# ═══════════════════════════════════════════════════════════════════════════════
# PAC: PAC-TEST-001
# Lane: 🟢 GREEN — Test Lane
# ═══════════════════════════════════════════════════════════════════════════════
"""

def some_function():
    pass
''')

        result = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--file", str(test_file), "--json"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        output = json.loads(result.stdout)
        assert output["passed"] is False
        assert "DENIED_ACTIVATION_MISSING" in output["denial_code"]

    def test_regular_file_without_pac_passes(self, tmp_path: Path):
        """Regular Python file without PAC structure passes (not enforced)."""
        test_file = tmp_path / "regular.py"
        test_file.write_text('''"""
A regular Python file without PAC structure.
"""

def some_function():
    pass
''')

        result = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--file", str(test_file), "--json"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["passed"] is True

    def test_malformed_activation_missing_gid_returns_denied_malformed(self, tmp_path: Path):
        """Activation block without GID returns DENIED_ACTIVATION_MALFORMED."""
        test_file = tmp_path / "malformed_activation.py"
        test_file.write_text('''"""
# ═══════════════════════════════════════════════════════════════════════════════
# PAC: PAC-TEST-001
# Lane: 🟢 GREEN — Test Lane
# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTING AGENT: DAN
# (Missing GID!)
# ═══════════════════════════════════════════════════════════════════════════════
"""

def some_function():
    pass
''')

        result = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--file", str(test_file), "--json"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        output = json.loads(result.stdout)
        assert output["passed"] is False
        assert "DENIED_ACTIVATION_MALFORMED" in output["denial_code"]

    def test_duplicate_activation_block_returns_denied_duplicate(self, tmp_path: Path):
        """Duplicate activation blocks return DENIED_ACTIVATION_DUPLICATE."""
        test_file = tmp_path / "duplicate_activation.py"
        test_file.write_text('''"""
# ═══════════════════════════════════════════════════════════════════════════════
# AGENT ACTIVATION BLOCK
# ═══════════════════════════════════════════════════════════════════════════════
# PAC: PAC-TEST-001
# Lane: 🟢 GREEN — DevOps / CI-CD
# EXECUTING AGENT: DAN (GID-07)
# Status: ACTIVE
# ═══════════════════════════════════════════════════════════════════════════════
"""

# ... some code ...

"""
# ═══════════════════════════════════════════════════════════════════════════════
# AGENT ACTIVATION BLOCK
# ═══════════════════════════════════════════════════════════════════════════════
# PAC: PAC-TEST-002
# Lane: 🟢 GREEN — DevOps / CI-CD
# EXECUTING AGENT: DAN (GID-07)
# Status: ACTIVE
# ═══════════════════════════════════════════════════════════════════════════════
"""

def some_function():
    pass
''')

        result = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--file", str(test_file), "--json"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        output = json.loads(result.stdout)
        assert output["passed"] is False
        assert "DENIED_ACTIVATION_DUPLICATE" in output["denial_code"]

    def test_misordered_activation_block_returns_denied_misordered(self, tmp_path: Path):
        """Activation block too far from PAC header returns DENIED_ACTIVATION_MISORDERED."""
        test_file = tmp_path / "misordered_activation.py"
        # PAC header is at line ~4, but EXECUTING AGENT is way later (>20 lines gap)
        test_file.write_text('''"""
# PAC: PAC-TEST-001
"""

import os
import sys
import json
import re
import datetime
import pathlib
import collections
import functools
import itertools
import logging
import argparse
import subprocess
import tempfile
import unittest
import dataclasses
import typing
import enum
import abc
import contextlib

"""
# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTING AGENT: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════
"""

def some_function():
    pass
''')

        result = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--file", str(test_file), "--json"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        output = json.loads(result.stdout)
        assert output["passed"] is False
        assert "DENIED_ACTIVATION_MISORDERED" in output["denial_code"]

    def test_valid_activation_block_passes(self, tmp_path: Path):
        """Valid activation block at proper position passes."""
        test_file = tmp_path / "valid_activation.py"
        test_file.write_text('''"""
# ═══════════════════════════════════════════════════════════════════════════════
# AGENT ACTIVATION BLOCK
# ═══════════════════════════════════════════════════════════════════════════════
# PAC: PAC-TEST-001
# Lane: 🟢 GREEN — DevOps / CI-CD
# EXECUTING AGENT: DAN (GID-07)
# Status: ACTIVE
# ═══════════════════════════════════════════════════════════════════════════════
"""

def some_function():
    pass
''')

        result = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--file", str(test_file), "--json"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["passed"] is True
        assert output["denial_code"] is None


class TestActivationGateCI:
    """Test CI integration behavior."""

    def test_json_output_is_valid_json(self, tmp_path: Path):
        """JSON output can be parsed for CI systems."""
        test_file = tmp_path / "test.py"
        test_file.write_text('"""No PAC structure."""\n')

        result = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--file", str(test_file), "--json"],
            capture_output=True,
            text=True,
        )

        # Should be valid JSON regardless of pass/fail
        output = json.loads(result.stdout)
        assert "passed" in output
        assert "denial_code" in output
        assert "file_path" in output

    def test_verbose_output_includes_details(self, tmp_path: Path):
        """Verbose mode includes additional details."""
        test_file = tmp_path / "test.py"
        test_file.write_text('"""No PAC structure."""\n')

        result = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--file", str(test_file), "--verbose"],
            capture_output=True,
            text=True,
        )

        # Should have detailed output
        assert "ACTIVATION GATE" in result.stdout or "Activation" in result.stdout

    def test_exit_code_nonzero_on_pac_file_failure(self, tmp_path: Path):
        """Exit code is non-zero on PAC file validation failure."""
        test_file = tmp_path / "bad_pac.py"
        # PAC structure but missing EXECUTING AGENT
        test_file.write_text('''"""
# PAC: PAC-TEST-001
"""
''')

        result = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--file", str(test_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0

    def test_exit_code_zero_on_success(self, tmp_path: Path):
        """Exit code is zero on validation success."""
        test_file = tmp_path / "valid.py"
        test_file.write_text('''"""
# ═══════════════════════════════════════════════════════════════════════════════
# AGENT ACTIVATION BLOCK
# ═══════════════════════════════════════════════════════════════════════════════
# PAC: PAC-TEST-001
# Lane: 🟢 GREEN — DevOps / CI-CD
# EXECUTING AGENT: DAN (GID-07)
# Status: ACTIVE
# ═══════════════════════════════════════════════════════════════════════════════
"""
''')

        result = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--file", str(test_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0


class TestActivationGateScriptExists:
    """Verify the gate script infrastructure exists."""

    def test_gate_script_exists(self):
        """CI gate script exists at expected location."""
        assert GATE_SCRIPT.exists(), f"Gate script not found at {GATE_SCRIPT}"

    def test_gate_script_executable_with_python(self):
        """Gate script can be executed with Python."""
        result = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "activation" in result.stdout.lower() or "usage" in result.stdout.lower()


class TestActivationGateWorkflow:
    """Test workflow integration scenarios."""

    def test_multiple_valid_pac_files_pass(self, tmp_path: Path):
        """Multiple valid PAC files all pass."""
        valid_content = '''"""
# ═══════════════════════════════════════════════════════════════════════════════
# AGENT ACTIVATION BLOCK
# ═══════════════════════════════════════════════════════════════════════════════
# PAC: PAC-TEST-001
# Lane: 🟢 GREEN — DevOps / CI-CD
# EXECUTING AGENT: DAN (GID-07)
# Status: ACTIVE
# ═══════════════════════════════════════════════════════════════════════════════
"""
'''
        (tmp_path / "file1.py").write_text(valid_content)
        (tmp_path / "file2.py").write_text(valid_content)

        # Test each file
        for f in ["file1.py", "file2.py"]:
            result = subprocess.run(
                [sys.executable, str(GATE_SCRIPT), "--file", str(tmp_path / f)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"File {f} should pass"

    def test_one_invalid_pac_file_fails_gate(self, tmp_path: Path):
        """If one PAC file is invalid, gate fails for that file."""
        valid_content = '''"""
# ═══════════════════════════════════════════════════════════════════════════════
# AGENT ACTIVATION BLOCK
# ═══════════════════════════════════════════════════════════════════════════════
# PAC: PAC-TEST-001
# Lane: 🟢 GREEN — DevOps / CI-CD
# EXECUTING AGENT: DAN (GID-07)
# Status: ACTIVE
# ═══════════════════════════════════════════════════════════════════════════════
"""
'''
        # PAC structure but missing EXECUTING AGENT
        invalid_content = '''"""
# PAC: PAC-TEST-002
# This is a PAC file but missing EXECUTING AGENT
"""
'''

        (tmp_path / "valid.py").write_text(valid_content)
        (tmp_path / "invalid.py").write_text(invalid_content)

        # Valid file passes
        result1 = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--file", str(tmp_path / "valid.py")],
            capture_output=True,
            text=True,
        )
        assert result1.returncode == 0

        # Invalid PAC file fails
        result2 = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--file", str(tmp_path / "invalid.py")],
            capture_output=True,
            text=True,
        )
        assert result2.returncode != 0
