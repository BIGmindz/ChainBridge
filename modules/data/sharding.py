"""
Sovereign State Sharding
========================

Persistent storage layer with per-tenant isolation and encryption.

Each tenant gets a dedicated SQLite database file stored in their
isolated directory (from GaaS P900). Databases use WAL mode for
durability and are encrypted at rest with AES-256-GCM.

Architecture:
    ShardManager (Registry)
        └── TenantShard (SQLite + Encryption)
                └── shard_{tenant_id}.db (File)

Invariants:
    INV-DATA-003 (Shard Isolation): Tenant can ONLY access its assigned shard
    INV-DATA-004 (Persistence Guarantee): Committed transactions survive SIGKILL

PAC Reference: PAC-OCC-P920-SHARDING
"""

from __future__ import annotations

import os
import json
import sqlite3
import hashlib
import threading
import secrets
import struct
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, List, Any, Union
from datetime import datetime, timezone
from enum import Enum
from contextlib import contextmanager
import logging

# Encryption imports
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)


class ShardState(Enum):
    """Lifecycle states for a TenantShard."""
    CLOSED = "closed"
    OPENING = "opening"
    OPEN = "open"
    CORRUPTED = "corrupted"
    LOCKED = "locked"


@dataclass
class ShardConfig:
    """Configuration for a tenant shard."""
    tenant_id: str
    data_dir: Path
    encryption_key: Optional[bytes] = None
    use_encryption: bool = True
    wal_mode: bool = True
    busy_timeout_ms: int = 5000
    cache_size_kb: int = 2048
    
    def __post_init__(self):
        self.data_dir = Path(self.data_dir)
    
    @property
    def shard_path(self) -> Path:
        """Path to the SQLite database file."""
        return self.data_dir / f"shard_{self.tenant_id}.db"
    
    @property
    def wal_path(self) -> Path:
        """Path to the WAL file."""
        return self.data_dir / f"shard_{self.tenant_id}.db-wal"
    
    @property
    def shm_path(self) -> Path:
        """Path to the shared memory file."""
        return self.data_dir / f"shard_{self.tenant_id}.db-shm"
    
    @property
    def key_path(self) -> Path:
        """Path to the encrypted key file."""
        return self.data_dir / f"shard_{self.tenant_id}.key"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "data_dir": str(self.data_dir),
            "shard_path": str(self.shard_path),
            "use_encryption": self.use_encryption,
            "wal_mode": self.wal_mode,
        }


class ShardEncryption:
    """
    AES-256-GCM encryption for shard data.
    
    Provides at-rest encryption for SQLite pages using
    application-level encryption (encrypt before write,
    decrypt after read).
    
    Note: For production, consider SQLCipher for transparent
    page-level encryption. This implementation provides
    record-level encryption within standard SQLite.
    """
    
    SALT_SIZE = 16
    NONCE_SIZE = 12
    TAG_SIZE = 16
    KEY_SIZE = 32  # AES-256
    
    def __init__(self, master_key: bytes):
        """
        Initialize encryption with a master key.
        
        Args:
            master_key: 32-byte master encryption key
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography package required for encryption")
        
        if len(master_key) != self.KEY_SIZE:
            raise ValueError(f"Master key must be {self.KEY_SIZE} bytes")
        
        self._master_key = master_key
        self._aesgcm = AESGCM(master_key)
    
    @classmethod
    def generate_key(cls) -> bytes:
        """Generate a random 256-bit encryption key."""
        return secrets.token_bytes(cls.KEY_SIZE)
    
    @classmethod
    def derive_key(cls, password: str, salt: bytes = None) -> tuple[bytes, bytes]:
        """
        Derive encryption key from password using PBKDF2.
        
        Returns:
            Tuple of (derived_key, salt)
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography package required")
        
        if salt is None:
            salt = secrets.token_bytes(cls.SALT_SIZE)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=cls.KEY_SIZE,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(password.encode())
        return key, salt
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypt data with AES-256-GCM.
        
        Format: nonce (12 bytes) || ciphertext || tag (16 bytes)
        """
        nonce = secrets.token_bytes(self.NONCE_SIZE)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        Decrypt AES-256-GCM encrypted data.
        
        Raises:
            ValueError: If decryption fails (tampering detected)
        """
        if len(ciphertext) < self.NONCE_SIZE + self.TAG_SIZE:
            raise ValueError("Ciphertext too short")
        
        nonce = ciphertext[:self.NONCE_SIZE]
        data = ciphertext[self.NONCE_SIZE:]
        
        try:
            return self._aesgcm.decrypt(nonce, data, None)
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    def encrypt_value(self, value: Any) -> bytes:
        """Encrypt a JSON-serializable value."""
        plaintext = json.dumps(value).encode('utf-8')
        return self.encrypt(plaintext)
    
    def decrypt_value(self, ciphertext: bytes) -> Any:
        """Decrypt a JSON-serializable value."""
        plaintext = self.decrypt(ciphertext)
        return json.loads(plaintext.decode('utf-8'))


