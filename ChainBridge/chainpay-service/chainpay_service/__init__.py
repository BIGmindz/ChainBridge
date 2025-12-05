"""Compatibility package so tests can import chainpay_service.*.

This module bootstraps the local `app` package and re-exports it under
`chainpay_service` to satisfy imports in tests and other tooling without
requiring installation as an installed distribution.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Resolve service root (directory containing the real `app` package)
_SERVICE_ROOT = Path(__file__).resolve().parent.parent

if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))

# Ensure the top-level `app` package is loaded
if "app" not in sys.modules:
    app_spec = importlib.util.spec_from_file_location("app", _SERVICE_ROOT / "app" / "__init__.py")
    assert app_spec is not None and app_spec.loader is not None
    app_module = importlib.util.module_from_spec(app_spec)
    sys.modules["app"] = app_module
    app_spec.loader.exec_module(app_module)

# Re-export the app package under chainpay_service for compatibility
import app as _app  # type: ignore  # noqa: E402
sys.modules.setdefault("chainpay_service.app", _app)

# Convenience re-export for callers expecting `from chainpay_service import app`
app = _app

__all__ = ["app"]
