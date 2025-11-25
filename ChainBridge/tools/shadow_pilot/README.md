# Shadow Pilot

Simulation harness for financeability and protocol revenue on historical shipment data.

## Inputs
- CSV with columns: `shipment_id`, `cargo_value_usd`, `delivery_timestamp`, `planned_delivery_timestamp`, `pickup_timestamp`, `exception_flag`, `loss_flag`, `loss_amount_usd`. Optional: `days_to_payment` (defaults to 45 when missing).
- Timestamps should be parseable ISO strings; flags expected as 0/1.

## CLI
```bash
python -m tools.shadow_pilot.shadow_pilot \
  --input shipments_history.csv \
  --out-dir ./shadow_output \
  --annual_rate 0.06 \
  --advance_rate 0.7 \
  --take_rate 0.01
```

Or import programmatically:

```python
from pathlib import Path
from tools.shadow_pilot import run_shadow_pilot_from_csv

summary, results, _ = run_shadow_pilot_from_csv(
    Path("shipments_history.csv"),
    annual_rate=0.06,
    advance_rate=0.7,
    take_rate=0.01,
)
```

## Outputs
- `shadow_results.csv`: per-shipment truth score, financeability, financed amount, days pulled forward, working capital saved, protocol revenue, avoided loss, salvage revenue.
- `summary.json`: aggregated totals (`total_gmv_usd`, `financeable_gmv_usd`, `financed_gmv_usd`, `protocol_revenue_usd`, `working_capital_saved_usd`, `losses_avoided_usd`, `salvage_revenue_usd`, `average_days_pulled_forward`, counts).

## Notes
- Financeability defaults: `min_value=50000`, `min_truth=0.7`. Override with `--min_value` and `--min_truth`.
- Truth score recipe is intentionally simple and clamped to `[0.0, 1.0]` for the MVP.
