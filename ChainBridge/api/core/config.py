"""Bridge module for API-side config access."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable so `app.core.config` resolves when api is imported standalone.
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from app.core.config import settings  # type: ignore  # re-export for api.*
except ModuleNotFoundError:
    import importlib.util

    config_path = project_root / "app" / "core" / "config.py"
    spec = importlib.util.spec_from_file_location("app.core.config", config_path)
    if spec is None or spec.loader is None:
        raise
    module = importlib.util.module_from_spec(spec)
    sys.modules["app.core.config"] = module
    spec.loader.exec_module(module)
    settings = module.settings  # type: ignore[attr-defined]
