## Trading Bot De-Coupling

As of 2026-01, all trading bot systems have been intentionally removed from
the ChainBridge repository.

### Rationale
- ChainBridge is an enterprise logistics and governance platform
- Trading systems have different risk, compliance, and CI requirements
- Co-location caused repeated CI and scope violations

### Action Taken
- All trading bot code, CI, and documentation removed
- Git history preserved for audit purposes
- Trading bot development to continue in a separate repository

### Approval
- Benson CTO
