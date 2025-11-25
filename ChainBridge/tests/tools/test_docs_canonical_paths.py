from __future__ import annotations

import pathlib

import pytest

pytestmark = pytest.mark.core

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_root_docs_are_stubs_only():
    """
    Root-level PROJECT_* docs must remain stubs.

    Canonical content lives under docs/product/.
    This keeps navigation consistent and avoids drift.
    """
    root_files = [
        ROOT / "PROJECT_CHECKLIST.md",
        ROOT / "PROJECT_STATUS_SUMMARY.md",
        ROOT / "M02_QUICK_REFERENCE.md",
    ]

    for path in root_files:
        if not path.exists():
            continue
        text = _read(path)
        # Simple heuristic: stub files should be short and contain a redirect note.
        assert len(text.splitlines()) < 80, f"{path} looks too long to be a stub"
        assert "docs/product/" in text, f"{path} must point to docs/product/ as canonical source"
