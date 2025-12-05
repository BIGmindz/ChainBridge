# ChainPay CB-USDx Guardrails (USD→MXN P0) – V1

Owner: MAGGIE (GID-10) · Date: 2025-12-05 · PAC: MAGGIE-005

## 1. Commercial Audit – Why Guardrails Matter
- CB-USDx shifts settlement from internal ledger to tokenized flow for USD→MXN P0; errors propagate to real cashflow.
- Guardrails jobs-to-be-done:
  - Prevent loss blowups per tier/corridor (loss rate, tail breaches).
  - Keep days-to-cash within promised SLA so carriers see value.
  - Detect miscalibrated tiers/policies early (too generous/too harsh).
  - Provide stop/slow/go signals for Pax rollout phases.
- Critical KPIs: loss rate; SLA breach rate (cash timing + claim window); p95 days-to-final-cash (D2); reserve utilization / unused reserve ratio.

## 2. SLA Formulas (derived from SettlementOutcome)
- Available fields now: delivered_timestamp, first_payment_timestamp, final_payment_timestamp, claim_window_close_timestamp.
- Missing (TODO Cody): claim_open_timestamp, claim_resolved_timestamp, manual_review_open_timestamp, manual_review_close_timestamp, claim_window_open_timestamp.
- Definitions:
  - D1 (days to first cash) = first_payment_timestamp − delivered_timestamp (days).
  - D2 (days to final cash) = final_payment_timestamp − delivered_timestamp (days).
  - Cash SLA breach: 1 if D2 > tier_target_d2_p95 (see table), else 0.
  - Claim-window breach (future): 1 if claim_open_timestamp > claim_window_close_timestamp, else 0.
  - Manual-review breach (future): 1 if manual_review_close_timestamp > claim_window_close_timestamp, else 0.

USD→MXN P0 SLA targets (conservative):

| Tier | Target D2 p95 (days) | Max cash SLA breach % | Max claim-window breach % |
| --- | --- | --- | --- |
| LOW | 5  | 2% | 1% |
| MEDIUM | 7 | 3% | 2% |
| HIGH | 10 | 5% | 3% |
| CRITICAL | 14 | 7% | 5% |

## 3. Red/Amber/Green Thresholds (per KPI, USD→MXN P0)
Apply over rolling 30d (fast) and 90d (stable) windows. All rates per tier.

### Loss rate (loss / cb_usd_total)
- LOW: Green ≤0.25%; Amber 0.25–0.5%; Red >0.5%
- MEDIUM: Green ≤0.35%; Amber 0.35–0.7%; Red >0.7%
- HIGH: Green ≤0.6%; Amber 0.6–1.0%; Red >1.0%
- CRITICAL: Green ≤1.0%; Amber 1.0–1.5%; Red >1.5%

### SLA breach – cash timing (D2 vs target)
- Green: breach_rate ≤ target_max_breach (table above)
- Amber: target_max_breach < breach_rate ≤ (target_max_breach + 3pp)
- Red: breach_rate > (target_max_breach + 3pp)

### p95 Days-to-Final-Cash (D2)
- Green: p95 ≤ tier target (table above)
- Amber: tier target < p95 ≤ (tier target + 2 days)
- Red: p95 > (tier target + 2 days)

### Unused reserve ratio (cb_usd_reserved_unused / cb_usd_reserved_initial)
- Green: 10–30%
- Amber: 5–10% or 30–40%
- Red: <5% or >40%

## 4. Phase Gates for CB-USDx Rollout (USD→MXN P0)
Rollout phases from CHAINPAY_CB_USDX_ROLLOUT_V1: INTERNAL_ONLY → SHADOW → LIMITED_PROD → FULL_PROD.

Entry criteria (all computed over last 90d unless noted):
- Phase 0 → Phase 1 (Shadow): require corridor-level data present; no Reds on loss rate or D2 p95; Amber allowed if shipment_count < minimal volume (e.g., <20).
- Phase 1 → Phase 2 (Limited Prod): for LOW & MEDIUM tiers: loss rate Green; cash SLA breach Green; D2 p95 Green/Amber (not Red); unused reserve not Red. HIGH/CRITICAL may remain Shadow if volume low.
- Phase 2 → Phase 3 (Full Prod): 90d all-Green for LOW/MEDIUM; Amber allowed for HIGH with explicit monitoring; no Red anywhere. Require minimum volume (e.g., ≥50 settlements/tier) to trust metrics.

Rollback/freeze rules (monitor rolling 30d):
- If any tier hits Red on loss rate or cash SLA breach for two consecutive 7d windows → freeze CB-USDx for that tier (switch to INTERNAL_LEDGER) and alert Pax/ALEX.
- If D2 p95 Red for two consecutive 7d windows → throttle payouts (policy-level hold) and investigate ops bottlenecks.
- If unused reserve Red (<5% or >40%) for 30d → recalibrate payout/reserve config before continuing rollout.

## 5. Implementation Notes (Cody, Dan, Sonny)
- Cody (backend):
  - Ensure `SettlementOutcome` captures missing timestamps (claim_open/claim_resolved/manual_review_open/manual_review_close/claim_window_open). Mark new fields nullable; backfill not required for P0 but enables SLA math.
  - Extend analytics_service aggregates to emit: loss counts, breach counts, p95 D2, shipment counts per tier and window.
- Dan (data/ops):
  - Nightly job: compute 30d/90d per-tier KPIs; assign R/A/G; evaluate phase-gate criteria; emit guardrail status (JSON/table).
  - CI test: synthetic fixtures that trip Red/Amber/Green to validate guardrail logic.
  - Alerts: on any Red sustained 2×7d windows, raise Pager/Slack and set “freeze recommended” flag for corridor/tier.
- Sonny (OC):
  - Show guardrail badge per corridor/tier (R/A/G) and banner when rollout phase is blocked by a Red condition.
  - Expose latest “guardrail status” and “phase gate” evaluation timestamps.

## 6. Risks & Mitigations
- Missing timestamps → SLA metrics blind. Mitigation: add fields; until then, surface “SLA metrics provisional” banner.
- Low volume → noisy rates. Mitigation: allow Amber when shipment_count below thresholds; use longer windows.
- Policy drift without versioning → misread metrics. Mitigation: always log payout_policy_version and analytics_version; refuse evaluation if missing.

## 7. BLUF & Next Steps
- BLUF: USD→MXN P0 guardrails are now mathematically defined (loss/SLA/unused reserve thresholds) and tied to CB-USDx rollout phases with freeze/advance rules.
- Next PACs:
  - CODY: add missing SLA timestamps to SettlementOutcome and extend analytics_service outputs.
  - DAN: implement nightly guardrail evaluator + alerts + CI fixtures.
  - SONNY: add guardrail R/A/G indicators and phase-block banners in the OC using Dan’s status feed.
