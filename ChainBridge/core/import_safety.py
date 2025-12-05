"""
ChainBridge Import Safety Shim
Ensures deterministic importlib.metadata behavior and venv interpreter lock.
"""
import sys
import os
import warnings

# Unified importlib.metadata API
try:
    import importlib.metadata as _metadata
except ImportError:
    import importlib_metadata as _metadata

__all__ = ["version", "packages", "ensure_import_safety"]

version = _metadata.version
packages = _metadata.packages if hasattr(_metadata, "packages") else lambda: []


def ensure_import_safety():
    # Enforce venv interpreter
    venv_path = os.environ.get("VIRTUAL_ENV")
    expected = os.path.abspath(os.path.join(os.getcwd(), ".venv"))
    actual = sys.executable
    if venv_path and not actual.startswith(venv_path):
        warnings.warn(f"[IMPORT SAFETY] Python interpreter is not inside .venv! Found: {actual}")
        raise RuntimeError(f"Python interpreter must be .venv/bin/python, found: {actual}")
    # Check importlib.metadata availability
    try:
        _ = version("pip")
    except Exception as e:
        warnings.warn(f"[IMPORT SAFETY] importlib.metadata not available: {e}")
        raise
    return True
