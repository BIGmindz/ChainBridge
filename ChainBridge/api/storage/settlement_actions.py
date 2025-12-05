"""
Settlement Action Logging Storage
=================================

Lightweight SQLite-backed log for settlement operator actions.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "SETTLEMENT_ACTION_DB_URL",
    os.getenv("CHAINBOARD_ACTION_DB_URL", "sqlite:///./settlement_actions.db"),
)

engine = create_engine(
    DATABASE_URL,
    connect_args=({"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SettlementAction(Base):
    """SQLAlchemy model for operator actions."""

    __tablename__ = "settlement_actions"

    id = Column(Integer, primary_key=True, index=True)
    milestone_id = Column(String(128), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    requested_by = Column(String(128), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
        index=True,
    )


Base.metadata.create_all(bind=engine)


@dataclass
class ActionRecord:
    milestone_id: str
    action: str
    reason: Optional[str]
    requested_by: Optional[str]
    created_at: datetime


@contextmanager
def _session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def log_action(*, milestone_id: str, action: str, reason: str | None, requested_by: str | None) -> ActionRecord:
    """Persist an operator action."""
    with _session_scope() as session:
        record = SettlementAction(
            milestone_id=milestone_id,
            action=action,
            reason=reason,
            requested_by=requested_by,
        )
        session.add(record)
        session.flush()
        session.refresh(record)
        return ActionRecord(
            milestone_id=record.milestone_id,
            action=record.action,
            reason=record.reason,
            requested_by=record.requested_by,
            created_at=record.created_at,
        )


def list_recent_actions(limit: int) -> List[ActionRecord]:
    """Return the most recent actions ordered by created_at DESC."""
    with SessionLocal() as session:
        rows = session.query(SettlementAction).order_by(SettlementAction.created_at.desc()).limit(limit).all()
        return [
            ActionRecord(
                milestone_id=row.milestone_id,
                action=row.action,
                reason=row.reason,
                requested_by=row.requested_by,
                created_at=row.created_at,
            )
            for row in rows
        ]


def clear_actions() -> None:
    """Utility for tests to truncate the table."""
    with _session_scope() as session:
        session.query(SettlementAction).delete()
