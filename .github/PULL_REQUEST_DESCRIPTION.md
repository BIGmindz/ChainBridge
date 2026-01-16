## Description

Promote `fail_closed_pipeline.yml` workflow from PR branches to `main` to resolve governance topology mismatch preventing PR merges.

**Critical governance fix:** Branch protection requires workflows to be defined on target branch.

## Problem Statement

GitHub branch protection enforces checks that must exist on `main`:
- `fail_closed_pipeline.yml` currently only exists on PR branches
- GitHub cannot resolve required checks not defined on target branch
- Creates infinite reconciliation loop blocking PR merges

## Solution

Isolated promotion of canonical fail-closed workflow to `main`:
- Single file: `.github/workflows/fail_closed_pipeline.yml`
- Zero logic changes (exact copy from PR #38)
- Governance topology now aligned

## Impact

**Unblocks:** PR #38 and all future infrastructure work
**Fixes:** Control-plane topology mismatch
**Classification:** Critical path governance correction

---

Closes #40
