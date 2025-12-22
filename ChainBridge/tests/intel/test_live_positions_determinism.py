from __future__ import annotations


def test_live_positions_stable_within_cache_window(client) -> None:
    first = client.get("/intel/live-positions")
    assert first.status_code == 200
    payload_one = first.json()

    second = client.get("/intel/live-positions")
    assert second.status_code == 200
    payload_two = second.json()

    assert payload_one == payload_two, "positions should be deterministic across the cache window"
