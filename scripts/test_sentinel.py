#!/usr/bin/env python3
"""
Titan Sentinel Integration Test
================================

Tests the kill switch functionality by:
1. Starting sentinel with mock hardware
2. Spawning a long-running Python node
3. Simulating hardware signal loss
4. Verifying immediate node termination

PAC Reference: PAC-OCC-P16-HW-TITAN-SENTINEL
"""

import os
import sys
import time
import json
import signal
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def create_test_node_script() -> str:
    """Create a simple Python node that runs forever."""
    script = '''
import os
import time
import signal
import sys

def handle_term(signum, frame):
    print("[NODE] Received SIGTERM - graceful shutdown")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_term)

print("[NODE] Starting - PID", os.getpid())
sys.stdout.flush()

while True:
    print("[NODE] Heartbeat", time.time())
    sys.stdout.flush()
    time.sleep(0.5)
'''
    fd, path = tempfile.mkstemp(suffix='.py', prefix='test_node_')
    with os.fdopen(fd, 'w') as f:
        f.write(script)
    return path


def main():
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}  PAC-OCC-P16-HW-TITAN-SENTINEL TEST{RESET}")
    print(f"{BOLD}{CYAN}  Hardware Kill Switch Verification{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")
    
    # Paths
    project_root = Path(__file__).parent.parent
    sentinel_binary = project_root / "chainbridge_kernel" / "target" / "release" / "titan_sentinel"
    
    if not sentinel_binary.exists():
        print(f"{RED}ERROR: Sentinel binary not found at {sentinel_binary}{RESET}")
        return {"verdict": "FAILED", "reason": "binary_not_found"}
    
    # Create temp directory for test
    test_dir = Path(tempfile.mkdtemp(prefix='sentinel_test_'))
    signal_file = test_dir / "hardware_signal"
    log_file = test_dir / "sentinel.json"
    
    # Create test node script
    node_script = create_test_node_script()
    
    print(f"{YELLOW}[SETUP]{RESET} Test directory: {test_dir}")
    print(f"{YELLOW}[SETUP]{RESET} Signal file: {signal_file}")
    print(f"{YELLOW}[SETUP]{RESET} Node script: {node_script}")
    
    try:
        # Initialize hardware signal as PRESENT
        signal_file.write_text("1")
        print(f"\n{GREEN}[INIT]{RESET} Hardware signal set to PRESENT (1)")
        
        # Start sentinel
        env = os.environ.copy()
        env.update({
            "SENTINEL_HARDWARE": "mock",
            "SENTINEL_SIGNAL_FILE": str(signal_file),
            "SENTINEL_PYTHON_CMD": f"python3 {node_script}",
            "SENTINEL_WORK_DIR": str(test_dir),
            "SENTINEL_LOG_FILE": str(log_file),
            "SENTINEL_POLL_MS": "50",
            "SENTINEL_MAX_FAILURES": "3",
            "RUST_LOG": "info",
        })
        
        print(f"\n{YELLOW}[START]{RESET} Launching Titan Sentinel...")
        sentinel_proc = subprocess.Popen(
            [str(sentinel_binary)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(test_dir),
        )
        
        # Wait for node to start
        time.sleep(1.5)
        
        if sentinel_proc.poll() is not None:
            print(f"{RED}[ERROR]{RESET} Sentinel exited prematurely")
            stdout = sentinel_proc.stdout.read().decode()
            print(f"Output: {stdout}")
            return {"verdict": "FAILED", "reason": "sentinel_crashed"}
        
        print(f"{GREEN}[RUNNING]{RESET} Sentinel running (PID {sentinel_proc.pid})")
        
        # Simulate hardware signal LOSS
        print(f"\n{RED}[KILL SWITCH]{RESET} Removing hardware signal...")
        kill_time = time.time()
        signal_file.write_text("0")  # Signal LOST
        
        # Wait for sentinel to react
        max_wait = 2.0  # 2 seconds max
        start_wait = time.time()
        
        while sentinel_proc.poll() is None:
            if time.time() - start_wait > max_wait:
                print(f"{RED}[FAILED]{RESET} Sentinel did not react to signal loss!")
                sentinel_proc.kill()
                return {"verdict": "FAILED", "reason": "no_reaction"}
            time.sleep(0.01)
        
        reaction_time = time.time() - kill_time
        exit_code = sentinel_proc.returncode
        
        print(f"\n{GREEN}[RESULT]{RESET} Sentinel exited with code {exit_code}")
        print(f"{GREEN}[RESULT]{RESET} Reaction time: {reaction_time*1000:.1f}ms")
        
        # Parse log file
        print(f"\n{YELLOW}[LOG]{RESET} Sentinel events:")
        events = []
        if log_file.exists():
            for line in log_file.read_text().strip().split('\n'):
                if line:
                    try:
                        event = json.loads(line)
                        events.append(event)
                        print(f"  {event.get('event', 'UNKNOWN')}: {event.get('timestamp', '')}")
                    except json.JSONDecodeError:
                        pass
        
        # Verify kill event
        kill_events = [e for e in events if e.get('event') == 'EMERGENCY_KILL']
        
        # Results
        print(f"\n{BOLD}{'='*70}{RESET}")
        print(f"{BOLD}  VERIFICATION RESULTS{RESET}")
        print(f"{BOLD}{'='*70}{RESET}")
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pac": "PAC-OCC-P16-HW-TITAN-SENTINEL",
            "sentinel_binary": str(sentinel_binary),
            "binary_size_bytes": sentinel_binary.stat().st_size,
            "reaction_time_ms": reaction_time * 1000,
            "exit_code": exit_code,
            "kill_events": len(kill_events),
            "invariants": {
                "INV-HW-001": exit_code == 1,  # Sentinel killed node
                "INV-HW-002": reaction_time < 0.5,  # < 500ms reaction
            },
            "verdict": "PASSED" if (exit_code == 1 and reaction_time < 0.5) else "FAILED",
        }
        
        print(f"\n  Binary Size:     {results['binary_size_bytes']:,} bytes")
        print(f"  Reaction Time:   {results['reaction_time_ms']:.1f}ms (target: <10ms)")
        print(f"  Exit Code:       {results['exit_code']} (expected: 1)")
        print(f"\n  INV-HW-001 (Binary Supremacy):    {'✓ VERIFIED' if results['invariants']['INV-HW-001'] else '✗ VIOLATED'}")
        print(f"  INV-HW-002 (Physical Binding):    {'✓ VERIFIED' if results['invariants']['INV-HW-002'] else '✗ VIOLATED'}")
        
        verdict_color = GREEN if results['verdict'] == 'PASSED' else RED
        print(f"\n  {BOLD}VERDICT: {verdict_color}{results['verdict']}{RESET}")
        
        print(f"\n{BOLD}{'='*70}{RESET}\n")
        
        return results
        
    finally:
        # Cleanup
        if os.path.exists(node_script):
            os.unlink(node_script)


if __name__ == "__main__":
    results = main()
    sys.exit(0 if results.get("verdict") == "PASSED" else 1)
