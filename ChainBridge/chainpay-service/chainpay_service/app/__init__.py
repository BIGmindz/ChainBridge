"""Shim package mapping `chainpay_service.app` to the local `app` module."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parents[2]

if "app" not in sys.modules:
    app_spec = importlib.util.spec_from_file_location("app", _SERVICE_ROOT / "app" / "__init__.py")
    assert app_spec is not None and app_spec.loader is not None
    app_module = importlib.util.module_from_spec(app_spec)
    sys.modules["app"] = app_module
    app_spec.loader.exec_module(app_module)

# Re-export everything from the real app package
from app import *  # type: ignore  # noqa: F401,F403,E402
