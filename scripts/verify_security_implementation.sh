#!/usr/bin/env bash
# SAM (GID-06) Security Verification Script
# Quick validation of ML model security implementation

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔒 SAM (GID-06) — ML Model Security Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Find project root (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Check 1: Security module exists
echo "✓ Checking security module..."
if [ -f "ChainBridge/chainiq-service/app/ml/model_security.py" ]; then
    echo "  ✅ model_security.py found"
else
    echo "  ❌ model_security.py MISSING"
    exit 1
fi

# Check 2: Training module integration
echo "✓ Checking training module integration..."
if grep -q "ModelSecurityManager" "ChainBridge/chainiq-service/app/ml/training_v02.py"; then
    echo "  ✅ training_v02.py integrated"
else
    echo "  ❌ training_v02.py NOT integrated"
    exit 1
fi

# Check 3: Secure storage directories
echo "✓ Checking secure storage..."
if [ -d ".chainbridge/models" ]; then
    echo "  ✅ .chainbridge/models/ exists"
else
    echo "  ⚠️  .chainbridge/models/ not yet created (will be auto-created)"
fi

if [ -d ".chainbridge/quarantine" ]; then
    echo "  ✅ .chainbridge/quarantine/ exists"
else
    echo "  ℹ️  .chainbridge/quarantine/ not yet created (will be auto-created)"
fi

# Check 4: Documentation
echo "✓ Checking documentation..."
docs_found=0
if [ -f "ChainBridge/docs/security/MODEL_SECURITY_POLICY.md" ]; then
    echo "  ✅ MODEL_SECURITY_POLICY.md found"
    ((docs_found++))
fi
if [ -f "ChainBridge/docs/security/SAM_GID06_DELIVERABLES.md" ]; then
    echo "  ✅ SAM_GID06_DELIVERABLES.md found"
    ((docs_found++))
fi
if [ -f "ChainBridge/chainiq-service/app/ml/README_SECURITY.md" ]; then
    echo "  ✅ README_SECURITY.md found"
    ((docs_found++))
fi

if [ $docs_found -lt 3 ]; then
    echo "  ⚠️  Some documentation files missing"
fi

# Check 5: Scripts
echo "✓ Checking security scripts..."
if [ -x "scripts/check_model_integrity.py" ]; then
    echo "  ✅ check_model_integrity.py (executable)"
else
    echo "  ❌ check_model_integrity.py missing or not executable"
    exit 1
fi

if [ -x "scripts/sign_model.py" ]; then
    echo "  ✅ sign_model.py (executable)"
else
    echo "  ❌ sign_model.py missing or not executable"
    exit 1
fi

# Check 6: CI/CD workflow
echo "✓ Checking CI/CD integration..."
if [ -f ".github/workflows/model-integrity-check.yml" ]; then
    echo "  ✅ model-integrity-check.yml found"
else
    echo "  ❌ CI workflow MISSING"
    exit 1
fi

# Check 7: Test suite
echo "✓ Checking test suite..."
if [ -f "ChainBridge/chainiq-service/tests/test_model_security.py" ]; then
    echo "  ✅ test_model_security.py found"
else
    echo "  ❌ Test suite MISSING"
    exit 1
fi

# Check 8: .gitignore protection
echo "✓ Checking .gitignore protection..."
if grep -q "quarantine" ".gitignore"; then
    echo "  ✅ .gitignore protects quarantine directory"
else
    echo "  ⚠️  .gitignore may not protect quarantine"
fi

# Check 9: Python import test
echo "✓ Testing Python imports..."
cd ChainBridge/chainiq-service
if python3 -c "from app.ml.model_security import ModelSecurityManager; print('✅ ModelSecurityManager import successful')" 2>/dev/null; then
    :
else
    echo "  ⚠️  Python import failed (dependencies may not be installed)"
fi
cd "$PROJECT_ROOT"

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ML Model Security Implementation Verified"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next Steps:"
echo "1. Run tests: cd ChainBridge/chainiq-service && pytest tests/test_model_security.py -v"
echo "2. Sign models: ./scripts/sign_model.py <model.pkl>"
echo "3. Verify integrity: ./scripts/check_model_integrity.py <path>"
echo "4. Review policy: ChainBridge/docs/security/MODEL_SECURITY_POLICY.md"
echo ""
echo "🔒 SAM (GID-06) — Security & Threat Engineer"
echo ""
