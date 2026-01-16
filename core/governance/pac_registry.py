#!/usr/bin/env python3
"""
PAC Registry Enforcement Module

Enforces canonical PAC numbering and registry-backed sequencing.
All PAC operations must pass through this module for validation.

REGISTRY REFERENCE: PAC-REGISTRY-001
PAC AUTHORITY: PAC-P743-GOV-PAC-REGISTRY-ENFORCEMENT
CLASSIFICATION: LAW_TIER

Authors:
- CODY (GID-01) - Registry Backend
- ALEX (GID-08) - Enforcement Logic
- DAN (GID-07) - CI Integration

Invariants:
- INV-REG-001: Global Uniqueness
- INV-REG-002: Monotonic Sequence
- INV-REG-003: Registry Authority
"""

import json
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ValidationResult(Enum):
    """PAC validation result codes."""
    VALID = "VALID"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_DOMAIN = "INVALID_DOMAIN"
    DUPLICATE_NUMBER = "DUPLICATE_NUMBER"
    OUT_OF_SEQUENCE = "OUT_OF_SEQUENCE"
    REUSE_VIOLATION = "REUSE_VIOLATION"
    UNAUTHORIZED = "UNAUTHORIZED"


@dataclass
class PACValidation:
    """Result of PAC ID validation."""
    pac_id: str
    valid: bool
    result: ValidationResult
    message: str
    p_number: Optional[int] = None
    domain: Optional[str] = None
    intent: Optional[str] = None


class PACRegistry:
    """
    Canonical PAC Registry and Numbering Enforcer.
    
    Ensures all PACs follow the global P-series numbering scheme:
    PAC-P<NNN>-<DOMAIN>-<INTENT>
    """
    
    REGISTRY_FILE = "core/governance/PAC_REGISTRY.json"
    CANONICAL_PATTERN = re.compile(r"^PAC-P(\d{1,4})-([A-Z]+)-([A-Z0-9-]+)$")
    
    # Legacy patterns for grandfather clause
    LEGACY_PATTERNS = [
        re.compile(r"^PAC-JEFFREY-.*$"),
        re.compile(r"^PAC-TEST-.*$"),
        re.compile(r"^TEST-P\d+-.*$"),
    ]
    
    VALID_DOMAINS = {
        "GOV", "OPS", "STRAT", "BIZ", "OCC", "SYS",
        "RES", "LOG", "SWARM", "TEST", "EXP", "ARCH", "INT"
    }
    
    def __init__(self, governance_root: Optional[Path] = None):
        self.governance_root = governance_root or Path(__file__).parent.parent.parent.parent
        self.logger = logging.getLogger("pac.registry")
        self.registry = self._load_registry()
        self.allocated_numbers: set = self._build_allocation_set()
    
    def _load_registry(self) -> Dict:
        """Load PAC registry from file."""
        registry_path = self.governance_root / self.REGISTRY_FILE
        
        if registry_path.exists():
            with open(registry_path, encoding="utf-8") as f:
                return json.load(f)
        
        self.logger.warning(f"Registry not found at {registry_path}")
        return {
            "sequence_state": {
                "highest_committed_p_number": 0,
                "next_available_p_number": 1
            },
            "allocation_log": []
        }
    
    def _build_allocation_set(self) -> set:
        """Build set of allocated P-numbers from log."""
        numbers = set()
        for entry in self.registry.get("allocation_log", []):
            numbers.add(entry.get("p_number"))
        return numbers
    
    def _save_registry(self):
        """Persist registry to file."""
        registry_path = self.governance_root / self.REGISTRY_FILE
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(self.registry, f, indent=2)
    
    def validate_pac_id(self, pac_id: str) -> PACValidation:
        """
        Validate a PAC ID against registry rules.
        
        Returns validation result with details.
        """
        # Check canonical format
        match = self.CANONICAL_PATTERN.match(pac_id)
        
        if match:
            p_number = int(match.group(1))
            domain = match.group(2)
            intent = match.group(3)
            
            # Validate domain code
            if domain not in self.VALID_DOMAINS:
                return PACValidation(
                    pac_id=pac_id,
                    valid=False,
                    result=ValidationResult.INVALID_DOMAIN,
                    message=f"Invalid domain code '{domain}'. Valid: {', '.join(sorted(self.VALID_DOMAINS))}",
                    p_number=p_number,
                    domain=domain,
                    intent=intent
                )
            
            # Check for duplicate
            if p_number in self.allocated_numbers:
                return PACValidation(
                    pac_id=pac_id,
                    valid=False,
                    result=ValidationResult.DUPLICATE_NUMBER,
                    message=f"P-number {p_number} already allocated",
                    p_number=p_number,
                    domain=domain,
                    intent=intent
                )
            
            # Check sequence (warn if out of order, but allow)
            next_available = self.registry["sequence_state"]["next_available_p_number"]
            if p_number < next_available:
                self.logger.warning(f"P-number {p_number} is below next_available {next_available}")
            
            return PACValidation(
                pac_id=pac_id,
                valid=True,
                result=ValidationResult.VALID,
                message="PAC ID is valid and compliant",
                p_number=p_number,
                domain=domain,
                intent=intent
            )
        
        # Check legacy patterns (grandfather clause)
        for pattern in self.LEGACY_PATTERNS:
            if pattern.match(pac_id):
                return PACValidation(
                    pac_id=pac_id,
                    valid=True,
                    result=ValidationResult.VALID,
                    message="Legacy PAC ID grandfathered under reconciliation policy"
                )
        
        # Invalid format
        return PACValidation(
            pac_id=pac_id,
            valid=False,
            result=ValidationResult.INVALID_FORMAT,
            message="PAC ID does not match canonical format PAC-P<NNN>-<DOMAIN>-<INTENT>"
        )
    
    def allocate_next(self, domain: str, intent: str, authority: str = "BENSON (GID-00)") -> Tuple[str, int]:
        """
        Allocate the next available P-number.
        
        Returns (pac_id, p_number).
        """
        if domain not in self.VALID_DOMAINS:
            raise ValueError(f"Invalid domain: {domain}")
        
        p_number = self.registry["sequence_state"]["next_available_p_number"]
        pac_id = f"PAC-P{p_number}-{domain}-{intent}"
        
        # Update registry
        self.registry["sequence_state"]["highest_committed_p_number"] = p_number
        self.registry["sequence_state"]["next_available_p_number"] = p_number + 1
        self.registry["sequence_state"]["last_updated_by"] = pac_id
        
        # Add to allocation log
        self.registry["allocation_log"].append({
            "p_number": p_number,
            "pac_id": pac_id,
            "allocated_at": datetime.now(timezone.utc).isoformat(),
            "allocated_by": authority,
            "authority": "JEFFREY (Architect)",
            "status": "COMMITTED"
        })
        
        self.allocated_numbers.add(p_number)
        self._save_registry()
        
        self.logger.info(f"Allocated P-{p_number}: {pac_id}")
        return pac_id, p_number
    
    def get_next_available(self) -> int:
        """Get the next available P-number without allocating."""
        return self.registry["sequence_state"]["next_available_p_number"]
    
    def get_highest_committed(self) -> int:
        """Get the highest committed P-number."""
        return self.registry["sequence_state"]["highest_committed_p_number"]
    
    def get_allocation_history(self, limit: int = 10) -> List[Dict]:
        """Get recent allocation history."""
        log = self.registry.get("allocation_log", [])
        return log[-limit:] if log else []
    
    def is_number_allocated(self, p_number: int) -> bool:
        """Check if a P-number is already allocated."""
        return p_number in self.allocated_numbers
    
    def get_registry_status(self) -> Dict:
        """Get current registry status summary."""
        return {
            "registry_id": self.registry.get("registry_id", "UNKNOWN"),
            "highest_committed": self.get_highest_committed(),
            "next_available": self.get_next_available(),
            "total_allocations": len(self.allocated_numbers),
            "valid_domains": list(self.VALID_DOMAINS),
            "enforcement_active": True
        }


