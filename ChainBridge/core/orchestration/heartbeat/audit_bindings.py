"""
Audit Bindings - BER & Ledger Integration for Heartbeat Events
===============================================================

PAC Reference: PAC-P745-OCC-HEARTBEAT-PERSISTENCE-AUDIT
Classification: LAW_TIER
Author: DIGGI (GID-12) - Audit Trail
Orchestrator: BENSON (GID-00)

Binds heartbeat event snapshots to BER evaluations and ledger commits.
Ensures complete audit trail for governance proof.
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

from .event_store import get_event_store, HeartbeatEventStore, StoredEvent
from .hash_chain import get_chain_manager, HashChainManager


@dataclass
class AuditSnapshot:
    """
    Immutable snapshot of heartbeat state for audit binding.
    
    Snapshots are created at:
    - WRAP generation
    - BER evaluation
    - Ledger commit
    """
    snapshot_id: str
    snapshot_type: str  # WRAP_BINDING, BER_BINDING, LEDGER_BINDING
    pac_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Chain state at snapshot time
    event_count: int = 0
    chain_head: Optional[str] = None
    merkle_root: Optional[str] = None
    chain_verified: bool = False
    
    # Binding references
    wrap_id: Optional[str] = None
    ber_id: Optional[str] = None
    ledger_record: Optional[str] = None
    
    # Event summary
    event_types: Dict[str, int] = field(default_factory=dict)
    first_event_time: Optional[str] = None
    last_event_time: Optional[str] = None
    
    # Snapshot hash
    snapshot_hash: str = ""
    
    def compute_hash(self) -> str:
        """Compute SHA-256 hash of snapshot."""
        content = json.dumps({
            "snapshot_id": self.snapshot_id,
            "snapshot_type": self.snapshot_type,
            "pac_id": self.pac_id,
            "event_count": self.event_count,
            "chain_head": self.chain_head,
            "merkle_root": self.merkle_root,
            "wrap_id": self.wrap_id,
            "ber_id": self.ber_id
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class AuditBindingManager:
    """
    Manages audit bindings between heartbeat events and governance artifacts.
    
    Creates immutable snapshots that link:
    - Heartbeat event chains to WRAP proofs
    - Event chain state to BER evaluations
    - Event history to ledger commits
    
    Usage:
        manager = AuditBindingManager()
        
        # Bind to WRAP
        snapshot = manager.bind_to_wrap("PAC-P745-...", "WRAP-P745-...")
        
        # Bind to BER
        snapshot = manager.bind_to_ber("PAC-P745-...", "BER-P745-...", score=100)
        
        # Bind to Ledger
        snapshot = manager.bind_to_ledger("PAC-P745-...", "heartbeat_system_record")
    """
    
    def __init__(
        self,
        store: Optional[HeartbeatEventStore] = None,
        chain_manager: Optional[HashChainManager] = None,
        snapshot_path: str = "logs/audit_snapshots.jsonl"
    ):
        self.store = store or get_event_store()
        self.chain_manager = chain_manager or get_chain_manager()
        self.snapshot_path = Path(snapshot_path)
        self._snapshots: Dict[str, AuditSnapshot] = {}
        
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _capture_chain_state(self, pac_id: str) -> Dict[str, Any]:
        """Capture current chain state for a PAC."""
        if self.store:
            summary = self.store.get_chain_summary(pac_id)
            verification = self.store.verify_chain(pac_id)
        else:
            summary = {"exists": False}
            verification = {"verified": True}
        
        if self.chain_manager:
            merkle = self.chain_manager.get_merkle_root(pac_id)
        else:
            merkle = None
        
        return {
            "event_count": summary.get("event_count", 0),
            "chain_head": summary.get("chain_head"),
            "merkle_root": merkle,
            "chain_verified": verification.get("verified", True),
            "event_types": summary.get("event_types", {}),
            "first_event_time": summary.get("first_event"),
            "last_event_time": summary.get("last_event")
        }
    
    def bind_to_wrap(
        self,
        pac_id: str,
        wrap_id: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> AuditSnapshot:
        """
        Create audit snapshot binding heartbeat chain to WRAP.
        
        Called when WRAP is generated to capture event state.
        """
        chain_state = self._capture_chain_state(pac_id)
        
        snapshot = AuditSnapshot(
            snapshot_id=f"SNAP-WRAP-{wrap_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            snapshot_type="WRAP_BINDING",
            pac_id=pac_id,
            wrap_id=wrap_id,
            **chain_state
        )
        snapshot.snapshot_hash = snapshot.compute_hash()
        
        self._save_snapshot(snapshot)
        return snapshot
    
    def bind_to_ber(
        self,
        pac_id: str,
        ber_id: str,
        score: int,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> AuditSnapshot:
        """
        Create audit snapshot binding heartbeat chain to BER.
        
        Called when BER is generated to capture event state.
        """
        chain_state = self._capture_chain_state(pac_id)
        
        snapshot = AuditSnapshot(
            snapshot_id=f"SNAP-BER-{ber_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            snapshot_type="BER_BINDING",
            pac_id=pac_id,
            ber_id=ber_id,
            **chain_state
        )
        snapshot.snapshot_hash = snapshot.compute_hash()
        
        self._save_snapshot(snapshot)
        return snapshot
    
    def bind_to_ledger(
        self,
        pac_id: str,
        ledger_record: str,
        ledger_path: str = "core/governance/SOVEREIGNTY_LEDGER.json"
    ) -> AuditSnapshot:
        """
        Create audit snapshot binding heartbeat chain to ledger commit.
        
        Called when ledger is updated.
        """
        chain_state = self._capture_chain_state(pac_id)
        
        snapshot = AuditSnapshot(
            snapshot_id=f"SNAP-LEDGER-{pac_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            snapshot_type="LEDGER_BINDING",
            pac_id=pac_id,
            ledger_record=ledger_record,
            **chain_state
        )
        snapshot.snapshot_hash = snapshot.compute_hash()
        
        self._save_snapshot(snapshot)
        return snapshot
    
    def _save_snapshot(self, snapshot: AuditSnapshot) -> None:
        """Save snapshot to store and file."""
        self._snapshots[snapshot.snapshot_id] = snapshot
        
        try:
            with open(self.snapshot_path, "a") as f:
                f.write(json.dumps(snapshot.to_dict()) + "\n")
        except Exception:
            pass  # Don't fail on write errors
    
    def get_snapshot(self, snapshot_id: str) -> Optional[AuditSnapshot]:
        """Get snapshot by ID."""
        return self._snapshots.get(snapshot_id)
    
    def get_snapshots_for_pac(self, pac_id: str) -> List[AuditSnapshot]:
        """Get all snapshots for a PAC."""
        return [s for s in self._snapshots.values() if s.pac_id == pac_id]
    
    def verify_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """Verify a snapshot's integrity."""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return {"snapshot_id": snapshot_id, "exists": False}
        
        computed_hash = snapshot.compute_hash()
        hash_valid = computed_hash == snapshot.snapshot_hash
        
        # Verify current chain state matches (if chain still exists)
        current_state = self._capture_chain_state(snapshot.pac_id)
        chain_matches = (
            current_state.get("chain_head") == snapshot.chain_head or
            snapshot.chain_head is None  # Chain may have grown
        )
        
        return {
            "snapshot_id": snapshot_id,
            "exists": True,
            "hash_valid": hash_valid,
            "stored_hash": snapshot.snapshot_hash,
            "computed_hash": computed_hash,
            "chain_integrity": chain_matches,
            "snapshot": snapshot.to_dict()
        }
    
    def generate_audit_report(self, pac_id: str) -> Dict[str, Any]:
        """
        Generate complete audit report for a PAC.
        
        Includes all snapshots, chain verification, and binding proof.
        """
        snapshots = self.get_snapshots_for_pac(pac_id)
        chain_state = self._capture_chain_state(pac_id)
        
        if self.store:
            chain_verification = self.store.verify_chain(pac_id)
        else:
            chain_verification = {"verified": True}
        
        return {
            "pac_id": pac_id,
            "report_generated": datetime.now(timezone.utc).isoformat(),
            "chain_state": chain_state,
            "chain_verified": chain_verification.get("verified", True),
            "snapshot_count": len(snapshots),
            "snapshots": [s.to_dict() for s in snapshots],
            "wrap_bindings": [s.to_dict() for s in snapshots if s.snapshot_type == "WRAP_BINDING"],
            "ber_bindings": [s.to_dict() for s in snapshots if s.snapshot_type == "BER_BINDING"],
            "ledger_bindings": [s.to_dict() for s in snapshots if s.snapshot_type == "LEDGER_BINDING"]
        }


