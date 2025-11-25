from __future__ import annotations

import time


def test_intel_snapshot_perf_under_mock_load(client) -> None:
    # warm cache
    client.get("/intel/global-snapshot")

    runs = 5
    start = time.perf_counter()
    for _ in range(runs):
        resp = client.get("/intel/global-snapshot")
        assert resp.status_code == 200
    duration_ms = ((time.perf_counter() - start) / runs) * 1000

    assert duration_ms < 120.0
