# Git Hooks Setup — Governance Enforcement

## Overview

ChainBridge uses local git hooks for pre-commit governance enforcement. These hooks run the PAC linter and validate governance compliance before allowing commits.

## Quick Setup

```bash
# Configure git to use the .githooks directory
git config core.hooksPath .githooks

# Verify
git config --get core.hooksPath
# Should output: .githooks
```

## Available Hooks

### pre-commit

**Location:** `.githooks/pre-commit`

**Purpose:** Blocks commits containing governance violations.

**Checks performed:**
1. **PAC Lint** — Runs `tools/pac_linter.py --check` on staged Python files
2. **Structure Check** — Verifies PACs have required EXECUTING AGENT and EXECUTING COLOR
3. **GID/Color Alignment** — Verifies TEAL is only used by GID-00
4. **Hybrid Artifact Detection** — Ensures PAC and Evidence are not mixed in same file

**Exit behavior:**
- Exit 0: All checks pass, commit proceeds
- Exit 1: Violations found, commit blocked

### commit-msg

**Location:** `.githooks/commit-msg`

**Purpose:** Ensures commit messages contain valid PAC IDs.

**Allowlist:** Commits touching only `docs/`, `.github/`, or `README.md` bypass this check.

## Manual Hook Execution

You can run hooks manually to test:

```bash
# Run pre-commit hook
./.githooks/pre-commit

# Run commit-msg hook (requires commit message file)
echo "PAC-TEST-001: Test commit" > /tmp/commit_msg
./.githooks/commit-msg /tmp/commit_msg
```

## Troubleshooting

### Hook not running

Verify hooks path is set:
```bash
git config --get core.hooksPath
```

If empty, run:
```bash
git config core.hooksPath .githooks
```

### Permission denied

Ensure hooks are executable:
```bash
chmod +x .githooks/*
```

### Python not found

Ensure Python 3 is available:
```bash
which python3
```

The hooks require Python 3.8+ with access to the repository's `tools/` directory.

## Bypass (NOT PERMITTED)

There is no bypass flag for governance hooks. If you believe a violation is a false positive:

1. Open an issue describing the false positive
2. Tag ALEX (GID-08) for governance review
3. Wait for rule update if approved

Do NOT use `--no-verify` to skip hooks. CI will still block the PR.

---

**PAC Reference:** PAC-BENSON-ATLAS-GOVERNANCE-HARDENING-01
**Maintained by:** ATLAS (GID-11)
