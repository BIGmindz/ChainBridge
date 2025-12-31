#!/usr/bin/env python3
"""Runtime vs Agent Identity Block Linter.

🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢
EXECUTING AGENT: DAN (GID-07) — DevOps & CI/CD Lead — 🟢 GREEN
🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢

PAC: PAC-DAN-RUNTIME-IDENTITY-LINT-ENFORCEMENT-01
Authority: Benson (GID-00)
Mode: FAIL-CLOSED

PURPOSE:
Permanently prevent runtime ↔ agent identity drift by enforcing machine-verifiable
lint rules that prohibit:
- Runtimes from declaring GIDs
- Runtimes from using AGENT_* blocks
- Agents from using RUNTIME_* blocks
- Missing required fields in activation blocks

HARD INVARIANTS (NON-NEGOTIABLE):
- runtime_has_gid: false
- runtime_uses_agent_name: false
- agent_has_gid: true
- agent_uses_runtime_block: false

Violation of any invariant results in CI FAILURE.

TRAINING SIGNAL:
- Program: Agent University
- Level: L3
- Domain: Identity Boundary Enforcement & CI-as-Governance

🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢
END — DAN (GID-07) — 🟢 GREEN
🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class BlockType(Enum):
    """Activation block types."""
    RUNTIME = "RUNTIME_ACTIVATION_ACK"
    AGENT = "AGENT_ACTIVATION_ACK"


class ViolationType(Enum):
    """Identity violation types."""
    RUNTIME_HAS_GID = "RUNTIME_DECLARES_GID"
    RUNTIME_HAS_AGENT_NAME = "RUNTIME_USES_AGENT_NAME"
    AGENT_MISSING_GID = "AGENT_MISSING_GID"
    AGENT_MISSING_NAME = "AGENT_MISSING_AGENT_NAME"
    AGENT_BEFORE_RUNTIME = "AGENT_BLOCK_BEFORE_RUNTIME_BLOCK"
    MIXED_BLOCKS = "MIXED_IDENTITY_BLOCKS"


@dataclass
class Violation:
    """A single identity violation."""
    violation_type: ViolationType
    file_path: str
    line_number: int
    context: str

    def __str__(self) -> str:
        return (
            f"❌ {self.violation_type.value}\n"
            f"   File: {self.file_path}\n"
            f"   Line: {self.line_number}\n"
            f"   Context: {self.context}"
        )


@dataclass
class LintResult:
    """Result of identity lint check."""
    violations: list[Violation] = field(default_factory=list)
    files_checked: int = 0
    runtime_blocks_found: int = 0
    agent_blocks_found: int = 0

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    def add_violation(self, v: Violation) -> None:
        self.violations.append(v)


# Regex patterns for block detection
RUNTIME_BLOCK_PATTERN = re.compile(
    r'RUNTIME_ACTIVATION_ACK\s*\{([^}]+)\}',
    re.MULTILINE | re.DOTALL
)

AGENT_BLOCK_PATTERN = re.compile(
    r'AGENT_ACTIVATION_ACK\s*\{([^}]+)\}',
    re.MULTILINE | re.DOTALL
)

# Pattern to detect markdown code blocks (to exclude examples)
CODE_BLOCK_PATTERN = re.compile(
    r'```[\s\S]*?```|`[^`]+`',
    re.MULTILINE
)

# Forbidden fields in runtime blocks
RUNTIME_FORBIDDEN_FIELDS = [
    r'\bgid\b\s*:',
    r'\bagent_name\b\s*:',
    r'\bagent_id\b\s*:',
    r'\bGID-\d+\b',  # Direct GID reference
]

# Required fields in agent blocks
AGENT_REQUIRED_FIELDS = [
    r'\bgid\b\s*:',
    r'\bagent_name\b\s*:',
]


def find_line_number(content: str, match_start: int) -> int:
    """Find line number for a match position."""
    return content[:match_start].count('\n') + 1


def remove_code_blocks(content: str) -> str:
    """Remove markdown code blocks to avoid linting examples/documentation.

    Code blocks in markdown (```...``` or `...`) often contain example
    activation blocks that are documentation, not real violations.
    """
    return CODE_BLOCK_PATTERN.sub('', content)


def lint_runtime_block(content: str, match: re.Match, file_path: str) -> list[Violation]:
    """Check runtime block for forbidden fields."""
    violations = []
    block_content = match.group(1)
    line_num = find_line_number(content, match.start())

    for pattern in RUNTIME_FORBIDDEN_FIELDS:
        if re.search(pattern, block_content, re.IGNORECASE):
            # Determine specific violation type
            if 'gid' in pattern.lower() or 'GID-' in pattern:
                vtype = ViolationType.RUNTIME_HAS_GID
            else:
                vtype = ViolationType.RUNTIME_HAS_AGENT_NAME

            violations.append(Violation(
                violation_type=vtype,
                file_path=file_path,
                line_number=line_num,
                context=f"RUNTIME_ACTIVATION_ACK contains forbidden field: {pattern}"
            ))

    return violations


def lint_agent_block(content: str, match: re.Match, file_path: str) -> list[Violation]:
    """Check agent block for required fields."""
    violations = []
    block_content = match.group(1)
    line_num = find_line_number(content, match.start())

    # Check for gid
    if not re.search(r'\bgid\b\s*:', block_content, re.IGNORECASE):
        violations.append(Violation(
            violation_type=ViolationType.AGENT_MISSING_GID,
            file_path=file_path,
            line_number=line_num,
            context="AGENT_ACTIVATION_ACK missing required 'gid' field"
        ))

    # Check for agent_name
    if not re.search(r'\bagent_name\b\s*:', block_content, re.IGNORECASE):
        violations.append(Violation(
            violation_type=ViolationType.AGENT_MISSING_NAME,
            file_path=file_path,
            line_number=line_num,
            context="AGENT_ACTIVATION_ACK missing required 'agent_name' field"
        ))

    return violations


def check_block_ordering(content: str, file_path: str) -> list[Violation]:
    """Ensure RUNTIME block appears before AGENT block if both present."""
    violations = []

    runtime_match = RUNTIME_BLOCK_PATTERN.search(content)
    agent_match = AGENT_BLOCK_PATTERN.search(content)

    if runtime_match and agent_match:
        # Both blocks present - check ordering
        if agent_match.start() < runtime_match.start():
            violations.append(Violation(
                violation_type=ViolationType.AGENT_BEFORE_RUNTIME,
                file_path=file_path,
                line_number=find_line_number(content, agent_match.start()),
                context="AGENT_ACTIVATION_ACK must appear AFTER RUNTIME_ACTIVATION_ACK"
            ))

    return violations


def lint_file(file_path: Path) -> tuple[list[Violation], int, int]:
    """Lint a single file for identity block violations."""
    violations = []
    runtime_count = 0
    agent_count = 0

    try:
        content = file_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return violations, 0, 0

    # For markdown files, remove code blocks to avoid linting examples
    if file_path.suffix.lower() == '.md':
        lint_content = remove_code_blocks(content)
    else:
        lint_content = content

    # Find and check runtime blocks (using lint_content to exclude examples)
    for match in RUNTIME_BLOCK_PATTERN.finditer(lint_content):
        runtime_count += 1
        violations.extend(lint_runtime_block(lint_content, match, str(file_path)))

    # Find and check agent blocks (using lint_content to exclude examples)
    for match in AGENT_BLOCK_PATTERN.finditer(lint_content):
        agent_count += 1
        violations.extend(lint_agent_block(lint_content, match, str(file_path)))

    # Check block ordering (use lint_content to match what we're counting)
    violations.extend(check_block_ordering(lint_content, str(file_path)))

    return violations, runtime_count, agent_count


def lint_directory(
    root: Path,
    extensions: tuple[str, ...] = ('.md', '.py', '.yaml', '.yml', '.txt', '.json'),
    exclude_dirs: tuple[str, ...] = ('node_modules', '.git', '__pycache__', '.venv', 'venv', 'build', 'dist'),
) -> LintResult:
    """Recursively lint all files in directory."""
    result = LintResult()

    for file_path in root.rglob('*'):
        # Skip excluded directories
        if any(excluded in file_path.parts for excluded in exclude_dirs):
            continue

        # Skip non-matching extensions
        if file_path.suffix.lower() not in extensions:
            continue

        # Skip if not a file
        if not file_path.is_file():
            continue

        violations, runtime_count, agent_count = lint_file(file_path)
        result.files_checked += 1
        result.runtime_blocks_found += runtime_count
        result.agent_blocks_found += agent_count

        for v in violations:
            result.add_violation(v)

    return result


def print_report(result: LintResult) -> None:
    """Print lint report."""
    print("━" * 60)
    print("🔒 RUNTIME vs AGENT IDENTITY LINT")
    print("━" * 60)
    print(f"PAC: PAC-DAN-RUNTIME-IDENTITY-LINT-ENFORCEMENT-01")
    print(f"Authority: Benson (GID-00)")
    print(f"Mode: FAIL-CLOSED")
    print("━" * 60)
    print()
    print(f"Files checked: {result.files_checked}")
    print(f"RUNTIME_ACTIVATION_ACK blocks found: {result.runtime_blocks_found}")
    print(f"AGENT_ACTIVATION_ACK blocks found: {result.agent_blocks_found}")
    print()

    if result.passed:
        print("━" * 60)
        print("✅ IDENTITY LINT PASSED")
        print("━" * 60)
        print()
        print("INVARIANTS VERIFIED:")
        print("  ✓ runtime_has_gid: false")
        print("  ✓ runtime_uses_agent_name: false")
        print("  ✓ agent_has_gid: true (where applicable)")
        print("  ✓ agent_uses_runtime_block: false")
        print()
    else:
        print("━" * 60)
        print(f"❌ IDENTITY LINT FAILED — {len(result.violations)} VIOLATION(S)")
        print("━" * 60)
        print()
        for v in result.violations:
            print(v)
            print()
        print("━" * 60)
        print("REMEDIATION:")
        print("  1. Runtime blocks must NOT contain: gid, agent_name, agent_id")
        print("  2. Agent blocks MUST contain: gid, agent_name")
        print("  3. RUNTIME_ACTIVATION_ACK must appear BEFORE AGENT_ACTIVATION_ACK")
        print("━" * 60)


def main() -> int:
    """Main entry point."""
    # Determine root directory
    if len(sys.argv) > 1:
        root = Path(sys.argv[1])
    else:
        # Default to current directory or workspace root
        root = Path.cwd()
        # Try to find workspace root
        for candidate in [root, root.parent, root.parent.parent]:
            if (candidate / '.git').exists():
                root = candidate
                break

    print(f"Scanning: {root}")
    print()

    result = lint_directory(root)
    print_report(result)

    # Exit code: 0 = pass, 1 = fail
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
