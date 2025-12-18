# Archive Contract

> **LEGAL BOUNDARY**: This document defines the contract for all archived code.

---

## Purpose

This archive exists to preserve historical code that is **no longer part of ChainBridge**.

The archived code represents legacy experiments, specifically:
- RSI-based cryptocurrency trading bots
- Multi-signal trading engines
- Crypto exchange integrations
- Trading dashboards and visualization tools

These artifacts are retained for:
1. **Historical reference** — Understanding prior work
2. **Forensics** — Investigating past decisions
3. **Extraction** — Migrating to separate repositories if needed

---

## Contract Terms

### 1. Non-Executable

Archived code is **inert**. It must not:
- Be imported by any ChainBridge module
- Be executed by any CI pipeline
- Be included in any Docker build
- Be referenced by any Makefile target

### 2. Forbidden Imports

The following import patterns are blocked:

```python
# FORBIDDEN - Will fail CI
from archive import anything
from archive.legacy_rsi_bot import module
import archive
```

Violations trigger immediate CI failure via scope guard.

### 3. Excluded from Runtime

This directory is excluded from:
- `PYTHONPATH`
- `pytest` test discovery
- `ruff` / linting scope
- Docker `COPY` instructions
- Production deployments

### 4. Read-Only Intent

Contents should be treated as **read-only**. If you need to:
- **Use this code**: Extract to a separate repository
- **Reference this code**: Read directly, do not import
- **Delete this code**: Requires governance approval

---

## Directory Structure

```
archive/
└── legacy-rsi-bot/
    ├── README.md              # What this was, why archived
    ├── Makefile.legacy        # Original build targets
    ├── Makefile.dashboard     # Dashboard build targets
    ├── Dockerfile.enterprise  # Enterprise deployment
    ├── requirements-*.txt     # Legacy dependencies
    ├── config/                # Configuration backups
    ├── scripts/               # Shell scripts
    └── src/                   # Python source backups
```

---

## Enforcement

| Mechanism | Scope | Action |
|-----------|-------|--------|
| `scripts/scope_guard/check_repo_scope.py` | Local + CI | Fails on archive imports |
| `.github/workflows/scope-guard.yml` | CI | Blocks PRs with violations |
| `pytest.ini` testpaths | Tests | Excludes archive from discovery |
| `ruff.toml` exclude | Lint | Excludes archive from linting |

---

## Recovery Procedure

If you need to restore archived functionality:

```bash
# 1. Copy to separate location
cp -r archive/legacy-rsi-bot ~/chainbridge-legacy/

# 2. Create new repository
cd ~/chainbridge-legacy
git init
git add .
git commit -m "Extract legacy RSI bot from ChainBridge archive"

# 3. Never import back into ChainBridge
```

---

## Governance

| Field | Value |
|-------|-------|
| Contract Version | 1.0.0 |
| Created | December 2024 |
| Created By | ATLAS (GID-11) |
| PAC Reference | PAC-ATLAS-LEGACY-CLEAN-02 |
| Modification | Requires governance review |

---

**This archive is inert. Violations fail CI. No exceptions.**
