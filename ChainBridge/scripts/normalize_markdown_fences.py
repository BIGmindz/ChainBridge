#!/usr/bin/env python3
"""Markdown Fence Normalizer & Language Inference
=================================================

Purpose:
    Ensure every opening code fence has an explicit language while heuristically
    inferring a better language than a generic "text" where possible.

Heuristic Inference (ordered):
    - Bash/Shell: lines starting with `$`, contain common shell cmds (pip install, make, git, ls, export, docker)
    - Python: lines starting with `import `, `from X import`, shebang `#!/usr/bin/env python`, or typical Python keywords (def, class) without trailing `;`
    - YAML: presence of typical keys (version:, services:, apiVersion:, kind:, metadata:) early and contains ':' structure
    - JSON: starts with `{` or `[` and valid JSON-like structure
    - TOML: lines with `key = value` and at least one bracketed table `[section]`
    - INI: bracketed section headers and key=value pairs
    - Markdown: banner fences used for ASCII art (no inference change -> text)
    - Fallback: text

Idempotent:
    - Existing language spec preserved
    - Already inferred fences not re-written unless heuristic changed and previous was 'text'
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import json


ROOT = Path(__file__).resolve().parents[1]

FENCE_RE = re.compile(
    r"^(?P<indent>\s*)(?P<marker>(`{3,}|~{3,}))(?:\s*(?P<lang>\S.*)?)?\s*$"
)


def infer_language(code_block_lines: list[str]) -> str:
    """Infer a reasonable language for a code fence based on its content.

    We inspect only the first N non-empty lines to keep it fast.
    Returns a short language token accepted by common highlighters.
    """
    SAMPLE_LINES = 12
    lines = [line.rstrip() for line in code_block_lines if line.strip()][:SAMPLE_LINES]
    if not lines:
        return "text"

    joined = "\n".join(lines)
    first = lines[0]

    shell_indicators = ("$ ", "#!/bin/bash", "#!/usr/bin/env bash")
    shell_cmds = {
        "pip",
        "python",
        "pytest",
        "git",
        "ls",
        "echo",
        "cat",
        "make",
        "docker",
        "export",
    }
    py_keywords = {
        "import ",
        "from ",
        "def ",
        "class ",
        "async def ",
        "with ",
        "for ",
        "if ",
        "print(",
    }
    yaml_keys = {
        "version:",
        "services:",
        "apiVersion:",
        "kind:",
        "metadata:",
        "spec:",
        "name:",
    }

    # Bash / shell
    if first.startswith(shell_indicators) or any(
        line.startswith("$") for line in lines
    ):
        return "bash"
    if sum(any(tok in line for tok in shell_cmds) for line in lines) >= 2 and not any(
        line.strip().startswith("def ") for line in lines
    ):
        return "bash"

    # Python
    if first.startswith("#!/usr/bin/env python") or any(
        line.startswith(k) for k in py_keywords for line in lines
    ):
        return "python"
    if any(
        line.endswith(":") and line.split()[0] in {"class", "def"} for line in lines
    ):
        return "python"

    # JSON (quick heuristic: starts with { or [ and json.loads succeeds on a trimmed subset)
    if first.strip().startswith(("{", "[")):
        snippet = joined
        # Attempt a safe truncated parse
        try:
            json.loads(snippet)
            return "json"
        except Exception:
            pass

    # YAML (contains multiple key: value patterns and yaml-like top keys)
    yaml_like = sum(1 for line in lines if re.match(r"^[A-Za-z0-9_-]+:\s*", line))
    if yaml_like >= 2 and any(any(k in line for k in yaml_keys) for line in lines):
        return "yaml"

    # TOML
    if sum(
        1 for line in lines if re.match(r"^[A-Za-z0-9_.-]+\s*=\s*.+", line)
    ) >= 2 and any(line.startswith("[") and line.endswith("]") for line in lines):
        return "toml"

    # INI
    if (
        any(line.startswith("[") and line.endswith("]") for line in lines)
        and sum(1 for line in lines if re.match(r"^[A-Za-z0-9_.-]+\s*=\s*.+", line))
        >= 1
    ):
        return "ini"

    return "text"


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
    buffer: list[str] = []  # collect code lines for inference

    for line in lines:
        m = FENCE_RE.match(line)
        if m:
            indent = m.group("indent") or ""
            marker = m.group("marker") or "````"
            lang = (m.group("lang") or "").strip()

            if not in_fence:
                # Opening fence
                if not lang:
                    # We'll tentatively mark as text; inference will adjust when closing encountered
                    out_lines.append(f"{indent}{marker} text")
                    changed = True
                    fixes += 1
                    in_fence = True
                    current_marker = marker
                    buffer = []
                    continue
                else:
                    in_fence = True
                    current_marker = marker
                    buffer = []
            else:
                # Closing fence: ensure we close only if marker matches
                if current_marker and marker.startswith(current_marker[0]):
                    # Perform inference if the opening fence we wrote was 'text'
                    if buffer and out_lines:
                        open_line = (
                            out_lines[-(len(buffer) + 1)]
                            if len(out_lines) >= (len(buffer) + 1)
                            else out_lines[-1]
                        )
                        if open_line.strip().startswith(
                            marker
                        ) and open_line.strip().endswith(" text"):
                            inferred = infer_language(buffer)
                            if inferred != "text":
                                out_lines[-(len(buffer) + 1)] = open_line.replace(
                                    " text", f" {inferred}"
                                )
                    buffer = []
                    in_fence = False
                    current_marker = None

        out_lines.append(line)
        if in_fence and not FENCE_RE.match(line):
            buffer.append(line)

    if changed:
        path.write_text(
            "\n".join(out_lines) + ("\n" if text.endswith("\n") else ""),
            encoding="utf-8",
        )
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
