# Synthetic Risk Grid (Maggie Sandbox)

## Purpose
The Synthetic Risk Grid Evaluator is an offline tool designed to evaluate the `chainiq_v1_maggie` risk engine across a configurable grid of shipment scenarios. It allows for:
- Sweeping key feature dimensions (value, hazmat, delays, etc.).
- Verifying engine behavior over a wide range of conditions.
- Generating datasets for calibration analysis and visualization.

## Usage

The tool is available as a CLI module within the `chainiq-service`.

### Core Mode (Default)
Generates a smaller, focused grid of scenarios to avoid combinatorial explosion.

```bash
cd chainiq-service
.venv/bin/python -m app.risk.synthetic_eval --mode core --out ./tmp/synthetic_core.csv
```

### Extended Mode
Generates a comprehensive grid covering more feature combinations. Use with `--max-rows` to limit output size if needed.

```bash
cd chainiq-service
.venv/bin/python -m app.risk.synthetic_eval --mode extended --max-rows 1000 --out ./tmp/synthetic_extended_sample.csv
```

## Output Format
The tool produces a CSV file with the following columns:
- `scenario_id`: Sequential identifier.
- Input Features: `origin`, `destination`, `value_usd`, `is_hazmat`, `is_temp_control`, `expected_transit_days`, `iot_alert_count`, `recent_delay_events`, `lane_risk_index`, `border_crossing_count`, `carrier_incident_rate_90d`, `carrier_tenure_days`.
- Output: `risk_score`, `risk_band`.

## Determinism
The generator is deterministic. Running the tool with the same configuration will always produce the same set of scenarios and scores.
