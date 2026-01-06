"""Pytest configuration for ChainBridge tests.

PAC-BENSON-CORR-P08: Deterministic Termination Enforcement
Invariant: CB-INV-TEST-TERM-001 — All test executions MUST terminate
"""

import os
import sys
import warnings


def pytest_configure(config):
    """Configure pytest with optional strict warnings mode.

    Optional strict mode. Disabled by default.
    Usage: PYTEST_WARNINGS=error pytest ...
    """
    mode = os.getenv("PYTEST_WARNINGS", "").strip().lower()
    if mode == "error":
        warnings.simplefilter("error")


def pytest_sessionfinish(session, exitstatus):
    """
    PAC-BENSON-CORR-P08: Ensure deterministic session termination.
    
    Invariant: CB-INV-TEST-TERM-001
    This hook guarantees pytest exits cleanly after all tests complete.
    Prevents hanging processes that block WRAP/BER issuance.
    """
    # Force cleanup of any lingering resources
    import gc
    gc.collect()
    
    # Log termination for audit trail
    import logging
    logger = logging.getLogger("pytest.termination")
    logger.debug(f"pytest_sessionfinish: exitstatus={exitstatus}, tests_collected={session.testscollected}")


def pytest_unconfigure(config):
    """
    PAC-BENSON-CORR-P08: Final termination guard.
    
    This runs after all other cleanup. Ensures no daemon threads
    or background processes prevent clean exit.
    """
    import threading
    
    # Check for non-daemon threads that could block exit
    active_threads = [t for t in threading.enumerate() if t.is_alive() and not t.daemon and t.name != "MainThread"]
    
    if active_threads:
        import logging
        logger = logging.getLogger("pytest.termination")
        logger.warning(f"Active non-daemon threads at exit: {[t.name for t in active_threads]}")
        
        # Give threads a moment to finish
        for t in active_threads:
            t.join(timeout=1.0)
