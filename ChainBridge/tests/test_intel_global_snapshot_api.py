from __future__ import annotations

import pytest

pytestmark = pytest.mark.core


@pytest.mark.parametrize("path", ["/intel/global-snapshot"])
def test_global_snapshot_aggregates_positions(client, path: str) -> None:
    resp = client.get(path)
    assert resp.status_code == 200
    data = resp.json()

    for key in ["corridorKpis", "modeKpis", "portHotspots", "globalTotals", "timestamp"]:
        assert key in data

    assert isinstance(data["corridorKpis"], list)
    assert isinstance(data["modeKpis"], list)
    assert data["globalTotals"]["totalShipments"] >= 0

    for bucket in data["corridorKpis"]:
        assert "corridorId" in bucket
        assert "corridorName" in bucket
        assert "stpRate" in bucket
        assert "highRiskShipments" in bucket
