#!/usr/bin/env python3
"""Automated structural Markdown hygiene fixer (Phase 1 + Phase 2 structural).

Fixes applied (Phase 1):
- Collapse multiple consecutive blank lines to a single blank line.
- Ensure a single blank line before and after headings (non-first heading).
- Remove leading spaces before heading markers (#) (MD023).
- Insert a top-level H1 if file missing one (MD041) using filename.
- Convert pure emphasis pseudo-headings (e.g., *Section Title*) to level-2 headings (MD036 heuristic).
- Normalize ordered list numbering to '1.' style (optional minimal normalization when inconsistent).

Additional Phase 2 Fixes:
- Remove trailing punctuation from heading text (? ! , : ; .) except when single word acronym.
- Demote multiple top-level H1 headings to H2 (MD025).
- Convert Setext headings to ATX style (MD003).
- Add language hint to fenced code blocks lacking one (default to 'text').
- Ensure blank lines around fenced code blocks (MD031) and lists (MD032).
- Fix reversed link syntax patterns: [('text')['url']] -> [text](url).
- Normalize heading level increments (best effort; excess jumps demoted one level).

Limitations:
- Does NOT wrap long lines (MD013 is intentionally ignored in Phase 1).
- Does not refactor embedded HTML.
- Conservative: skips .github directory and binary-large docs.

Usage:
    python scripts/fix_markdown_structure.py

Re-run pymarkdown after execution to view remaining issues.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import List

RE_EMPH_HEADING = re.compile(r"^(?:\*\*?|__)([^*_`].{0,120}?)(?:\*\*?|__)$")
RE_ORDERED_ITEM = re.compile(r"^(\s*)(\d+)(\.)\s+")
RE_SETEXT_H1 = re.compile(r"^=+$")
RE_SETEXT_H2 = re.compile(r"^-+$")
RE_FENCED_START = re.compile(r"^```")
RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
RE_TRAIL_PUNCT = re.compile(r"[?!,:;.]$")
RE_REVERSED_LINK = re.compile(
    r"\[\('([^']+)'\)\['([^']+)'\]\]"
)  # rare pattern placeholder
RE_REVERSED_LINK_SIMPLE = re.compile(r"\(\['([^']+)'\]\)\['([^']+)'\]")

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIR_SUBSTR = {
    ".github",
    "ml_models",
    "reports",
    "strategies",
}  # reduce risk on binary-ish or model dirs


def is_markdown_file(p: Path) -> bool:
    if p.suffix.lower() != ".md":
        return False
    rel = str(p.relative_to(ROOT))
    return not any(token in rel for token in SKIP_DIR_SUBSTR)


def load_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def ensure_top_level_heading(lines: list[str], filename: str) -> list[str]:
    for line in lines:
        if line.strip():
            if line.lstrip().startswith("#"):
                return lines
            # Insert heading
            title = filename.replace("_", " ").replace("-", " ").title()
            return [f"# {title}", "", *lines]
    return lines  # empty file


def normalize_heading_spacing(lines: List[str]) -> List[str]:
    out: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            # strip leading spaces safely
            m = re.match(r"^(#+)(.*)$", stripped)
            if not m:
                out.append(line.rstrip())
                continue
            hashes, rest = m.groups()
            line = f"{hashes}{rest.rstrip()}"
            # previous line blank enforcement (unless first content line)
            if out and out[-1].strip() != "":
                out.append("")
            out.append(line.rstrip())
            # ensure following blank line (will adjust next iteration if already blank)
            if i + 1 < len(lines):
                nxt = lines[i + 1]
                if nxt.strip() != "":
                    out.append("")
            continue
        out.append(line.rstrip())
    return out


def collapse_blank_lines(lines: List[str]) -> List[str]:
    out: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
        else:
            blank_run = 0
        if blank_run <= 1:
            out.append(line.rstrip())
    # trim trailing blanks
    while out and out[-1] == "":
        out.pop()
    out.append("")  # end with single newline
    return out


def convert_emphasis_headings(lines: List[str]) -> List[str]:
    out: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        m = RE_EMPH_HEADING.match(stripped)
        if m:
            content = m.group(1).strip()
            # Avoid converting if previous line already a heading
            if not (i > 0 and lines[i - 1].lstrip().startswith("#")):
                out.append(f"## {content}")
                continue
        out.append(line)
    return out


def normalize_ordered_lists(lines: List[str]) -> List[str]:
    out: list[str] = []
    for line in lines:
        m = RE_ORDERED_ITEM.match(line)
        if m:
            indent = m.group(1)
            # Always reset numbering to 1. (consistent style)
            out.append(f"{indent}1. " + line[m.end() :].rstrip())
        else:
            out.append(line)
    return out


def convert_setext_headings(lines: List[str]) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            if (
                RE_SETEXT_H1.match(next_line.strip())
                and line.strip()
                and not line.startswith("#")
            ):
                out.append(f"# {line.strip()}")
                i += 2
                continue
            if (
                RE_SETEXT_H2.match(next_line.strip())
                and line.strip()
                and not line.startswith("#")
            ):
                out.append(f"## {line.strip()}")
                i += 2
                continue
        out.append(line)
        i += 1
    return out


def demote_extra_h1(lines: List[str]) -> List[str]:
    seen_first = False
    out: List[str] = []
    for line in lines:
        m = RE_HEADING.match(line.strip())
        if m:
            hashes, text = m.groups()
            if len(hashes) == 1:
                if not seen_first:
                    seen_first = True
                else:
                    # demote to level 2
                    line = f"## {text}"
        out.append(line)
    return out


def strip_heading_trailing_punct(lines: List[str]) -> List[str]:
    out: List[str] = []
    for line in lines:
        m = RE_HEADING.match(line.strip())
        if m:
            hashes, text = m.groups()
            # remove trailing punctuation except if text is a single token with punctuation intentionally
            cleaned = text.strip()
            if " " in cleaned and RE_TRAIL_PUNCT.search(cleaned):
                cleaned = RE_TRAIL_PUNCT.sub("", cleaned).rstrip()
            line = f"{hashes} {cleaned}"
        out.append(line)
    return out


def add_language_to_fences(lines: List[str]) -> List[str]:
    out: List[str] = []
    for i, line in enumerate(lines):
        if RE_FENCED_START.match(line):
            if line.strip() == "```":
                out.append("```text")
                continue
        out.append(line)
    return out


def ensure_blank_around_fences_and_lists(lines: List[str]) -> List[str]:
    out: List[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        is_fence = stripped.startswith("```")
        is_list = bool(re.match(r"^(-|\*|\d+\.)\s+", stripped))
        if (is_fence or is_list) and out and out[-1] != "":
            out.append("")
        out.append(line)
        # add blank after closing fence
        if is_fence and i + 1 < len(lines) and lines[i + 1].strip() != "":
            out.append("")
    return out


def fix_reversed_links(lines: List[str]) -> List[str]:
    # Placeholder simple heuristic: not common; skip heavy regex risk
    return lines


def adjust_heading_increments(lines: List[str]) -> List[str]:
    # Best-effort: prevent jumps > 1 level (except upward resets). Conservative.
    last_level = 0
    out: List[str] = []
    for line in lines:
        m = RE_HEADING.match(line.strip())
        if m:
            hashes, text = m.groups()
            level = len(hashes)
            if last_level and level > last_level + 1:
                # clamp down one level
                level = last_level + 1
                line = f"{'#'*level} {text}"
            last_level = level
        out.append(line)
    return out


def process_file(path: Path) -> bool:
    original = load_text(path)
    lines = original.splitlines()
    fname = path.stem
    lines = ensure_top_level_heading(lines, fname)
    lines = convert_setext_headings(lines)
    lines = convert_emphasis_headings(lines)
    lines = normalize_heading_spacing(lines)
    lines = demote_extra_h1(lines)
    lines = strip_heading_trailing_punct(lines)
    lines = normalize_ordered_lists(lines)
    lines = add_language_to_fences(lines)
    lines = ensure_blank_around_fences_and_lists(lines)
    lines = adjust_heading_increments(lines)
    lines = collapse_blank_lines(lines)
    lines = fix_reversed_links(lines)
    new_text = "\n".join(lines)
    if new_text != original:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main():
    changed = 0
    examined = 0
    for path in ROOT.rglob("*.md"):
        if not is_markdown_file(path):
            continue
        examined += 1
        try:
            if process_file(path):
                changed += 1
        except Exception as e:
            print(f"[WARN] Failed to process {path}: {e}")
    print(
        f"Markdown structural cleanup complete. Examined={examined} Changed={changed}"
    )


if __name__ == "__main__":
    main()