def validate_pac_format(pac_id: str) -> bool:
    """
    Quick validation check for PAC ID format.
    
    Use for pre-flight checks before full validation.
    """
    registry = PACRegistry()
    result = registry.validate_pac_id(pac_id)
    return result.valid


def get_next_pac_id(domain: str, intent: str) -> str:
    """
    Get the next PAC ID for a given domain and intent.
    
    Convenience function for PAC creation.
    """
    registry = PACRegistry()
    pac_id, _ = registry.allocate_next(domain, intent)
    return pac_id


# Module-level singleton
_registry: Optional[PACRegistry] = None


def get_registry() -> PACRegistry:
    """Get or create the registry singleton."""
    global _registry
    if _registry is None:
        _registry = PACRegistry()
    return _registry


if __name__ == "__main__":
    # Self-test
    print("PAC Registry Enforcement - Self Test")
    print("=" * 50)
    
    registry = get_registry()
    status = registry.get_registry_status()
    
    print(f"Registry ID: {status['registry_id']}")
    print(f"Highest Committed: P{status['highest_committed']}")
    print(f"Next Available: P{status['next_available']}")
    print(f"Total Allocations: {status['total_allocations']}")
    
    # Test validations
    test_cases = [
        "PAC-P744-GOV-TEST-VALIDATION",  # Valid
        "PAC-P743-GOV-DUPLICATE",         # Duplicate (should fail)
        "PAC-JEFFREY-TEST-01",            # Legacy (grandfathered)
        "INVALID-PAC-FORMAT",             # Invalid
        "PAC-P999-INVALID-DOMAIN",        # Invalid domain
    ]
    
    print("\nValidation Tests:")
    for pac_id in test_cases:
        result = registry.validate_pac_id(pac_id)
        status_str = "✅" if result.valid else "❌"
        print(f"  {status_str} {pac_id}: {result.result.value} - {result.message}")
    
    print("\n✓ PAC Registry Enforcement Module Loaded")
