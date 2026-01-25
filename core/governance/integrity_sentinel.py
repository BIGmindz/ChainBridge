"""
PAC-P825: Constitutional Integrity Sentinel

The Seal of the Law - ensures critical governance files remain immutable.
Cryptographically locks SCRAM, TGL, IG, Byzantine, and SovereignRunner logic.

INVARIANTS:
- SEAL-01: Critical files MUST match governance.lock baseline (SHA3-512)
- SEAL-02: Modification to Law requires full SCRAM reset + re-baselining

Author: BENSON (GID-04) via PAC-P825
Chain Position: 6/6 (Final constitutional hardening before P800 wargame)
"""

import hashlib
import json
import os
import asyncio
import logging
from typing import Dict, List, Optional
from pathlib import Path

from core.governance.scram import get_scram_controller, SCRAMController


logger = logging.getLogger(__name__)


class IntegritySentinel:
    """
    Constitutional Integrity Sentinel - cryptographic seal for governance layer.
    
    Uses Trust On First Use (TOFU) model:
    1. First run: Compute SHA3-512 hashes of critical files → save to governance.lock
    2. Subsequent runs: Verify current hashes match baseline → SCRAM if drift detected
    
    Critical Files Protected:
    - core/governance/scram.py (emergency shutdown)
    - core/governance/test_governance_layer.py (TGL Constitutional Court)
    - core/governance/inspector_general.py (runtime oversight)
    - core/swarm/byzantine_voter.py (consensus mechanism)
    - core/runners/sovereign_runner.py (autonomous execution)
    """
    
    # Critical governance files to protect (relative to workspace root)
    CRITICAL_FILES = [
        "core/governance/scram.py",
        "core/governance/test_governance_layer.py",
        "core/governance/inspector_general.py",
        "core/swarm/byzantine_voter.py",
        "core/runners/sovereign_runner.py",
    ]
    
    # Lock file location (SHA3-512 baseline hashes)
    LOCK_FILE = "logs/governance/governance.lock"
    
    def __init__(self, scram: Optional[SCRAMController] = None):
        """
        Initialize Integrity Sentinel with SCRAM controller.
        
        Args:
            scram: SCRAM controller instance (or None to auto-load)
        """
        self.scram = scram or get_scram_controller()
        self.logger = logging.getLogger("IntegritySentinel")
        self.baseline_hashes: Dict[str, str] = {}
        self._monitoring = False
        
    def _compute_hash(self, filepath: str) -> str:
        """
        Compute SHA3-512 hash of file contents.
        
        Uses SHA3-512 for quantum resistance alignment with ChainBridge architecture.
        
        Args:
            filepath: Path to file (relative to workspace root)
            
        Returns:
            Hex digest of SHA3-512 hash, or "FILE_MISSING" if file not found
        """
        sha = hashlib.sha3_512()
        
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(8192):
                    sha.update(chunk)
            return sha.hexdigest()
        except FileNotFoundError:
            self.logger.warning(f"File not found for hashing: {filepath}")
            return "FILE_MISSING"
        except Exception as e:
            self.logger.error(f"Error hashing {filepath}: {e}")
            return "HASH_ERROR"
    
    def _load_or_create_baseline(self) -> Dict[str, str]:
        """
        Load existing governance.lock or create new baseline (TOFU).
        
        Trust On First Use (TOFU) Model:
        - If governance.lock exists: Load baseline hashes (already locked)
        - If governance.lock missing: Compute current hashes → create lock file
        
        Returns:
            Dictionary mapping filepath → SHA3-512 hash
        """
        # Load existing lock file
        if os.path.exists(self.LOCK_FILE):
            try:
                with open(self.LOCK_FILE, 'r') as f:
                    hashes = json.load(f)
                self.logger.info(f"🔒 Loaded governance baseline: {len(hashes)} files")
                return hashes
            except Exception as e:
                self.logger.error(f"Failed to load governance.lock: {e}")
                return {}
        
        # Create new baseline (TOFU - Trust On First Use)
        self.logger.info("🔐 Creating governance baseline (TOFU)...")
        hashes = {}
        
        for path in self.CRITICAL_FILES:
            file_hash = self._compute_hash(path)
            hashes[path] = file_hash
            self.logger.info(f"  ✓ {path}: {file_hash[:16]}...")
        
        # Persist baseline to lock file
        try:
            os.makedirs(os.path.dirname(self.LOCK_FILE), exist_ok=True)
            with open(self.LOCK_FILE, 'w') as f:
                json.dump(hashes, f, indent=2)
            self.logger.info(f"🔒 Governance baseline locked: {len(hashes)} files")
        except Exception as e:
            self.logger.error(f"Failed to save governance.lock: {e}")
        
        return hashes
    
    async def verify_integrity(self) -> str:
        """
        Verify current file hashes against governance.lock baseline.
        
        SEAL-01 Enforcement: Critical files MUST match baseline.
        SEAL-02 Enforcement: Modification triggers SCRAM.
        
        Returns:
            "INTEGRITY_VERIFIED" if all files match baseline
            "BREACH_DETECTED" if any file modified (SCRAM triggered)
            "NO_BASELINE" if governance.lock missing
        """
        # Load baseline if not already loaded
        if not self.baseline_hashes:
            self.baseline_hashes = self._load_or_create_baseline()
        
        if not self.baseline_hashes:
            self.logger.error("❌ No governance baseline found")
            return "NO_BASELINE"
        
        self.logger.info("🛡️ Verifying constitutional integrity...")
        violations = []
        
        # Check each critical file against baseline
        for path, expected_hash in self.baseline_hashes.items():
            current_hash = self._compute_hash(path)
            
            if current_hash != expected_hash:
                violation_msg = f"{path} (expected: {expected_hash[:16]}..., got: {current_hash[:16]}...)"
                violations.append(violation_msg)
                self.logger.critical(f"🚨 SEAL-01 VIOLATION: {violation_msg}")
        
        # Trigger SCRAM on any violation (SEAL-02 enforcement)
        if violations:
            reason_str = f"INTEGRITY_BREACH (SEAL-01): {len(violations)} file(s) modified - {', '.join(violations)}"
            self.logger.critical(f"🚨 {reason_str}")
            
            # Trigger SCRAM using proper API
            from core.governance.scram import trigger_scram, SCRAMReason
            await trigger_scram(
                reason=SCRAMReason.SENTINEL_TRIGGER,
                context={
                    "breach_type": "INTEGRITY_VIOLATION",
                    "violations": violations,
                    "files_modified": len(violations)
                }
            )
            
            return "BREACH_DETECTED"
        
        self.logger.info(f"✅ Constitutional integrity verified ({len(self.baseline_hashes)} files)")
        return "INTEGRITY_VERIFIED"
    
    async def reset_baseline(self, confirmation: str) -> bool:
        """
        Reset governance.lock baseline after SCRAM reset (SEAL-02).
        
        CRITICAL: Requires explicit confirmation to prevent accidental resets.
        Only call this after SCRAM reset and constitutional review.
        
        Args:
            confirmation: Must be "RESET_GOVERNANCE_BASELINE" to proceed
            
        Returns:
            True if baseline reset successful, False otherwise
        """
        if confirmation != "RESET_GOVERNANCE_BASELINE":
            self.logger.error("❌ Baseline reset requires confirmation")
            return False
        
        self.logger.warning("⚠️ Resetting governance baseline (SEAL-02)...")
        
        # Remove old lock file
        if os.path.exists(self.LOCK_FILE):
            try:
                os.remove(self.LOCK_FILE)
                self.logger.info(f"🗑️ Removed old governance.lock")
            except Exception as e:
                self.logger.error(f"Failed to remove governance.lock: {e}")
                return False
        
        # Create new baseline
        self.baseline_hashes = self._load_or_create_baseline()
        
        if self.baseline_hashes:
            self.logger.info(f"✅ Governance baseline reset complete")
            return True
        else:
            self.logger.error("❌ Failed to create new baseline")
            return False
    
    def get_status(self) -> Dict:
        """
        Get current integrity sentinel status.
        
        Returns:
            Dictionary with baseline info, monitoring state, SCRAM status
        """
        return {
            "baseline_loaded": bool(self.baseline_hashes),
            "protected_files": len(self.baseline_hashes),
            "lock_file": self.LOCK_FILE,
            "lock_file_exists": os.path.exists(self.LOCK_FILE),
            "scram_status": self.scram.status,
        }


# ============================================================================
# SINGLETON FACTORY
# ============================================================================

_sentinel_instance: Optional[IntegritySentinel] = None


def get_integrity_sentinel() -> IntegritySentinel:
    """
    Get singleton IntegritySentinel instance.
    
    Returns:
        Global IntegritySentinel instance
    """
    global _sentinel_instance
    
    if _sentinel_instance is None:
        _sentinel_instance = IntegritySentinel()
        logger.info("🔐 IntegritySentinel initialized (singleton)")
    
    return _sentinel_instance


async def initialize_integrity_sentinel() -> IntegritySentinel:
    """
    Initialize Integrity Sentinel and load/create baseline.
    
    Call this at application startup to establish governance lock.
    
    Returns:
        IntegritySentinel instance with baseline loaded
    """
    sentinel = get_integrity_sentinel()
    sentinel.baseline_hashes = sentinel._load_or_create_baseline()
    
    logger.info(f"🛡️ PAC-P825: Constitutional Integrity Sentinel initialized")
    logger.info(f"    Protected files: {len(sentinel.baseline_hashes)}")
    logger.info(f"    Lock file: {sentinel.LOCK_FILE}")
    
    return sentinel
