from __future__ import annotations


def test_oc_feed_contract_and_fallback(client) -> None:
    resp = client.get("/intel/oc-feed")
    assert resp.status_code == 200
    data = resp.json()

    for key in ["queueCards", "globalSnapshot", "livePositionsMeta"]:
        assert key in data

    assert isinstance(data["queueCards"], list)
    assert data["queueCards"], "expected at least one queue card"
    assert data["livePositionsMeta"]["activeShipments"] >= 0

    snapshot_totals = data["globalSnapshot"]["globalTotals"]["totalShipments"]
    assert snapshot_totals == data["livePositionsMeta"]["activeShipments"]
