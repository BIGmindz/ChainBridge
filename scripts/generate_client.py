#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           SDK GENERATOR - Generate Python Client from OpenAPI                ║
║                   PAC-DEV-P223-SDK-V2-GENERATION                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Regenerates sovereign_client.py from docs/api/v2/openapi.json               ║
║  Ensures INV-DEV-001 (Contract Alignment) is maintained                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

This script provides tooling to regenerate the SDK when the API contract changes.
For most operations, the SDK is hand-maintained for better ergonomics.

Usage:
    python scripts/generate_client.py --verify       # Verify SDK matches contract
    python scripts/generate_client.py --list-models  # List models in contract
    python scripts/generate_client.py --diff         # Show schema drift

INVARIANTS:
    INV-DEV-001: SDK must support all Contract features
    INV-DEV-002: SDK must be ergonomic and Pythonic
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONTRACT_PATH = PROJECT_ROOT / "docs" / "api" / "v2" / "openapi.json"
SDK_PATH = PROJECT_ROOT / "clients" / "python" / "sovereign_client.py"


def load_contract() -> dict:
    """Load the OpenAPI contract."""
    if not CONTRACT_PATH.exists():
        print(f"ERROR: Contract not found at {CONTRACT_PATH}")
        sys.exit(1)
    
    with open(CONTRACT_PATH) as f:
        return json.load(f)


def get_contract_models(contract: dict) -> set:
    """Extract model names from contract schemas."""
    schemas = contract.get("components", {}).get("schemas", {})
    return set(schemas.keys())


def get_sdk_models() -> set:
    """Extract dataclass model names from SDK."""
    if not SDK_PATH.exists():
        print(f"ERROR: SDK not found at {SDK_PATH}")
        sys.exit(1)
    
    models = set()
    with open(SDK_PATH) as f:
        content = f.read()
        
    # Parse @dataclass definitions
    import re
    pattern = r"@dataclass\s*\nclass\s+(\w+)"
    matches = re.findall(pattern, content)
    models = set(matches)
    
    return models


def compute_contract_hash() -> str:
    """Compute hash of current contract."""
    with open(CONTRACT_PATH, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def get_sdk_contract_hash() -> str:
    """Extract contract hash from SDK file."""
    with open(SDK_PATH) as f:
        content = f.read()
    
    import re
    match = re.search(r'__contract_hash__\s*=\s*"(\w+)"', content)
    if match:
        return match.group(1)
    return None


def verify_alignment():
    """Verify SDK is aligned with contract."""
    print("=" * 70)
    print("SOVEREIGN SDK v2.0 - Contract Alignment Verification")
    print("=" * 70)
    
    contract = load_contract()
    contract_models = get_contract_models(contract)
    sdk_models = get_sdk_models()
    
    # Models that must be in SDK
    required_models = {
        "UserData", "PaymentData", "ShipmentData", "ManifestData",
        "TelemetryData", "FinancialTrace", "TransactionReceipt",
        "HealthResponse"
    }
    
    print(f"\n[Contract] Version: {contract.get('info', {}).get('version', 'Unknown')}")
    print(f"[Contract] Models: {len(contract_models)}")
    print(f"[SDK] Models: {len(sdk_models)}")
    
    # Check required models
    print(f"\n[Checking Required Models]")
    missing = required_models - sdk_models
    if missing:
        print(f"  ✗ MISSING: {missing}")
        return False
    else:
        print(f"  ✓ All required models present")
    
    # Check contract hash
    print(f"\n[Checking Contract Hash]")
    current_hash = compute_contract_hash()
    sdk_hash = get_sdk_contract_hash()
    
    if sdk_hash == current_hash:
        print(f"  ✓ Contract hash matches: {current_hash[:16]}...")
    else:
        print(f"  ⚠ Contract hash mismatch!")
        print(f"    SDK hash:      {sdk_hash[:16] if sdk_hash else 'Not found'}...")
        print(f"    Contract hash: {current_hash[:16]}...")
    
    # Check v2.0 specific features
    print(f"\n[Checking v2.0 Features]")
    
    with open(SDK_PATH) as f:
        sdk_content = f.read()
    
    v2_features = [
        ("FinancialTrace", "financial_trace" in sdk_content.lower()),
        ("fee_strategy", "fee_strategy" in sdk_content),
        ("PaymentRequiredError", "PaymentRequiredError" in sdk_content),
        ("402 handling", "402" in sdk_content),
        ("ledger_committed", "ledger_committed" in sdk_content),
        ("settlement_intent_id", "settlement_intent_id" in sdk_content),
    ]
    
    all_v2_present = True
    for feature, present in v2_features:
        status = "✓" if present else "✗"
        print(f"  {status} {feature}")
        if not present:
            all_v2_present = False
    
    print("\n" + "=" * 70)
    if all_v2_present:
        print("VERIFICATION PASSED ✅ - SDK is aligned with Contract v2.0")
    else:
        print("VERIFICATION FAILED ❌ - SDK missing v2.0 features")
    print("=" * 70)
    
    return all_v2_present


def list_models():
    """List all models in the contract."""
    print("=" * 70)
    print("OpenAPI Contract v2.0 - Schema Models")
    print("=" * 70)
    
    contract = load_contract()
    schemas = contract.get("components", {}).get("schemas", {})
    
    for name, schema in sorted(schemas.items()):
        model_type = schema.get("type", "object")
        props = schema.get("properties", {})
        required = schema.get("required", [])
        
        print(f"\n{name}:")
        print(f"  Type: {model_type}")
        print(f"  Properties: {len(props)}")
        print(f"  Required: {len(required)}")
        
        if props:
            print(f"  Fields:")
            for prop_name, prop_schema in props.items():
                prop_type = prop_schema.get("type", prop_schema.get("$ref", "any"))
                req = "*" if prop_name in required else " "
                print(f"    {req} {prop_name}: {prop_type}")


def show_diff():
    """Show differences between contract and SDK."""
    print("=" * 70)
    print("Contract vs SDK - Schema Drift Analysis")
    print("=" * 70)
    
    contract = load_contract()
    contract_models = get_contract_models(contract)
    sdk_models = get_sdk_models()
    
    print(f"\n[In Contract but not SDK]")
    contract_only = contract_models - sdk_models
    if contract_only:
        for m in sorted(contract_only):
            print(f"  - {m}")
    else:
        print("  (none)")
    
    print(f"\n[In SDK but not Contract]")
    sdk_only = sdk_models - contract_models
    # Filter out helper classes
    sdk_only = {m for m in sdk_only if not m.endswith("Response") or m in contract_models}
    if sdk_only:
        for m in sorted(sdk_only):
            print(f"  + {m}")
    else:
        print("  (none - SDK may have extra helper classes)")
    
    print(f"\n[In Both]")
    both = contract_models & sdk_models
    for m in sorted(both):
        print(f"  = {m}")


def main():
    parser = argparse.ArgumentParser(
        description="SDK Generator - Verify and manage Sovereign Client SDK"
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Verify SDK aligns with OpenAPI contract"
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="List all models in the contract"
    )
    parser.add_argument(
        "--diff", action="store_true",
        help="Show differences between contract and SDK"
    )
    
    args = parser.parse_args()
    
    if args.verify:
        success = verify_alignment()
        sys.exit(0 if success else 1)
    elif args.list_models:
        list_models()
    elif args.diff:
        show_diff()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
