#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# PAC-STRAT-P26-FULL-IGNITION — ChainBridge Live Monitor
# Real-time log visualization with color-coded output
# Governance Tier: INFRASTRUCTURE_GO_LIVE
# ═══════════════════════════════════════════════════════════════════════════════
"""
ChainBridge Live Monitor v1.0.0

Real-time visualization of bridge_relay.py activity with color-coded output:
- 🟢 Green: Success messages (✅)
- 🔴 Red: Blocked/Denied (⛔, 401, 403)
- 🟡 Yellow: Security events (🔒)
- 🔵 Cyan: PAC Ingress events

"The machine is listening. Observe the Law."
"""

import os
import subprocess
import sys
import time

# ═══════════════════════════════════════════════════════════════════════════════
# ANSI COLOR CODES
# ═══════════════════════════════════════════════════════════════════════════════

BLUE = "\033[1;34m"
GREEN = "\033[1;32m"
RED = "\033[1;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[1;36m"
RESET = "\033[0m"

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

LOG_FILE = "logs/bridge_relay_stdout.log"


def monitor():
    """
    Real-time log monitor with color-coded output.
    
    Uses tail -F to follow the log file even across rotations.
    """
    print(f"{BLUE}{'=' * 70}{RESET}")
    print(f"{BLUE}🔵 CHAINBRIDGE LIVE MONITOR - v2.2.1{RESET}")
    print(f"{BLUE}   Observing the Sovereign Relay{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}")
    print(f"{YELLOW}   Press Ctrl+C to stop monitoring{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}")
    print()

    # Ensure log directory and file exist
    if not os.path.exists(LOG_FILE):
        os.makedirs("logs", exist_ok=True)
        with open(LOG_FILE, "w") as f:
            f.write("--- MONITOR STARTED ---\n")
        print(f"{YELLOW}Created {LOG_FILE}{RESET}")

    # Start tail process
    p = subprocess.Popen(
        ["tail", "-F", LOG_FILE],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    try:
        while True:
            line = p.stdout.readline()
            if line:
                line_stripped = line.strip()
                
                # Color code based on content
                if "✅" in line_stripped or "ACTIVE" in line_stripped or "200" in line_stripped:
                    # Success - Green
                    print(f"{GREEN}{line_stripped}{RESET}")
                elif "⛔" in line_stripped or "401" in line_stripped or "403" in line_stripped or "BLOCKED" in line_stripped:
                    # Blocked/Denied - Red
                    print(f"{RED}{line_stripped}{RESET}")
                elif "🔒" in line_stripped or "SOVEREIGN" in line_stripped or "GATE" in line_stripped:
                    # Security events - Yellow
                    print(f"{YELLOW}{line_stripped}{RESET}")
                elif "PAC" in line_stripped or "INGRESS" in line_stripped:
                    # PAC events - Cyan
                    print(f"{CYAN}{line_stripped}{RESET}")
                elif "ERROR" in line_stripped or "CRITICAL" in line_stripped or "FAIL" in line_stripped:
                    # Errors - Red
                    print(f"{RED}{line_stripped}{RESET}")
                elif "WARNING" in line_stripped or "⚠️" in line_stripped:
                    # Warnings - Yellow
                    print(f"{YELLOW}{line_stripped}{RESET}")
                else:
                    # Default - No color
                    print(line_stripped)
                    
    except KeyboardInterrupt:
        print(f"\n{BLUE}{'=' * 70}{RESET}")
        print(f"{BLUE}🔵 MONITOR STOPPED{RESET}")
        print(f"{BLUE}{'=' * 70}{RESET}")
        p.kill()
        sys.exit(0)


if __name__ == "__main__":
    monitor()
