#!/usr/bin/env python3
"""
PAC-DOC-P222-API-CONTRACT-V2: OpenAPI Schema Generator

Freezes the Sovereign Server API contract as static JSON.
The Interface is Law - extractable without runtime dependency.

v2.0 Update:
  - Captures FinancialTrace, fee_strategy, and full financial schemas
  - Outputs to docs/api/v2/openapi.json
  - "A Sovereign speaks clearly and writes it down."

Usage:
    python scripts/generate_openapi.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def generate_openapi_contract():
    """Extract OpenAPI schema from Sovereign Server v2.0 and freeze as contract."""
    
    print("=" * 70)
    print("PAC-DOC-P222-API-CONTRACT-V2: Schema Extraction")
    print("\"A Sovereign speaks clearly and writes it down.\"")
    print("=" * 70)
    
    # Import the FastAPI application
    print("\n[1/5] Importing Sovereign Server v2.0 application...")
    from sovereign_server import app
    print("      ✓ Application imported successfully")
    
    # Extract the OpenAPI schema
    print("\n[2/5] Extracting OpenAPI schema...")
    openapi_schema = app.openapi()
    api_version = openapi_schema.get('info', {}).get('version', 'unknown')
    print(f"      ✓ Schema version: {openapi_schema.get('openapi', 'unknown')}")
    print(f"      ✓ API title: {openapi_schema.get('info', {}).get('title', 'unknown')}")
    print(f"      ✓ API version: {api_version}")
    
    # Count components
    paths = openapi_schema.get('paths', {})
    schemas = openapi_schema.get('components', {}).get('schemas', {})
    print(f"      ✓ Endpoints: {len(paths)}")
    print(f"      ✓ Schema models: {len(schemas)}")
    
    # v2 specific: Check for financial models
    print("\n[3/5] Verifying v2.0 Financial Models...")
    v2_models = ['FinancialTrace', 'TransactionReceipt', 'PaymentData']
    for model in v2_models:
        if model in schemas:
            print(f"      ✓ {model}: PRESENT")
        else:
            print(f"      ⚠ {model}: MISSING")
    
    # Check PaymentData for fee_strategy field
    payment_data = schemas.get('PaymentData', {}).get('properties', {})
    if 'fee_strategy' in payment_data:
        print("      ✓ PaymentData.fee_strategy: PRESENT")
    else:
        print("      ⚠ PaymentData.fee_strategy: MISSING")
    
    # Determine version directory (extract major.minor from version)
    version_parts = api_version.split('.')
    version_dir = f"v{version_parts[0]}" if version_parts else "v2"
    
    # Ensure output directory exists
    output_dir = project_root / "docs" / "api" / version_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write the schema with formatting for human readability
    print(f"\n[4/5] Writing contract to docs/api/{version_dir}/openapi.json...")
    output_path = output_dir / "openapi.json"
    with open(output_path, 'w') as f:
        json.dump(openapi_schema, f, indent=2, sort_keys=False)
    print(f"      ✓ Contract written: {output_path}")
    
    # Calculate contract hash for attestation
    import hashlib
    with open(output_path, 'rb') as f:
        contract_hash = hashlib.sha256(f.read()).hexdigest()
    print(f"      ✓ Contract hash: {contract_hash[:16]}...")
    
    # Generate attestation log
    print(f"\n[5/5] Generating attestation log...")
    logs_dir = project_root / "logs" / "docs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine PAC based on version
    pac_id = "PAC-DOC-P222-API-CONTRACT-V2" if api_version.startswith("2.") else "PAC-DOC-P97-API-CONTRACT"
    attestation_name = "MASTER-BER-P222-CONTRACT" if api_version.startswith("2.") else "MASTER-BER-P97-CONTRACT"
    ledger_commit = "ATTEST: API_SCHEMA_V2_FROZEN" if api_version.startswith("2.") else "ATTEST: API_SCHEMA_FROZEN"
    
    attestation = {
        "pac_id": pac_id,
        "execution_time": datetime.now(timezone.utc).isoformat(),
        "status": "CONTRACT_RATIFIED",
        "artifact": f"docs/api/{version_dir}/openapi.json",
        "contract_hash": contract_hash,
        "openapi_version": openapi_schema.get('openapi'),
        "api_version": api_version,
        "endpoints_frozen": list(paths.keys()),
        "models_frozen": list(schemas.keys()),
        "v2_financial_models": {
            "FinancialTrace": "FinancialTrace" in schemas,
            "fee_strategy": "fee_strategy" in payment_data
        },
        "invariants_enforced": [
            "INV-DOC-001: Truth in Documentation - docs cannot lie about code",
            "INV-DOC-002: Accessibility - contract exists even if server is dead"
        ],
        "attestation": attestation_name,
        "ledger_commit": ledger_commit
    }
    
    log_filename = f"API_V{version_parts[0]}_CONTRACT_GENERATION.json" if version_parts else "API_CONTRACT_GENERATION.json"
    log_path = logs_dir / log_filename
    with open(log_path, 'w') as f:
        json.dump(attestation, f, indent=2)
    print(f"      ✓ Attestation logged: {log_path}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("CONTRACT RATIFIED")
    print("=" * 70)
    print(f"Artifact:     docs/api/{version_dir}/openapi.json")
    print(f"API Version:  {api_version}")
    print(f"Hash:         {contract_hash}")
    print(f"Attestation:  {attestation_name}")
    print(f"Ledger:       {ledger_commit}")
    print("=" * 70)
    print("\n🔒 The Contract is signed. The Interface is Law.")
    
    return {
        "status": "success",
        "artifact": str(output_path),
        "hash": contract_hash,
        "api_version": api_version,
        "attestation": attestation
    }


if __name__ == "__main__":
    result = generate_openapi_contract()
    sys.exit(0 if result["status"] == "success" else 1)
