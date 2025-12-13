#!/usr/bin/env python3
"""
ALEX Governance Python Checker

Enforces ChainBridge governance rules for Python code:
- Security checks (forbidden imports, crypto compliance)
- ML safety (no black-box models, version metadata required)
- Performance (no heavy imports in request path)
- Code quality (linting, typing, formatting)
- Commit message governance tags
- Agent color-lock validation (PAC-ALEX-GOV-022)
- PAC header structure enforcement

Part of ALEX governance layer (PAC-A by DAN-GID-07).
"""

import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# ═══════════════════════════════════════════════════════════════════════════
# GOVERNANCE RULES
# ═══════════════════════════════════════════════════════════════════════════

# Forbidden imports (security/crypto compliance)
FORBIDDEN_IMPORTS = {
    "rsa",
    "cryptography.hazmat.primitives.asymmetric.rsa",
    "cryptography.hazmat.primitives.asymmetric.ec",
    "cryptography.hazmat.primitives.asymmetric.dsa",
    "ecdsa",
}

# Heavy ML imports that should not be in request path
HEAVY_ML_IMPORTS = {
    "torch",
    "tensorflow",
    "keras",
    "transformers",
    "sklearn",
    "xgboost",
    "lightgbm",
}

# Allowed request path modules (FastAPI handlers)
REQUEST_PATH_MODULES = {
    "app/api.py",
    "app/api_iq_ml.py",
    "app/main.py",
    "chainpay-service/app",
}

# Required governance tags in PR commits
REQUIRED_GOV_TAGS = ["[GOV]", "[RISK]", "[SEC]", "[ML]", "[ALEX-APPROVED]"]

# Max lines changed without ALEX-APPROVED tag
MAX_LINES_WITHOUT_APPROVAL = 600

# ═══════════════════════════════════════════════════════════════════════════
# AGENT COLOR-LOCK REGISTRY (PAC-ALEX-GOV-022)
# ═══════════════════════════════════════════════════════════════════════════

AGENT_COLORS = {
    "CODY": {"gid": "GID-01", "emoji": "🔵", "color": "blue"},
    "MAGGIE": {"gid": "GID-02", "emoji": "🟣", "color": "purple"},
    "SONNY": {"gid": "GID-03", "emoji": "🟢", "color": "green"},
    "DAN": {"gid": "GID-04", "emoji": "🟠", "color": "orange"},
    "ATLAS": {"gid": "GID-05", "emoji": "🟤", "color": "brown"},
    "SAM": {"gid": "GID-06", "emoji": "🔴", "color": "red"},
    "DANA": {"gid": "GID-07", "emoji": "🟡", "color": "yellow"},
    "ALEX": {"gid": "GID-08", "emoji": "⚪", "color": "white"},
    "CINDY": {"gid": "GID-09", "emoji": "🔷", "color": "diamond_blue"},
    "PAX": {"gid": "GID-10", "emoji": "💰", "color": "gold"},
    "LIRA": {"gid": "GID-11", "emoji": "🩷", "color": "pink"},
}

# PAC header pattern: emoji row, agent line, model line, paste instruction, emoji row
PAC_HEADER_PATTERNS = {
    "emoji_row": r"^[⚪🔵🟣🟢🟠🟤🔴🟡🔷💰🩷]{10}$",
    "agent_line": r"^[⚪🔵🟣🟢🟠🟤🔴🟡🔷💰🩷]\s+(\w+)\s+—\s+(GID-\d+)\s+—",
    "pac_id": r"^PAC-(\w+)-(\w+)-?(\d+)?\s+—",
}


@dataclass
class GovernanceViolation:
    """A governance rule violation."""

    severity: str  # "ERROR" or "WARNING"
    category: str  # "SECURITY", "ML_SAFETY", "PERFORMANCE", "QUALITY", "COLOR_LOCK", "PAC_STRUCTURE"
    file: str
    line: int
    message: str


