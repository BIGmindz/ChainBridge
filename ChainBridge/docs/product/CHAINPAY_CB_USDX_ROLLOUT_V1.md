# CB-USDx Rail Rollout Policy (V1)

## 1. Purpose & Scope
Defines how ChainPay enables the CB-USDx rail, the modes of operation, and the phased adoption plan for the USD→MXN pilot (policy `CHAINPAY_V1_USD_MXN_P0`). This is a docs-only policy for Cody/Cindy (backend/config), Maggie/Dan (analytics/guardrails), and Sonny (UI labels).

## 2. Mode Definitions (Conceptual)
- **MODE_INTERNAL_ONLY**
  - Behavior: InternalLedgerRail only. No CB-USDx settlement calls.
  - Flag state: `CHAINPAY_USE_CB_USDX_RAIL=false` (current default).
  - Provider surfaced: `settlement_provider=INTERNAL_LEDGER`.
- **MODE_SHADOW** (future)
  - Behavior: InternalLedgerRail remains source of truth; CB-USDx rail runs in simulation, logging “would-send” transfers (no XRPL writes).
  - Purpose: Validate logic/volume/edge cases before value moves.
  - Provider surfaced: `settlement_provider=INTERNAL_LEDGER`, with shadow telemetry flagged.
- **MODE_LIMITED_PROD** (future)
  - Behavior: CB-USDx rail active for an allowlist (corridors/tiers/customers/notional caps); InternalLedgerRail used for out-of-scope or failover.
  - Provider surfaced per settlement: `CB_USDX` when eligible; fallback `INTERNAL_LEDGER` otherwise.
- **MODE_FULL_PROD** (future)
  - Behavior: CB-USDx is primary for allowed corridors/tiers; InternalLedgerRail as failover only.
  - Provider surfaced: predominantly `CB_USDX`, with explicit failover events logged.

Flag semantics (today vs future):
- Today: `CHAINPAY_USE_CB_USDX_RAIL` is a boolean gate mapped to MODE_INTERNAL_ONLY=false / future-mode=true. No enum implemented yet.
- Future design: `CHAINPAY_CB_USDX_MODE` enum {INTERNAL_ONLY, SHADOW, LIMITED_PROD, FULL_PROD}; optional allowlists and caps (see Section 5).

## 3. USD→MXN P0 – Adoption Plan (phased)
- **Phase 0 – Baseline**
  - Mode: MODE_INTERNAL_ONLY.
  - Rail used: InternalLedgerRail only.
  - Entry: current state; payout policy `CHAINPAY_V1_USD_MXN_P0` live; tests green.
  - Exit/rollback trigger: none (baseline).
  - Success signals: stable days-to-cash, SLA breach rate low, reserve utilization within 0.3–1.0 band (Maggie/Dan KPIs).

- **Phase 1 – Shadow Simulation (no XRPL)**
  - Mode: MODE_SHADOW (design-stage only; not coded yet).
  - Behavior: Simulate CB-USDx transfers alongside InternalLedgerRail; log would-be amounts, tx metadata, and provider=`CB_USDX_SHADOW` in analytics; no on-chain writes.
  - Entry: Phase 0 stable + ops sign-off to collect simulation data.
  - Exit to Phase 2 criteria (examples):
    - Simulation covers ≥ N shipments and all tiers (LOW/MED/HIGH/CRITICAL) without policy drift.
    - No simulation anomalies > threshold (e.g., rounding or batch mismatches).
  - Rollback: revert to Phase 0 (just stop simulation logging).

- **Phase 2 – Limited CB-USDx Production**
  - Mode: MODE_LIMITED_PROD.
  - Eligibility (initial for USD→MXN): corridor `USD_MXN`; tiers `LOW`, `MEDIUM`; max notional per shipment (e.g., USD 50k); allowlisted customers/carriers.
  - Behavior: Eligible settlements use CB-USDx rail; others route to InternalLedgerRail. Automatic failover to InternalLedgerRail on CB-USDx rail errors.
  - Entry: Phase 1 simulation KPIs clean + ops/finance approval + treasury buffer funded.
  - Exit to Phase 3 criteria (examples):
    - SLA: XRPL reconciliation within ≤15m for ≥99% of CB-USDx payouts over 30 days.
    - Loss/claim metrics stable vs baseline; no reserve breaches above threshold.
  - Rollback triggers: SLA breach > threshold, XRPL adapter instability, reserve/utilization outside guardrails.

