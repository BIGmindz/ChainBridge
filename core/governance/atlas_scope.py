"""
Atlas Scope Loader — Domain Boundary Enforcement

Loads and enforces Atlas (GID-11) path restrictions.
Atlas is a meta-agent with zero domain authority.

@see PAC-GOV-ATLAS-01 — Atlas Domain Boundary Enforcement
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import yaml

# Atlas GID constant
ATLAS_GID = "GID-11"

# Default path to scope lock file (relative to repo root)
_DEFAULT_SCOPE_FILE = Path(__file__).parent.parent.parent / "docs" / "governance" / "ATLAS_SCOPE_LOCK_v1.yaml"


class AtlasScopeNotFoundError(Exception):
    """Raised when the Atlas scope lock file is not found."""

    pass


class AtlasScopeInvalidError(Exception):
    """Raised when the Atlas scope lock file is invalid."""

    pass


@dataclass(frozen=True)
class AtlasScope:
    """Immutable Atlas scope configuration.

    Defines which paths Atlas can and cannot modify.
    """

    version: str
    forbidden_paths: Tuple[str, ...]
    allowed_paths: Tuple[str, ...]
    governance_lock: bool

    def is_path_forbidden(self, path: str) -> Optional[str]:
        """Check if a path is forbidden for Atlas.

        Args:
            path: The path to check (relative or absolute)

        Returns:
            The matching forbidden pattern if forbidden, None if allowed
        """
        # Normalize path (remove leading slashes, use forward slashes)
        normalized = path.lstrip("/").replace("\\", "/")

        for pattern in self.forbidden_paths:
            # Convert glob pattern to work with fnmatch
            # Handle ** for recursive matching
            if "**" in pattern:
                # For patterns like "core/**", match "core/anything/deep"
                base = pattern.replace("/**", "")
                if normalized == base or normalized.startswith(base + "/"):
                    return pattern
            elif fnmatch.fnmatch(normalized, pattern):
                return pattern

        return None

    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is explicitly allowed for Atlas.

        Args:
            path: The path to check

        Returns:
            True if path matches an allowed pattern
        """
        normalized = path.lstrip("/").replace("\\", "/")

        for pattern in self.allowed_paths:
            if "**" in pattern:
                base = pattern.replace("/**", "")
                if normalized == base or normalized.startswith(base + "/"):
                    return True
            elif fnmatch.fnmatch(normalized, pattern):
                return True

        return False


def load_atlas_scope(scope_file: Optional[Path] = None) -> AtlasScope:
    """Load Atlas scope configuration from YAML file.

    Args:
        scope_file: Path to scope file. Defaults to docs/governance/ATLAS_SCOPE_LOCK_v1.yaml

    Returns:
        AtlasScope configuration

    Raises:
        AtlasScopeNotFoundError: If file not found
        AtlasScopeInvalidError: If file is invalid
    """
    file_path = scope_file or _DEFAULT_SCOPE_FILE

    if not file_path.exists():
        raise AtlasScopeNotFoundError(f"Atlas scope file not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise AtlasScopeInvalidError(f"Invalid YAML in Atlas scope file: {e}") from e

    if not isinstance(data, dict):
        raise AtlasScopeInvalidError("Atlas scope file must contain a YAML object")

    # Validate required fields
    version = data.get("version")
    if not version:
        raise AtlasScopeInvalidError("Atlas scope file missing 'version'")

    forbidden_paths = data.get("forbidden_paths", [])
    if not isinstance(forbidden_paths, list):
        raise AtlasScopeInvalidError("'forbidden_paths' must be a list")

    allowed_paths = data.get("allowed_paths", [])
    if not isinstance(allowed_paths, list):
        raise AtlasScopeInvalidError("'allowed_paths' must be a list")

    governance_lock = data.get("governance_lock", False)
    if not isinstance(governance_lock, bool):
        raise AtlasScopeInvalidError("'governance_lock' must be a boolean")

    return AtlasScope(
        version=version,
        forbidden_paths=tuple(forbidden_paths),
        allowed_paths=tuple(allowed_paths),
        governance_lock=governance_lock,
    )


def is_atlas(agent_gid: str) -> bool:
    """Check if an agent GID is Atlas.

    Args:
        agent_gid: The GID to check

    Returns:
        True if GID is Atlas (GID-11)
    """
    return agent_gid == ATLAS_GID


# Module-level singleton
_atlas_scope: Optional[AtlasScope] = None


def get_atlas_scope() -> Optional[AtlasScope]:
    """Get the loaded Atlas scope (if any)."""
    return _atlas_scope


def set_atlas_scope(scope: AtlasScope) -> None:
    """Set the Atlas scope (for testing)."""
    global _atlas_scope
    _atlas_scope = scope


def reset_atlas_scope() -> None:
    """Reset the Atlas scope singleton (for testing)."""
    global _atlas_scope
    _atlas_scope = None
