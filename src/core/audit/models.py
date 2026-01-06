"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         CHAINAUDIT — DATA MODELS                              ║
║              PAC-OCC-P30 — The Black Box + P32-C — Iron Gateway               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

SQLAlchemy ORM models for the ChainBridge Audit Ledger.

LAW: "If it isn't in the DB, it didn't happen."

Authors:
- CODY (GID-01) — Implementation
- SAM (GID-06) — Security Review
- JEFFREY — P32-C Iron Hardening
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Index, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

# ═══════════════════════════════════════════════════════════════════════════════
# P32-C: IRON DATABASE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DEFAULT_DB_PATH = _PROJECT_ROOT / "chainbridge.db"
DB_PATH = os.getenv("CHAINBRIDGE_DB_PATH", str(DEFAULT_DB_PATH))

# Global engine and session factory (thread-safe)
_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=_engine)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(_engine)
    print(f"📼 [ChainAudit] Ledger initialized at {DB_PATH}")


class AuditLog(Base):
    """
    Immutable audit record for all ChainBridge actions.
    
    Every PAC execution, agent spawn, and governance decision
    must be recorded here. No exceptions.
    
    Schema:
    - id: Auto-increment primary key
    - timestamp: When the action occurred (UTC)
    - agent_gid: Which agent performed the action (e.g., "GID-00")
    - action: What was done (e.g., "SPAWN_AGENT", "EXECUTE_PAC")
    - target: What was affected (e.g., "GID-11", "tools.py")
    - status: Result (SUCCESS, FAILED, BLOCKED)
    - payload: Full context as JSON/text (for forensics)
    - integrity_hash: SHA256 of payload (tamper detection)
    - pac_id: Reference to originating PAC (if applicable)
    - session_id: Unique session identifier
    """
    
    __tablename__ = "audit_log"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Temporal
    timestamp = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    
    # Actor
    agent_gid = Column(String(16), nullable=False, index=True)
    
    # Action
    action = Column(String(64), nullable=False, index=True)
    target = Column(String(256), nullable=True)
    status = Column(String(16), nullable=False, default="SUCCESS")
    
    # Context
    payload = Column(Text, nullable=True)
    integrity_hash = Column(String(64), nullable=True)  # SHA256
    
    # References
    pac_id = Column(String(32), nullable=True, index=True)
    session_id = Column(String(64), nullable=True)
    
    # Additional indexes for common queries
    __table_args__ = (
        Index("ix_audit_agent_action", "agent_gid", "action"),
        Index("ix_audit_timestamp_status", "timestamp", "status"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, agent={self.agent_gid}, "
            f"action={self.action}, status={self.status})>"
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "agent_gid": self.agent_gid,
            "action": self.action,
            "target": self.target,
            "status": self.status,
            "payload": self.payload,
            "integrity_hash": self.integrity_hash,
            "pac_id": self.pac_id,
            "session_id": self.session_id,
        }


class PACAudit(Base):
    """
    PAC execution audit record.
    
    Tracks the full lifecycle of a PAC from issuance to closure.
    """
    
    __tablename__ = "pac_audit"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pac_id = Column(String(32), nullable=False, unique=True, index=True)
    version = Column(String(16), nullable=False, default="1.0.0")
    
    # Lifecycle timestamps
    issued_at = Column(DateTime, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(16), nullable=False, default="PENDING")  # PENDING, IN_PROGRESS, COMPLETED, REJECTED
    
    # Actors
    issuer_gid = Column(String(16), nullable=False)  # Who issued (e.g., "GID-JEFFREY")
    executor_gid = Column(String(16), nullable=True)  # Who executed (e.g., "GID-00")
    
    # Content
    title = Column(String(256), nullable=True)
    scope = Column(String(256), nullable=True)
    
    # BER (Bridge Execution Record)
    ber_verdict = Column(String(16), nullable=True)  # ACCEPTED, REJECTED
    ber_notes = Column(Text, nullable=True)
    
    def __repr__(self) -> str:
        return f"<PACAudit(pac_id={self.pac_id}, status={self.status})>"


class AgentSpawnAudit(Base):
    """
    Agent spawn audit record.
    
    Every time an agent is spawned, this record captures:
    - Who requested it
    - Which agent was spawned
    - Whether it was blocked (kill switch, governance)
    """
    
    __tablename__ = "agent_spawn_audit"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Spawn details
    requester_gid = Column(String(16), nullable=False)  # Who requested
    target_gid = Column(String(16), nullable=False)     # Who was spawned
    
    # Task
    task_summary = Column(String(512), nullable=True)
    
    # Result
    status = Column(String(16), nullable=False)  # SUCCESS, BLOCKED, FAILED
    block_reason = Column(String(256), nullable=True)  # Why blocked (if applicable)
    
    # Execution
    execution_time_ms = Column(Integer, nullable=True)
    
    def __repr__(self) -> str:
        return f"<AgentSpawnAudit(target={self.target_gid}, status={self.status})>"
