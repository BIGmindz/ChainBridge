#!/usr/bin/env python3
from __future__ import annotations
"""RSI Threshold Consistency Validator (canonical BUY=35 SELL=64)

Authoritative cleaned implementation replacing prior corrupted mixed content.

Rules:
  * Canonical thresholds are fixed constants (35, 64)
  * Scan .py/.yaml/.yml files only
  * Only flag integer literals 10–90 that appear near RSI context
  * Ignore fractional values (0.x) used by unrelated modules
  * Skip excluded directories (.venv, backups, experiments, regime, strategy, notebooks, .git, etc.)
  * Do not self-flag this script
  * Exit non-zero if divergences unless --warn-only supplied
"""

import argparse
import os
import re
import sys
from typing import List

CANON_BUY = 35
CANON_SELL = 64
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
THIS_FILE = os.path.basename(__file__)

EXCLUDE_SUBSTRINGS = [
    '.venv', '__pycache__', '.git', 'archive', 'backup', '.bak', '.old', '.orig',
    'experimental', 'experiments', 'legacy', 'regime', 'strategy', 'notebooks', 'docs/generated'
]

PY_PATTERNS = [
    re.compile(r"buy_threshold\s*[:=]\s*(\d+)(?:\.0)?"),
    re.compile(r"sell_threshold\s*[:=]\s*(\d+)(?:\.0)?"),
    re.compile(r"\.get\(\s*['\"]buy_threshold['\"]\s*,\s*(\d+)\s*\)"),
    re.compile(r"\.get\(\s*['\"]sell_threshold['\"]\s*,\s*(\d+)\s*\)"),
]
YAML_PATTERNS = [
    re.compile(r"buy_threshold:\s*(\d+)(?:\.0)?"),
    re.compile(r"sell_threshold:\s*(\d+)(?:\.0)?"),
]

OVERRIDE_MARKER = "RSI_OVERRIDE_JUSTIFIED"

CONTEXT_WINDOW = 60

def plausible_rsi(val: int) -> bool:
    return 10 <= val <= 90

def is_excluded(rel: str) -> bool:
    lo = rel.lower()
    return any(s in lo for s in EXCLUDE_SUBSTRINGS)

def scan_file(path: str) -> List[str]:
    rel = os.path.relpath(path, REPO_ROOT)
    if is_excluded(rel):
        return []
    if os.path.basename(path) == THIS_FILE:
        return []
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    except Exception as e:
        return [f"{rel}: ERROR reading file: {e}"]

    pats = PY_PATTERNS if path.endswith('.py') else YAML_PATTERNS if path.endswith(('.yaml', '.yml')) else []
    if not pats:
        return []

    lower_text = text.lower()
    issues: List[str] = []
    for pat in pats:
        for m in pat.finditer(text):
            # Skip if override marker appears on the same line
            line_start = text.rfind('\n', 0, m.start()) + 1
            line_end = text.find('\n', m.end())
            if line_end == -1:
                line_end = len(text)
            line = text[line_start:line_end]
            if OVERRIDE_MARKER in line:
                continue
            try:
                val = int(m.group(1))
            except Exception:
                continue
            if not plausible_rsi(val):
                continue
            if val in (CANON_BUY, CANON_SELL):
                continue
            snippet = lower_text[max(0, m.start()-CONTEXT_WINDOW):m.end()+CONTEXT_WINDOW]
            if 'rsi' in snippet:
                issues.append(f"{rel}: RSI threshold {val} != canonical {CANON_BUY}/{CANON_SELL}")
    return issues

def collect_divergences() -> List[str]:
    divergences: List[str] = []
    for root, _, files in os.walk(REPO_ROOT):
        for fname in files:
            if not fname.endswith(('.py', '.yaml', '.yml')):
                continue
            full = os.path.join(root, fname)
            divergences.extend(scan_file(full))
    return divergences

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--warn-only', action='store_true', help='Do not exit non-zero on divergences')
    args = parser.parse_args()

    print(f"Canonical RSI thresholds (fixed) BUY={CANON_BUY} SELL={CANON_SELL}")
    divergences = collect_divergences()
    if divergences:
        print('\nDivergences detected:')
        for d in sorted(divergences):
            print(' -', d)
        if args.warn_only:
            print('\nWARN-ONLY: Divergences present')
            return 0
        print('\nFAIL: Non-canonical RSI thresholds present (update or justify).')
        return 1
    print('\nPASS: All RSI thresholds match canonical values.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
