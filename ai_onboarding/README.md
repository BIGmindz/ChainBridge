# AI Onboarding Snapshots

**Purpose:** Deterministic onboarding snapshots for AI assistant context transfer.

---

## Directory Structure

```
ai_onboarding/
├── snapshots/     → ZIP files only (uploadable to ChatGPT Desktop)
├── manifests/     → MANIFEST.txt copies with file listings and hashes
└── README.md      → This file
```

---

## Usage

### 1. Generate Snapshot
Run the snapshot generation PAC to create a new ZIP in `snapshots/`.

### 2. Upload to ChatGPT
1. Navigate to `ai_onboarding/snapshots/`
2. Locate the latest `ChainBridge-snapshot-YYYYMMDD-HHMMSS.zip`
3. Upload to ChatGPT macOS Desktop app
4. Begin onboarding handshake

### 3. Verify Contents
Check corresponding manifest in `manifests/MANIFEST-YYYYMMDD-HHMMSS.txt` for:
- File count
- Total size
- SHA256 hash
- Complete file listing

---

## Naming Convention

| Artifact | Format |
|----------|--------|
| Snapshot ZIP | `ChainBridge-snapshot-YYYYMMDD-HHMMSS.zip` |
| Manifest | `MANIFEST-YYYYMMDD-HHMMSS.txt` |

---

## Exclusions

Snapshots **never** contain:
- `.env` files or secrets
- Credentials or API keys
- `node_modules/`, `__pycache__/`, `.venv/`
- Binary files, images, or large data files
- Git history (`.git/`)
- Build artifacts (`dist/`, `build/`, `htmlcov/`)
- Log files (`*.log`, `logs/`)
- Cache directories (`cache/`, `.cache/`)

---

## Git Exclusion

This directory is **excluded from git commits**. Add to `.gitignore`:

```
ai_onboarding/snapshots/
ai_onboarding/manifests/
```

Snapshots are local artifacts for manual upload only.

---

## Governance

| Property | Value |
|----------|-------|
| PAC Reference | PAC-BENSON-EXEC-REPO-SNAPSHOT-BOOT-002 |
| Schema | CHAINBRIDGE_CANONICAL_WRAP_SCHEMA v1.0.0 |
| Discipline | FAIL-CLOSED |
| Canon | PDO (Proof → Decision → Outcome) |

---

**Last Updated:** 2025-12-26
