# Legacy RSI / Crypto Trading Bot Archive

> **WARNING**: This code is NOT part of ChainBridge and must NOT be used in production.

## What This Was

This archive contains historical artifacts from the **Benson RSI Multi-Signal Trading Bot** — a cryptocurrency trading experiment that predates the ChainBridge platform.

These files represent:
- RSI-based trading strategies
- Crypto exchange integrations (Kraken, etc.)
- Streamlit dashboards for signal visualization
- Dynamic cryptocurrency symbol selection
- Multi-signal ensemble decision systems

## Why It Was Archived

1. **Not part of ChainBridge**: These artifacts are unrelated to:
   - Supply chain management
   - Payment orchestration
   - Governance enforcement
   - Gateway decision evaluation

2. **Creates confusion**: Co-locating crypto trading code with enterprise governance creates:
   - Import confusion
   - CI noise
   - Developer misdirection
   - Security audit complexity

3. **Historical preservation**: Rather than delete, we archive for:
   - Reference
   - Forensics
   - Potential future extraction to separate repository

## Contents

```
archive/legacy-rsi-bot/
├── README.md                    # This file
├── Makefile.legacy              # Legacy build targets
├── Makefile.dashboard           # Dashboard build targets
├── Dockerfile.enterprise        # Enterprise deployment config
├── requirements-*.txt           # Legacy dependency files
├── viz_requirements.txt         # Visualization dependencies
├── *.sarif, *.bundle, *.txt     # Analysis/snapshot artifacts
├── config/                      # Config backups
├── scripts/                     # Shell scripts
│   ├── run_bot.sh
│   ├── start_trading.sh
│   ├── run_dashboard.sh
│   ├── monitor.sh
│   └── ...
└── src/                         # Python backups
    ├── multi_signal_bot.py.backup
    └── MultiSignalBot.py.backup
```

## Explicit Exclusions

This archive is:
- **NOT** in Python path
- **NOT** executed by CI
- **NOT** imported by any ChainBridge module
- **NOT** included in Docker builds

## Recovery

If you need to restore these targets:

```bash
# Copy Makefile.legacy back to root
cp archive/legacy-rsi-bot/Makefile.legacy ./Makefile.legacy

# Use legacy targets explicitly
make -f Makefile.legacy legacy-help
```

## Do Not

- Do NOT add this directory to PYTHONPATH
- Do NOT import from archive/
- Do NOT reference these scripts in CI
- Do NOT assume this code is maintained

---

**Archived**: December 2024
**Archived By**: ATLAS (GID-11) — Repository Integrity Engineer
**PAC Reference**: PAC-ARCHIVE-LEGACY-01
