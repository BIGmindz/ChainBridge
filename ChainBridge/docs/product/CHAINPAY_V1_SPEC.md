# ChainPay v1 Product Specification

## 1. Title & Summary

ChainPay v1 is a risk-aware settlement layer for mid-market 3PLs and digital freight brokers operating an initial USD→MXN reefer corridor (Laredo, TX → Monterrey, MX). It turns shipment context + IoT + ChainIQ risk scores into a governed 20/70/10 payout schedule, reducing days-to-pay while preserving controls. All milestone accounting is kept in an off-chain context ledger, with optional mirroring of final net settlements onto XRPL; brokers get faster, more transparent cash flow, and carriers see clear rules for when and how they get paid.

See `docs/ai/CHAINPAY_RISK_ANALYTICS_V1.md` for the companion risk analytics and monitoring spec.

## 2. Problem Statement

- **Slow settlement cycles:** Carriers routinely wait **21+ days** to get paid, creating working capital stress and friction with brokers.
- **Disputes around damage and temperature:** Reefer moves are particularly contentious; parties argue after the fact about spoilage, delays, and door events because evidence is fragmented.
- **Opaque payout rules:** Carriers and brokers lack a shared, machine-readable view of **when**, **why**, and **how much** gets released at each stage, leading to manual overrides and mistrust.

## 3. Lifecycle & Milestones

ChainPay v1 runs entirely off the **context ledger**, using existing shipment, IoT, and risk artifacts to drive milestone-based payouts. The core lifecycle for a shipment in the pilot corridor is:

1. `context_created`
   - Shipment is onboarded into the context ledger (from ChainFreight / TMS).
   - Baseline payout schedule (20/70/10) and initial risk band are attached.

2. `pickup_confirmed`
   - Proof that the load was actually picked up (event from ChainFreight + IoT door/open, GPS at origin, timestamp alignment).
   - Unlocks the **first payout tranche** based on current risk band.

3. `mid_transit_verified`
   - Derived virtual milestone, not a single raw event:
     - Reefer temperature within agreed band over a rolling window.
     - GPS route adherence (no large unexplained detours).
     - Sufficient IoT uptime and `signal_confidence` above threshold.
   - Confirms that the lane is behaving as expected mid-journey and unlocks the **second payout tranche**.

4. `delivery_confirmed`
   - Delivery is confirmed via POD / scanned document / facility event + GPS at destination.
   - No major incident flags in IoT or exceptions.
   - Unlocks the **final 10% tranche**, subject to any holds or reversals.

5. `settlement_released`
   - Context ledger records that all preconditions for final settlement are met (including risk and IoT checks).
   - Triggers computation of net payout for the carrier and (optionally) an XRPL settlement transaction.

6. `reversal_detected`
   - Post-settlement reversal or dispute (chargeback, damage claim, fraud, compliance issue).
   - Logged against the same context ledger entry with reason codes and references.
   - Used to adjust subsequent risk bands and potentially claw back or offset future payouts.

### 3.1 Payout Schedule Table (20/70/10)

| Ledger Event           | Release % (Baseline) | Unlock Conditions                                                                 | Notes                                                                                  |
|------------------------|----------------------|------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| `pickup_confirmed`     | 20%                  | Shipment context exists; pickup event confirmed; basic IoT presence at origin     | Early liquidity for carrier once load is verifiably in motion                         |
| `mid_transit_verified` | 70%                  | IoT health OK; temp within band; route adherence; no major alerts                 | Bulk of payment; risk-aware adjustments applied based on ChainIQ risk band and IoT    |
| `delivery_confirmed`   | 10%                  | POD / delivery event; GPS at destination; no outstanding critical exceptions       | Final true-up; can be held or reduced on high/critical risk or dispute                |
| `settlement_released`  | 0% (accounting only) | All prior tranches accounted; netted per carrier; ready for bank/XRPL settlement   | Represents completion of off-chain accounting step                                    |
| `reversal_detected`    | N/A                  | Post-settlement dispute, clawback, fraud, or compliance flag                       | Adjusts future risk and, where possible, is offset against future payouts             |

Percentages above are **baseline** for LOW risk in the pilot; dynamic rules below adjust them per risk band and IoT health but never exceed 20/70/10 in total.

## 4. Risk-Aware Payout Matrix

ChainPay v1 uses ChainIQ risk bands and IoT health to modulate how much of each tranche is actually released at each milestone.

### 4.1 Risk Bands & Tranches

