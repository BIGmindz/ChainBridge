#!/usr/bin/env python3
"""
Normalize Markdown code fences across the repository by ensuring every opening
triple-backtick fence includes a language. Default language: "text".

Rules:
- Replace lines that are an opening fence of the form "```" (optionally with
  trailing spaces) with "```text".
- Preserve existing fences that already specify a language, e.g., ```bash.
- Preserve closing fences (```), do not add a language to closing lines.

Idempotent: Running multiple times will not change already-correct fences.
"""

from __future__ import annotations

import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

FENCE_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>(`{3,}|~{3,}))(?:\s*(?P<lang>\S.*)?)?\s*$")


def normalize_file(path: Path) -> tuple[bool, int]:
    changed = False
    fixes = 0
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return False, 0

    lines = text.splitlines()
    out_lines = []
    in_fence = False
    current_marker: str | None = None

    for line in lines:
        m = FENCE_RE.match(line)
        if m:
            indent = m.group("indent") or ""
            marker = m.group("marker") or "````"
            lang = (m.group("lang") or "").strip()

            if not in_fence:
                # Opening fence
                if not lang:
                    out_lines.append(f"{indent}{marker} text")
                    changed = True
                    fixes += 1
                    in_fence = True
                    current_marker = marker
                    continue
                else:
                    in_fence = True
                    current_marker = marker
            else:
                # Closing fence: ensure we close only if marker matches
                if current_marker and marker.startswith(current_marker[0]):
                    in_fence = False
                    current_marker = None

        out_lines.append(line)

    if changed:
        path.write_text("\n".join(out_lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    return changed, fixes


def main() -> None:
    md_files = [p for p in ROOT.rglob("*.md") if p.is_file()]
    total_changed = 0
    total_fixes = 0
    for p in md_files:
        changed, fixes = normalize_file(p)
        if changed:
            print(f"fixed {fixes:02d} fence(s): {p.relative_to(ROOT)}")
            total_changed += 1
            total_fixes += fixes
    print(f"\nSummary: files changed={total_changed}, fences fixed={total_fixes}")


if __name__ == "__main__":
    main()
