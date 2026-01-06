"""
Constitution Sealing — Cryptographic Integrity Verification

PAC: PAC-OCC-P07
Lane: EX2 — Constitution Sealing
Agent: ALEX (GID-08)

Addresses existential failure EX2: "Constitution Tampering"
BER-P05 finding: ALEX_RULES.json lacks automated integrity checks

MECHANICAL ENFORCEMENT:
- SHA-256 hash of ALEX_RULES.json stored in sealed manifest
- CI hook verifies hash on every commit
- Runtime verification on service startup
- Tamper detection alerts immediately

INVARIANTS:
- INV-SEAL-001: Constitution hash MUST match sealed manifest
- INV-SEAL-002: Hash mismatch BLOCKS deployment
- INV-SEAL-003: All seal verifications are audited
- INV-SEAL-004: Seal updates require T4 dual control
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Default paths
DEFAULT_CONSTITUTION_PATH = ".github/ALEX_RULES.json"
DEFAULT_MANIFEST_PATH = ".github/governance/constitution_seal.json"

# Environment overrides
CONSTITUTION_PATH = os.environ.get("CHAINBRIDGE_CONSTITUTION_PATH", DEFAULT_CONSTITUTION_PATH)
MANIFEST_PATH = os.environ.get("CHAINBRIDGE_SEAL_MANIFEST_PATH", DEFAULT_MANIFEST_PATH)


class SealViolation(Exception):
    """Constitution seal integrity violation."""
    
    def __init__(self, message: str, expected_hash: str, actual_hash: str):
        super().__init__(message)
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash


# ═══════════════════════════════════════════════════════════════════════════════
# SEAL MANIFEST
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SealManifest:
    """Sealed constitution manifest."""
    
    constitution_path: str
    sha256_hash: str
    sealed_at: str
    sealed_by: str
    version: str
    dual_control_request_id: Optional[str] = None
    previous_hash: Optional[str] = None
    seal_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "constitution_path": self.constitution_path,
            "sha256_hash": self.sha256_hash,
            "sealed_at": self.sealed_at,
            "sealed_by": self.sealed_by,
            "version": self.version,
            "dual_control_request_id": self.dual_control_request_id,
            "previous_hash": self.previous_hash,
            "seal_history": self.seal_history,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SealManifest":
        """Create from dictionary."""
        return cls(
            constitution_path=data["constitution_path"],
            sha256_hash=data["sha256_hash"],
            sealed_at=data["sealed_at"],
            sealed_by=data["sealed_by"],
            version=data["version"],
            dual_control_request_id=data.get("dual_control_request_id"),
            previous_hash=data.get("previous_hash"),
            seal_history=data.get("seal_history", []),
        )


@dataclass
class SealVerificationResult:
    """Result of a seal verification."""
    
    valid: bool
    constitution_path: str
    expected_hash: str
    actual_hash: str
    verified_at: str
    error_message: Optional[str] = None
    manifest_version: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTITUTION SEALER
# ═══════════════════════════════════════════════════════════════════════════════


class ConstitutionSealer:
    """
    Manages cryptographic sealing and verification of the constitution.
    
    INVARIANT ENFORCEMENT:
    - INV-SEAL-001: Verify hash matches manifest
    - INV-SEAL-002: Block on mismatch
    - INV-SEAL-003: Audit all verifications
    - INV-SEAL-004: Seal updates require T4 dual control
    """
    
    def __init__(
        self,
        constitution_path: Optional[str] = None,
        manifest_path: Optional[str] = None,
        repo_root: Optional[str] = None,
    ):
        """Initialize the constitution sealer."""
        self._lock = threading.Lock()
        
        # Determine repo root
        if repo_root:
            self._repo_root = Path(repo_root)
        else:
            # Try to find repo root from current directory
            self._repo_root = self._find_repo_root()
        
        self._constitution_path = Path(constitution_path or CONSTITUTION_PATH)
        self._manifest_path = Path(manifest_path or MANIFEST_PATH)
        
        # Make paths absolute if relative
        if not self._constitution_path.is_absolute():
            self._constitution_path = self._repo_root / self._constitution_path
        if not self._manifest_path.is_absolute():
            self._manifest_path = self._repo_root / self._manifest_path
        
        self._verification_log: List[SealVerificationResult] = []
        
        logger.info(f"ConstitutionSealer initialized — constitution: {self._constitution_path}")
    
    def _find_repo_root(self) -> Path:
        """Find the repository root by looking for .git directory."""
        current = Path.cwd()
        
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists():
                return parent
        
        # Fallback to current directory
        return current
    
    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()
    
    def _read_constitution(self) -> tuple[bytes, Dict[str, Any]]:
        """Read constitution file and return raw bytes and parsed JSON."""
        if not self._constitution_path.exists():
            raise FileNotFoundError(f"Constitution not found: {self._constitution_path}")
        
        content = self._constitution_path.read_bytes()
        parsed = json.loads(content.decode("utf-8"))
        
        return content, parsed
    
    def _read_manifest(self) -> Optional[SealManifest]:
        """Read the seal manifest if it exists."""
        if not self._manifest_path.exists():
            return None
        
        content = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        return SealManifest.from_dict(content)
    
    def _write_manifest(self, manifest: SealManifest) -> None:
        """Write the seal manifest atomically."""
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write atomically
        tmp_path = self._manifest_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
        tmp_path.replace(self._manifest_path)
    
    def _audit(self, result: SealVerificationResult) -> None:
        """Record verification in audit log."""
        self._verification_log.append(result)
        
        status = "PASS" if result.valid else "FAIL"
        logger.info(
            f"CONSTITUTION_SEAL_VERIFICATION [{status}]: "
            f"expected={result.expected_hash[:16]}... actual={result.actual_hash[:16]}..."
        )
        
        if not result.valid:
            logger.critical(
                f"INV-SEAL-001 VIOLATION: Constitution hash mismatch! "
                f"Expected: {result.expected_hash}, Got: {result.actual_hash}"
            )
    
    def verify(self, raise_on_mismatch: bool = True) -> SealVerificationResult:
        """
        Verify constitution integrity against sealed manifest.
        
        Args:
            raise_on_mismatch: If True, raise SealViolation on mismatch
            
        Returns:
            Verification result
            
        Raises:
            SealViolation: If hash mismatch and raise_on_mismatch=True
            FileNotFoundError: If constitution or manifest not found
            
        ENFORCES: INV-SEAL-001, INV-SEAL-002
        """
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            
            # Read current constitution
            try:
                content, _ = self._read_constitution()
                actual_hash = self._compute_hash(content)
            except FileNotFoundError as e:
                result = SealVerificationResult(
                    valid=False,
                    constitution_path=str(self._constitution_path),
                    expected_hash="N/A",
                    actual_hash="N/A",
                    verified_at=now,
                    error_message=str(e),
                )
                self._audit(result)
                if raise_on_mismatch:
                    raise
                return result
            
            # Read manifest
            manifest = self._read_manifest()
            if manifest is None:
                result = SealVerificationResult(
                    valid=False,
                    constitution_path=str(self._constitution_path),
                    expected_hash="NO_MANIFEST",
                    actual_hash=actual_hash,
                    verified_at=now,
                    error_message="No seal manifest found — constitution unsealed",
                )
                self._audit(result)
                
                if raise_on_mismatch:
                    raise SealViolation(
                        "No seal manifest found — constitution is unsealed",
                        expected_hash="NO_MANIFEST",
                        actual_hash=actual_hash,
                    )
                return result
            
            # Compare hashes
            valid = actual_hash == manifest.sha256_hash
            
            result = SealVerificationResult(
                valid=valid,
                constitution_path=str(self._constitution_path),
                expected_hash=manifest.sha256_hash,
                actual_hash=actual_hash,
                verified_at=now,
                manifest_version=manifest.version,
            )
            
            self._audit(result)
            
            if not valid and raise_on_mismatch:
                raise SealViolation(
                    f"INV-SEAL-001 VIOLATION: Constitution hash mismatch",
                    expected_hash=manifest.sha256_hash,
                    actual_hash=actual_hash,
                )
            
            return result
    
    def seal(
        self,
        sealed_by: str,
        dual_control_request_id: Optional[str] = None,
        require_dual_control: bool = True,
    ) -> SealManifest:
        """
        Seal the current constitution state.
        
        Args:
            sealed_by: Operator performing the seal
            dual_control_request_id: Required T4 dual control request ID
            require_dual_control: Whether to enforce dual control requirement
            
        Returns:
            The new seal manifest
            
        ENFORCES: INV-SEAL-004 (requires T4 dual control)
        """
        with self._lock:
            # INV-SEAL-004: Require dual control for seal operations
            if require_dual_control and not dual_control_request_id:
                raise ValueError(
                    "INV-SEAL-004 VIOLATION: Constitution seal requires T4 dual control. "
                    "Provide dual_control_request_id."
                )
            
            # Read current constitution
            content, parsed = self._read_constitution()
            current_hash = self._compute_hash(content)
            
            # Get existing manifest for history
            existing = self._read_manifest()
            previous_hash = existing.sha256_hash if existing else None
            seal_history = existing.seal_history.copy() if existing else []
            
            # Add to history
            seal_history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "hash": current_hash,
                "sealed_by": sealed_by,
                "dual_control_request_id": dual_control_request_id,
            })
            
            # Keep last 50 seals
            seal_history = seal_history[-50:]
            
            # Extract version from constitution
            version = parsed.get("version", "unknown")
            
            # Create new manifest
            manifest = SealManifest(
                constitution_path=str(self._constitution_path.relative_to(self._repo_root)),
                sha256_hash=current_hash,
                sealed_at=datetime.now(timezone.utc).isoformat(),
                sealed_by=sealed_by,
                version=version,
                dual_control_request_id=dual_control_request_id,
                previous_hash=previous_hash,
                seal_history=seal_history,
            )
            
            self._write_manifest(manifest)
            
            logger.info(
                f"CONSTITUTION_SEALED: hash={current_hash[:16]}... "
                f"version={version} by {sealed_by}"
            )
            
            return manifest
    
    def get_current_hash(self) -> str:
        """Get the current constitution hash (without verification)."""
        content, _ = self._read_constitution()
        return self._compute_hash(content)
    
    def get_verification_log(self, limit: int = 100) -> List[SealVerificationResult]:
        """Get recent verification log entries."""
        with self._lock:
            return self._verification_log[-limit:]


# ═══════════════════════════════════════════════════════════════════════════════
# CI HOOK — For GitHub Actions / CI Pipeline
# ═══════════════════════════════════════════════════════════════════════════════


def verify_constitution_ci(repo_root: Optional[str] = None) -> int:
    """
    CI hook to verify constitution integrity.
    
    Returns:
        Exit code: 0 for success, 1 for failure
        
    Usage in CI:
        python -c "from core.occ.governance.constitution_seal import verify_constitution_ci; exit(verify_constitution_ci())"
    """
    try:
        sealer = ConstitutionSealer(repo_root=repo_root)
        result = sealer.verify(raise_on_mismatch=True)
        
        print(f"✅ CONSTITUTION SEAL VERIFIED")
        print(f"   Path: {result.constitution_path}")
        print(f"   Hash: {result.expected_hash}")
        print(f"   Version: {result.manifest_version}")
        
        return 0
        
    except SealViolation as e:
        print(f"❌ CONSTITUTION SEAL VIOLATED")
        print(f"   Expected: {e.expected_hash}")
        print(f"   Actual: {e.actual_hash}")
        print(f"   ERROR: {str(e)}")
        print()
        print("INV-SEAL-002: Deployment BLOCKED due to constitution tampering")
        
        return 1
        
    except FileNotFoundError as e:
        print(f"❌ CONSTITUTION NOT FOUND")
        print(f"   Error: {str(e)}")
        
        return 1
        
    except Exception as e:
        print(f"❌ SEAL VERIFICATION ERROR")
        print(f"   Error: {str(e)}")
        
        return 1


# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP HOOK — For Runtime Verification
# ═══════════════════════════════════════════════════════════════════════════════


def verify_constitution_on_startup(
    repo_root: Optional[str] = None,
    fail_open: bool = False,
) -> bool:
    """
    Verify constitution on service startup.
    
    Args:
        repo_root: Optional repository root path
        fail_open: If True, log warning but don't fail on missing manifest
        
    Returns:
        True if verified, False if failed
        
    Raises:
        SealViolation: If hash mismatch and fail_open=False
    """
    try:
        sealer = ConstitutionSealer(repo_root=repo_root)
        result = sealer.verify(raise_on_mismatch=not fail_open)
        
        if result.valid:
            logger.info(
                f"STARTUP: Constitution seal verified — "
                f"hash={result.expected_hash[:16]}... version={result.manifest_version}"
            )
            return True
        else:
            if fail_open:
                logger.warning(
                    f"STARTUP: Constitution seal FAILED but fail_open=True — "
                    f"{result.error_message}"
                )
                return False
            else:
                raise SealViolation(
                    result.error_message or "Verification failed",
                    expected_hash=result.expected_hash,
                    actual_hash=result.actual_hash,
                )
                
    except Exception as e:
        if fail_open:
            logger.warning(f"STARTUP: Constitution verification error (fail_open=True): {e}")
            return False
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_sealer_instance: Optional[ConstitutionSealer] = None
_sealer_lock = threading.Lock()


def get_constitution_sealer() -> ConstitutionSealer:
    """Get the singleton constitution sealer instance."""
    global _sealer_instance
    
    if _sealer_instance is None:
        with _sealer_lock:
            if _sealer_instance is None:
                _sealer_instance = ConstitutionSealer()
    
    return _sealer_instance
