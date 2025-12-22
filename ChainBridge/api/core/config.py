"""Bridge module for API-side config access."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Ensure project root is importable so `app.core.config` resolves when api is imported standalone.
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# CRITICAL: Always load the monorepo's app.core.config by explicit file path to avoid
# sys.modules pollution from chainiq-service's app package. The ChainIQ router loader
# can add chainiq-service/app to sys.modules before this runs, causing wrong Settings.
config_path = project_root / "app" / "core" / "config.py"
spec = importlib.util.spec_from_file_location("_monorepo_app_core_config", config_path)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load monorepo config from {config_path}")
_config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_config_module)
settings = _config_module.settings  # type: ignore[attr-defined]

# Also ensure the monorepo settings are registered as app.core.config for other imports
if "app.core.config" not in sys.modules:
    sys.modules["app.core.config"] = _config_module