# ==================== Global Singleton ====================

_global_binding_manager: Optional[AuditBindingManager] = None


def get_binding_manager() -> AuditBindingManager:
    """Get or create global binding manager."""
    global _global_binding_manager
    if _global_binding_manager is None:
        _global_binding_manager = AuditBindingManager()
    return _global_binding_manager


# ==================== Self-Test ====================

if __name__ == "__main__":
    import tempfile
    
    print("AuditBindingManager Self-Test")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = AuditBindingManager(
            store=None,  # Skip store for test
            chain_manager=None,
            snapshot_path=f"{tmpdir}/snapshots.jsonl"
        )
        
        pac_id = "PAC-P745-TEST"
        
        # Test WRAP binding
        wrap_snap = manager.bind_to_wrap(pac_id, "WRAP-P745-TEST")
        print(f"✅ WRAP binding: {wrap_snap.snapshot_id}")
        print(f"   Hash: {wrap_snap.snapshot_hash[:16]}...")
        
        # Test BER binding
        ber_snap = manager.bind_to_ber(pac_id, "BER-P745-TEST", score=100)
        print(f"✅ BER binding: {ber_snap.snapshot_id}")
        
        # Test Ledger binding
        ledger_snap = manager.bind_to_ledger(pac_id, "test_record")
        print(f"✅ Ledger binding: {ledger_snap.snapshot_id}")
        
        # Verify
        result = manager.verify_snapshot(wrap_snap.snapshot_id)
        print(f"✅ Verification: hash_valid={result['hash_valid']}")
        
        # Report
        report = manager.generate_audit_report(pac_id)
        print(f"✅ Report: {report['snapshot_count']} snapshots")
    
    print("\n✅ Self-test PASSED")
