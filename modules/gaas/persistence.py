"""
GaaS Persistence Integration
============================

Integrates Sovereign State Sharding (P920) with GaaS Controller (P900).

This module provides:
- Automatic shard creation for new tenants
- Shard lifecycle management tied to tenant lifecycle
- Persistence verification (spawn → write → kill → respawn → verify)

Invariants:
    INV-DATA-003 (Shard Isolation): Each tenant has isolated storage
    INV-DATA-004 (Persistence Guarantee): Data survives process death

PAC Reference: PAC-OCC-P920-SHARDING
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from modules.data.sharding import ShardManager, TenantShard, ShardConfig, ShardState

logger = logging.getLogger(__name__)


class GaaSPersistence:
    """
    Persistence layer for GaaS tenants.
    
    Integrates with GaaSController to provide automatic
    shard management for tenant lifecycle events.
    
    Usage:
        persistence = GaaSPersistence(base_dir="/data/gaas")
        
        # On tenant spawn
        persistence.init_tenant("tenant-001")
        
        # Write tenant data
        persistence.write_entry("tenant-001", "transaction", {"amount": 100})
        
        # On tenant termination
        persistence.checkpoint_tenant("tenant-001")
    """
    
    def __init__(
        self,
        base_dir: str = "/tmp/chainbridge_gaas/shards",
        use_encryption: bool = True,
    ):
        self.base_dir = Path(base_dir)
        self._shard_manager = ShardManager(
            base_dir=str(self.base_dir),
            use_encryption=use_encryption,
            log_dir=str(self.base_dir / "logs"),
        )
        
        logger.info(f"[GAAS_PERSIST] Initialized at {self.base_dir}")
    
    def init_tenant(self, tenant_id: str) -> TenantShard:
        """
        Initialize persistence for a new tenant.
        
        Creates or opens the tenant's shard and records
        initialization in the audit log.
        """
        shard = self._shard_manager.get_shard(tenant_id, create=True)
        
        # Record initialization
        shard.write_ledger("TENANT_INIT", {
            "tenant_id": tenant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "persistence_initialized",
        })
        
        logger.info(f"[GAAS_PERSIST] Initialized tenant {tenant_id}")
        return shard
    
    def get_shard(self, tenant_id: str) -> TenantShard:
        """Get the shard for a tenant (must be initialized first)."""
        return self._shard_manager.get_shard(tenant_id, create=False)
    
    def write_entry(self, tenant_id: str, entry_type: str, payload: Any, signature: bytes = None) -> int:
        """
        Write a ledger entry for a tenant.
        
        Returns the entry ID.
        """
        shard = self._shard_manager.get_shard(tenant_id)
        return shard.write_ledger(entry_type, payload, signature)
    
    def read_entries(self, tenant_id: str, entry_type: str = None, limit: int = 100) -> list:
        """Read ledger entries for a tenant."""
        shard = self._shard_manager.get_shard(tenant_id)
        return shard.read_ledger(entry_type=entry_type, limit=limit)
    
    def set_config(self, tenant_id: str, key: str, value: Any):
        """Set a configuration value for a tenant."""
        shard = self._shard_manager.get_shard(tenant_id)
        shard.set_config(key, value)
    
    def get_config(self, tenant_id: str, key: str, default: Any = None) -> Any:
        """Get a configuration value for a tenant."""
        shard = self._shard_manager.get_shard(tenant_id)
        return shard.get_config(key, default)
    
    def checkpoint_tenant(self, tenant_id: str):
        """
        Checkpoint tenant's shard before shutdown.
        
        Ensures all data is flushed to disk (WAL checkpoint).
        """
        try:
            shard = self._shard_manager.get_shard(tenant_id, create=False)
            
            # Record checkpoint
            shard.write_ledger("CHECKPOINT", {
                "tenant_id": tenant_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            
            # Close shard (triggers WAL checkpoint)
            self._shard_manager.close_shard(tenant_id)
            
            logger.info(f"[GAAS_PERSIST] Checkpointed tenant {tenant_id}")
        except Exception as e:
            logger.error(f"[GAAS_PERSIST] Checkpoint failed for {tenant_id}: {e}")
    
    def verify_tenant_persistence(self, tenant_id: str) -> Dict[str, Any]:
        """
        Verify that tenant's data persisted correctly.
        
        Used after respawn to confirm INV-DATA-004.
        """
        try:
            shard = self._shard_manager.get_shard(tenant_id, create=False)
            
            # Get integrity check
            integrity = shard.verify_integrity()
            
            # Check for initialization entry
            entries = shard.read_ledger(entry_type="TENANT_INIT", limit=1)
            has_init = len(entries) > 0
            
            return {
                "tenant_id": tenant_id,
                "verified": integrity["valid"] and has_init,
                "integrity": integrity,
                "has_init_entry": has_init,
                "ledger_count": integrity.get("ledger_count", 0),
            }
        except Exception as e:
            return {
                "tenant_id": tenant_id,
                "verified": False,
                "error": str(e),
            }
    
    def list_persisted_tenants(self) -> list:
        """List all tenants with persisted data."""
        return self._shard_manager.list_persisted_shards()
    
    def verify_all_isolation(self) -> Dict[str, Any]:
        """Verify shard isolation across all tenants."""
        return self._shard_manager.verify_isolation()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics."""
        return self._shard_manager.get_total_stats()
    
    def shutdown(self):
        """Shutdown persistence layer, closing all shards."""
        self._shard_manager.close_all()
        logger.info("[GAAS_PERSIST] Shutdown complete")


def integrate_with_gaas_controller(controller, persistence: GaaSPersistence):
    """
    Integrate persistence with a GaaSController instance.
    
    Sets up callbacks to automatically manage shard lifecycle.
    """
    def on_spawn(tenant_id: str):
        persistence.init_tenant(tenant_id)
    
    def on_terminate(tenant_id: str, reason: str):
        persistence.checkpoint_tenant(tenant_id)
    
    controller.on_spawn(on_spawn)
    controller.on_terminate(on_terminate)
    
    logger.info("[GAAS_PERSIST] Integrated with GaaSController")
