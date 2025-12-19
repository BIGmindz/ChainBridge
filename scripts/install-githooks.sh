#!/bin/sh
#
# PAC-DAN-PAC-ENFORCEMENT-01
# Install git hooks for ChainBridge repository
#
# Author: DAN (GID-07)
# Date: 2025-12-19
#
# Usage:
#   ./scripts/install-githooks.sh
#
# This script:
#   1. Sets git hooks path to .githooks/
#   2. Makes hooks executable
#   3. Verifies installation
#

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.githooks"

echo "════════════════════════════════════════════════════════════════════"
echo "Installing ChainBridge Git Hooks"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Check we're in a git repository
if [ ! -d "$REPO_ROOT/.git" ]; then
    echo "❌ ERROR: Not a git repository: $REPO_ROOT" >&2
    exit 1
fi

# Check hooks directory exists
if [ ! -d "$HOOKS_DIR" ]; then
    echo "❌ ERROR: Hooks directory not found: $HOOKS_DIR" >&2
    exit 1
fi

# Configure git to use our hooks directory
echo "[1/3] Configuring git hooks path..."
git -C "$REPO_ROOT" config core.hooksPath .githooks
echo "      ✅ Set core.hooksPath to .githooks"

# Make hooks executable
echo ""
echo "[2/3] Making hooks executable..."
chmod +x "$HOOKS_DIR"/*
for hook in "$HOOKS_DIR"/*; do
    if [ -f "$hook" ]; then
        echo "      ✅ $(basename "$hook")"
    fi
done

# Verify installation
echo ""
echo "[3/3] Verifying installation..."
CONFIGURED_PATH=$(git -C "$REPO_ROOT" config --get core.hooksPath 2>/dev/null || echo "")
if [ "$CONFIGURED_PATH" = ".githooks" ]; then
    echo "      ✅ Git hooks path verified"
else
    echo "      ❌ Failed to verify hooks path" >&2
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "✅ Git hooks installed successfully!"
echo ""
echo "Active hooks:"
for hook in "$HOOKS_DIR"/*; do
    if [ -f "$hook" ] && [ -x "$hook" ]; then
        echo "  - $(basename "$hook")"
    fi
done
echo ""
echo "Enforcement:"
echo "  - All commits must contain a PAC ID (PAC-[AGENT]-[TASK-ID])"
echo "  - Exempt: commits touching only docs/, .github/, README.md"
echo ""
echo "See: docs/governance/PAC_ENFORCEMENT.md"
echo "════════════════════════════════════════════════════════════════════"
