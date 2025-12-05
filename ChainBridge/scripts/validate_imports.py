"""
ChainBridge Import Validator Script
Scans for broken imports and validates importlib_metadata safety.
"""
import sys
import importlib
import traceback
from core.import_safety import ensure_import_safety

LIBRARIES = [
    "importlib.metadata",
    "importlib_metadata",
    "fastapi",
    "sqlalchemy",
    "pydantic",
    "uvicorn",
    "pytest",
    "ccxt",
    "xrpl",
    "numpy",
    "pandas",
]

def main():
    print("[Import Safety] Validating Python import environment...")
    errors = []
    try:
        ensure_import_safety()
    except Exception as e:
        errors.append(f"Import safety check failed: {e}")
    for lib in LIBRARIES:
        try:
            importlib.import_module(lib)
            print(f"[OK] {lib}")
        except Exception as e:
            errors.append(f"[FAIL] {lib}: {e}\n{traceback.format_exc()}")
    if errors:
        print("\n[Import Safety] FAILURES DETECTED:")
        for err in errors:
            print(err)
        sys.exit(1)
    print("\n[Import Safety] All imports validated successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()
