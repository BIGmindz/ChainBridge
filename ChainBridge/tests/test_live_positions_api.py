from __future__ import annotations

import pytest

pytestmark = pytest.mark.core


@pytest.mark.parametrize("path", ["/intel/live-positions"])
def test_live_positions_demo_mode(client, path: str) -> None:
    resp = client.get(path)
    assert resp.status_code == 200
    data = resp.json()

    assert isinstance(data, list)
    assert data, "should return at least one live shipment"
    for pos in data:
        assert "shipmentId" in pos
        assert "corridorId" in pos or "corridor" in pos
        assert "lat" in pos and "lon" in pos
        assert isinstance(pos["lat"], (float, int))
        assert isinstance(pos["lon"], (float, int))
        assert "cargoValueUsd" in pos
        assert "etaBandHours" in pos
