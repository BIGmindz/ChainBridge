# ChainPay Risk & Settlement Analytics Spec (V1)

Owner: MAGGIE (GID-10) · Date: 2025-12-05 · Scope: Pilot corridor USD→MXN reefer · PAC: MAGGIE-004 (docs-only)

## 1. Commercial Audit – What Are We Measuring?
- Revenue: bps fees on CB-USDx volume; potential risk spread; value of faster days-to-cash for carriers.
- Risk: realized loss amounts vs reserve; mis-calibrated tiers (losses showing up in LOW/MEDIUM); operational risk from late reviews/claim handling.
- Core questions:
  - Are we getting paid enough for the risk we’re taking in each tier and corridor?
  - Are carriers actually experiencing better days-to-cash vs Net-30/45 baselines?
  - Do reserves and claim windows cover expected claims for each tier without starving good carriers?

## 2. Settlement Outcome Log – Canonical Schema
Logical table/model: `chainpay_settlement_outcomes` (1 row per shipment settlement lifecycle, PICKUP → CLAIM WINDOW CLOSE). Mark **R=Required**, **F=Future**.

**Identity & Routing (R):** shipment_id; corridor_id (e.g., USD_MXN); broker_id; carrier_id; shipper_id; created_at_utc; settlement_closed_at.

**Risk Inputs (R):** risk_score_initial (0–1); risk_tier_initial (LOW/MEDIUM/HIGH/CRITICAL); risk_model_version; risk_features_version (optional/F if unavailable).

**Payout & Reserve Config (R):** payout_pickup_percent; payout_delivered_percent; payout_claim_percent; claim_window_days; requires_manual_review (bool); payout_policy_version (from Pax/Cindy config).

**Financials (R):** cb_usd_total; cb_usd_released_at_pickup; cb_usd_released_at_delivery; cb_usd_released_at_claim_close; cb_usd_reserved_initial; cb_usd_reserved_unused; cb_usd_loss_realized. (FX fields F if/when multi-currency).

**Timing / SLA (R):** pickup_timestamp; delivered_timestamp; claim_window_open_timestamp; claim_window_close_timestamp; first_payment_timestamp; final_payment_timestamp; manual_review_open_timestamp / manual_review_close_timestamp (nullable if no review).

**Outcomes & Flags (R):** had_claim (bool); had_dispute (bool); claim_amount_cb_usd; manual_review_outcome (enum APPROVED/PARTIAL/REJECTED/NONE); tier_downgraded (bool); tier_upgraded (bool); settlement_status (enum CLEAN / LOSS_WITHIN_RESERVE / LOSS_ABOVE_RESERVE).

**Audit / Lineage (R):** analytics_version (this doc version); payout_matrix_version; created_by_service (e.g., chainpay-service); created_at_utc.

**Future (F):** IoT health summary, EDI doc health, lane volatility index, carrier scorecards, macro factors, explanations/top factors, decision_path_id.

Append-only/immutable per settlement outcome for auditability; updates via UPSERT should be idempotent on shipment_id + settlement cycle.

## 3. KPIs & Metrics – Glass-Box Definitions
All metrics sliced by corridor_id, risk_tier_initial, time window; optionally by carrier_id for ops triage.

- Days to First Cash: `first_payment_timestamp - pickup_timestamp` (or delivered_timestamp if pickup already paid). Unit: days. Meaning: carrier experience uplift vs Net-30/45.
- Days to Final Cash: `final_payment_timestamp - delivered_timestamp`. Unit: days. Meaning: speed to full settlement.
- Reserve Utilization: `cb_usd_loss_realized / cb_usd_reserved_initial`. Bands: <0.3 over-conservative; 0.3–1.0 healthy; >1.0 under-reserved.
- Loss Rate by Tier: `sum(cb_usd_loss_realized) / sum(cb_usd_total)` per risk_tier_initial. Expect monotonic: HIGH > MEDIUM > LOW; if LOW ≈ HIGH → model/policy broken.
- Unused Reserve Ratio: `cb_usd_reserved_unused / cb_usd_total`. High values → capital idle; track by tier/corridor.
- Tail Breach Count: count where `loss_amount_cb_usd > cb_usd_reserved_unused`. Signals reserve failure.
- Claim/Dispute Rate: `count(had_claim) / count(*)` and `count(had_dispute) / count(*)` per tier.
- SLA Breach – Manual Review: `count(manual_review_close_timestamp > claim_window_close_timestamp) / count(manual_review_open_timestamp not null)`. Ops reliability.
- Tier Calibration Quick Check: volume share per tier and claim rate per tier. Sanity that distribution and outcomes align with expectations.

