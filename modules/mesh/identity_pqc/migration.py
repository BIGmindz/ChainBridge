#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      LEGACY MIGRATION                                        ║
║                    PAC-SEC-P819 Implementation                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Migration utilities for upgrading ED25519-only identities to hybrid PQC.

Migration preserves:
  - Node ID (unchanged, as it's derived from ED25519 key)
  - Node name
  - Federation ID
  - Existing capabilities (plus "PQC" capability)

Migration adds:
  - ML-DSA-65 key pair
  - Hybrid signature capability
"""

import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from .core import HybridIdentity, HybridKeyPair, ED25519KeyPair, PQCKeyPair
from .constants import (
    VERSION,
    FORMAT_VERSION,
    NODE_ID_LENGTH,
    SIGNATURE_MODE_HYBRID,
    SignatureMode,
)
from .errors import (
    MigrationError,
    UnsupportedMigrationError,
    MigrationIntegrityError,
    SerializationError,
)
from .backends.dilithium_py import DilithiumPyBackend, is_available as pqc_available

logger = logging.getLogger(__name__)


def can_migrate(identity_path: str) -> Tuple[bool, str]:
    """
    Check if an identity file can be migrated to hybrid format.
    
    Args:
        identity_path: Path to identity JSON file
        
    Returns:
        Tuple of (can_migrate, reason)
    """
    try:
        with open(identity_path, "r") as f:
            data = json.load(f)
        
        # Check if already hybrid
        if data.get("format") == "HYBRID_ED25519_MLDSA65":
            return False, "Already in hybrid format"
        
        # Check for v3.x format
        version = data.get("version", "")
        if not version.startswith("3."):
            return False, f"Unsupported version: {version}"
        
        # Check for required fields
        if "public_key" not in data:
            return False, "Missing public_key field"
        
        # Check if we have private key for full migration
        if "private_key" not in data:
            return True, "Public key only - will create peer identity"
        
        # Check PQC backend availability
        if not pqc_available():
            return False, "PQC backend (dilithium-py) not available"
        
        return True, "Ready for migration"
        
    except FileNotFoundError:
        return False, f"File not found: {identity_path}"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def migrate_legacy_identity(
    identity_path: str,
    output_path: Optional[str] = None,
    backup: bool = True,
) -> HybridIdentity:
    """
    Migrate a legacy ED25519 identity to hybrid format.
    
    Args:
        identity_path: Path to legacy identity JSON
        output_path: Path for migrated identity (default: same as input)
        backup: Create backup of original (default: True)
        
    Returns:
        Migrated HybridIdentity
        
    Raises:
        MigrationError: If migration fails
    """
    # Check if migration is possible
    can_do, reason = can_migrate(identity_path)
    if not can_do:
        raise UnsupportedMigrationError("3.x", VERSION)
    
    # Load legacy identity
    with open(identity_path, "r") as f:
        legacy_data = json.load(f)
    
    # Create backup if requested
    if backup:
        backup_path = f"{identity_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_path, "w") as f:
            json.dump(legacy_data, f, indent=2)
        logger.info(f"Created backup: {backup_path}")
    
    # Extract ED25519 keys
    ed_public = base64.b64decode(legacy_data["public_key"])
    ed_private = None
    if "private_key" in legacy_data:
        ed_private = base64.b64decode(legacy_data["private_key"])
    
    # Verify node ID consistency
    expected_node_id = hashlib.sha256(ed_public).hexdigest()[:NODE_ID_LENGTH]
    if legacy_data.get("node_id") != expected_node_id:
        raise MigrationIntegrityError(
            "Node ID does not match public key hash"
        )
    
    # Generate new ML-DSA-65 key pair
    if ed_private is not None:
        # Full migration with signing capability
        pqc_backend = DilithiumPyBackend()
        pqc_public, pqc_private = pqc_backend.keygen()
        logger.info("Generated new ML-DSA-65 key pair for migration")
    else:
        # Peer identity migration - no private keys
        raise MigrationError(
            "Cannot migrate public-key-only identity - no PQC key generation without original private key"
        )
    
    # Build key pairs
    ed25519_keys = ED25519KeyPair(public_key=ed_public, private_key=ed_private)
    pqc_keys = PQCKeyPair(public_key=pqc_public, private_key=pqc_private)
    hybrid_keys = HybridKeyPair(ed25519=ed25519_keys, pqc=pqc_keys)
    
    # Build capabilities (add PQC if not present)
    capabilities = legacy_data.get("capabilities", ["ATTEST", "RELAY", "GOSSIP"])
    if "PQC" not in capabilities:
        capabilities.append("PQC")
    
    # Create hybrid identity
    hybrid = HybridIdentity(
        node_id=legacy_data["node_id"],
        node_name=legacy_data.get("node_name", "MIGRATED"),
        keys=hybrid_keys,
        federation_id=legacy_data.get("federation_id", "CHAINBRIDGE-FEDERATION"),
        capabilities=capabilities,
        created_at=legacy_data.get("created_at", datetime.now(timezone.utc).isoformat()),
        signature_mode=SignatureMode.HYBRID,
    )
    
    # Save migrated identity
    save_path = output_path or identity_path
    hybrid.save(save_path)
    
    logger.info(f"Migration complete: {legacy_data['node_id'][:16]}... → HYBRID")
    
    return hybrid


def create_migration_report(
    identity_path: str,
) -> Dict[str, Any]:
    """
    Create a migration assessment report for an identity file.
    
    Args:
        identity_path: Path to identity file
        
    Returns:
        Dictionary with migration assessment
    """
    report = {
        "path": identity_path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "can_migrate": False,
        "reason": "",
        "current_format": "unknown",
        "has_private_key": False,
        "node_id": None,
        "node_name": None,
    }
    
    try:
        with open(identity_path, "r") as f:
            data = json.load(f)
        
        report["current_format"] = data.get("format", f"v{data.get('version', '?')}")
        report["has_private_key"] = "private_key" in data or (
            "keys" in data and "private" in data.get("keys", {}).get("ed25519", {})
        )
        report["node_id"] = data.get("node_id")
        report["node_name"] = data.get("node_name")
        
        can_do, reason = can_migrate(identity_path)
        report["can_migrate"] = can_do
        report["reason"] = reason
        
    except Exception as e:
        report["reason"] = str(e)
    
    return report
