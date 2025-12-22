"""
ACM Loader — Load and cache Agent Capability Manifests at startup.

This module provides deterministic loading of ACM YAML files with:
- Schema validation
- Version verification
- Governance lock verification
- Read-only in-memory caching
- Hard-fail on any invalid manifest

ALEX (GID-08) is the enforcement authority.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional

import yaml


class ACMLoadError(Exception):
    """Raised when ACM manifests cannot be loaded."""

    pass


class ACMValidationError(Exception):
    """Raised when ACM manifest fails schema validation."""

    pass


@dataclass(frozen=True)
class ACMCapabilities:
    """Immutable capability set for an agent."""

    read: FrozenSet[str] = field(default_factory=frozenset)
    propose: FrozenSet[str] = field(default_factory=frozenset)
    execute: FrozenSet[str] = field(default_factory=frozenset)
    block: FrozenSet[str] = field(default_factory=frozenset)
    escalate: FrozenSet[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ACM:
    """Immutable Agent Capability Manifest (ACM) record."""

    agent_id: str
    gid: str
    role: str
    color: str
    version: str
    constraints: FrozenSet[str]
    capabilities: ACMCapabilities
    escalation_triggers: FrozenSet[str]
    invariants: FrozenSet[str]

    def has_capability(self, verb: str, target: str) -> bool:
        """Check if agent has explicit capability for verb and target.

        Args:
            verb: The capability verb (READ, PROPOSE, EXECUTE, BLOCK, ESCALATE)
            target: The target scope/resource

        Returns:
            True only if explicit permission exists (no inference)
        """
        verb_lower = verb.lower()
        cap_set: FrozenSet[str] = getattr(self.capabilities, verb_lower, frozenset())

        if not cap_set:
            return False

        # Check for exact match or glob pattern match
        for allowed in cap_set:
            if self._matches_scope(target, allowed):
                return True

        return False

    @staticmethod
    def _matches_scope(target: str, allowed: str) -> bool:
        """Match target against allowed scope pattern.

        Matching rules (strict, no inference):
        1. "all" or "all *" patterns grant universal access
        2. Exact match (case-insensitive)
        3. Glob/fnmatch patterns
        4. Single-word target that appears in or contains a word from allowed scope
           (e.g., "pytest" matches "local test runs" because "test" is in "pytest")
        5. Multi-word target must share the domain-prefix word with allowed scope
           (e.g., "backend tests" matches "backend source code" but not "frontend source code")
        """
        allowed_lower = allowed.lower()
        target_lower = target.lower()

        # "all" or "all *" patterns grant universal access for that verb
        if allowed_lower.startswith("all ") or allowed_lower == "all":
            return True

        # Exact match
        if target_lower == allowed_lower:
            return True

        # Glob/fnmatch pattern
        if fnmatch.fnmatch(target_lower, allowed_lower):
            return True

        # Keyword matching with strict domain-prefix rules
        allowed_words = allowed_lower.split()
        target_words = target_lower.split()

        # Common non-distinguishing words
        generic_words = {
            "and",
            "or",
            "the",
            "a",
            "an",
            "for",
            "in",
            "of",
            "to",
            "source",
            "code",
            "changes",
            "updates",
            "modifications",
            "logic",
            "runs",
            "tests",
            "suites",
            "files",
        }

        # Get domain-prefix words (typically first word, domain-specific)
        # e.g., "backend", "frontend", "api", "security", "test"
        def get_domain_words(words: list[str]) -> set[str]:
            domain = set()
            for w in words:
                if w not in generic_words:
                    domain.add(w)
            return domain

        allowed_domain = get_domain_words(allowed_words)
        target_domain = get_domain_words(target_words)

        # Single-word target: check if it appears in or contains any allowed word
        if len(target_words) == 1:
            single_target = target_lower
            for allowed_word in allowed_words:
                # "pytest" contains "test", or "test" is in "pytest"
                if single_target in allowed_word or allowed_word in single_target:
                    return True
            return False

        # Multi-word target: require at least one domain word to match exactly
        # This prevents "frontend source code" from matching "backend source code"
        if allowed_domain & target_domain:
            return True

        return False

    def can_block(self) -> bool:
        """Check if agent has any BLOCK authority."""
        return len(self.capabilities.block) > 0


# Required fields in ACM YAML schema
_REQUIRED_FIELDS = {"agent_id", "gid", "role", "color", "version", "capabilities"}
_REQUIRED_CAPABILITY_VERBS = {"read", "propose", "execute", "block", "escalate"}
_GOVERNANCE_LOCK_MARKER = "END OF ACM — GOVERNANCE LOCKED"


class ACMLoader:
    """Load and cache ACM manifests with strict validation.

    All manifests are loaded at startup and cached as immutable records.
    Any validation failure causes hard startup failure.
    """

    def __init__(self, manifests_dir: str | Path | None = None) -> None:
        """Initialize the ACM loader.

        Args:
            manifests_dir: Path to manifests directory. Defaults to ./manifests
        """
        if manifests_dir is None:
            # Default to manifests/ relative to project root
            manifests_dir = Path(__file__).parent.parent.parent / "manifests"
        self._manifests_dir = Path(manifests_dir)
        self._cache: Dict[str, ACM] = {}
        self._loaded = False

    @property
    def manifests_dir(self) -> Path:
        """Return the manifests directory path."""
        return self._manifests_dir

    def load_all(self) -> Dict[str, ACM]:
        """Load and validate all ACM manifests.

        Returns:
            Dict mapping GID to validated ACM record

        Raises:
            ACMLoadError: If manifests directory doesn't exist or is empty
            ACMValidationError: If any manifest fails validation
        """
        if not self._manifests_dir.exists():
            raise ACMLoadError(f"Manifests directory not found: {self._manifests_dir}")

        manifest_files = list(self._manifests_dir.glob("GID-*.yaml"))

        if not manifest_files:
            raise ACMLoadError(f"No ACM manifests found in {self._manifests_dir}")

        errors: List[str] = []

        for manifest_path in manifest_files:
            try:
                acm = self._load_and_validate(manifest_path)
                self._cache[acm.gid] = acm
            except (ACMValidationError, yaml.YAMLError) as e:
                errors.append(f"{manifest_path.name}: {e}")

        if errors:
            raise ACMValidationError(f"ACM validation failed for {len(errors)} manifest(s):\n" + "\n".join(f"  - {err}" for err in errors))

        self._loaded = True
        return self._cache.copy()

    def get(self, gid: str) -> Optional[ACM]:
        """Get a cached ACM by GID.

        Args:
            gid: The agent GID (e.g., "GID-01")

        Returns:
            The ACM if found, None otherwise
        """
        if not self._loaded:
            self.load_all()
        return self._cache.get(gid)

    def get_all(self) -> Dict[str, ACM]:
        """Get all cached ACMs.

        Returns:
            Dict mapping GID to ACM
        """
        if not self._loaded:
            self.load_all()
        return self._cache.copy()

    def is_loaded(self) -> bool:
        """Check if manifests have been loaded."""
        return self._loaded

    def _load_and_validate(self, path: Path) -> ACM:
        """Load and validate a single ACM manifest.

        Args:
            path: Path to the YAML manifest file

        Returns:
            Validated ACM record

        Raises:
            ACMValidationError: If validation fails
        """
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify governance lock marker
        if _GOVERNANCE_LOCK_MARKER not in content:
            raise ACMValidationError(f"Missing governance lock marker in {path.name}")

        data = yaml.safe_load(content)

        if not isinstance(data, dict):
            raise ACMValidationError(f"Invalid YAML structure in {path.name}")

        # Validate required fields
        missing = _REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise ACMValidationError(f"Missing required fields: {missing}")

        # Validate capabilities structure
        caps = data.get("capabilities", {})
        if not isinstance(caps, dict):
            raise ACMValidationError("capabilities must be a mapping")

        # Validate each capability verb exists (can be empty list)
        for verb in _REQUIRED_CAPABILITY_VERBS:
            if verb not in caps:
                raise ACMValidationError(f"Missing capability verb: {verb}")

        # Validate version format
        version = data.get("version", "")
        if not self._validate_version(version):
            raise ACMValidationError(f"Invalid version format: {version}")

        # Build immutable ACM record
        capabilities = ACMCapabilities(
            read=frozenset(self._normalize_list(caps.get("read"))),
            propose=frozenset(self._normalize_list(caps.get("propose"))),
            execute=frozenset(self._normalize_list(caps.get("execute"))),
            block=frozenset(self._normalize_list(caps.get("block"))),
            escalate=frozenset(self._normalize_list(caps.get("escalate"))),
        )

        return ACM(
            agent_id=str(data["agent_id"]),
            gid=str(data["gid"]),
            role=str(data["role"]),
            color=str(data["color"]),
            version=str(data["version"]),
            constraints=frozenset(self._normalize_list(data.get("constraints"))),
            capabilities=capabilities,
            escalation_triggers=frozenset(self._normalize_list(data.get("escalation_triggers"))),
            invariants=frozenset(self._normalize_list(data.get("invariants"))),
        )

    @staticmethod
    def _normalize_list(value: object) -> List[str]:
        """Normalize a value to a list of strings."""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v) for v in value if v is not None]
        return []

    @staticmethod
    def _validate_version(version: str) -> bool:
        """Validate semantic version format."""
        if not version:
            return False
        parts = version.split(".")
        if len(parts) != 3:
            return False
        return all(part.isdigit() for part in parts)


# Module-level singleton for convenience
_default_loader: Optional[ACMLoader] = None


def get_acm_loader(manifests_dir: str | Path | None = None) -> ACMLoader:
    """Get or create the default ACM loader singleton.

    Args:
        manifests_dir: Optional custom manifests directory

    Returns:
        The ACM loader instance
    """
    global _default_loader
    if _default_loader is None or manifests_dir is not None:
        _default_loader = ACMLoader(manifests_dir)
    return _default_loader
