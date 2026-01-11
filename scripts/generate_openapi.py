#!/usr/bin/env python3
"""
PAC-DOC-P97-API-CONTRACT: OpenAPI Schema Generator

Freezes the Sovereign Server API contract as static JSON.
The Interface is Law - extractable without runtime dependency.

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
    """Extract OpenAPI schema from Sovereign Server and freeze as contract."""
    
    print("=" * 60)
    print("PAC-DOC-P97-API-CONTRACT: Schema Extraction")
    print("=" * 60)
    
    # Import the FastAPI application
    print("\n[1/4] Importing Sovereign Server application...")
    from sovereign_server import app
    print("      ✓ Application imported successfully")
    
    # Extract the OpenAPI schema
    print("\n[2/4] Extracting OpenAPI schema...")
    openapi_schema = app.openapi()
    print(f"      ✓ Schema version: {openapi_schema.get('openapi', 'unknown')}")
    print(f"      ✓ API title: {openapi_schema.get('info', {}).get('title', 'unknown')}")
    print(f"      ✓ API version: {openapi_schema.get('info', {}).get('version', 'unknown')}")
    
    # Count components
    paths = openapi_schema.get('paths', {})
    schemas = openapi_schema.get('components', {}).get('schemas', {})
    print(f"      ✓ Endpoints: {len(paths)}")
    print(f"      ✓ Schema models: {len(schemas)}")
    
    # Ensure output directory exists
    output_dir = project_root / "docs" / "api" / "v1"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write the schema with formatting for human readability
    print("\n[3/4] Writing contract to docs/api/v1/openapi.json...")
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
    print("\n[4/4] Generating attestation log...")
    logs_dir = project_root / "logs" / "docs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    attestation = {
        "pac_id": "PAC-DOC-P97-API-CONTRACT",
        "execution_time": datetime.now(timezone.utc).isoformat(),
        "status": "CONTRACT_RATIFIED",
        "artifact": "docs/api/v1/openapi.json",
        "contract_hash": contract_hash,
        "openapi_version": openapi_schema.get('openapi'),
        "api_version": openapi_schema.get('info', {}).get('version'),
        "endpoints_frozen": list(paths.keys()),
        "models_frozen": list(schemas.keys()),
        "invariants_enforced": [
            "INV-DOC-001: Truth in Documentation - docs cannot lie about code",
            "INV-DOC-002: Accessibility - contract exists even if server is dead"
        ],
        "attestation": "MASTER-BER-P97-CONTRACT",
        "ledger_commit": "ATTEST: API_SCHEMA_FROZEN"
    }
    
    log_path = logs_dir / "API_CONTRACT_GENERATION.json"
    with open(log_path, 'w') as f:
        json.dump(attestation, f, indent=2)
    print(f"      ✓ Attestation logged: {log_path}")
    
    # Final summary
    print("\n" + "=" * 60)
    print("CONTRACT RATIFIED")
    print("=" * 60)
    print(f"Artifact:     docs/api/v1/openapi.json")
    print(f"Hash:         {contract_hash}")
    print(f"Attestation:  MASTER-BER-P97-CONTRACT")
    print(f"Ledger:       ATTEST: API_SCHEMA_FROZEN")
    print("=" * 60)
    print("\n🔒 The Contract is signed. The Interface is Law.")
    
    return {
        "status": "success",
        "artifact": str(output_path),
        "hash": contract_hash,
        "attestation": attestation
    }


if __name__ == "__main__":
    result = generate_openapi_contract()
    sys.exit(0 if result["status"] == "success" else 1)
