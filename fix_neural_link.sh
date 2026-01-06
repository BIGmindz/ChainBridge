#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# 🟥🟦🟩 CHAINBRIDGE ENVIRONMENT REPAIR SCRIPT 🟥🟦🟩
# ═══════════════════════════════════════════════════════════════════════════════
# PAC-ID: PAC-20260106-ENV-REPAIR
# Purpose: Nuke and rebuild .venv, then launch jeffrey_link.py
# Governance: INV-OPS-001 (Environment Determinism)
# ═══════════════════════════════════════════════════════════════════════════════

set -e  # Fail fast on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "🟥🟦🟩 CHAINBRIDGE NEURAL LINK REPAIR — STARTING 🟥🟦🟩"
echo "═══════════════════════════════════════════════════════════════════════════════"

# Step 1: Deactivate existing venv if active
echo ""
echo "[1/5] Deactivating existing virtual environment (if active)..."
if [[ -n "$VIRTUAL_ENV" ]]; then
    deactivate 2>/dev/null || true
    echo "      ✓ Deactivated: $VIRTUAL_ENV"
else
    echo "      ✓ No active virtual environment detected."
fi

# Step 2: Remove existing .venv
echo ""
echo "[2/5] Removing existing .venv directory..."
if [[ -d ".venv" ]]; then
    rm -rf .venv
    echo "      ✓ Removed .venv"
else
    echo "      ✓ No existing .venv found."
fi

# Step 3: Create fresh .venv
echo ""
echo "[3/5] Creating new virtual environment..."
python3 -m venv .venv
echo "      ✓ Created .venv using: $(python3 --version)"

# Step 4: Install dependencies
echo ""
echo "[4/5] Installing dependencies from requirements.txt..."
./.venv/bin/pip install --upgrade pip --quiet
./.venv/bin/pip install -r requirements.txt --quiet
echo "      ✓ Dependencies installed."

# Step 5: Export API Key and launch jeffrey_link.py
echo ""
echo "[5/5] Launching Jeffrey Neural Link..."
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

# Export the API key (user should set JEFFREY_API_KEY environment variable or edit here)
if [[ -z "$JEFFREY_API_KEY" ]]; then
    echo "⚠️  JEFFREY_API_KEY not set. Please export it before running:"
    echo "    export JEFFREY_API_KEY=\"your-api-key-here\""
    echo ""
    echo "Then re-run: ./fix_neural_link.sh"
    exit 1
fi

export JEFFREY_API_KEY="$JEFFREY_API_KEY"

# Launch using explicit path to new venv binary
exec ./.venv/bin/python jeffrey_link.py
