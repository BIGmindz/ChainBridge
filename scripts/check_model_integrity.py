#!/usr/bin/env python3
"""
ChainIQ ML Model Integrity Check Script
SAM (GID-06) - Security & Threat Engineer

Automated integrity verification for ML model artifacts.
Run this script in CI/CD pipelines and as a pre-deployment check.

Usage:
    # Check single model
    ./scripts/check_model_integrity.py ChainBridge/chainiq-service/app/ml/models/risk_model_v0.2.pkl

    # Check all models in directory
    ./scripts/check_model_integrity.py ChainBridge/chainiq-service/app/ml/models/

    # CI mode (strict, exit on any failure)
    ./scripts/check_model_integrity.py --ci ChainBridge/chainiq-service/app/ml/models/

Exit Codes:
    0 - All checks passed
    1 - Signature verification failed
    2 - Threats detected
    3 - Model file not found
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "ChainBridge" / "chainiq-service"))

from app.ml.model_security import ModelQuarantineError, ModelSecurityError, ModelSecurityManager


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header():
    """Print script header."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}╔════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}║  ChainIQ ML Model Integrity Check                     ║{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}║  SAM (GID-06) — Security & Threat Engineer            ║{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}╚════════════════════════════════════════════════════════╝{Colors.RESET}\n")


def check_model_integrity(model_path: Path, manager: ModelSecurityManager, ci_mode: bool = False) -> Tuple[bool, str]:
    """
    Check integrity of a single model.

    Args:
        model_path: Path to model file
        manager: ModelSecurityManager instance
        ci_mode: If True, be more strict

    Returns:
        Tuple of (success, message)
    """
    # Check file exists
    if not model_path.exists():
        return False, f"Model file not found: {model_path}"

    # Step 1: Verify signature
    print(f"{Colors.BLUE}[1/3]{Colors.RESET} Verifying signature: {model_path.name}")

    is_valid, error = manager.verify_model_signature(model_path, strict=False)

    if not is_valid:
        print(f"  {Colors.RED}✗ FAILED{Colors.RESET}: {error}")
        return False, f"Signature verification failed: {error}"

    print(f"  {Colors.GREEN}✓ PASSED{Colors.RESET}: Signature valid")

    # Step 2: Detect threats
    print(f"{Colors.BLUE}[2/3]{Colors.RESET} Detecting threats")

    threats = manager.detect_threats(model_path)

    if threats:
        print(f"  {Colors.YELLOW}⚠ WARNINGS{Colors.RESET}:")
        for threat in threats:
            print(f"    - {threat}")

        # In CI mode, some threats are fatal
        if ci_mode:
            critical_threats = [t for t in threats if any(keyword in t for keyword in ["CRITICAL", "SUSPICIOUS_IMPORTS", "UNSIGNED"])]
            if critical_threats:
                return False, f"Critical threats detected: {'; '.join(critical_threats)}"
    else:
        print(f"  {Colors.GREEN}✓ PASSED{Colors.RESET}: No threats detected")

    # Step 3: Load test (optional in CI mode)
    if not ci_mode:
        print(f"{Colors.BLUE}[3/3]{Colors.RESET} Load test")

        try:
            model = manager.load_verified_model(model_path, enable_quarantine=False)
            print(f"  {Colors.GREEN}✓ PASSED{Colors.RESET}: Model loaded successfully ({type(model).__name__})")
        except Exception as e:
            print(f"  {Colors.RED}✗ FAILED{Colors.RESET}: {e}")
            return False, f"Load test failed: {e}"
    else:
        print(f"{Colors.BLUE}[3/3]{Colors.RESET} Load test: {Colors.YELLOW}SKIPPED{Colors.RESET} (CI mode)")

    return True, "All checks passed"


def find_model_files(path: Path) -> List[Path]:
    """
    Find all .pkl model files in a path.

    Args:
        path: File or directory path

    Returns:
        List of model file paths
    """
    if path.is_file():
        if path.suffix == ".pkl":
            return [path]
        else:
            return []
    elif path.is_dir():
        return list(path.rglob("*.pkl"))
    else:
        return []


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ChainIQ ML Model Integrity Check (SAM GID-06)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check single model
  %(prog)s ChainBridge/chainiq-service/app/ml/models/risk_model_v0.2.pkl

  # Check all models in directory
  %(prog)s ChainBridge/chainiq-service/app/ml/models/

  # CI mode (strict)
  %(prog)s --ci ChainBridge/chainiq-service/app/ml/models/

  # JSON output for automation
  %(prog)s --json ChainBridge/chainiq-service/app/ml/models/ > results.json
        """,
    )

    parser.add_argument("path", type=Path, help="Path to model file or directory containing models")

    parser.add_argument("--ci", action="store_true", help="CI mode: strict checks, exit on any failure")

    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    parser.add_argument("--no-color", action="store_true", help="Disable colored output")

    args = parser.parse_args()

    # Disable colors if requested
    if args.no_color or args.json:
        for attr in dir(Colors):
            if not attr.startswith("_"):
                setattr(Colors, attr, "")

    if not args.json:
        print_header()

    # Initialize security manager
    manager = ModelSecurityManager(project_root=PROJECT_ROOT)

    # Find model files
    model_files = find_model_files(args.path)

    if not model_files:
        print(f"{Colors.RED}Error:{Colors.RESET} No .pkl model files found in {args.path}")
        sys.exit(3)

    if not args.json:
        print(f"Found {len(model_files)} model file(s)\n")

    # Check each model
    results = {}
    all_passed = True

    for i, model_path in enumerate(model_files, 1):
        if not args.json:
            print(f"{Colors.MAGENTA}{Colors.BOLD}Model {i}/{len(model_files)}: {model_path.name}{Colors.RESET}")
            print(f"{Colors.MAGENTA}{'─' * 60}{Colors.RESET}")

        success, message = check_model_integrity(model_path, manager, args.ci)

        results[str(model_path)] = {"success": success, "message": message}

        if not success:
            all_passed = False
            if not args.json:
                print(f"\n{Colors.RED}{Colors.BOLD}RESULT: FAILED{Colors.RESET}\n")

            if args.ci:
                # In CI mode, fail fast
                if not args.json:
                    print(f"{Colors.RED}CI Mode: Exiting due to failure{Colors.RESET}\n")
                sys.exit(1)
        else:
            if not args.json:
                print(f"\n{Colors.GREEN}{Colors.BOLD}RESULT: PASSED{Colors.RESET}\n")

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Summary
        print(f"{Colors.BOLD}╔════════════════════════════════════════════════════════╗{Colors.RESET}")
        print(f"{Colors.BOLD}║  SUMMARY                                               ║{Colors.RESET}")
        print(f"{Colors.BOLD}╚════════════════════════════════════════════════════════╝{Colors.RESET}")

        passed = sum(1 for r in results.values() if r["success"])
        failed = len(results) - passed

        print(f"\nTotal Models: {len(results)}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")

        if all_passed:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL CHECKS PASSED{Colors.RESET}")
            print(f"{Colors.GREEN}Models are secure and ready for deployment.{Colors.RESET}\n")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}✗ INTEGRITY CHECK FAILED{Colors.RESET}")
            print(f"{Colors.RED}Review failures above and re-sign models if necessary.{Colors.RESET}\n")

    # Exit with appropriate code
    if all_passed:
        sys.exit(0)
    else:
        sys.exit(1 if any("Signature" in r["message"] for r in results.values()) else 2)


if __name__ == "__main__":
    main()
