# Ingestion Alignment Notes

**PAC Reference:** PAC-CODY-026 — Shadow Mode + Ingestion Alignment Patch
**Date:** 2025-01-XX
**Status:** ✅ Complete

---

## Overview

This document describes changes made to achieve **deterministic backend ingestion** with **zero drift** and **perfect feature parity** between the ML training pipeline and shadow mode inference.

---

## Changes Summary

### 1. ShipmentTrainingRow Property Accessors

**File:** `app/ml/datasets.py`

**Problem:** `ShipmentTrainingRow` required accessing nested `features.X` for each field, making code verbose and error-prone.

**Solution:** Added 15+ property accessors that delegate to the underlying `features` object:

```python
@property
def shipment_id(self) -> str:
    return self.features.shipment_id

@property
def planned_transit_hours(self) -> float:
    return self.features.planned_transit_hours
# ... etc
```

**Properties Added:**
- `shipment_id`, `origin`, `destination`, `corridor`
- `planned_transit_hours`, `carrier_id`, `mode`, `commodity_category`
- `historical_otd_rate`, `carrier_reliability_score`
- `origin_country`, `destination_country`, `is_international`
- `weight_kg`, `value_usd`

---

### 2. UTC Timezone Normalization

**Files:** `app/ml/ingestion.py`, `app/ml/event_parsing.py`

**Problem:** Mixed timezone-aware and naive datetimes caused `TypeError` in arithmetic operations.

**Solution:** Added `normalize_to_utc()` helper that treats naive datetimes as UTC:

```python
def normalize_to_utc(dt: datetime) -> datetime:
    """Normalize datetime to UTC. Treats naive datetimes as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
```

**Policy:** All datetime calculations now normalize to UTC before comparison/arithmetic.

---

### 3. 48-Hour Severe Delay Threshold

**File:** `app/ml/ingestion.py`

**Problem:**
- `planned_transit_hours` defaulted to `None` when missing
- `derive_severe_delay()` failed when `eta_deviation_hours` was `None`

**Solution:**
1. Explicit default: `planned_transit_hours = 48.0` when not specified
2. Direct calculation in `derive_severe_delay()`:

```python
def derive_severe_delay(events: list[ParsedEvent]) -> bool:
    """Derive severe_delay label. Uses >48 hour rule."""
    # Calculate actual delay directly with UTC normalization
    # Returns True if actual_hours - planned_hours > 48
```

**Rule:** `severe_delay = True` when `actual_transit - planned_transit > 48 hours`

---

### 4. Multi-Claim Loss Summation

**File:** `app/ml/ingestion.py`

**Problem:** `derive_loss_amount()` was returning `max()` of approved amounts for multiple claims.

**Solution:** Changed to `sum()` all approved claim amounts:

```python
def derive_loss_amount(events: list[ParsedEvent]) -> float:
    """Derive loss_amount label by summing all approved claim amounts."""
    total = 0.0
    for event in events:
        if event.event_type == "claim_filed":
            if event.payload.get("status") == "approved":
                total += event.payload.get("approved_amount", 0.0)
    return total
```

**Rationale:** A shipment with 2 claims of $180 and $280 represents $460 total loss, not $280.

---

### 5. Explicit None Checks for Defaults

**File:** `app/ml/ingestion.py`

**Problem:** `dict.get(key, default)` returns `None` when value is explicitly `None`, not the default.

**Solution:** Explicit None checks:

```python
# Before (broken)
planned_transit_hours = extracted.get("planned_transit_hours", 48.0)

# After (correct)
planned_transit_hours = extracted.get("planned_transit_hours")
if planned_transit_hours is None:
    planned_transit_hours = 48.0
```

---

## Test Coverage

### Ingestion Tests: 52 passing
- `test_ingestion_label_rules.py` — Label derivation (severe_delay, loss_amount)
- `test_ingestion_training_rows.py` — Training row creation

### Shadow Tests: 62 passing
- `test_shadow_mode.py` — Shadow mode enable/disable
- `test_shadow_repo.py` — Event persistence
- `test_shadow_corridor_analysis.py` — Drift detection
- `test_shadow_statistics.py` — Statistics computation

### Consistency Tests: 9 passing (NEW)
- `test_ingestion_shadow_consistency.py`
  - `TestIngestionShadowFeatureParity` — Feature field coverage
  - `TestIngestionShadowLabelConsistency` — Label derivation rules
  - `TestIngestionShadowTimezoneConsistency` — UTC handling
  - `TestIngestionShadowDataFlow` — End-to-end flow

**Total: 123 tests passing**

---

## CLI Backfill Command

**Location:** `app/ingest/backfill.py`

**Usage:**
```bash
python -m app.ingest.backfill <input.jsonl> [output.jsonl]
python -m app.ingest.backfill events.jsonl training.jsonl --verbose
python -m app.ingest.backfill events.jsonl --include-incomplete
```

**Options:**
- `--filter-incomplete` (default): Skip shipments without delivery events
- `--include-incomplete`: Include all shipments
- `--verbose, -v`: Enable verbose logging

---

## ALEX Governance Compliance

- ✅ No XGBoost imports in request path
- ✅ Inference latency unaffected (shadow mode is async)
- ✅ All changes are in ML training pipeline, not serving path

---

## File Change Summary

| File | Lines Changed | Type |
|------|--------------|------|
| `app/ml/datasets.py` | +100 | Property accessors |
| `app/ml/ingestion.py` | +50 | Label derivation fixes |
| `app/ml/event_parsing.py` | +15 | UTC normalization |
| `tests/test_ingestion_label_rules.py` | +5 | Test expectations |
| `tests/test_ingestion_training_rows.py` | +10 | Timestamp fixes |
| `tests/test_ingestion_shadow_consistency.py` | +200 | NEW - Consistency tests |
| `app/ingest/__init__.py` | +10 | NEW - Module exports |
| `app/ingest/backfill.py` | +115 | NEW - CLI command |

---

## Verification Commands

```bash
# Run all ingestion + shadow tests
python -m pytest tests/test_ingestion*.py tests/test_shadow*.py -v

# Test CLI
python -m app.ingest.backfill --help

# Validate specific functionality
python -c "from app.ml.datasets import ShipmentTrainingRow; print('OK')"
python -c "from app.ingest import backfill_training_data; print('OK')"
```
