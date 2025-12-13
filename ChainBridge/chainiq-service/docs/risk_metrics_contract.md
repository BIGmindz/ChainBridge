# ChainIQ Risk Metrics Contract

This document locks the contract for structured risk evaluation logs and the analytics-facing schemas for downstream storage (Postgres/SQLite today, warehouse later). The service remains storage-agnostic; ETL jobs consume the logs and populate tables.

## LOG_EVENT shape (emitted by `/risk/score`)
- Prefix: `LOG_EVENT: ` followed by a JSON object on a single line.
- Fields:
  - `event_type` (string): Always `"RISK_EVALUATION"`.
  - `evaluation_id` (string, UUID): Unique per scoring call.
  - `timestamp` (ISO-8601, UTC): Time the score was produced.
  - `model_version` (string): Scoring model version, e.g., `chainiq_v1_maggie`.
  - `shipment_id` (string)
  - `carrier_id` (string)
  - `lane_id` (string, e.g., `US-MX`)
  - `risk_score` (int 0-100)
  - `risk_band` (string: LOW|MEDIUM|HIGH|CRITICAL)
  - `primary_reasons` (array[string]): Top contributors to the score.
  - `features_snapshot` (object): Point-in-time feature vector with keys:
    - `value_usd` (float)
    - `is_hazmat` (bool)
    - `is_temp_control` (bool)
    - `expected_transit_days` (int)
    - `iot_alert_count` (int)
    - `recent_delay_events` (int)
    - `lane_risk_index` (float)
    - `border_crossing_count` (int)
    - Additional keys may be included (e.g., carrier health stats) but the above are guaranteed.

### Example LOG_EVENT line
```json
{"prefix":"LOG_EVENT:","payload":{
  "event_type": "RISK_EVALUATION",
  "evaluation_id": "5d807545-0f03-4d9e-a2c6-8a6ac6c9f7f2",
  "timestamp": "2025-12-06T10:15:30.123456+00:00",
  "model_version": "chainiq_v1_maggie",
  "shipment_id": "SHP-LOG-1",
  "carrier_id": "CARR-LOG",
  "lane_id": "US-CA",
  "risk_score": 32,
  "risk_band": "LOW",
  "primary_reasons": ["Lane Risk Contribution: 6"],
  "features_snapshot": {
    "value_usd": 50000,
    "is_hazmat": false,
    "is_temp_control": false,
    "expected_transit_days": 3,
    "iot_alert_count": 1,
    "recent_delay_events": 0,
    "lane_risk_index": 0.1,
    "border_crossing_count": 1
  }
}}
```
(The emitted line is `LOG_EVENT: { ...json... }`; the wrapper above is to show structure.)

## Warehouse / DB schemas

### `risk_evaluations` (row-per-evaluation)
- `evaluation_id` (UUID, PK)
- `timestamp` (timestamptz)
- `model_version` (text)
- `shipment_id` (text)
- `carrier_id` (text)
- `lane_id` (text)
- `risk_score` (int)
- `risk_band` (text)
- `primary_reasons` (jsonb or text[])
- `features_snapshot` (jsonb) — must include the guaranteed feature keys above

### `risk_model_metrics` (aggregated model health)
- `model_version` (text)
- `window_start` (timestamptz)
- `window_end` (timestamptz)
- `total_evaluations` (int)
- `avg_score` (float)
- `p50_score` (float)
- `p90_score` (float)
- `p99_score` (float)
- `risk_band_counts` (jsonb: {"LOW": int, "MEDIUM": int, "HIGH": int, "CRITICAL": int})
- `data_freshness_ts` (timestamptz)
- Primary key recommendation: `(model_version, window_start, window_end)`

## ETL outline
1. **Ingest logs**: tail log output (stdout, file, or log forwarder) and extract lines starting with `LOG_EVENT:`.
2. **Parse**: strip the prefix and `json.loads` the remaining payload.
3. **Load `risk_evaluations`**: insert parsed events directly, coercing `timestamp` to timestamptz and `primary_reasons`/`features_snapshot` to JSON.
4. **Compute `risk_model_metrics`**: over a rolling window (e.g., 1h or 1d):
   - `total_evaluations`: count(*)
   - `avg_score`: avg(risk_score)
   - percentiles: p50/p90/p99 over risk_score
   - `risk_band_counts`: count by band
   - `data_freshness_ts`: max(timestamp)
5. **Publish**: write aggregates to `risk_model_metrics` for BI/dbt or alerts.

### Minimal Python sketch
```python
import json
from datetime import datetime
from uuid import UUID

RAW = "LOG_EVENT: {\"event_type\": ... }"
if RAW.startswith("LOG_EVENT: "):
    event = json.loads(RAW.split("LOG_EVENT: ", 1)[1])
    _ = UUID(event["evaluation_id"])  # validation
    # insert event into risk_evaluations; aggregate separately
```

## Local ETL & CLI

A developer-friendly CLI is available in `app/risk/etl_cli.py` to hydrate a local SQLite database from log files.

### Load logs from file
```bash
python -m app.risk.etl_cli load-log-file --path ./logs/risk_events.log
```
This parses lines starting with `LOG_EVENT:`, validates them, and upserts them into `chainiq_risk_metrics.db` (or custom `--db-url`).

### Preview latest evaluations
```bash
python -m app.risk.etl_cli show-latest --limit 5
```
Prints a table of the most recent risk scores stored in the local DB.

### Compute aggregate metrics
```bash
python -m app.risk.etl_cli compute-metrics --model-version chainiq_v1_maggie --window-days 30
```
Computes Maggie-style metrics (Critical Incident Recall, Ops Workload %, Calibration, etc.) from stored evaluations and persists a `RiskModelMetrics` row. Outputs a summary including any red-flag failures or warnings.

## Validation command
Run the risk API tests (includes log-shape assertion):
```
pytest -q app/risk/tests/test_api_risk.py
```
