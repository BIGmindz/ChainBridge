"""Supabase replay hook for preset feedback.

This module provides a simple, batch-oriented replay mechanism that can
pull raw preset feedback events from Supabase and POST them into the
ChainIQ feedback endpoint (`/api/ai/presets/feedback`).

The goal is to keep this logic small, explicit and easy to reason
about. It is intentionally written so it can run as an ad-hoc script,
cron job, or be wrapped by a more sophisticated scheduler later.

NOTE: This is a skeleton. It assumes either `supabase-py` is available
or that you will replace the client creation with a direct HTTP
implementation when wiring this up in production.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import requests

try:
    from supabase import Client, create_client  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Client = Any  # type: ignore

    def create_client(*args: Any, **kwargs: Any) -> Any:  # type: ignore
        raise RuntimeError("supabase-py is not installed; install it or swap in an HTTP client.")


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
CHAINIQ_FEEDBACK_URL = os.getenv("CHAINIQ_FEEDBACK_URL", "http://localhost:8000/api/ai/presets/feedback")


def get_supabase_client() -> Client:
    """Return a Supabase client using service-role credentials.

    Raises RuntimeError if mandatory environment variables are missing.
    """

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase env vars not configured")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def map_supabase_row_to_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map a Supabase row into the ChainIQ feedback payload schema.

    This mapping assumes the Supabase table columns roughly mirror the
    `PresetFeedbackEvent` fields plus any additional data you want to
    supply to the reinforcement engine.
    """

    return {
        "preset_id": row["preset_id"],
        "profile": row["profile"],
        "rank": row.get("rank"),
        "chosen": row.get("chosen", False),
        "explicit": row.get("explicit_feedback"),
        "session_id": row.get("session_id"),
        "user_id": row.get("user_id"),
        # Component scores are optional and may be stored as JSON in Supabase.
        "component_scores": row.get("component_scores") or {},
        # Future-ready scoping
        "tenant_id": row.get("tenant_id"),
        "console_id": row.get("console_id"),
    }


def replay_batch(limit: int = 100) -> int:
    """Replay up to `limit` events from Supabase into ChainIQ.

    This function is deliberately conservative: it fetches a small
    batch, POSTs each row to the ChainIQ feedback endpoint, and only
    marks a row as `replayed` in Supabase when the POST succeeds.

    It is expected that the Supabase table `preset_feedback_events`
    contains a boolean `replayed` column and a primary key `id`.
    """

    client = get_supabase_client()

    resp = client.table("preset_feedback_events").select("*").eq("replayed", False).limit(limit).execute()

    rows = getattr(resp, "data", None) or []
    if not rows:
        return 0

    processed = 0
    for row in rows:
        payload = map_supabase_row_to_payload(row)
        try:
            r = requests.post(CHAINIQ_FEEDBACK_URL, json=payload, timeout=5)
        except Exception as exc:  # pragma: no cover - network failure path
            print("Failed to POST to ChainIQ", exc)
            continue

        if r.status_code == 200:
            client.table("preset_feedback_events").update({"replayed": True}).eq("id", row["id"]).execute()
            processed += 1
        else:
            # Log and move on; the row will remain unreplayed and can be retried.
            print(
                "Failed to replay row",
                row.get("id"),
                r.status_code,
                r.text,
            )

    return processed


if __name__ == "__main__":
    count = replay_batch()
    print(f"Replayed {count} events")
