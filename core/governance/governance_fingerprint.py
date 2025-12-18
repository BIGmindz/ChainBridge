"""
Governance Fingerprint — Deterministic hashing of governance roots.

This module implements cryptographic fingerprinting of governance state:
- Compute SHA-256 hashes of governance root files at startup
- Cache fingerprint in memory for runtime verification
- Detect drift if governance files change after boot
- Fail closed on any inconsistency

ALEX (GID-08) is the sole authority for governance verification.

Governance roots (hash inputs):
- config/agents.json          — Agent authority
- .github/ALEX_RULES.json     — Governance rules
- manifests/*.yaml            — ACM manifests
- core/governance/drcp.py     — DRCP logic
- core/governance/diggi_*     — Diggi corrections
- docs/governance/REPO_SCOPE_MANIFEST.md — Repo scope

Ordering is deterministic (sorted paths, normalized content).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Dict, FrozenSet, List, Optional, Tuple

# Defer telemetry import to avoid circular imports
if TYPE_CHECKING:
    pass


class GovernanceHashError(Exception):
    """Raised when governance hashing fails."""

    pass


class GovernanceDriftError(Exception):
    """Raised when governance files change after startup."""

    def __init__(self, message: str, original_hash: str, current_hash: str) -> None:
        super().__init__(message)
        self.original_hash = original_hash
        self.current_hash = current_hash


class GovernanceBootError(Exception):
    """Raised when governance fingerprint cannot be computed at boot."""

    pass


# Governance root file patterns (relative to project root)
# Note: Use glob patterns (*.json, *.yaml) to catch NEW files in monitored directories
GOVERNANCE_ROOTS: Dict[str, List[str]] = {
    "agent_authority": ["config/*.json"],  # Glob: detect new config files
    "governance_rules": [".github/ALEX_RULES.json"],
    "acm_manifests": ["manifests/*.yaml"],  # Glob pattern
    "drcp_logic": ["core/governance/drcp.py"],
    "diggi_corrections": ["core/governance/diggi_*.py"],  # Glob pattern
    "repo_scope": ["docs/governance/REPO_SCOPE_MANIFEST.md"],
}

# Current fingerprint schema version
FINGERPRINT_VERSION = "v1"


@dataclass(frozen=True)
class FileHash:
    """Hash of a single governance file."""

    path: str
    hash: str
    size: int


@dataclass(frozen=True)
class GovernanceFingerprint:
    """Immutable governance fingerprint computed at startup."""

    version: str
    composite_hash: str
    computed_at: str
    file_hashes: Tuple[FileHash, ...]
    input_categories: FrozenSet[str]

    def to_dict(self) -> Dict[str, object]:
        """Convert to dictionary for API/audit output."""
        return {
            "governance_version": self.version,
            "composite_hash": self.composite_hash,
            "computed_at": self.computed_at,
            "inputs": {fh.path: fh.hash for fh in self.file_hashes},
            "categories": sorted(self.input_categories),
            "file_count": len(self.file_hashes),
        }

    def to_audit_extension(self) -> Dict[str, str]:
        """Return minimal fingerprint for audit log extension."""
        return {
            "composite_hash": self.composite_hash,
            "version": self.version,
        }


class GovernanceFingerprintEngine:
    """Engine for computing and verifying governance fingerprints.

    This engine:
    1. Loads governance root files at startup
    2. Normalizes content (strips trailing whitespace)
    3. Computes SHA-256 hashes
    4. Caches the fingerprint for runtime verification
    5. Detects drift if files change after boot
    """

    def __init__(self, project_root: Path | str | None = None) -> None:
        """Initialize the fingerprint engine.

        Args:
            project_root: Path to project root. Defaults to detected root.
        """
        if project_root is None:
            # Default to project root (parent of core/governance/)
            project_root = Path(__file__).parent.parent.parent
        self._root = Path(project_root)
        self._fingerprint: Optional[GovernanceFingerprint] = None
        self._initialized = False

    @property
    def project_root(self) -> Path:
        """Return the project root path."""
        return self._root

    def compute_fingerprint(self) -> GovernanceFingerprint:
        """Compute governance fingerprint from root files.

        Returns:
            GovernanceFingerprint with composite hash and per-file hashes

        Raises:
            GovernanceBootError: If required files are missing or unreadable
        """
        file_hashes: List[FileHash] = []
        categories_found: set[str] = set()
        errors: List[str] = []

        # Process each category in sorted order for determinism
        for category in sorted(GOVERNANCE_ROOTS.keys()):
            patterns = GOVERNANCE_ROOTS[category]
            category_files: List[Path] = []

            for pattern in patterns:
                if "*" in pattern:
                    # Glob pattern
                    matches = sorted(self._root.glob(pattern))
                    category_files.extend(matches)
                else:
                    # Exact file
                    file_path = self._root / pattern
                    if file_path.exists():
                        category_files.append(file_path)
                    else:
                        errors.append(f"Missing required governance file: {pattern}")

            # Hash each file in sorted order
            for file_path in sorted(category_files):
                try:
                    file_hash = self._hash_file(file_path)
                    file_hashes.append(file_hash)
                    categories_found.add(category)
                except Exception as e:
                    errors.append(f"Failed to hash {file_path.relative_to(self._root)}: {e}")

        # Fail closed if any errors
        if errors:
            raise GovernanceBootError("Governance fingerprint computation failed:\n" + "\n".join(f"  - {e}" for e in errors))

        # Compute composite hash from all file hashes (sorted, deterministic)
        composite = self._compute_composite_hash(file_hashes)

        fingerprint = GovernanceFingerprint(
            version=FINGERPRINT_VERSION,
            composite_hash=composite,
            computed_at=datetime.now(timezone.utc).isoformat(),
            file_hashes=tuple(file_hashes),
            input_categories=frozenset(categories_found),
        )

        self._fingerprint = fingerprint
        self._initialized = True

        return fingerprint

    def get_fingerprint(self) -> GovernanceFingerprint:
        """Get the cached fingerprint.

        Returns:
            Cached GovernanceFingerprint

        Raises:
            GovernanceBootError: If fingerprint not yet computed
        """
        if not self._initialized or self._fingerprint is None:
            raise GovernanceBootError("Governance fingerprint not computed. Call compute_fingerprint() first.")
        return self._fingerprint

    def is_initialized(self) -> bool:
        """Check if fingerprint has been computed."""
        return self._initialized

    def verify_no_drift(self) -> bool:
        """Verify governance files haven't changed since boot.

        Returns:
            True if no drift detected

        Raises:
            GovernanceDriftError: If drift is detected
            GovernanceBootError: If fingerprint not initialized
        """
        if not self._initialized or self._fingerprint is None:
            raise GovernanceBootError("Cannot verify drift: fingerprint not computed")

        # Recompute fingerprint
        try:
            current = self._compute_current_hash()
        except Exception as e:
            # PAC-GOV-OBS-01: Emit telemetry before raising (fail-open on emit)
            self._emit_drift_event(
                original_hash=self._fingerprint.composite_hash,
                current_hash="COMPUTATION_FAILED",
                message=f"Failed to recompute governance hash: {e}",
            )
            raise GovernanceDriftError(
                f"Failed to recompute governance hash: {e}",
                original_hash=self._fingerprint.composite_hash,
                current_hash="COMPUTATION_FAILED",
            )

        if current != self._fingerprint.composite_hash:
            # PAC-GOV-OBS-01: Emit telemetry before raising (fail-open on emit)
            self._emit_drift_event(
                original_hash=self._fingerprint.composite_hash,
                current_hash=current,
                message="Governance drift detected: files changed after startup",
            )
            raise GovernanceDriftError(
                "Governance drift detected: files changed after startup",
                original_hash=self._fingerprint.composite_hash,
                current_hash=current,
            )

        return True

    def _emit_drift_event(
        self,
        original_hash: str,
        current_hash: str,
        message: str,
    ) -> None:
        """Emit drift detection telemetry (fail-open).

        Args:
            original_hash: Original governance fingerprint
            current_hash: Current (changed) fingerprint
            message: Drift detection message
        """
        try:
            # Lazy import to avoid circular imports
            from core.governance.event_sink import emit_event
            from core.governance.events import governance_drift_event

            emit_event(
                governance_drift_event(
                    original_hash=original_hash,
                    current_hash=current_hash,
                    message=message,
                )
            )
        except Exception:
            # Fail-open: Telemetry failure does not block governance
            pass

    def _compute_current_hash(self) -> str:
        """Recompute composite hash from current files."""
        file_hashes: List[FileHash] = []

        for category in sorted(GOVERNANCE_ROOTS.keys()):
            patterns = GOVERNANCE_ROOTS[category]
            for pattern in patterns:
                if "*" in pattern:
                    matches = sorted(self._root.glob(pattern))
                    for match in matches:
                        file_hashes.append(self._hash_file(match))
                else:
                    file_path = self._root / pattern
                    if file_path.exists():
                        file_hashes.append(self._hash_file(file_path))

        return self._compute_composite_hash(file_hashes)

    def _hash_file(self, path: Path) -> FileHash:
        """Hash a single file with content normalization.

        Normalization:
        - Read as UTF-8
        - Strip trailing whitespace from lines
        - Normalize line endings to LF
        - Strip trailing newlines

        Args:
            path: Path to file

        Returns:
            FileHash with SHA-256 hash
        """
        content = path.read_text(encoding="utf-8")

        # Normalize content for deterministic hashing
        # 1. Normalize line endings to LF
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        # 2. Strip trailing whitespace from each line
        lines = [line.rstrip() for line in content.split("\n")]
        # 3. Rejoin and strip trailing newlines
        normalized = "\n".join(lines).rstrip("\n")

        # Compute SHA-256
        hash_value = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        # Get relative path for storage
        try:
            rel_path = str(path.relative_to(self._root))
        except ValueError:
            rel_path = str(path)

        return FileHash(
            path=rel_path,
            hash=hash_value,
            size=len(normalized),
        )

    def _compute_composite_hash(self, file_hashes: List[FileHash]) -> str:
        """Compute composite hash from all file hashes.

        The composite is computed by:
        1. Sort file hashes by path (deterministic)
        2. Concatenate path:hash pairs with newlines
        3. Hash the result

        Args:
            file_hashes: List of FileHash objects

        Returns:
            SHA-256 composite hash
        """
        # Sort by path for determinism
        sorted_hashes = sorted(file_hashes, key=lambda fh: fh.path)

        # Build composite input
        composite_input = "\n".join(f"{fh.path}:{fh.hash}" for fh in sorted_hashes)

        return hashlib.sha256(composite_input.encode("utf-8")).hexdigest()


# Module-level singleton
_fingerprint_engine: Optional[GovernanceFingerprintEngine] = None


def get_fingerprint_engine(project_root: Path | str | None = None) -> GovernanceFingerprintEngine:
    """Get or create the fingerprint engine singleton.

    Args:
        project_root: Optional project root path

    Returns:
        GovernanceFingerprintEngine instance
    """
    global _fingerprint_engine
    if _fingerprint_engine is None or project_root is not None:
        _fingerprint_engine = GovernanceFingerprintEngine(project_root)
    return _fingerprint_engine


def compute_governance_fingerprint(project_root: Path | str | None = None) -> GovernanceFingerprint:
    """Compute governance fingerprint (convenience function).

    Args:
        project_root: Optional project root path

    Returns:
        GovernanceFingerprint
    """
    engine = get_fingerprint_engine(project_root)
    return engine.compute_fingerprint()


def get_governance_fingerprint() -> GovernanceFingerprint:
    """Get cached governance fingerprint (convenience function).

    Returns:
        Cached GovernanceFingerprint

    Raises:
        GovernanceBootError: If not yet computed
    """
    engine = get_fingerprint_engine()
    return engine.get_fingerprint()


def verify_governance_integrity() -> bool:
    """Verify no governance drift (convenience function).

    Returns:
        True if no drift

    Raises:
        GovernanceDriftError: If drift detected
    """
    engine = get_fingerprint_engine()
    return engine.verify_no_drift()