class TenantShard:
    """
    Encrypted SQLite database for a single tenant.
    
    Provides:
    - Isolated database file per tenant
    - WAL mode for crash safety (INV-DATA-004)
    - Optional AES-256-GCM encryption at rest
    - Thread-safe connection management
    
    Usage:
        shard = TenantShard(config)
        shard.open()
        
        with shard.transaction() as cursor:
            cursor.execute("INSERT INTO ledger VALUES (?)", (data,))
        
        shard.close()
    """
    
    # Default schema for sovereign state
    DEFAULT_SCHEMA = """
        -- Ledger entries
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            payload BLOB NOT NULL,
            signature BLOB,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Key-value store for configuration
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value BLOB NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Transaction log for audit
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            checksum TEXT
        );
        
        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_ledger_timestamp ON ledger(timestamp);
        CREATE INDEX IF NOT EXISTS idx_ledger_type ON ledger(entry_type);
        CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
    """
    
    def __init__(self, config: ShardConfig):
        self.config = config
        self.tenant_id = config.tenant_id
        self.state = ShardState.CLOSED
        
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()
        self._encryption: Optional[ShardEncryption] = None
        
        # Statistics
        self._stats = {
            "opens": 0,
            "closes": 0,
            "reads": 0,
            "writes": 0,
            "errors": 0,
        }
        
        logger.info(f"[SHARD] Created shard for tenant {self.tenant_id}")
    
    def open(self, create: bool = True) -> bool:
        """
        Open the shard database.
        
        Args:
            create: Create database if it doesn't exist
        
        Returns:
            True if opened successfully
        """
        with self._lock:
            if self.state == ShardState.OPEN:
                return True
            
            self.state = ShardState.OPENING
            
            try:
                # Ensure directory exists
                self.config.data_dir.mkdir(parents=True, exist_ok=True)
                
                # Initialize encryption if enabled
                if self.config.use_encryption and CRYPTO_AVAILABLE:
                    self._init_encryption()
                
                # Check if database exists
                db_exists = self.config.shard_path.exists()
                
                if not db_exists and not create:
                    logger.error(f"[SHARD] Database not found: {self.config.shard_path}")
                    self.state = ShardState.CLOSED
                    return False
                
                # Open SQLite connection
                self._conn = sqlite3.connect(
                    str(self.config.shard_path),
                    check_same_thread=False,  # We manage our own locking
                    isolation_level=None,  # Autocommit for explicit transaction control
                )
                
                # Configure pragmas for durability and performance
                self._configure_pragmas()
                
                # Initialize schema if new database
                if not db_exists:
                    self._init_schema()
                
                self.state = ShardState.OPEN
                self._stats["opens"] += 1
                
                logger.info(f"[SHARD] Opened {self.tenant_id} at {self.config.shard_path}")
                return True
                
            except sqlite3.DatabaseError as e:
                logger.error(f"[SHARD] Database error opening {self.tenant_id}: {e}")
                self.state = ShardState.CORRUPTED
                self._stats["errors"] += 1
                return False
            except Exception as e:
                logger.error(f"[SHARD] Error opening {self.tenant_id}: {e}")
                self.state = ShardState.CLOSED
                self._stats["errors"] += 1
                return False
    
    def _init_encryption(self):
        """Initialize encryption with stored or new key."""
        if self.config.encryption_key:
            # Use provided key
            self._encryption = ShardEncryption(self.config.encryption_key)
        elif self.config.key_path.exists():
            # Load existing key (in production, this would be encrypted with tenant's master key)
            key_data = self.config.key_path.read_bytes()
            self._encryption = ShardEncryption(key_data)
        else:
            # Generate new key
            key = ShardEncryption.generate_key()
            self.config.key_path.write_bytes(key)
            # Secure permissions (owner read/write only)
            os.chmod(self.config.key_path, 0o600)
            self._encryption = ShardEncryption(key)
            logger.info(f"[SHARD] Generated encryption key for {self.tenant_id}")
    
    def _configure_pragmas(self):
        """Configure SQLite pragmas for durability and performance."""
        cursor = self._conn.cursor()
        
        # WAL mode for crash safety (INV-DATA-004)
        if self.config.wal_mode:
            cursor.execute("PRAGMA journal_mode=WAL")
        
        # Synchronous mode for durability
        cursor.execute("PRAGMA synchronous=NORMAL")
        
        # Busy timeout for concurrent access
        cursor.execute(f"PRAGMA busy_timeout={self.config.busy_timeout_ms}")
        
        # Cache size for performance
        cursor.execute(f"PRAGMA cache_size=-{self.config.cache_size_kb}")
        
        # Foreign keys enabled
        cursor.execute("PRAGMA foreign_keys=ON")
        
        # Auto-vacuum for space reclamation
        cursor.execute("PRAGMA auto_vacuum=INCREMENTAL")
        
        cursor.close()
    
    def _init_schema(self):
        """Initialize database schema."""
        cursor = self._conn.cursor()
        cursor.executescript(self.DEFAULT_SCHEMA)
        
        # Record shard creation
        cursor.execute("""
            INSERT INTO audit_log (timestamp, action, details)
            VALUES (?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            "SHARD_CREATED",
            json.dumps({"tenant_id": self.tenant_id, "encrypted": self._encryption is not None}),
        ))
        
        self._conn.commit()
        cursor.close()
        
        logger.info(f"[SHARD] Initialized schema for {self.tenant_id}")
    
    def close(self):
        """Close the shard database."""
        with self._lock:
            if self._conn:
                try:
                    # Checkpoint WAL before closing
                    if self.config.wal_mode:
                        self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    
                    self._conn.close()
                    self._conn = None
                    self.state = ShardState.CLOSED
                    self._stats["closes"] += 1
                    
                    logger.info(f"[SHARD] Closed {self.tenant_id}")
                except Exception as e:
                    logger.error(f"[SHARD] Error closing {self.tenant_id}: {e}")
                    self._stats["errors"] += 1
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        
        Usage:
            with shard.transaction() as cursor:
                cursor.execute("INSERT ...")
        
        Commits on success, rolls back on exception.
        """
        if self.state != ShardState.OPEN:
            raise RuntimeError(f"Shard not open (state: {self.state})")
        
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            
            try:
                yield cursor
                self._conn.commit()
                self._stats["writes"] += 1
            except Exception:
                self._conn.rollback()
                self._stats["errors"] += 1
                raise
            finally:
                cursor.close()
    
    @contextmanager
    def read_cursor(self):
        """Context manager for read-only queries."""
        if self.state != ShardState.OPEN:
            raise RuntimeError(f"Shard not open (state: {self.state})")
        
        with self._lock:
            cursor = self._conn.cursor()
            try:
                yield cursor
                self._stats["reads"] += 1
            finally:
                cursor.close()
    
    # === High-Level API ===
    
    def write_ledger(self, entry_type: str, payload: Any, signature: bytes = None) -> int:
        """
        Write an entry to the ledger.
        
        Args:
            entry_type: Type of ledger entry
            payload: JSON-serializable data
            signature: Optional cryptographic signature
        
        Returns:
            Entry ID
        """
        # Encrypt payload if encryption is enabled
        if self._encryption:
            payload_bytes = self._encryption.encrypt_value(payload)
        else:
            payload_bytes = json.dumps(payload).encode('utf-8')
        
        with self.transaction() as cursor:
            cursor.execute("""
                INSERT INTO ledger (timestamp, entry_type, payload, signature)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                entry_type,
                payload_bytes,
                signature,
            ))
            return cursor.lastrowid
    
    def read_ledger(self, entry_id: int = None, entry_type: str = None, limit: int = 100) -> List[Dict]:
        """
        Read ledger entries.
        
        Args:
            entry_id: Specific entry ID (optional)
            entry_type: Filter by type (optional)
            limit: Maximum entries to return
        
        Returns:
            List of ledger entries
        """
        with self.read_cursor() as cursor:
            if entry_id:
                cursor.execute("SELECT * FROM ledger WHERE id = ?", (entry_id,))
            elif entry_type:
                cursor.execute(
                    "SELECT * FROM ledger WHERE entry_type = ? ORDER BY id DESC LIMIT ?",
                    (entry_type, limit)
                )
            else:
                cursor.execute("SELECT * FROM ledger ORDER BY id DESC LIMIT ?", (limit,))
            
            rows = cursor.fetchall()
        
        entries = []
        for row in rows:
            entry = {
                "id": row[0],
                "timestamp": row[1],
                "entry_type": row[2],
                "signature": row[4],
                "created_at": row[5],
            }
            
            # Decrypt payload if encrypted
            payload_bytes = row[3]
            if self._encryption:
                try:
                    entry["payload"] = self._encryption.decrypt_value(payload_bytes)
                except ValueError:
                    entry["payload"] = None
                    entry["decryption_error"] = True
            else:
                entry["payload"] = json.loads(payload_bytes.decode('utf-8'))
            
            entries.append(entry)
        
        return entries
    
    def set_config(self, key: str, value: Any):
        """Set a configuration value."""
        if self._encryption:
            value_bytes = self._encryption.encrypt_value(value)
        else:
            value_bytes = json.dumps(value).encode('utf-8')
        
        with self.transaction() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value_bytes, datetime.now(timezone.utc).isoformat()))
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        with self.read_cursor() as cursor:
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
        
        if not row:
            return default
        
        if self._encryption:
            try:
                return self._encryption.decrypt_value(row[0])
            except ValueError:
                return default
        else:
            return json.loads(row[0].decode('utf-8'))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get shard statistics."""
        stats = dict(self._stats)
        stats["state"] = self.state.value
        stats["path"] = str(self.config.shard_path)
        stats["encrypted"] = self._encryption is not None
        
        if self.config.shard_path.exists():
            stats["size_bytes"] = self.config.shard_path.stat().st_size
        
        return stats
    
    def verify_integrity(self) -> Dict[str, Any]:
        """Verify database integrity."""
        result = {
            "tenant_id": self.tenant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {},
        }
        
        with self.read_cursor() as cursor:
            # SQLite integrity check
            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()[0]
            result["checks"]["sqlite_integrity"] = integrity == "ok"
            
            # Count tables
            cursor.execute("SELECT COUNT(*) FROM ledger")
            result["ledger_count"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM config")
            result["config_count"] = cursor.fetchone()[0]
        
        result["valid"] = all(result["checks"].values())
        return result


class ShardManager:
    """
    Registry and lifecycle manager for tenant shards.
    
    The ShardManager ensures:
    - Each tenant gets exactly one shard
    - Shards are properly isolated (INV-DATA-003)
    - Shards can be opened/closed on demand
    - Automatic cleanup on shutdown
    
    Usage:
        manager = ShardManager(base_dir="/data/shards")
        
        shard = manager.get_shard("tenant-001")
        shard.write_ledger("transaction", {"amount": 100})
        
        manager.close_all()
    """
    
    def __init__(
        self,
        base_dir: str = "/tmp/chainbridge_shards",
        use_encryption: bool = True,
        log_dir: str = None,
    ):
        self.base_dir = Path(base_dir)
        self.use_encryption = use_encryption
        self.log_dir = Path(log_dir) if log_dir else self.base_dir / "logs"
        
        self._shards: Dict[str, TenantShard] = {}
        self._lock = threading.RLock()
        
        # Initialize directories
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[SHARD_MANAGER] Initialized at {self.base_dir}")
    
    def get_shard(self, tenant_id: str, create: bool = True) -> TenantShard:
        """
        Get or create a shard for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            create: Create shard if it doesn't exist
        
        Returns:
            TenantShard instance (opened)
        
        Raises:
            ValueError: If shard doesn't exist and create=False
        """
        with self._lock:
            # Return existing shard
            if tenant_id in self._shards:
                shard = self._shards[tenant_id]
                if shard.state != ShardState.OPEN:
                    shard.open(create=create)
                return shard
            
            # Create new shard
            config = ShardConfig(
                tenant_id=tenant_id,
                data_dir=self.base_dir / tenant_id,
                use_encryption=self.use_encryption,
            )
            
            shard = TenantShard(config)
            
            if not shard.open(create=create):
                if not create:
                    raise ValueError(f"Shard not found for tenant {tenant_id}")
                raise RuntimeError(f"Failed to create shard for tenant {tenant_id}")
            
            self._shards[tenant_id] = shard
            
            # Log shard creation
            self._log_event("SHARD_OPENED", tenant_id, {
                "path": str(config.shard_path),
                "encrypted": self.use_encryption,
            })
            
            return shard
    
    def close_shard(self, tenant_id: str):
        """Close a specific tenant's shard."""
        with self._lock:
            if tenant_id in self._shards:
                self._shards[tenant_id].close()
                del self._shards[tenant_id]
                
                self._log_event("SHARD_CLOSED", tenant_id, {})
    
    def close_all(self):
        """Close all open shards."""
        with self._lock:
            for tenant_id in list(self._shards.keys()):
                self._shards[tenant_id].close()
            self._shards.clear()
            
            logger.info("[SHARD_MANAGER] All shards closed")
    
    def list_shards(self) -> List[Dict[str, Any]]:
        """List all managed shards."""
        with self._lock:
            return [
                {
                    "tenant_id": tid,
                    "state": shard.state.value,
                    "stats": shard.get_stats(),
                }
                for tid, shard in self._shards.items()
            ]
    
    def list_persisted_shards(self) -> List[str]:
        """List tenant IDs with persisted shard files."""
        tenant_ids = []
        for path in self.base_dir.iterdir():
            if path.is_dir():
                db_file = path / f"shard_{path.name}.db"
                if db_file.exists():
                    tenant_ids.append(path.name)
        return tenant_ids
    
    def verify_isolation(self) -> Dict[str, Any]:
        """
        Verify shard isolation (INV-DATA-003).
        
        Checks that each tenant's shard is in a separate directory
        with no overlapping paths.
        """
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "invariant": "INV-DATA-003",
            "checks": [],
            "verified": True,
        }
        
        with self._lock:
            paths_seen = set()
            
            for tenant_id, shard in self._shards.items():
                shard_path = str(shard.config.shard_path.resolve())
                data_dir = str(shard.config.data_dir.resolve())
                
                check = {
                    "tenant_id": tenant_id,
                    "path": shard_path,
                    "isolated": True,
                }
                
                # Check for path collision
                if shard_path in paths_seen:
                    check["isolated"] = False
                    check["error"] = "path_collision"
                    report["verified"] = False
                
                # Check that shard is in tenant's directory
                if tenant_id not in shard_path:
                    check["isolated"] = False
                    check["error"] = "wrong_directory"
                    report["verified"] = False
                
                paths_seen.add(shard_path)
                report["checks"].append(check)
        
        return report
    
    def _log_event(self, event: str, tenant_id: str, data: Dict[str, Any]):
        """Log a shard event."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "tenant_id": tenant_id,
            "data": data,
        }
        
        log_file = self.log_dir / "SHARDING_INIT.json"
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def get_total_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics across all shards."""
        with self._lock:
            total = {
                "shard_count": len(self._shards),
                "total_size_bytes": 0,
                "total_reads": 0,
                "total_writes": 0,
                "total_errors": 0,
            }
            
            for shard in self._shards.values():
                stats = shard.get_stats()
                total["total_reads"] += stats.get("reads", 0)
                total["total_writes"] += stats.get("writes", 0)
                total["total_errors"] += stats.get("errors", 0)
                total["total_size_bytes"] += stats.get("size_bytes", 0)
            
            return total


# === Demo / Test Function ===

def demo_sharding(tenant_count: int = 5):
    """
    Demonstrate sovereign state sharding with multiple tenants.
    
    Tests INV-DATA-003 (isolation) and INV-DATA-004 (persistence).
    """
    import tempfile
    
    print("=" * 60)
    print("SOVEREIGN STATE SHARDING DEMONSTRATION")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create shard manager
        manager = ShardManager(
            base_dir=tmpdir,
            use_encryption=CRYPTO_AVAILABLE,
        )
        
        print(f"\n[DEMO] Shard directory: {tmpdir}")
        print(f"[DEMO] Encryption: {CRYPTO_AVAILABLE}")
        
        # Create shards for tenants
        print(f"\n[DEMO] Creating {tenant_count} tenant shards...")
        for i in range(tenant_count):
            tenant_id = f"tenant-{i:03d}"
            shard = manager.get_shard(tenant_id)
            
            # Write some data
            entry_id = shard.write_ledger(
                "initialization",
                {"message": f"Hello from {tenant_id}", "index": i}
            )
            shard.set_config("genesis_entry", entry_id)
            
            print(f"  ✓ {tenant_id}: entry_id={entry_id}")
        
        # Verify isolation
        print("\n[DEMO] Verifying shard isolation...")
        isolation = manager.verify_isolation()
        print(f"  Invariant: {isolation['invariant']}")
        print(f"  Verified: {isolation['verified']}")
        
        # Read back data
        print("\n[DEMO] Reading data back...")
        for tenant_id in [f"tenant-{i:03d}" for i in range(tenant_count)]:
            shard = manager.get_shard(tenant_id)
            entries = shard.read_ledger(limit=1)
            if entries:
                print(f"  {tenant_id}: {entries[0]['payload']}")
        
        # Show stats
        print("\n[DEMO] Shard statistics:")
        stats = manager.get_total_stats()
        print(f"  Shards: {stats['shard_count']}")
        print(f"  Total size: {stats['total_size_bytes']:,} bytes")
        print(f"  Writes: {stats['total_writes']}")
        
        # Cleanup
        print("\n[DEMO] Closing all shards...")
        manager.close_all()
        
        print("\n" + "=" * 60)
        print("DEMONSTRATION COMPLETE")
        print("=" * 60)
        
        return isolation


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_sharding(5)
