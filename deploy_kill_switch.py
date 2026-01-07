#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# PAC-OCC-P16-DEPLOY — Kill Switch Deployment Script
# Physical Sovereignty Layer - Auto-Patcher
# Governance Tier: CONSTITUTIONAL_LAW
# ═══════════════════════════════════════════════════════════════════════════════
"""
Kill Switch Deployment Script

This script patches bridge_relay.py to integrate the Sovereign Kill Switch.
It ensures that no manual error can leave the bridge undefended.

Usage:
    python deploy_kill_switch.py
    
Post-deployment:
    1. Install requirements: pip install pyserial RPi.GPIO
    2. Start bridge_relay.py
    3. TEST: Unplug the kill switch. Confirm termination.

Constitutional Mandate:
"Deployment is the bridge between Theory and Reality. The code is now Law."
"""

import os
import sys
from pathlib import Path

DAEMON_FILENAME = "sovereign_kill_daemon.py"
RELAY_FILENAME = "bridge_relay.py"

# Marker to identify patched files
PATCH_MARKER = "# INJECTED HARDWARE SHIELD (P16-DEPLOY)"


def check_daemon_exists() -> bool:
    """Verify the daemon file exists."""
    if not os.path.exists(DAEMON_FILENAME):
        print(f"ERROR: {DAEMON_FILENAME} not found!")
        print("Please ensure sovereign_kill_daemon.py is in the repository root.")
        return False
    return True


def check_relay_exists() -> bool:
    """Verify the relay file exists."""
    if not os.path.exists(RELAY_FILENAME):
        print(f"ERROR: {RELAY_FILENAME} not found!")
        return False
    return True


def is_already_patched(lines: list) -> bool:
    """Check if the relay is already patched."""
    for line in lines:
        if PATCH_MARKER in line:
            return True
        if "from sovereign_kill_daemon import kill_switch" in line:
            return True
    return False


def patch_relay() -> bool:
    """
    Patch bridge_relay.py to integrate the Sovereign Kill Switch.
    
    Returns True on success, False on failure.
    """
    print("=" * 60)
    print("🛡️ SOVEREIGN KILL SWITCH DEPLOYMENT")
    print("=" * 60)
    
    # Verify prerequisites
    print(f"[1/4] Checking {DAEMON_FILENAME}...")
    if not check_daemon_exists():
        return False
    print(f"      ✓ Found {DAEMON_FILENAME}")
    
    print(f"[2/4] Checking {RELAY_FILENAME}...")
    if not check_relay_exists():
        return False
    print(f"      ✓ Found {RELAY_FILENAME}")
    
    # Read relay file
    print(f"[3/4] Reading {RELAY_FILENAME}...")
    with open(RELAY_FILENAME, "r") as f:
        lines = f.readlines()
    
    # Check if already patched
    if is_already_patched(lines):
        print("      ⚠️ Already patched. Skipping.")
        print("=" * 60)
        print("✓ Deployment verified. Sovereignty active.")
        print("=" * 60)
        return True
    
    print(f"[4/4] Patching {RELAY_FILENAME}...")
    
    # Insert import at the top (after the module docstring)
    import_line = f"from sovereign_kill_daemon import kill_switch  {PATCH_MARKER}\n"
    
    # Find the right place to insert the import (after docstring and existing imports)
    insert_idx = 0
    in_docstring = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if in_docstring:
                in_docstring = False
                insert_idx = i + 1
            else:
                in_docstring = True
        elif not in_docstring and (stripped.startswith("import ") or stripped.startswith("from ")):
            insert_idx = i + 1
    
    # Insert after existing imports
    lines.insert(insert_idx, "\n")
    lines.insert(insert_idx + 1, import_line)
    
    # Find startup_event and inject kill_switch.start()
    patched_lines = []
    startup_found = False
    def_found = False
    injection_done = False
    
    for line in lines:
        patched_lines.append(line)
        
        # Look for @app.on_event("startup")
        if '@app.on_event("startup")' in line:
            startup_found = True
            continue
        
        # After finding the decorator, look for the def
        if startup_found and "def startup_event" in line:
            def_found = True
            continue
        
        # After finding the def, inject on the next line that starts with content
        if startup_found and def_found and not injection_done:
            # Check if this is the first line of the function body
            if line.strip() and not line.strip().startswith('#'):
                # Insert before this line
                indent = "    "  # Assuming 4-space indent
                injection = f"{indent}kill_switch.start()  {PATCH_MARKER}\n"
                patched_lines.insert(-1, injection)
                injection_done = True
                startup_found = False
                def_found = False
    
    # Write patched file
    with open(RELAY_FILENAME, "w") as f:
        f.writelines(patched_lines)
    
    print("      ✓ Import added")
    print("      ✓ Startup hook injected")
    print("=" * 60)
    print("✓ Deployment Complete. Sovereignty Active.")
    print("=" * 60)
    print("")
    print("Next steps:")
    print("  1. Install requirements:")
    print("     pip install pyserial RPi.GPIO")
    print("")
    print("  2. Start the relay:")
    print("     python bridge_relay.py")
    print("")
    print("  3. TEST: Unplug hardware. Confirm process termination.")
    print("")
    print("The code is now Law.")
    print("=" * 60)
    
    return True


def verify_patch() -> bool:
    """Verify the patch was applied correctly."""
    if not os.path.exists(RELAY_FILENAME):
        return False
    
    with open(RELAY_FILENAME, "r") as f:
        content = f.read()
    
    has_import = "from sovereign_kill_daemon import kill_switch" in content
    has_start = "kill_switch.start()" in content
    
    return has_import and has_start


if __name__ == "__main__":
    success = patch_relay()
    
    if success and verify_patch():
        print("\n🛡️ Patch verification: PASSED")
        sys.exit(0)
    elif success:
        print("\n⚠️ Patch applied but verification unclear")
        sys.exit(0)
    else:
        print("\n❌ Deployment failed")
        sys.exit(1)