- **Phase 3 – Broad CB-USDx Production**
  - Mode: MODE_FULL_PROD.
  - Scope: USD→MXN plus future corridors per policy; tiers and caps expanded per governance.
  - Behavior: CB-USDx as primary rail with documented failover path to InternalLedgerRail.
  - Entry: Phase 2 metrics sustained; governance approval for corridor expansion.
  - Rollback: revert to Phase 2 or 0 based on severity; maintain failover ready.

## 4. Entry/Exit Signals (examples, to be set by ops/analytics)
- **Entry to Phase 1:** tests stable; ops wants simulation telemetry.
- **Entry to Phase 2:** Phase 1 coverage across tiers; zero critical anomalies; treasury and trustlines ready for pilot allowlist.
- **Entry to Phase 3:** 30+ days of Phase 2 meeting SLA (recon ≤15m), loss rates within expected by tier, reserve utilization 0.3–1.0, claim SLA breach <10%.
- **Rollback conditions (any phase >0):** recon SLA breach beyond threshold, repeated rail errors, anomaly in reserve/loss metrics, or governance halt.

## 5. Configuration & Flags (design)
Current (in code):
- `CHAINPAY_USE_CB_USDX_RAIL` (bool)
  - false → MODE_INTERNAL_ONLY.
  - true → future could map to MODE_LIMITED_PROD or MODE_FULL_PROD; today remains internal-only until enum is implemented.

Proposed future config keys (document-only):
- `CHAINPAY_CB_USDX_MODE`: enum {INTERNAL_ONLY, SHADOW, LIMITED_PROD, FULL_PROD}
- `CHAINPAY_CB_USDX_ALLOWED_CORRIDORS`: list of corridor IDs (e.g., ["USD_MXN"])
- `CHAINPAY_CB_USDX_ALLOWED_TIERS`: list of tiers (e.g., ["LOW", "MEDIUM"])
- `CHAINPAY_CB_USDX_MAX_NOTIONAL_PER_SHIPMENT`: number (USD)
- `CHAINPAY_CB_USDX_ALLOWLIST_CUSTOMERS`: list of customer/broker IDs
- `CHAINPAY_CB_USDX_ALLOWLIST_CARRIERS`: list of carrier IDs
- `CHAINPAY_CB_USDX_FAILOVER_PROVIDER`: provider to use on error (default `INTERNAL_LEDGER`)

### Config matrix (USD→MXN P0)
| Phase | Mode | Rail Provider(s) Used | Corridors | Allowed Tiers | Max Notional | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | INTERNAL_ONLY | INTERNAL_LEDGER | USD_MXN | All | N/A | Current state (flag=false) |
| 1 | SHADOW | INTERNAL_LEDGER + simulated CB_USDX | USD_MXN | All | N/A | Simulation only, no XRPL writes |
| 2 | LIMITED_PROD | CB_USDX + INTERNAL_LEDGER fallback | USD_MXN | LOW, MEDIUM | e.g., $50k | Allowlisted customers/carriers |
| 3 | FULL_PROD | CB_USDX (+ failover) | USD_MXN + future corridors | Policy-defined | TBD | Broader rollout subject to governance |

## 6. Analytics & UI Alignment
- Maggie/Dan: slice metrics by `settlement_provider` (INTERNAL_LEDGER, CB_USDX, CB_USDX_SHADOW), `corridor_id`, `payout_policy_version`, and phase/mode.
- Sonny: show current mode/provider and eligibility (corridor/tiers/allowlist) in OC; flag failovers and shadow status.
- Cody/Cindy: log provider chosen per settlement; on failover, emit an event for analytics.

## 7. Governance & Safety
- Phased, reversible rollout; failover always available to InternalLedgerRail.
- Treasury/trustline prerequisites must be met before enabling LIMITED_PROD.
- All mode changes should be logged in governance log with operator, timestamp, reason, and expected blast radius.

## 8. Future Extensions
- Multi-corridor support following the same allowlist + caps pattern.
- Enum flag (`CHAINPAY_CB_USDX_MODE`) and admin UI to manage allowlists and caps.
- Automated gates: block mode promotion if reserve utilization or SLA metrics breach thresholds.
