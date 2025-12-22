import pytest

# Phase 2: SXT (Space and Time) client not yet implemented
# This module will integrate with SXT's proof-of-SQL blockchain service
pytest.importorskip("app.services.data.sxt_client", reason="SXT client not yet implemented (Phase 2)")

from app.services.data.sxt_client import archive_telemetry, generate_proof_of_sql

pytestmark = pytest.mark.phase2


def test_sxt_archive_acknowledged() -> None:
    res = archive_telemetry([{"shipment_id": "S1", "temp": 4.5}])
    assert res["records"] >= 1
    assert res["status"].startswith("ACK")


def test_sxt_proof_request() -> None:
    proof = generate_proof_of_sql("select 1")
    assert proof["proof_id"]
    assert "status" in proof
