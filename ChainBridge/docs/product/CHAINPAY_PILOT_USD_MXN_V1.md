# ChainPay USD→MXN Pilot Blueprint (V1)

## 1. Pilot Corridor Overview
- **Scope:** Cross-border US border-state warehouses → Monterrey MX distribution centers (reefer TL/FTL focus; dry allowed as secondary).
- **Actors:**
  - **PilotBroker:** Integrates ChainPay, funds CB-USDx, owns customer relationship.
  - **PilotCarrier:** Paid via CB-USDx-backed settlement (redeemed to fiat by treasury); may be custodial or BYO XRPL wallet.
  - **PilotShipper:** Invoiced via normal ERP; settlement orchestrated through ChainPay.
- **Shipment profile:** Ticket size $2k–$10k (median ~$6k); 25–40 loads/month initially; expected risk mix: ~60% LOW, 30% MEDIUM, 10% HIGH; CRITICAL rare.
- **Corridor ID:** `USD_MXN` (aligns with risk matrix config).

## 2. ChainPay Pricing Model (Pilot)
- **Base transaction fee:** 20 bps (0.20%) on CB-USDx notional per settlement batch (billed to PilotBroker).
- **Risk surcharge:** +10 bps on HIGH-tier settlements (applied to notional released in that batch). CRITICAL is manual/no auto-settlement (no surcharge until approved).
- **FX handling:** V1 assumes broker handles FX off-platform; ChainPay charges no FX spread. (If treasury provides FX later, add transparent FX bps.)
- **Carrier fast-pay discounting:** Optional: carriers accept implicit 5 bps discount in exchange for faster days-to-cash (can be trialed lanes; off by default).
- **Illustrative economics:** $50M annual corridor volume × 0.20% ≈ $100k base; if 10% volume is HIGH, add ~$5k via surcharge.

## 3. Risk-Sharing Structure (by Tier)
- **LOW:** Standard reserve per matrix (20/70/10, 3d claim). Losses first absorbed by reserve; excess borne by PilotBroker/shipper. ChainPay treasury exposure minimal.
- **MEDIUM:** Reserve increased (15/65/20, 5d). Broker/shipper shoulder over-reserve losses; ChainPay exposure limited to operational error.
- **HIGH:** Conservative payouts (10/60/30, 7d) + manual review on final tranche. Over-reserve losses shared by broker/shipper; ChainPay may collect risk surcharge but does not underwrite losses.
- **CRITICAL:** No auto-release; manual decision sets liability allocation case-by-case. Funds stay frozen until explicit approval.

## 4. Operational SLAs & Experience
- **Days-to-cash targets (from milestone):**
  - LOW: pickup tranche same/next day; delivery tranche within 1 day; claim tranche after 3d.
  - MEDIUM: pickup same/next day; delivery within 1–2 days; claim after 5d.
  - HIGH: pickup within 1–2 days; delivery within 2 days; claim after 7d and manual review.
  - CRITICAL: no automatic payout; manual review required.
- **Support SLAs:**
  - Dispute intake response < 4 business hours; resolution targets LOW/MEDIUM < 72h, HIGH < 96h; CRITICAL requires explicit operator sign-off.
  - Manual review queue (HIGH/CRITICAL finals) processed within 1 business day where possible.
- **Analytics tie-in:** Maggie’s dashboards track days-to-cash, reserve utilization, and loss rates per tier/corridor to validate SLA adherence.

## 5. Pilot KPIs & 30/60/90-Day Plan
- **Risk & loss KPIs:**
  - Loss rate per tier = loss_amount_cb_usd / cb_usd_total_settled (target < 0.25% overall; HIGH < 0.6%; CRITICAL manual only).
  - Reserve utilization: % of claims covered by held reserves (target ≥ 90% of claims covered by reserves for LOW/MEDIUM; ≥ 80% for HIGH).
- **Experience KPIs:**
  - Median days-to-cash: LOW ≤ 2 days; MEDIUM ≤ 3 days; HIGH ≤ 5 days (excluding claim window hold); CRITICAL N/A (manual).
  - On-time delivery rate (from TMS/EDI): target ≥ 95%.
- **Adoption & volume KPIs:**
  - Shipments onboarded: Day 30 target 40–60 loads; Day 60 target 100–150; Day 90 target 200–250.
  - CB-USDx notional processed: Day 30 target $0.2–0.3M; Day 60 target $0.6–0.9M; Day 90 target $1.2–1.5M.
- **30/60/90 cadence:**
  - **0–30 days:** Single broker + 1–2 carriers; validate data flow, payouts, and SLA tracking; tune operational playbooks.
  - **31–60 days:** Increase volume; exercise MEDIUM/HIGH tiers; evaluate surcharge efficacy; adjust claim windows if reserves under/over cover.
  - **61–90 days:** Decide scale/tweak/pause based on KPIs and loss performance; prepare corridor expansion if targets met.

## 6. Implementation Pointers
- **Config hooks:** Use `corridor_id=USD_MXN` in the risk/payout config (see `CHAINPAY_RISK_PAYOUT_MATRIX_V1.md`). Pricing bps can sit in a parallel `pricing` config keyed by corridor.
- **Backend (Cody/Cindy):** Annotate settlements with `tier`, payout plan, claim window, and applied fee/surcharge; expose in `SettlementStatus` for Sonny.
- **ML (Maggie):** Track outcomes and recalibrate tiers/thresholds; include `tier`, `corridor_id`, `claim_window_days`, and `fee_applied_bps` in analytics logs.
- **UI (Sonny):** Show corridor, tier, payout split, claim window, and applied fees/surcharges in the settlement panel.

## 7. Open Items
1) Confirm whether HIGH manual review is always required for the final tranche or only when IoT confidence is degraded.
2) Decide if fast-pay discounting (carrier implicit 5 bps) is enabled in the pilot or kept as an experiment toggle.
3) Clarify whether any regulatory/FX partner constraints impose corridor-wide claim window overrides.
