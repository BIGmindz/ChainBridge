"""
ChainBridge PDO Registry — Session Registry for PDO Artifacts
════════════════════════════════════════════════════════════════════════════════

In-memory/session registry of PDO artifacts.
Enforces uniqueness per PAC and provides retrieval for audit and tests.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-PDO-ARTIFACT-ENGINE-020
Effective Date: 2025-12-26

INVARIANTS:
- INV-PDO-001: One PDO per PAC (enforced via registry)
- Retrieval by pac_id, pdo_id, or iteration

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterator, List, Optional

from core.governance.pdo_artifact import (
    PDOArtifact,
    PDODuplicateError,
    PDO_AUTHORITY,
)


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class PDONotFoundError(Exception):
    """Raised when PDO is not found in registry."""
    
    def __init__(self, identifier: str, id_type: str = "pac_id"):
        self.identifier = identifier
        self.id_type = id_type
        super().__init__(
            f"PDO_NOT_FOUND: No PDO found for {id_type}='{identifier}'"
        )


class PDORegistryError(Exception):
    """Base exception for registry errors."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# PDO REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class PDORegistry:
    """
    In-memory registry for PDO artifacts.
    
    Thread-safe singleton that maintains:
    - PAC → PDO mapping (one-to-one)
    - PDO_ID → PDO mapping (direct access)
    - Ordered list for iteration
    
    INV-PDO-001: Enforces one PDO per PAC.
    """
    
    def __init__(self):
        self._by_pac_id: Dict[str, PDOArtifact] = {}
        self._by_pdo_id: Dict[str, PDOArtifact] = {}
        self._ordered: List[PDOArtifact] = []
        self._lock = threading.Lock()
    
    # ───────────────────────────────────────────────────────────────────────────
    # REGISTRATION
    # ───────────────────────────────────────────────────────────────────────────
    
    def register(self, pdo: PDOArtifact) -> None:
        """
        Register a PDO artifact.
        
        INV-PDO-001: Enforces one PDO per PAC.
        
        Args:
            pdo: PDO artifact to register
        
        Raises:
            PDODuplicateError: If PDO already exists for PAC
        """
        with self._lock:
            # Check for duplicate PAC
            if pdo.pac_id in self._by_pac_id:
                existing = self._by_pac_id[pdo.pac_id]
                raise PDODuplicateError(pdo.pac_id, existing.pdo_id)
            
            # Check for duplicate PDO ID (shouldn't happen, but defensive)
            if pdo.pdo_id in self._by_pdo_id:
                raise PDORegistryError(
                    f"PDO_ID_COLLISION: '{pdo.pdo_id}' already exists"
                )
            
            # Register
            self._by_pac_id[pdo.pac_id] = pdo
            self._by_pdo_id[pdo.pdo_id] = pdo
            self._ordered.append(pdo)
    
    # ───────────────────────────────────────────────────────────────────────────
    # RETRIEVAL
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_by_pac_id(self, pac_id: str) -> Optional[PDOArtifact]:
        """
        Get PDO by PAC ID.
        
        Returns None if not found.
        """
        with self._lock:
            return self._by_pac_id.get(pac_id)
    
    def get_by_pdo_id(self, pdo_id: str) -> Optional[PDOArtifact]:
        """
        Get PDO by PDO ID.
        
        Returns None if not found.
        """
        with self._lock:
            return self._by_pdo_id.get(pdo_id)
    
    def get(self, pac_id: str) -> Optional[PDOArtifact]:
        """Alias for get_by_pac_id."""
        return self.get_by_pac_id(pac_id)
    
    def require_by_pac_id(self, pac_id: str) -> PDOArtifact:
        """
        Get PDO by PAC ID, raising if not found.
        
        Raises:
            PDONotFoundError: If PDO not found
        """
        pdo = self.get_by_pac_id(pac_id)
        if pdo is None:
            raise PDONotFoundError(pac_id, "pac_id")
        return pdo
    
    def require_by_pdo_id(self, pdo_id: str) -> PDOArtifact:
        """
        Get PDO by PDO ID, raising if not found.
        
        Raises:
            PDONotFoundError: If PDO not found
        """
        pdo = self.get_by_pdo_id(pdo_id)
        if pdo is None:
            raise PDONotFoundError(pdo_id, "pdo_id")
        return pdo
    
    # ───────────────────────────────────────────────────────────────────────────
    # QUERY
    # ───────────────────────────────────────────────────────────────────────────
    
    def has_pac(self, pac_id: str) -> bool:
        """Check if PDO exists for PAC."""
        with self._lock:
            return pac_id in self._by_pac_id
    
    def has_pdo(self, pdo_id: str) -> bool:
        """Check if PDO ID exists."""
        with self._lock:
            return pdo_id in self._by_pdo_id
    
    @property
    def count(self) -> int:
        """Number of registered PDOs."""
        with self._lock:
            return len(self._ordered)
    
    def __len__(self) -> int:
        return self.count
    
    def __bool__(self) -> bool:
        """
        Registry is always truthy even when empty.
        
        This prevents the subtle bug where `registry or get_pdo_registry()`
        would use the singleton when an empty custom registry is passed.
        A registry exists as a valid object regardless of contents.
        """
        return True
    
    # ───────────────────────────────────────────────────────────────────────────
    # ITERATION
    # ───────────────────────────────────────────────────────────────────────────
    
    def list_all(self) -> List[PDOArtifact]:
        """Get all PDOs in registration order."""
        with self._lock:
            return list(self._ordered)
    
    def __iter__(self) -> Iterator[PDOArtifact]:
        with self._lock:
            return iter(list(self._ordered))
    
    # ───────────────────────────────────────────────────────────────────────────
    # FILTERING
    # ───────────────────────────────────────────────────────────────────────────
    
    def filter_by_outcome(self, outcome_status: str) -> List[PDOArtifact]:
        """Get PDOs with specific outcome status."""
        with self._lock:
            return [
                pdo for pdo in self._ordered
                if pdo.outcome_status == outcome_status
            ]
    
    def get_accepted(self) -> List[PDOArtifact]:
        """Get all ACCEPTED PDOs."""
        return self.filter_by_outcome("ACCEPTED")
    
    def get_corrective(self) -> List[PDOArtifact]:
        """Get all CORRECTIVE PDOs."""
        return self.filter_by_outcome("CORRECTIVE")
    
    def get_rejected(self) -> List[PDOArtifact]:
        """Get all REJECTED PDOs."""
        return self.filter_by_outcome("REJECTED")
    
    # ───────────────────────────────────────────────────────────────────────────
    # AUDIT
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_audit_summary(self) -> Dict:
        """
        Get audit summary of registry.
        
        Returns dict with counts and breakdown by outcome.
        """
        with self._lock:
            accepted = sum(1 for p in self._ordered if p.is_accepted)
            corrective = sum(1 for p in self._ordered if p.is_corrective)
            rejected = sum(1 for p in self._ordered if p.is_rejected)
            
            return {
                "total": len(self._ordered),
                "accepted": accepted,
                "corrective": corrective,
                "rejected": rejected,
                "pac_ids": list(self._by_pac_id.keys()),
            }
    
    # ───────────────────────────────────────────────────────────────────────────
    # MANAGEMENT
    # ───────────────────────────────────────────────────────────────────────────
    
    def clear(self) -> None:
        """
        Clear all PDOs from registry.
        
        WARNING: For testing only. Do not use in production.
        """
        with self._lock:
            self._by_pac_id.clear()
            self._by_pdo_id.clear()
            self._ordered.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

_registry_instance: Optional[PDORegistry] = None
_registry_lock = threading.Lock()


def get_pdo_registry() -> PDORegistry:
    """
    Get the global PDO registry singleton.
    
    Thread-safe lazy initialization.
    """
    global _registry_instance
    
    if _registry_instance is None:
        with _registry_lock:
            if _registry_instance is None:
                _registry_instance = PDORegistry()
    
    return _registry_instance


def reset_pdo_registry() -> None:
    """
    Reset the global PDO registry.
    
    WARNING: For testing only. Do not use in production.
    Creates a fresh registry instance.
    """
    global _registry_instance
    
    with _registry_lock:
        _registry_instance = PDORegistry()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Registry
    "PDORegistry",
    "get_pdo_registry",
    "reset_pdo_registry",
    
    # Exceptions
    "PDONotFoundError",
    "PDORegistryError",
]