Optional (future): Calibration bins and ECE/Brier per corridor once we store the full score distribution.

### SLA Metrics (formulas and required fields)
Fields available today in `SettlementOutcome` (R = present, F = future):
- R: `delivered_timestamp`, `first_payment_timestamp`, `final_payment_timestamp`, `claim_window_close_timestamp`.
- F (not yet in model_analytics): `claim_open_timestamp`, `claim_resolved_timestamp`, `manual_review_open_timestamp`, `manual_review_close_timestamp`, `claim_window_open_timestamp`.

Formulas (when F fields exist, use them; otherwise count only timing we have):
- Days to First Cash (D1): `D1 = (first_payment_timestamp - delivered_timestamp)` in days.
- Days to Final Cash (D2): `D2 = (final_payment_timestamp - delivered_timestamp)` in days.
- Cash SLA breach: `breach_cash = 1 if D2 > target_d2_p95_for_tier else 0`.
- Claim window breach (future): `breach_claim_window = 1 if claim_open_timestamp > claim_window_close_timestamp else 0`.
- Manual review SLA breach (future): `breach_manual_review = 1 if manual_review_close_timestamp > claim_window_close_timestamp else 0`.

USD→MXN P0 SLA targets (proposed, conservative):

| Tier | Target D2 p95 (days) | Max cash SLA breach % | Max claim window breach % |
| --- | --- | --- | --- |
| LOW | 5  | 2% | 1% |
| MEDIUM | 7 | 3% | 2% |
| HIGH | 10 | 5% | 3% |
| CRITICAL | 14 | 7% | 5% |

Notes:
- Use D2 p95 computed per tier over rolling window (e.g., 30/90 days). Targets are entry-level for P0; tighten after pilot data.
- Until claim timestamps exist, claim-window breach stays 0 by construction—Cody must add `claim_open_timestamp` (and optional `claim_resolved_timestamp`) to make this live.

## 4. Analytics Views & Dashboards (Operator & Benson)
- Risk Tier Health (Benson/Pax): loss rate vs reserve utilization by tier; volume share and claim rate by tier; tail breach counts. Answers: “Are tiers priced/configured correctly?”
- Days-to-Cash (Carriers/Brokers): median/P95 days_to_first_cash and days_to_final_cash by tier & corridor. Answers: “Are we delivering faster cash flow?”
- SLA & Reliability (Ops/Dan): SLA breach rates for manual reviews and claim windows; counts of disputes/claims by tier. Answers: “Is the system stable enough to scale?”

## 5. Implementation Notes (Cody, Dan, Sonny)
- Cody (backend): add `record_settlement_outcome(outcome)` in settlement finalization (claim window close or settlement_closed_at). UPSERT/append to `chainpay_settlement_outcomes`; include payout/risk snapshots to prevent drift; idempotent on shipment_id.
- Dan (data/ops): nightly (or hourly) batch to compute corridor×tier aggregates, emit `metrics/chainpay_risk_{date}.json` or table; add tests for formulas; CI contract: schema changes require doc/test update.
- Sonny (frontend): future OC “Analytics” tab with tier health cards, days-to-cash distributions, SLA stats; fed by Dan’s aggregates, not by live per-shipment calls.

## 6. Risks, Failure Modes, Mitigations
- Garbage-in timestamps/amounts → invalid metrics. Mitigate with required fields, non-negative checks, and QC rules (e.g., negative durations fail fast).
- Selection bias from pilot corridor → over-generalization. Mitigate by marking corridor_id and pilot_flag; avoid extrapolating beyond USD→MXN until data accrues.
- Spec/policy drift (tiers/payouts change without analytics_version bump) → misinterpretation. Mitigate by always logging payout_policy_version and analytics_version; block deployments that change schema without doc/test update.

## 7. BLUF & Next Steps
- BLUF: With the Settlement Outcome Log schema and glass-box KPIs, we can prove or disprove that the USD→MXN payout matrix and risk tiers are commercially sane (loss-aware, reserve-efficient, and faster cash for good carriers).
- Next PACs:
  - CODY: “CODY-010 – Implement SettlementOutcomeLog model + logging in settlement finalization path (idempotent UPSERT).”
  - DAN: “DAN-005 – Nightly ChainPay risk metrics job & alerting (corridor×tier aggregates, reserve/loss, days-to-cash, SLA breaches) plus CI contract.”
  - SONNY: “SONNY-004 – Operator Console analytics view fed by Dan’s aggregates (tier health, days-to-cash, SLA).”
