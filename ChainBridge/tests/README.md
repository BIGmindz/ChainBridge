# ChainBridge Test Spine

## Core tests (OC/Intel)

These validate the Operator Console + Global Intel backend spine.

Run core tests only:

```bash
./scripts/run_oc_intel_tests.sh
# or
python -m pytest -q -m core
```

Core tests:

- tests/test_live_positions_api.py
- tests/test_intel_global_snapshot_api.py

## Phase 2 tests (marketplace/RWA)

Tests marked with `@pytest.mark.phase2` cover marketplace, staking, Hedera, SxT, and other future modules. They are not required to be green for current milestones.

Run all tests:

```bash
python -m pytest
```
