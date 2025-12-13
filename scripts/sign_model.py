#!/usr/bin/env python3
"""
Model Signing Script for ChainIQ ML Models
SAM (GID-06) - Security & Threat Engineer

Convenience script for signing trained models after deployment.

Usage:
    # Sign a model
    ./scripts/sign_model.py ChainBridge/chainiq-service/app/ml/models/risk_model_v0.2.pkl

    # Sign with specific metadata
    ./scripts/sign_model.py risk_v0.2.0.pkl --sklearn 1.3.0 --numpy 1.24.3
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "ChainBridge" / "chainiq-service"))

from app.ml.model_security import ModelSecurityManager


def get_dependency_versions():
    """Auto-detect dependency versions if possible."""
    versions = {}

    try:
        import sklearn

        versions["sklearn"] = sklearn.__version__
    except ImportError:
        versions["sklearn"] = "unknown"

    try:
        import numpy as np

        versions["numpy"] = np.__version__
    except ImportError:
        versions["numpy"] = "unknown"

    return versions


def main():
    parser = argparse.ArgumentParser(description="Sign ChainIQ ML Model Artifacts", formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("model_path", type=Path, help="Path to model .pkl file")

    parser.add_argument("--name", help="Model name (default: inferred from filename)")

    parser.add_argument("--version", help="Model version (default: inferred from filename)")

    parser.add_argument("--sklearn", help="scikit-learn version (default: auto-detected)")

    parser.add_argument("--numpy", help="NumPy version (default: auto-detected)")

    parser.add_argument("--training-date", help="Training date in ISO format (default: today)")

    args = parser.parse_args()

    # Validate model path
    model_path = args.model_path
    if not model_path.exists():
        print(f"❌ Error: Model file not found: {model_path}")
        sys.exit(1)

    # Infer model name and version from filename if not provided
    if not args.name or not args.version:
        filename = model_path.stem  # e.g., "risk_model_v0.2" or "risk_v0.2.0"

        if not args.name:
            # Extract name (everything before version)
            if "_v" in filename:
                args.name = filename.split("_v")[0]
            else:
                args.name = filename

        if not args.version:
            # Extract version (everything after "_v")
            if "_v" in filename:
                args.version = "v" + filename.split("_v")[1]
            else:
                args.version = "v1.0.0"

    # Auto-detect dependency versions
    auto_versions = get_dependency_versions()
    sklearn_version = args.sklearn or auto_versions["sklearn"]
    numpy_version = args.numpy or auto_versions["numpy"]

    # Initialize security manager
    manager = ModelSecurityManager(project_root=PROJECT_ROOT)

    print("\n🔒 Signing Model")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Model: {model_path}")
    print(f"Name: {args.name}")
    print(f"Version: {args.version}")
    print(f"scikit-learn: {sklearn_version}")
    print(f"NumPy: {numpy_version}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    try:
        # Sign the model
        sig_path = manager.sign_model(
            model_path,
            model_name=args.name,
            model_version=args.version,
            training_date=args.training_date,
            sklearn_version=sklearn_version,
            numpy_version=numpy_version,
        )

        print("\n✅ SUCCESS")
        print(f"Signature saved to: {sig_path}")
        print("\nNext steps:")
        print(f"1. Verify signature: python3 -m app.ml.model_security verify {model_path}")
        print(f"2. Deploy to production: cp {model_path}* .chainbridge/models/")
        print(f"3. Commit both files: git add {model_path} {sig_path}\n")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
