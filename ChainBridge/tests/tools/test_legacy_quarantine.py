from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = pytest.mark.core

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _iter_py_files(root: pathlib.Path):
    for path in root.rglob("*.py"):
        # Skip legacy itself and virtualenvs
        if "legacy/legacy-benson-bot" in str(path):
            continue
        if ".venv" in str(path):
            continue
        yield path


def test_no_imports_from_legacy_benson_bot():
    """
    Guardrail: Prohibits imports from legacy/legacy-benson-bot in active code.

    If this fails, someone tried to re-wire production code to the old trading engine.
    """
    offenders = []

    for path in _iter_py_files(PROJECT_ROOT):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if (node.module or "").startswith("legacy.legacy-benson-bot"):
                    offenders.append((path, node.lineno, node.module))
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("legacy.legacy-benson-bot"):
                        offenders.append((path, node.lineno, alias.name))

    assert not offenders, f"Forbidden legacy imports detected: {offenders}"
