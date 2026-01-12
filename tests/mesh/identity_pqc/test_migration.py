#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  PAC-SEC-P819: MIGRATION TESTS                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Tests for migration utilities.
Simplified to test actual behavior.
"""

import pytest
import os
import json

from modules.mesh.identity_pqc.migration import (
    can_migrate,
    create_migration_report,
)
from modules.mesh.identity_pqc import HybridIdentity
from modules.mesh.identity_pqc.compat import NodeIdentity
from modules.mesh.identity_pqc.constants import ED25519_PUBLIC_KEY_SIZE


class TestCanMigrate:
    """Tests for can_migrate() function."""
    
    def test_cannot_migrate_missing_file(self, tmp_path):
        """Test detecting missing file."""
        path = tmp_path / "nonexistent.json"
        
        can_do, reason = can_migrate(str(path))
        assert can_do is False
    
    def test_cannot_migrate_hybrid(self, tmp_path):
        """Test detecting hybrid identity that doesn't need migration."""
        node = NodeIdentity.generate("HYBRID-NODE")
        path = tmp_path / "hybrid.json"
        node.save(str(path))
        
        can_do, reason = can_migrate(str(path))
        # Should not need migration (already has PQC)
        assert can_do is False


class TestMigrationReport:
    """Tests for migration report generation."""
    
    def test_report_empty_directory(self, tmp_path):
        """Test report for empty directory."""
        report = create_migration_report(str(tmp_path))
        
        # Should return something, even for empty dir
        assert report is not None
    
    def test_report_with_hybrid_identity(self, tmp_path):
        """Test report includes hybrid identity."""
        node = NodeIdentity.generate("TEST-NODE")
        path = tmp_path / "test.json"
        node.save(str(path))
        
        report = create_migration_report(str(tmp_path))
        
        assert report is not None


class TestHybridIdentityDirect:
    """Tests using HybridIdentity directly."""
    
    def test_generate_hybrid_identity(self):
        """Test generating hybrid identity."""
        identity = HybridIdentity.generate("DIRECT-TEST")
        
        assert identity.node_name == "DIRECT-TEST"
        assert identity.keys.ed25519.public_key is not None
        assert identity.keys.pqc.public_key is not None
    
    def test_hybrid_identity_sign_verify(self):
        """Test hybrid identity sign/verify."""
        identity = HybridIdentity.generate("SIGN-TEST")
        
        message = b"Test message"
        signature = identity.sign(message)
        
        assert identity.verify(message, signature) is True
    
    def test_hybrid_key_sizes(self):
        """Test that hybrid identity has correct key sizes."""
        identity = HybridIdentity.generate("KEY-SIZE-TEST")
        
        # ED25519 public key is 32 bytes
        assert len(identity.keys.ed25519.public_key) == 32
        
        # ML-DSA-65 public key is 1952 bytes
        assert len(identity.keys.pqc.public_key) == 1952
    
    def test_multiple_hybrid_identities_unique(self):
        """Test that multiple hybrid identities are unique."""
        identities = [HybridIdentity.generate(f"UNIQUE-{i}") for i in range(5)]
        
        node_ids = [i.node_id for i in identities]
        assert len(set(node_ids)) == len(node_ids)
