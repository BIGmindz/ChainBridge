# ═══════════════════════════════════════════════════════════════════════════════
# Benson Execution Directives — Package Init
# PAC-JEFFREY-C07: Permanent BER Enforcement & Directive Hardening
# ═══════════════════════════════════════════════════════════════════════════════

"""
Benson Execution Directives

This package contains constitutional directives that govern Benson Execution behavior.
Directives are LAW-tier and cannot be overridden.

Contents:
    - ber_requirement.yaml: Mandatory BER emission for all PACs
    - benson_jeffrey_contract.yaml: Interface contract between Benson and Jeffrey

INVARIANTS ENFORCED:
    - INV-GOV-010: Every PAC produces exactly one BER
    - INV-GOV-011: WRAP ≠ Decision (Proof only)
    - INV-GOV-012: LAW review without BER is FORBIDDEN
    - INV-GOV-013: Benson MUST emit BER before any closure
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


DIRECTIVES_DIR = Path(__file__).parent


def load_directive(name: str) -> Dict[str, Any]:
    """
    Load a directive by name.
    
    Args:
        name: Directive filename without .yaml extension
        
    Returns:
        Parsed directive as dictionary
        
    Raises:
        FileNotFoundError: If directive doesn't exist
    """
    path = DIRECTIVES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Directive not found: {name}")
    
    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_ber_requirement_directive() -> Dict[str, Any]:
    """Get the BER requirement directive."""
    return load_directive("ber_requirement")


def get_benson_jeffrey_contract() -> Dict[str, Any]:
    """Get the Benson-Jeffrey governance contract."""
    return load_directive("benson_jeffrey_contract")


# Directive IDs
BER_REQUIREMENT_DIRECTIVE_ID = "DIR-BER-001"
BENSON_JEFFREY_CONTRACT_ID = "CONTRACT-BENSON-JEFFREY-001"
