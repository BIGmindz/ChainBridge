import importlib.util
import json
from pathlib import Path


def test_run_preflight_json(tmp_path):
    out = tmp_path / "report.json"
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "run_preflight_local.py"
    spec = importlib.util.spec_from_file_location(
        "run_preflight_local", str(script_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run_preflight = module.run_preflight

    run_preflight(json_output=str(out))
    assert out.exists()
    data = json.loads(out.read_text())

    # Expect config symbols to be present in the report
    cfg_symbols = list(data.keys())
    assert len(cfg_symbols) > 0
    for s in cfg_symbols:
        assert isinstance(data[s], dict)
