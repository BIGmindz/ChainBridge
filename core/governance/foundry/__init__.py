"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CHAINBRIDGE LOGIC FOUNDRY v2.0                            ║
║                  PAC-RECOVERY-22-DEFENSE (AEROSPACE)                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  CLASSIFICATION: KERNEL_LEVEL_SOVEREIGNTY                                    ║
║  GOVERNANCE_TIER: LAW                                                        ║
║  SECURITY_CLEARANCE: NASA/DEFENSE_GRADE                                      ║
║  DRIFT_TOLERANCE: ZERO (Absolute)                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

FOUNDRY MODULE: Aerospace-grade deterministic logic synthesis.

PURPOSE:
  The Foundry v2.0 implements radiation-hardened logic synthesis with
  HMAC-SHA512 cryptographic binding and mandatory architectural justification.
  Zero drift tolerance. Fail-closed by default.

INVARIANTS:
  CB-SEC-01: HMAC-SHA512 cryptographic binding mandatory
  CB-LAW-01: Architectural justification mandatory (32+ chars)
  CB-INV-004: Zero drift tolerance (absolute)

TRAINING SIGNAL:
  "We manufacture radiation-hardened truth for the $100M Siege."
  
AUTHORITY: BENSON [GID-00] - Sovereign Core
ARCHITECT: JEFFREY (Chief Architect)
SECURITY_CLEARANCE: AEROSPACE/DEFENSE
"""

from .logic_foundry_v2 import LogicFoundry
from .sovereign_nfi import defense_signed, verify_nfi_signature, generate_instance_key
from .nfi_signer import NFISigner

__all__ = ["LogicFoundry", "defense_signed", "verify_nfi_signature", "generate_instance_key", "NFISigner"]
__version__ = "2.0.0"
__authority__ = "BENSON [GID-00]"
__security_clearance__ = "NASA/DEFENSE_GRADE"
