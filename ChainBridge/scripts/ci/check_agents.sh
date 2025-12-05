#!/usr/bin/env bash
set -euo pipefail

# Look for newly added files under AGENTS/
if git diff --cached --name-only --diff-filter=A | grep '^AGENTS/' >/dev/null 2>&1; then
  echo "ERROR: New agent files must go under 'AGENTS 2/', not 'AGENTS/'."
  echo "AGENTS/ is deprecated; see AGENTS/README.md."
  exit 1
fi
