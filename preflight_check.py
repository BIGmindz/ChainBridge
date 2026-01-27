#!/usr/bin/env python3
"""Comprehensive ChainBridge Preflight Checks"""
import sys
import os
from pathlib import Path

print("\n" + "="*70)
print("🚀 CHAINBRIDGE PREFLIGHT CHECKS")
print("="*70 + "\n")

# Check 1: Python Environment
print("📦 [1/6] Python Environment")
py_version = sys.version.split()[0]
py_major, py_minor = map(int, py_version.split('.')[:2])
REQUIRED_MAJOR = 3
REQUIRED_MINOR = 11
if py_major >= REQUIRED_MAJOR and py_minor >= REQUIRED_MINOR:
    print(f"   ✅ Python {py_version} (>= {REQUIRED_MAJOR}.{REQUIRED_MINOR} required)")
else:
    print(f"   ❌ Python {py_version} INSUFFICIENT - {REQUIRED_MAJOR}.{REQUIRED_MINOR}+ REQUIRED")
    print(f"   ⚠️  CRITICAL: ChainBridge requires Python {REQUIRED_MAJOR}.{REQUIRED_MINOR} or higher")
    all_deps_ok = False
print(f"   ✅ Platform: {sys.platform}")

# Check 2: Core Dependencies
print("\n📚 [2/6] Core Dependencies")
dependencies = [
    ('yaml', 'PyYAML'),
    ('numpy', 'NumPy'),
    ('pandas', 'Pandas'),
    ('requests', 'Requests'),
    ('ccxt', 'CCXT (crypto exchange)'),
    ('scipy', 'SciPy'),
    ('sklearn', 'scikit-learn')
]

# Optional PQC dependency (non-critical)
pqc_deps = [
    ('dilithium', 'dilithium-py (PQC ML-DSA) [OPTIONAL]')
]

all_deps_ok = True
for module, name in dependencies:
    try:
        __import__(module)
        print(f"   ✅ {name}")
    except ImportError:
        print(f"   ❌ {name} (missing)")
        all_deps_ok = False

# Check optional dependencies
for module, name in pqc_deps:
    try:
        __import__(module)
        print(f"   ✅ {name}")
    except ImportError:
        print(f"   ℹ️  {name} (not installed)")

# Check 3: Directory Structure
print("\n📁 [3/6] Directory Structure")
critical_dirs = ['config', 'scripts', 'tests', 'modules', 'occ', 'src', 'core']
for d in critical_dirs:
    if Path(d).exists():
        print(f"   ✅ {d}/")
    else:
        print(f"   ⚠️  {d}/ (missing)")

# Check 4: Configuration Files
print("\n⚙️  [4/6] Configuration Files")
config_files = [
    'config/auth_config.yaml',
    'config/blockchain_config.yaml',
    'config/governance.json',
    'core/governance/auth_policies.json',
    'core/governance/gid_registry.json',
    'core/governance/scram_policies.json',
    'pyproject.toml',
    'docker-compose.yml'
]
for f in config_files:
    if Path(f).exists():
        print(f"   ✅ {f}")
    else:
        print(f"   ⚠️  {f} (missing)")

# Check 5: Environment Variables
print("\n🔐 [5/6] Environment Variables")
env_vars = ['HOME', 'PATH', 'USER']
for var in env_vars:
    if os.getenv(var):
        print(f"   ✅ {var}")
    else:
        print(f"   ⚠️  {var} (not set)")

# Check 6: Write Permissions
print("\n✍️  [6/6] Write Permissions")
test_dirs = ['logs', 'reports', 'proofpacks', 'data']
for d in test_dirs:
    p = Path(d)
    if p.exists() and os.access(p, os.W_OK):
        print(f"   ✅ {d}/ writable")
    elif p.exists():
        print(f"   ⚠️  {d}/ not writable")
    else:
        print(f"   ⚠️  {d}/ does not exist")

print("\n" + "="*70)
if all_deps_ok:
    print("✅ PREFLIGHT CHECKS COMPLETE - SYSTEM READY")
else:
    print("⚠️  PREFLIGHT CHECKS COMPLETE - SOME DEPENDENCIES MISSING")
print("="*70 + "\n")

sys.exit(0 if all_deps_ok else 1)
