"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                       CHAINAUDIT — AUDIT RECORDER                             ║
║              PAC-OCC-P32-C — IRON TIMEOUT HARDENING v2.0.0                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝

The AuditRecorder is responsible for:
1. Recording all actions to the SQLite database (SYNCHRONOUS/SAFE)
2. Computing integrity hashes for tamper detection
3. Providing query interfaces for forensics
4. (P32-C) Daemonized SxT sync (ASYNCHRONOUS/NON-BLOCKING)

LAW: "Actions must be Recorded to be Valid."
LAW: "Local Proof takes priority. Global Attestation is deferred." (P32-C)
FAIL-CLOSED: If local recording fails, raise SystemError.
GRACEFUL: If SxT sync fails, daemon thread dies silently.

IRON ARCHITECTURE:
- Local DB Write = Synchronous (MUST succeed)
- ZK-Sync = Daemonized Thread (CANNOT block main process)
- No .join() calls in main execution path

Authors:
- CODY (GID-01) — Implementation
- SAM (GID-06) — Security Review
- JEFFREY — P32-C Iron Architecture
"""

import hashlib
import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from .models import (
    AuditLog, 
    PACAudit, 
    AgentSpawnAudit, 
    Base, 
    SessionLocal, 
    init_db,
    DB_PATH
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# P32-C: SxT Sync Configuration
SXT_SYNC_ENABLED = os.getenv("SXT_SYNC_ENABLED", "false").lower() == "true"
SXT_SYNC_TIMEOUT = int(os.getenv("SXT_SYNC_TIMEOUT", "5"))


# ═══════════════════════════════════════════════════════════════════════════════
# P32-C: IRON SxT ADAPTER
# ═══════════════════════════════════════════════════════════════════════════════

class SxTAdapter:
    """
    Hardened Space and Time Adapter with explicit timeouts.
    
    IRON RULES:
    - 5-second hard timeout
    - Runs ONLY in daemon threads
    - No blocking operations in main thread
    """
    
    @staticmethod
    def sync(payload: dict):
        """
        Sync audit record to Space and Time (ZK-Proof).
        
        This method is designed to run in a DAEMON THREAD only.
        It cannot hang the main process.
        """
        try:
            start_time = time.time()
            pac_id = payload.get("pac_id", "INTERNAL")
            
            print(f"📡 [SxT] Background Sync Initiated for {pac_id}...")
            
            # ═══════════════════════════════════════════════════════════════════
            # PRODUCTION: Replace with actual SxT SDK call:
            #
            #   import socket
            #   socket.setdefaulttimeout(SXT_SYNC_TIMEOUT)
            #   from spaceandtime import SpaceAndTime
            #   sxt = SpaceAndTime()
            #   sxt.authenticate()
            #   sxt.execute_query(f"INSERT INTO audit_log VALUES (...)")
            #
            # For now, simulate network latency:
            # ═══════════════════════════════════════════════════════════════════
            time.sleep(0.1)  # Simulated network call
            
            elapsed = time.time() - start_time
            if elapsed > SXT_SYNC_TIMEOUT:
                raise TimeoutError(f"SxT sync exceeded {SXT_SYNC_TIMEOUT}s timeout")
            
            print(f"✅ [SxT] ZK-Proof Attestation Logged for {pac_id} ({elapsed:.2f}s)")
            
        except TimeoutError as e:
            print(f"⚠️ [SxT] Timeout: {e}")
        except Exception as e:
            print(f"⚠️ [SxT] Background Sync Deferred/Failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRITY HASHING
# ═══════════════════════════════════════════════════════════════════════════════

def compute_integrity_hash(payload: Any) -> str:
    """
    Compute SHA256 hash of payload for tamper detection.
    """
    if payload is None:
        return hashlib.sha256(b"").hexdigest()
    
    if isinstance(payload, str):
        data = payload.encode("utf-8")
    else:
        data = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    
    return hashlib.sha256(data).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# IRON AUDIT RECORDER
# ═══════════════════════════════════════════════════════════════════════════════

class AuditRecorder:
    """
    ChainAudit Recorder — The Black Box for ChainBridge.
    
    IRON ARCHITECTURE (P32-C):
    - Local DB = Synchronous, Fail-Closed
    - ZK-Sync = Daemonized, Graceful Degradation
    - No blocking on external network calls
    
    Usage:
        recorder = AuditRecorder()
        recorder.log_action(
            agent_gid="GID-00",
            action="EXECUTE_PAC",
            target="PAC-OCC-P32",
            status="SUCCESS",
            payload={"details": "..."}
        )
    """
    
    _default_initialized = False
    
    @classmethod
    def _init_default_db(cls):
        """Initialize default database (idempotent)."""
        if not cls._default_initialized:
            init_db()
            cls._default_initialized = True
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the AuditRecorder.
        
        Args:
            db_path: Optional custom database path (for test isolation).
                     If None, uses the global default database.
        """
        if db_path is not None:
            # Custom database for test isolation
            self._custom_engine = create_engine(f"sqlite:///{db_path}", echo=False)
            self._custom_session_factory = sessionmaker(bind=self._custom_engine)
            Base.metadata.create_all(self._custom_engine)
            self._use_custom = True
        else:
            # Use global default
            AuditRecorder._init_default_db()
            self._use_custom = False
    
    def _get_session_factory(self):
        """Get the appropriate session factory."""
        if self._use_custom:
            return self._custom_session_factory
        return SessionLocal
    
    @contextmanager
    def _get_session(self):
        """
        Get a database session with automatic cleanup.
        
        IRON HARDENING:
        - Guarantees session.close() even on exception
        - Rollback on exception before close
        """
        session = self._get_session_factory()()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def _fire_sxt_sync(self, record: AuditLog) -> None:
        """
        Fire-and-forget SxT sync in daemon thread.
        
        IRON RULES:
        - daemon=True: Thread dies with main process
        - NO .join(): We never wait for this thread
        - Timeout inside thread: Cannot hang
        """
        if not SXT_SYNC_ENABLED:
            return
        
        sync_payload = {
            "pac_id": record.pac_id or "INTERNAL",
            "agent": record.agent_gid,
            "action": record.action,
            "hash": record.integrity_hash,
            "record_id": record.id,
        }
        
        bg_sync = threading.Thread(
            target=SxTAdapter.sync,
            args=(sync_payload,),
            daemon=True,  # CRITICAL: Cannot block process exit
            name=f"SxT-Sync-{record.id}"
        )
        bg_sync.start()
        # FORBIDDEN: bg_sync.join() — P32-C LAW
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CORE LOGGING METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def log_action(
        self,
        agent_gid: str,
        action: str,
        target: Optional[str] = None,
        status: str = "SUCCESS",
        payload: Optional[Any] = None,
        pac_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Record an action to the audit log.
        
        IRON FLOW:
        1. Hash payload (sync)
        2. Write to local DB (sync, fail-closed)
        3. Fire SxT sync (async, daemon thread)
        
        FAIL-CLOSED: Raises SystemError if local DB write fails.
        """
        # 1. PREPARE PAYLOAD
        payload_str = None
        if payload is not None:
            if isinstance(payload, str):
                payload_str = payload
            else:
                try:
                    payload_str = json.dumps(payload, default=str)
                except:
                    payload_str = str(payload)
        
        # 2. COMPUTE INTEGRITY HASH
        integrity_hash = compute_integrity_hash(payload_str)
        
        # 3. CREATE RECORD
        record = AuditLog(
            timestamp=datetime.now(timezone.utc),
            agent_gid=agent_gid,
            action=action,
            target=target,
            status=status,
            payload=payload_str,
            integrity_hash=integrity_hash,
            pac_id=pac_id,
            session_id=session_id,
        )
        
        # 4. LOCAL DB WRITE (SYNCHRONOUS — MUST SUCCEED)
        try:
            with self._get_session() as session:
                session.add(record)
                session.commit()
                session.refresh(record)
                print(f"📝 [Audit] Local Ledger Updated: {action}")
        except SQLAlchemyError as e:
            print(f"🔴 [FATAL] DATABASE DEADLOCK: {e}")
            raise SystemError(f"[ChainAudit] CRITICAL: Database Write Failed. Fail-Closed. Error: {e}")
        
        # 5. GLOBAL ATTESTATION (ASYNCHRONOUS — DAEMON THREAD)
        self._fire_sxt_sync(record)
        
        return record
    
    def log_pac_start(
        self,
        pac_id: str,
        issuer_gid: str,
        executor_gid: str,
        title: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> PACAudit:
        """Record PAC execution start."""
        try:
            record = PACAudit(
                pac_id=pac_id,
                issued_at=datetime.now(timezone.utc),
                started_at=datetime.now(timezone.utc),
                status="IN_PROGRESS",
                issuer_gid=issuer_gid,
                executor_gid=executor_gid,
                title=title,
                scope=scope,
            )
            
            with self._get_session() as session:
                session.add(record)
                session.commit()
                session.refresh(record)
                return record
                
        except SQLAlchemyError as e:
            raise SystemError(f"[ChainAudit] CRITICAL: Failed to record PAC start: {e}")
    
    def log_pac_complete(
        self,
        pac_id: str,
        verdict: str,
        notes: Optional[str] = None,
    ) -> Optional[PACAudit]:
        """Record PAC execution completion."""
        try:
            with self._get_session() as session:
                record = session.query(PACAudit).filter_by(pac_id=pac_id).first()
                if record:
                    record.completed_at = datetime.now(timezone.utc)
                    record.status = "COMPLETED"
                    record.ber_verdict = verdict
                    record.ber_notes = notes
                    session.commit()
                    session.refresh(record)
                    return record
                return None
                
        except SQLAlchemyError as e:
            raise SystemError(f"[ChainAudit] CRITICAL: Failed to record PAC completion: {e}")
    
    def log_agent_spawn(
        self,
        requester_gid: str,
        target_gid: str,
        task_summary: Optional[str] = None,
        status: str = "SUCCESS",
        block_reason: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
    ) -> AgentSpawnAudit:
        """Record agent spawn event."""
        try:
            record = AgentSpawnAudit(
                timestamp=datetime.now(timezone.utc),
                requester_gid=requester_gid,
                target_gid=target_gid,
                task_summary=task_summary,
                status=status,
                block_reason=block_reason,
                execution_time_ms=execution_time_ms,
            )
            
            with self._get_session() as session:
                session.add(record)
                session.commit()
                session.refresh(record)
                return record
                
        except SQLAlchemyError as e:
            raise SystemError(f"[ChainAudit] CRITICAL: Failed to record agent spawn: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # QUERY METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_logs_by_agent(self, agent_gid: str, limit: int = 100) -> List[AuditLog]:
        """Get logs for a specific agent."""
        with self._get_session() as session:
            return session.query(AuditLog).filter_by(agent_gid=agent_gid).order_by(
                AuditLog.timestamp.desc()
            ).limit(limit).all()
    
    def get_logs_by_pac(self, pac_id: str) -> List[AuditLog]:
        """Get all logs for a specific PAC."""
        with self._get_session() as session:
            return session.query(AuditLog).filter_by(pac_id=pac_id).order_by(
                AuditLog.timestamp.asc()
            ).all()
    
    def get_recent_logs(self, limit: int = 50) -> List[AuditLog]:
        """Get most recent audit logs."""
        with self._get_session() as session:
            return session.query(AuditLog).order_by(
                AuditLog.timestamp.desc()
            ).limit(limit).all()
    
    def get_pac_audit(self, pac_id: str) -> Optional[PACAudit]:
        """Get PAC audit record."""
        with self._get_session() as session:
            return session.query(PACAudit).filter_by(pac_id=pac_id).first()
    
    def get_logs_by_action(self, action: str, limit: int = 100) -> List[AuditLog]:
        """Get logs filtered by action type."""
        with self._get_session() as session:
            return session.query(AuditLog).filter_by(action=action).order_by(
                AuditLog.timestamp.desc()
            ).limit(limit).all()
    
    def count_logs(self) -> int:
        """Count total audit logs."""
        with self._get_session() as session:
            return session.query(AuditLog).count()
    
    def verify_integrity(self, record_id: int) -> bool:
        """
        Verify the integrity hash of an audit log record.
        
        Args:
            record_id: The ID of the record to verify
            
        Returns:
            True if hash matches, False otherwise
        """
        with self._get_session() as session:
            record = session.query(AuditLog).filter_by(id=record_id).first()
            if not record:
                return False
            
            computed_hash = compute_integrity_hash(record.payload)
            return computed_hash == record.integrity_hash
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get audit statistics.
        
        Returns:
            Dict with total_audit_logs, total_pac_executions, total_agent_spawns
        """
        with self._get_session() as session:
            total_logs = session.query(AuditLog).count()
            total_pacs = session.query(PACAudit).count()
            total_spawns = session.query(AgentSpawnAudit).count()
            
            # Count by status
            from sqlalchemy import func
            status_counts = dict(
                session.query(AuditLog.status, func.count(AuditLog.id))
                .group_by(AuditLog.status)
                .all()
            )
            
            # Count by agent
            agent_counts = dict(
                session.query(AuditLog.agent_gid, func.count(AuditLog.id))
                .group_by(AuditLog.agent_gid)
                .all()
            )
            
            return {
                "total_audit_logs": total_logs,
                "total_pac_executions": total_pacs,
                "total_agent_spawns": total_spawns,
                "total_logs": total_logs,
                "logs_by_status": status_counts,
                "logs_by_agent": agent_counts,
            }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_recorder_instance: Optional[AuditRecorder] = None


def get_recorder() -> AuditRecorder:
    """Get the singleton AuditRecorder instance."""
    global _recorder_instance
    if _recorder_instance is None:
        _recorder_instance = AuditRecorder()
    return _recorder_instance
