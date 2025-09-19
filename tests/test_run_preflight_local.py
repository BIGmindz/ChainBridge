import json
from pathlib import Path


def test_run_preflight_json(tmp_path):
    out = tmp_path / "report.json"
    from scripts.run_preflight_local import run_preflight

    report = run_preflight(json_output=str(out))
    assert out.exists()
    data = json.loads(out.read_text())

    # Expect config symbols to be present in the report
    cfg_symbols = list(data.keys())
    assert len(cfg_symbols) > 0
    for s in cfg_symbols:
        assert isinstance(data[s], dict)