| Risk Band  | Pickup (20% baseline)           | Transit (70% baseline)                            | Final 10%                      | Overrides / Notes                                                                  |
|------------|---------------------------------|---------------------------------------------------|--------------------------------|------------------------------------------------------------------------------------|
| **LOW**    | Full 20%                        | Full 70% on `mid_transit_verified`                | Full 10% on `delivery_confirmed` | Default behavior for healthy corridor; no extra holds                             |
| **MEDIUM** | Full 20%                        | 50–70% depending on IoT health and recent history | Remaining to final 10% or held | Some portion of the 70% may slide to final 10% or remain held for manual review   |
| **HIGH**   | 10–20% (reduced)                | 30–50% with stricter IoT/risk checks              | Remainder held or manually released | Designed to limit exposure; larger share contingent on good mid-transit evidence |
| **CRITICAL** | 0–10% (only hard-proven work) | 0–30% max; large part held until post-delivery review | Often 0% until manual decision | Requires explicit governance approval to release anything beyond minimal coverage |

### 4.2 Dynamic Rules

- **IoT degraded > 30 minutes → downgrade 1 risk band for this leg**
  - Example: LOW → MEDIUM, MEDIUM → HIGH, etc., for payout computation.
  - Applied if temperature or GPS streams are present but unstable/intermittent for > 30 minutes.

- **IoT offline + no GPS > 60 minutes → freeze 70% tranche**
  - Regardless of initial risk band, the mid-transit 70% tranche is frozen until:
    - Additional proof is provided (e.g., documents, facility attestations), or
    - An operator manually overrides after reviewing risk and IoT gaps.

- **Risk band can improve, but never exceed baseline percentages**
  - As more positive evidence accrues (consistent IoT, good historical performance, no disputes), a shipment can move from, say, MEDIUM → LOW for subsequent milestones.
  - However, **payouts can never exceed the 20/70/10 baseline**; improvements only unfreeze or reallocate held amounts within that cap.

- **Manual overrides MUST be written to the context ledger**
  - All non-automatic decisions (e.g., releasing 70% despite degraded IoT, or withholding final 10% on a LOW risk move) are recorded via a `record_decision`-style action:
    - Includes operator ID, timestamp, reason codes, associated evidence (IoT snapshot, docs, ChainIQ trace).
    - Enables post-hoc analysis and training data for future ML models.

## 5. IoT & ChainIQ Inputs

ChainPay v1 consumes the following signals to drive payouts:

- **IoT Signals (via ChainSense / telemetry feeds):**
  - Reefer temperature time series and band checks.
  - Door open/close events at origin, border, and destination.
  - GPS route and dwell, including geofence stays and unexpected detours.
  - Derived `signal_confidence` or IoT health score summarizing uptime, latency, and data consistency.

- **ChainIQ Risk Outputs:**
  - Risk score in [0,1] or [0,100] (normalized internally).
  - Discrete risk band: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
  - Reasons / factors (e.g., lane volatility, carrier dispute history, prior reversals).

These inputs are used to:

- Decide when `mid_transit_verified` is satisfied.
- Adjust risk band over time, including downgrades on degraded/offline IoT or repeat issues.
- Decide when to **freeze**, **unfreeze**, or **reallocate** payout tranches.
- Populate audit records so that Maggie can trace every settlement decision back to context and risk evidence.

## 6. Pilot Corridor Definition

For v1, ChainPay is intentionally constrained to a **single, well-defined pilot corridor**:

- **Corridor:** US→MX cross-border reefer lane
  - Origin hub: **Laredo, TX**.
  - Destination hub: **Monterrey, MX**.
  - Primary commodity: perishable produce with strict temperature requirements.

- **Volume:**
  - Target of **25–40 loads per month** in the pilot phase.

- **Actors:**
  - 1 digital freight broker as the coordinating entity.
  - 2 anchor carriers with strong operational history and willingness to integrate IoT feeds.

The goal is to validate ChainPay v1 under real operational constraints before expanding corridors, commodities, and the set of supported carriers.

## 7. Success Metrics

ChainPay v1 is considered successful in the pilot when the following metrics are met or exceeded:

- **Days-to-pay reduction:**
  - Baseline: ~**21 days** from delivery to carrier payment.
  - Target: **≤3 days** effective days-to-pay via milestone releases.

- **Auto-settlement rate:**
  - **≥90%** of shipments are fully auto-settled without manual payout overrides after `mid_transit_verified`.

- **Reversal / override rate:**
  - **≤5%** of shipments experience reversals or settlement overrides after mid-transit, indicating strong upfront risk and IoT gating.

- **Ledger↔XRPL reconciliation timeliness:**
  - **100%** of ledger settlements that trigger on-chain payouts are reconciled (on-chain tx hash + status confirmed) within **15 minutes**.

- **IoT uptime and correlation:**
  - **≥98%** IoT uptime on the corridor during active legs.
  - Documented correlation that IoT outages and degraded `signal_confidence` directly map to risk holds and frozen tranches (no silent failures).

