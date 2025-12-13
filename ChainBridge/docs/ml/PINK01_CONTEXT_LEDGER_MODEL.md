# PINK-01 Context Ledger Risk Model (v1.1)

> **Legend**:
> 🩷 **MAGGIE** (GID-10) — Chief AI Architect
> 🟢 **ALEX** (GID-08) — Governance & Alignment
> 🔵 **ATLAS** — Infrastructure & Security

## Purpose

PINK-01 scores ChainPay settlement context events for manual review and
operator attention. It provides a glass-box probability that a context
requires additional scrutiny, a calibrated risk band, and a small set of
human-readable reasons that can be surfaced directly in the Operator
Console.

This model is used by the ChainPay Context Ledger risk rail and feeds
the risk strip on the Operator Console.

## Inputs

The model ultimately consumes engineered features derived from
context-ledger style inputs. Key feature groups:

- `amount_log`: Log-transformed settlement amount.
- `risk_score`: Heuristic pre-score capturing amount, corridor and
  channel risk, reversals, recent failures and traffic.
- `reason_code_intensity`: Count of prior alerts / reasons.
- `policy_stack_depth`: Count of active policies applied.
- `corridor_risk_factor`: Encodes historically higher-churn corridors.
- `velocity_score`: Normalized recent event velocity.
- `anomaly_indicator`: Binary flag for unusual activity density.
- `role_tier_weight`: Weight derived from counterparty role tier.

The target label (`requires_manual_review`) is derived from `risk_score`
and `decision_status` in `ml_engine/feature_store/context_ledger_features.py`.

On the ChainPay side, `ContextLedgerEvent` includes:

- Event metadata: `event_id`, `timestamp`, `event_type`.
- Monetary fields: `amount`, `currency`.
- Route information: `corridor_id`, `route_notional_7d_usd`.
- Counterparty information: `counterparty_id`, `counterparty_role`,
  `counterparty_notional_30d_usd`.
- Activity statistics: `recent_event_count_24h`,
  `recent_failed_count_7d`.

These are transformed into features in
`chainpay-service/app/services/context_ledger_risk.py`.

## Outputs

The primary runtime output is `RiskScoreResponse` defined in
`chainpay-service/app/schemas_context_risk.py`:

- `risk_score` (float, 0–1): Model probability that the context requires
  manual review.
- `anomaly_score` (float, 0–1): Lightweight anomaly scalar derived from
  the probability and activity flags.
- `risk_band` ("LOW" | "MEDIUM" | "HIGH" | "CRITICAL"): Calibrated
  band for operators and policy.
- `top_features` (list[str]): Most influential model-level signals.
- `reason_codes` (list[str]): Operator-grade reason codes from a closed
  vocabulary.
- `trace_id` (str): Carries through the originating `event_id`.
- `version` (str): Defaults to `"pink-01"`; PINK-01 v1.1 is the current
  calibrated configuration.

## Band Thresholds (v1.1)

Banding is applied in the ChainPay wrapper via
`_map_score_to_band(probability)` in
`chainpay-service/app/services/context_ledger_risk.py`.

For a model probability `p` in `[0.0, 1.0]`:

- `0.00 ≤ p < 0.35` → `LOW`
- `0.35 ≤ p < 0.65` → `MEDIUM`
- `0.65 ≤ p < 0.80` → `HIGH`
- `0.80 ≤ p ≤ 1.00` → `CRITICAL`

The underlying model buckets in
`ml_engine/models/context_ledger_risk_model.py` use the same LOW / MEDIUM /
HIGH cut points (0.35 and 0.65) for consistency, while the CRITICAL
promotion is handled exclusively in the wrapper.

## Reason Codes (Closed Vocabulary)

PINK-01 v1.1 exposes a small, closed vocabulary of reason codes via
`_reason_codes(features)` in
`chainpay-service/app/services/context_ledger_risk.py`.

Codes and intent:

- `REPEATED_REVERSALS_ON_ROUTE` – Multiple or recent reversal events on
  this lane.
- `REPEATED_SETTLEMENT_FAILURES` – Elevated count of failed settlements
  in the last 7 days.
- `HIGH_RISK_CORRIDOR` – Corridor historically associated with higher
  investigative load.
- `ELEVATED_ROUTE_NOTIONAL` – 7-day route notional is high for this
  corridor.
- `CONCENTRATED_COUNTERPARTY_EXPOSURE` – 30-day notional is concentrated
  in a single counterparty.
- `AFTER_HOURS_ACTIVITY` – Activity is occurring outside normal
  operating hours.
- `XRPL_SETTLEMENT_CHANNEL` – XRPL-based settlement channel in use.
- `ONCHAIN_TOKEN_CHANNEL` – On-chain token settlement channel in use
  (non-XRPL).
- `BASELINE_MONITORING` – No specific elevated risk factor; baseline
  monitoring only.

At runtime the list is ordered by salience and truncated to a maximum of
five reasons to avoid overwhelming operators.

## Example Decisions

### Example: Low-Risk Context

- Medium-size payment on a stable corridor.
- Bank settlement channel during business hours.
- Low recent event and failure counts.

Expected output:

- `risk_score` in LOW band (< 0.35).
- `risk_band`: `"LOW"` or `"MEDIUM"` depending on context.
- `reason_codes`: `["BASELINE_MONITORING"]`.

### Example: High / Critical Risk Context

- Large payment (e.g., > 250k USD equivalent) on a corridor flagged as
  high risk.
- XRPL or on-chain token settlement.
- Reversal event with high recent failures and traffic.

Expected output:

- `risk_score` ≥ 0.65, often ≥ 0.80.
- `risk_band`: `"HIGH"` or `"CRITICAL"`.
- `reason_codes` includes at least:
  - `"REPEATED_REVERSALS_ON_ROUTE"`
  - `"REPEATED_SETTLEMENT_FAILURES"`
  - `"HIGH_RISK_CORRIDOR"`
  - Possibly `"XRPL_SETTLEMENT_CHANNEL"` or `"ONCHAIN_TOKEN_CHANNEL"`.

## Governance & Versioning

- Model implementation:
  - `ml_engine/models/context_ledger_risk_model.py`
  - `ml_engine/feature_store/context_ledger_features.py`
- ChainPay wrapper and schema:
  - `chainpay-service/app/services/context_ledger_risk.py`
  - `chainpay-service/app/schemas_context_risk.py`
- Tests:
  - `tests/ml/test_context_ledger_risk_model.py`
  - `chainpay-service/tests/test_context_ledger_risk_service.py`

Any change to:

- Band thresholds,
- Reason code vocabulary or conditions,
- Target derivation logic,

must be accompanied by:

1. An update to this document with a new minor version (e.g., v1.2).
2. Updated tests that exercise the new thresholds / reasons.
3. Confirmation that all the above tests pass.

PINK-01 v1.1 is the baseline for the ChainPay v1 pilot corridor and
should remain stable for the duration of the pilot unless a governance
change is explicitly approved.

---

🩷 **MAGGIE** — Chief AI Architect
