from datetime import datetime, timedelta, timezone

from api.routes.sla import sla_status
from api.sla.metrics import update_metric


def test_sla_snapshot_window_and_data_flag():
    now = datetime.now(timezone.utc)
    update_metric("operator_queue", now - timedelta(seconds=10))
    update_metric("payment_intents", now - timedelta(days=2))
    update_metric("webhooks", now - timedelta(seconds=10))
    update_metric("worker_heartbeat", now - timedelta(seconds=10))

    snapshot = sla_status()
    assert snapshot["data_window"] == "24h"
    assert snapshot["components"]["operator_queue"]["fresh"] is True
    assert snapshot["components"]["cash_view"]["fresh"] is False


def test_sla_snapshot_degraded_state():
    now = datetime.now(timezone.utc)
    update_metric("operator_queue", now - timedelta(seconds=500))
    update_metric("payment_intents", now - timedelta(seconds=10))
    update_metric("webhooks", now - timedelta(seconds=10))
    update_metric("worker_heartbeat", now - timedelta(seconds=10))

    snapshot = sla_status()
    assert snapshot["status"] in {"DEGRADED", "CRITICAL"}
    assert snapshot["components"]["operator_queue"]["fresh"] is False
