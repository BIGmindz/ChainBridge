#!/usr/bin/env python3
"""Test SCRAM timing to diagnose unbounded execution."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("Importing scram...")
start = time.time()
from core.governance.scram import (
    SCRAMController,
    SCRAMState,
    SCRAMReason,
    SCRAMKey,
    get_scram_controller,
)
print(f"Import took {time.time() - start:.2f}s")

import hashlib
from datetime import datetime, timezone

# Reset singleton
SCRAMController._instance = None

print("Creating controller...")
start = time.time()
controller = get_scram_controller()
print(f"Controller created in {time.time() - start:.2f}s")

operator_key = SCRAMKey(
    key_id="OP-TEST-001",
    key_type="operator",
    key_hash=hashlib.sha256(b"operator_secret").hexdigest(),
    issued_at=datetime.now(timezone.utc).isoformat(),
)

architect_key = SCRAMKey(
    key_id="ARCH-TEST-001",
    key_type="architect",
    key_hash=hashlib.sha256(b"architect_secret").hexdigest(),
    issued_at=datetime.now(timezone.utc).isoformat(),
)

print("Authorizing keys...")
start = time.time()
controller.authorize_key(operator_key)
controller.authorize_key(architect_key)
print(f"Keys authorized in {time.time() - start:.2f}s")

print("Calling activate...")
start = time.time()
event = controller.activate(SCRAMReason.OPERATOR_INITIATED)
print(f"Activate took {time.time() - start:.2f}s")
print(f"Result: {event.scram_state}")