These metrics give Cody, Maggie, Sonny, and Dan a shared target definition of “ChainPay v1 is working” and serve as guardrails for future iterations and corridors.

## 8. CB-USDx in the Product Story

### 8.1 What CB-USDx Is (and Isn’t)

- CB-USDx is ChainBridge’s internal settlement token on XRPL: a USD-denominated IOU that represents cash already escrowed for a shipment.
- It is **not** a speculative crypto asset. Carriers never hold XRP exposure; they receive a USD IOU that finance redeems back to fiat via the same Treasury team they already trust for ACH/wire payouts.
- Think of CB-USDx as an auditable receipt for “ChainPay approved this payout and funds are on the way,” not a bank deposit.

### 8.2 Why XRPL Shows Up

- XRPL gives the pilot corridor low-fee, near-instant settlement and mature IOU tooling (trustlines, freeze controls) without forcing brokers to re-platform their ERPs.
- Carriers mostly experience it as: “You were paid minutes after delivery instead of weeks later,” with an optional XRPL transaction hash they can paste into ChainBoard to confirm status.
- XRPL remains an **implementation detail**; brokers interact with ChainPay APIs/UI, and the XRPL write path simply provides a cryptographic receipt that finance can reconcile.

### 8.3 Customer-Facing Guarantees

- **Payout time:** ChainPay commits to ≤3 business days (and typically same day) from `delivery_confirmed`, subject to risk holds documented in the OC.
- **Auditability:** Every payout has three artifacts: (1) context ledger record, (2) ChainPay settlement record accessible via API/UI, (3) XRPL transaction hash. Disputes reference the same IDs end-to-end.
- **Redemption:** If a carrier prefers fiat, ChainBridge redeems CB-USDx back to USD via its treasury account. No FX spread or extra fee is applied beyond the agreed ChainPay pricing.

### 8.4 How Risk & CB-USDx Interact

- ChainIQ risk bands still govern payout timing. HIGH/CRITICAL lanes keep more funds in the final tranche (e.g., 30%) and may delay XRPL settlement until manual review clears.
- IoT outages or degraded confidence automatically reduce how much CB-USDx is sent during the mid-transit tranche; the withheld portion appears in ChainBoard as “held balance,” not a vanished payment.
- Because every XRPL payment memo contains the highest risk band touched in the batch, Maggie can later correlate on-chain behavior with model predictions, and brokers see that risk-driven holds are intentional, not arbitrary.

## 9. Risk-Aware Payout Matrix & Corridors

- ChainPay V1 uses a **config-driven payout matrix** keyed by `corridor_id` and `risk_score → tier` mapping. The canonical specification lives in `docs/product/CHAINPAY_RISK_PAYOUT_MATRIX_V1.md`.
- Tiers (LOW, MEDIUM, HIGH, CRITICAL) map to ChainIQ `risk_score` bands and define payout splits and claim windows. Example (USD→MXN pilot): LOW 20/70/10 with 3d claim; MEDIUM 15/65/20 with 5d; HIGH 10/60/30 with 7d + manual review flag; CRITICAL 0/0/100 frozen.
- Cody loads the matrix as JSON/YAML config (corridor-aware) and annotates each `settlement_id` with the selected tier, payout plan, and claim window before initiating XRPL settlements.
- Sonny can display the tier and schedule in the OC (e.g., “Tier: HIGH — 10/60/30, claim 7d; manual review”).
- Maggie can use `tier` and `corridor_id` as modeling features and track outcomes to recalibrate thresholds later.

## 10. Pilot Corridor: USD→MXN (V1)

- ChainPay V1 targets the USD→MXN cross-border freight lane (Laredo → Monterrey) as the initial pilot. The full corridor and pricing blueprint is in `docs/product/CHAINPAY_USD_MXN_PILOT_V1.md` (policy `CHAINPAY_V1_USD_MXN_P0`).
- Pricing, risk-sharing, SLAs, and 30/60/90 KPIs are defined there and align with the configurable risk/payout matrix (`docs/product/CHAINPAY_RISK_PAYOUT_MATRIX_V1.md`).
- Analytics alignment: outcomes and KPIs should be tracked per Maggie’s risk analytics spec (`docs/ai/CHAINPAY_RISK_ANALYTICS_V1.md`, if present) to drive “scale / tweak / pause” decisions after the pilot window.
- CB-USDx rail rollout modes, eligibility, and phase gating for the USD→MXN pilot are defined in `docs/product/CHAINPAY_CB_USDX_ROLLOUT_V1.md`; default production stance remains `MODE_INTERNAL_ONLY` (InternalLedgerRail) until promoted.
