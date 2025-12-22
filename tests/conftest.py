"""Pytest configuration for ChainBridge tests."""

import os
import warnings


def pytest_configure(config):
    """Configure pytest with optional strict warnings mode.

    Optional strict mode. Disabled by default.
    Usage: PYTEST_WARNINGS=error pytest ...
    """
    mode = os.getenv("PYTEST_WARNINGS", "").strip().lower()
    if mode == "error":
        warnings.simplefilter("error")
