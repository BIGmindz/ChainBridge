"""Minimal migration script for PaymentIntent and SettlementEvent schema updates.

Usage:
    python -m scripts.migrations.001_schema_updates

This is sqlite-focused for demo use. In production, replace with proper Alembic migrations.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "chainbridge.db"
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _execute(conn: sqlite3.Connection, sql: str) -> None:
    try:
        conn.execute(sql)
        conn.commit()
    except Exception as exc:  # pragma: no cover
        logger.warning("migration_step_failed", extra={"error": str(exc), "sql": sql})


def migrate() -> None:
    logger.info("migration_start", extra={"db": str(DB_PATH)})
    conn = sqlite3.connect(DB_PATH)
    try:
        # SettlementEvents: add sequence column if missing
        _execute(conn, "ALTER TABLE settlement_events ADD COLUMN sequence INTEGER DEFAULT 0;")
        # SettlementEvents indexes
        _execute(
            conn,
            "CREATE INDEX IF NOT EXISTS ix_settlement_events_intent_sequence ON settlement_events (payment_intent_id, sequence);",
        )
        _execute(
            conn,
            "CREATE INDEX IF NOT EXISTS ix_settlement_events_type_occurred ON settlement_events (event_type, occurred_at);",
        )
        # PaymentIntents: latest_risk_snapshot_id nullable
        _execute(
            conn,
            "ALTER TABLE payment_intents ADD COLUMN latest_risk_snapshot_id INTEGER;",
        )
        _execute(
            conn,
            "CREATE INDEX IF NOT EXISTS ix_payment_intents_shipment_latest_risk ON payment_intents (shipment_id, latest_risk_snapshot_id);",
        )
        logger.info("migration_complete")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