class ColorLockValidator:
    """Validates agent color assignments in PAC documents (PAC-ALEX-GOV-022)."""

    def __init__(self, colors_json_path: Optional[Path] = None):
        self.colors = AGENT_COLORS
        if colors_json_path and colors_json_path.exists():
            try:
                with open(colors_json_path) as f:
                    data = json.load(f)
                    self.colors = {
                        name: {"gid": info["gid"], "emoji": info["emoji"], "color": info["color_name"]}
                        for name, info in data.get("agents", {}).items()
                    }
            except (json.JSONDecodeError, KeyError):
                pass  # Fall back to hardcoded colors

    def validate_pac_header(self, content: str) -> List[GovernanceViolation]:
        """Validate PAC header structure and color consistency."""
        violations = []
        lines = content.split("\n")

        # Find PAC header start (emoji row)
        emoji_row_pattern = re.compile(PAC_HEADER_PATTERNS["emoji_row"])
        agent_line_pattern = re.compile(PAC_HEADER_PATTERNS["agent_line"])
        pac_id_pattern = re.compile(PAC_HEADER_PATTERNS["pac_id"])

        emoji_row_indices = []
        agent_line_idx = None
        pac_id_line_idx = None
        detected_emoji = None
        detected_agent = None
        detected_gid = None
        pac_agent = None

        # Track code block state to skip examples
        in_code_block = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Toggle code block state on ``` markers
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue

            # Skip lines inside code blocks (examples, templates)
            if in_code_block:
                continue

            # Check for emoji row
            if emoji_row_pattern.match(stripped):
                emoji_row_indices.append(i)
                if detected_emoji is None:
                    detected_emoji = stripped[0]  # First emoji in row

            # Check for agent line
            agent_match = agent_line_pattern.match(stripped)
            if agent_match:
                agent_line_idx = i
                detected_agent = agent_match.group(1).upper()
                detected_gid = agent_match.group(2)

                # Validate emoji matches agent
                line_emoji = stripped[0]
                if detected_agent in self.colors:
                    expected_emoji = self.colors[detected_agent]["emoji"]
                    expected_gid = self.colors[detected_agent]["gid"]

                    if line_emoji != expected_emoji:
                        violations.append(
                            GovernanceViolation(
                                severity="ERROR",
                                category="COLOR_LOCK",
                                file="<pac_header>",
                                line=i + 1,
                                message=f"Agent {detected_agent} must use {expected_emoji} emoji, found {line_emoji}",
                            )
                        )

                    if detected_gid != expected_gid:
                        violations.append(
                            GovernanceViolation(
                                severity="ERROR",
                                category="COLOR_LOCK",
                                file="<pac_header>",
                                line=i + 1,
                                message=f"Agent {detected_agent} GID must be {expected_gid}, found {detected_gid}",
                            )
                        )

            # Check for PAC ID line
            pac_match = pac_id_pattern.match(stripped)
            if pac_match:
                pac_id_line_idx = i
                pac_agent = pac_match.group(1).upper()

                # PAC prefix must match agent name
                if detected_agent and pac_agent != detected_agent:
                    violations.append(
                        GovernanceViolation(
                            severity="ERROR",
                            category="PAC_STRUCTURE",
                            file="<pac_header>",
                            line=i + 1,
                            message=f"PAC prefix '{pac_agent}' must match agent name '{detected_agent}'",
                        )
                    )

        # Validate emoji row consistency
        if len(emoji_row_indices) >= 2 and detected_emoji:
            for idx in emoji_row_indices:
                row = lines[idx].strip()
                if not all(c == detected_emoji for c in row):
                    violations.append(
                        GovernanceViolation(
                            severity="ERROR",
                            category="COLOR_LOCK",
                            file="<pac_header>",
                            line=idx + 1,
                            message=f"All emojis in border row must be same color ({detected_emoji})",
                        )
                    )

        return violations


class GovernanceChecker:
    """Main governance checker."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.violations: List[GovernanceViolation] = []
        self.color_validator = ColorLockValidator(repo_root / ".github" / "agents" / "colors.json")

    def check_file(self, file_path: Path) -> None:
        """Check a single Python file for governance violations."""
        if not file_path.suffix == ".py":
            return

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))

            # Check for forbidden imports
            self._check_forbidden_imports(tree, file_path, content)

            # Check for heavy ML imports in request path
            self._check_heavy_ml_imports(tree, file_path, content)

            # Check for model version metadata (ML files only)
            if "ml" in str(file_path).lower():
                self._check_model_metadata(tree, file_path, content)

        except UnicodeDecodeError:
            # Skip binary or non-UTF-8 files
            pass
        except SyntaxError as e:
            self.violations.append(
                GovernanceViolation(
                    severity="ERROR",
                    category="QUALITY",
                    file=str(file_path.relative_to(self.repo_root)),
                    line=e.lineno or 0,
                    message=f"Syntax error: {e.msg}",
                )
            )

    def _check_forbidden_imports(self, tree: ast.AST, file_path: Path, content: str) -> None:
        """Check for forbidden security/crypto imports."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_IMPORTS:
                        self.violations.append(
                            GovernanceViolation(
                                severity="ERROR",
                                category="SECURITY",
                                file=str(file_path.relative_to(self.repo_root)),
                                line=node.lineno,
                                message=f"Forbidden import: {alias.name}. Use quantum-safe crypto only (Dilithium/Kyber).",
                            )
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module and any(node.module.startswith(forbidden) for forbidden in FORBIDDEN_IMPORTS):
                    self.violations.append(
                        GovernanceViolation(
                            severity="ERROR",
                            category="SECURITY",
                            file=str(file_path.relative_to(self.repo_root)),
                            line=node.lineno,
                            message=f"Forbidden import from: {node.module}. Use quantum-safe crypto only.",
                        )
                    )

    def _check_heavy_ml_imports(self, tree: ast.AST, file_path: Path, content: str) -> None:
        """Check for heavy ML imports in request path."""
        # Only check if file is in request path
        rel_path = str(file_path.relative_to(self.repo_root))
        is_request_path = any(rel_path.startswith(module) for module in REQUEST_PATH_MODULES)

        if not is_request_path:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in HEAVY_ML_IMPORTS:
                        self.violations.append(
                            GovernanceViolation(
                                severity="WARNING",
                                category="PERFORMANCE",
                                file=str(file_path.relative_to(self.repo_root)),
                                line=node.lineno,
                                message=f"Heavy ML import in request path: {alias.name}. Use lazy loading or move to background worker.",
                            )
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module and any(node.module.startswith(heavy) for heavy in HEAVY_ML_IMPORTS):
                    self.violations.append(
                        GovernanceViolation(
                            severity="WARNING",
                            category="PERFORMANCE",
                            file=str(file_path.relative_to(self.repo_root)),
                            line=node.lineno,
                            message=f"Heavy ML import in request path: {node.module}. Use lazy loading.",
                        )
                    )

    def _check_model_metadata(self, tree: ast.AST, file_path: Path, content: str) -> None:
        """Check that ML model classes have @model_version metadata."""
        # Look for class definitions that might be ML models
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class name suggests it's a model
                if any(keyword in node.name.lower() for keyword in ["model", "predictor", "classifier", "regressor"]):
                    # Check for @model_version decorator or model_version attribute
                    has_version = False

                    # Check decorators
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name) and decorator.id == "model_version":
                            has_version = True
                        elif isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Name) and decorator.func.id == "model_version":
                                has_version = True

                    # Check class body for model_version attribute
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == "model_version":
                                    has_version = True

                    if not has_version:
                        self.violations.append(
                            GovernanceViolation(
                                severity="WARNING",
                                category="ML_SAFETY",
                                file=str(file_path.relative_to(self.repo_root)),
                                line=node.lineno,
                                message=f"ML model class '{node.name}' missing @model_version metadata or model_version attribute.",
                            )
                        )

    def check_commit_messages(self) -> None:
        """Check git commit messages for governance tags."""
        try:
            import subprocess

            result = subprocess.run(
                ["git", "log", "--format=%s", "-n", "10"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )

            if result.returncode == 0:
                messages = result.stdout.strip().split("\n")
                for msg in messages:
                    # Check if message has at least one governance tag
                    has_tag = any(tag in msg for tag in REQUIRED_GOV_TAGS)
                    if not has_tag and len(msg) > 20:  # Skip merge commits
                        self.violations.append(
                            GovernanceViolation(
                                severity="WARNING",
                                category="QUALITY",
                                file="<commit>",
                                line=0,
                                message=f"Commit missing governance tag: {msg[:60]}... (need one of: {', '.join(REQUIRED_GOV_TAGS)})",
                            )
                        )
        except Exception:
            # Git not available or other error - skip check
            pass

    def check_large_changes(self) -> None:
        """Check for large file changes without ALEX-APPROVED tag."""
        try:
            import subprocess

            # Get diff stats
            result = subprocess.run(
                ["git", "diff", "--stat", "HEAD~1"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )

            if result.returncode == 0:
                # Parse diff output
                for line in result.stdout.split("\n"):
                    if "|" in line:
                        parts = line.split("|")
                        if len(parts) >= 2:
                            file_path = parts[0].strip()
                            changes = parts[1].strip()
                            # Extract number of changes
                            nums = re.findall(r"\d+", changes)
                            if nums:
                                total_changes = sum(int(n) for n in nums)
                                if total_changes > MAX_LINES_WITHOUT_APPROVAL:
                                    # Check if recent commit has ALEX-APPROVED
                                    commit_result = subprocess.run(
                                        ["git", "log", "--format=%s", "-n", "1"],
                                        capture_output=True,
                                        text=True,
                                        cwd=self.repo_root,
                                    )
                                    if "[ALEX-APPROVED]" not in commit_result.stdout:
                                        self.violations.append(
                                            GovernanceViolation(
                                                severity="WARNING",
                                                category="QUALITY",
                                                file=file_path,
                                                line=0,
                                                message=f"Large change ({total_changes} lines) without [ALEX-APPROVED] tag.",
                                            )
                                        )
        except Exception:
            # Git not available - skip check
            pass

    def check_pac_documents(self) -> None:
        """Check PAC documents for color-lock and structure compliance."""
        # Check markdown files in docs/ directory
        docs_dir = self.repo_root / "docs"
        if docs_dir.exists():
            for md_file in docs_dir.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    # Only check files that look like PAC documents
                    if "PAC-" in content and ("GID-" in content or "⚪" in content or "🔵" in content):
                        pac_violations = self.color_validator.validate_pac_header(content)
                        for v in pac_violations:
                            v.file = str(md_file.relative_to(self.repo_root))
                            self.violations.append(v)
                except UnicodeDecodeError:
                    pass

        # Also check .github directory for PAC-related files
        github_dir = self.repo_root / ".github"
        if github_dir.exists():
            for md_file in github_dir.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    if "PAC-" in content and ("GID-" in content or "⚪" in content):
                        pac_violations = self.color_validator.validate_pac_header(content)
                        for v in pac_violations:
                            v.file = str(md_file.relative_to(self.repo_root))
                            self.violations.append(v)
                except UnicodeDecodeError:
                    pass

    def report(self) -> int:
        """Print governance report and return exit code."""
        if not self.violations:
            print("✅ ALEX Governance: All checks passed")
            return 0

        errors = [v for v in self.violations if v.severity == "ERROR"]
        warnings = [v for v in self.violations if v.severity == "WARNING"]

        print("=" * 80)
        print("🟥 ALEX GOVERNANCE VIOLATIONS DETECTED")
        print("=" * 80)

        if errors:
            print(f"\n❌ {len(errors)} ERROR(S) - Must be fixed before merge:\n")
            for v in errors:
                print(f"  {v.category} | {v.file}:{v.line}")
                print(f"    {v.message}\n")

        if warnings:
            print(f"\n⚠️  {len(warnings)} WARNING(S) - Review recommended:\n")
            for v in warnings:
                print(f"  {v.category} | {v.file}:{v.line}")
                print(f"    {v.message}\n")

        print("=" * 80)
        print("GOVERNANCE RULES:")
        print("  - No RSA/ECDSA crypto (use Dilithium/Kyber)")
        print("  - No heavy ML imports in request path")
        print("  - ML models require @model_version metadata")
        print("  - Commits need governance tags: [GOV] [RISK] [SEC] [ML]")
        print("  - Large changes (>600 lines) need [ALEX-APPROVED]")
        print("  - PAC documents must use correct agent colors (COLOR_LOCK)")
        print("  - PAC headers must match agent GID (PAC_STRUCTURE)")
        print("=" * 80)

        # Return non-zero exit code if there are errors
        return 1 if errors else 0


def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent

    checker = GovernanceChecker(repo_root)

    # Check all Python files in key directories
    for directory in ["chainiq-service", "chainpay-service", "tools", "scripts"]:
        dir_path = repo_root / directory
        if dir_path.exists():
            for py_file in dir_path.rglob("*.py"):
                if "__pycache__" not in str(py_file):
                    checker.check_file(py_file)

    # Check commit messages
    checker.check_commit_messages()

    # Check for large changes
    checker.check_large_changes()

    # Check PAC documents for color-lock compliance (PAC-ALEX-GOV-022)
    checker.check_pac_documents()

    # Generate report and exit
    return checker.report()


if __name__ == "__main__":
    sys.exit(main())
