#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAC-DAN-031: Legacy Workflow Cleanup Script
# Author: DAN (GID-07) DevOps & CI/CD Lead
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# This script identifies and optionally removes deprecated CI/CD workflows
# that have been superseded by the normalized workflow suite.
#
# USAGE:
#   ./cleanup_legacy_workflows.sh [--dry-run]
#   ./cleanup_legacy_workflows.sh --execute
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Find repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}           PAC-DAN-031: Legacy Workflow Cleanup                         ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEPRECATED WORKFLOWS (superseded by normalized suite)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Root-level workflows to deprecate (moved to ChainBridge/)
ROOT_DEPRECATED=(
    ".github/workflows/ci.yml"                    # → ci-core.yml
    ".github/workflows/model-integrity-check.yml" # → ci-model-integrity.yml
    ".github/workflows/chainbridge-ci.yml"        # → ci-core.yml
)

# ChainBridge workflows to deprecate (consolidated)
CHAINBRIDGE_DEPRECATED=(
    ".github/workflows/python-ci.yml"         # → ci-core.yml
    ".github/workflows/chainpay-iq-ui-ci.yml" # → ci-core.yml
    ".github/workflows/tests.yml"             # → ci-core.yml
    ".github/workflows/ci-basic.yml"          # → ci-core.yml
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ACTIVE WORKFLOWS (keep these!)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ACTIVE_WORKFLOWS=(
    ".github/workflows/ci-core.yml"           # Unified Python CI
    ".github/workflows/ci-model-integrity.yml" # Model security
    ".github/workflows/deploy-staging.yml"    # Staging pipeline
    ".github/workflows/repo-sanity.yml"       # Repo validation
    ".github/workflows/alex-governance.yml"   # ALEX governance
    ".github/workflows/shadow-ci.yml"         # Shadow mode (PAC-DAN-023)
    ".github/workflows/agent_ci.yml"          # Agent CI
    ".github/workflows/kafka-ci.yml"          # Kafka service CI
)

# Workflows to review (keep or deprecate based on usage)
REVIEW_WORKFLOWS=(
    ".github/workflows/governance_check.yml"     # Review: may duplicate alex-governance
    ".github/workflows/pac_color_check.yml"      # Review: PAC-specific, keep if used
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DRY RUN MODE (default)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DRY_RUN=true
if [[ "$1" == "--execute" ]]; then
    DRY_RUN=false
    echo -e "${RED}⚠️  EXECUTE MODE - Files will be moved to .deprecated/${NC}"
    echo ""
fi

# Create deprecated folder
DEPRECATED_DIR="$REPO_ROOT/.deprecated-workflows"
if [[ "$DRY_RUN" == false ]]; then
    mkdir -p "$DEPRECATED_DIR"
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCAN AND REPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${GREEN}✅ ACTIVE WORKFLOWS (keep):${NC}"
for workflow in "${ACTIVE_WORKFLOWS[@]}"; do
    if [[ -f "$REPO_ROOT/$workflow" ]]; then
        echo -e "   ${GREEN}✓${NC} $workflow"
    else
        echo -e "   ${YELLOW}⚠${NC} $workflow (not found)"
    fi
done
echo ""

echo -e "${YELLOW}🔍 WORKFLOWS TO REVIEW:${NC}"
for workflow in "${REVIEW_WORKFLOWS[@]}"; do
    if [[ -f "$REPO_ROOT/$workflow" ]]; then
        echo -e "   ${YELLOW}?${NC} $workflow"
    fi
done
echo ""

echo -e "${RED}❌ DEPRECATED WORKFLOWS (to remove):${NC}"
DEPRECATED_COUNT=0

# Root deprecated
for workflow in "${ROOT_DEPRECATED[@]}"; do
    if [[ -f "$REPO_ROOT/$workflow" ]]; then
        echo -e "   ${RED}✗${NC} $workflow"
        DEPRECATED_COUNT=$((DEPRECATED_COUNT + 1))

        if [[ "$DRY_RUN" == false ]]; then
            # Move to deprecated folder
            DEST="$DEPRECATED_DIR/$(basename "$workflow")"
            mv "$REPO_ROOT/$workflow" "$DEST"
            echo -e "     ${BLUE}→ Moved to .deprecated-workflows/${NC}"
        fi
    fi
done

# ChainBridge deprecated
for workflow in "${CHAINBRIDGE_DEPRECATED[@]}"; do
    if [[ -f "$REPO_ROOT/$workflow" ]]; then
        echo -e "   ${RED}✗${NC} $workflow"
        DEPRECATED_COUNT=$((DEPRECATED_COUNT + 1))

        if [[ "$DRY_RUN" == false ]]; then
            # Move to deprecated folder
            DEST="$DEPRECATED_DIR/$(basename "$workflow")"
            mv "$REPO_ROOT/$workflow" "$DEST"
            echo -e "     ${BLUE}→ Moved to .deprecated-workflows/${NC}"
        fi
    fi
done

echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SUMMARY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}                           SUMMARY                                       ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "Active workflows:     ${GREEN}${#ACTIVE_WORKFLOWS[@]}${NC}"
echo -e "Deprecated workflows: ${RED}${DEPRECATED_COUNT}${NC}"
echo -e "Needs review:         ${YELLOW}${#REVIEW_WORKFLOWS[@]}${NC}"
echo ""

if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}This was a DRY RUN. No files were modified.${NC}"
    echo -e "To execute cleanup, run: ${GREEN}./cleanup_legacy_workflows.sh --execute${NC}"
else
    echo -e "${GREEN}✅ Cleanup complete!${NC}"
    echo -e "Deprecated files moved to: ${BLUE}$DEPRECATED_DIR${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review .deprecated-workflows/ contents"
    echo "  2. Commit changes: git add -A && git commit -m 'chore(ci): cleanup deprecated workflows'"
    echo "  3. Delete .deprecated-workflows/ folder after verification"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
