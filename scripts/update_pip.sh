#!/bin/bash
# Canonical Pip Update Gateway
# Ensures both virtual environments have latest pip versions
# Author: BENSON [GID-00]
# Date: 2026-01-25

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "========================================"
echo "CANONICAL PIP UPDATE GATEWAY"
echo "========================================"
echo ""

# Update .venv (Python 3.11)
if [ -d ".venv" ]; then
    echo "🔄 Updating pip in .venv (Python 3.11)..."
    .venv/bin/python -m pip install --upgrade pip --quiet
    PIP_VERSION_1=$(.venv/bin/python -m pip --version | awk '{print $2}')
    echo "✅ .venv pip: $PIP_VERSION_1"
else
    echo "⚠️  .venv not found - skipping"
fi

echo ""

# Update .venv-pac41 (Python 3.13)
if [ -d ".venv-pac41" ]; then
    echo "🔄 Updating pip in .venv-pac41 (Python 3.13)..."
    .venv-pac41/bin/python3.13 -m pip install --upgrade pip --quiet
    PIP_VERSION_2=$(.venv-pac41/bin/python3.13 -m pip --version | awk '{print $2}')
    echo "✅ .venv-pac41 pip: $PIP_VERSION_2"
else
    echo "⚠️  .venv-pac41 not found - skipping"
fi

echo ""
echo "========================================"
echo "✅ All pip installations up to date"
echo "========================================"
