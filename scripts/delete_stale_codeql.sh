#!/bin/bash
# Delete stale CodeQL configuration for trading-bot-ci.yml
# Requires: gh CLI authenticated to BIGmindz/ChainBridge

set -e

REPO="BIGmindz/ChainBridge"

echo "🔍 Fetching CodeQL analyses for ${REPO}..."

# Get all CodeQL analyses
ANALYSES=$(gh api "/repos/${REPO}/code-scanning/analyses" \
  --jq '.[] | select(.tool.name=="CodeQL") | {id, ref, created_at, tool, category}')

if [ -z "$ANALYSES" ]; then
  echo "❌ No CodeQL analyses found"
  exit 1
fi

echo "📋 Found analyses:"
echo "$ANALYSES" | jq -c '.'

# Find analyses from trading-bot-ci.yml workflow
STALE_IDS=$(echo "$ANALYSES" | jq -r 'select(.category == "trading-bot-ci.yml" or .ref == "refs/heads/trading-bot-ci") | .id')

if [ -z "$STALE_IDS" ]; then
  echo "⚠️  No stale trading-bot-ci analyses found by category/ref"
  echo ""
  echo "📌 Manual deletion required:"
  echo "   1. Visit: https://github.com/${REPO}/settings/security_analysis"
  echo "   2. Navigate to Code scanning → Configurations"
  echo "   3. Find 'trading-bot-ci.yml' with ⚠️ status"
  echo "   4. Click ⋮ → Delete configuration"
  exit 0
fi

echo "🗑️  Deleting stale analyses..."
for ANALYSIS_ID in $STALE_IDS; do
  echo "   Deleting analysis: $ANALYSIS_ID"
  gh api -X DELETE "/repos/${REPO}/code-scanning/analyses/${ANALYSIS_ID}" || true
done

echo "✅ Deletion complete"
echo ""
echo "🔄 Verify at: https://github.com/${REPO}/security/code-scanning"
