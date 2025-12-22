# ChainPay Pricing Model (Pilot Edition)

## 1. Pricing Goals

1. **Value proof fast:** Tie pricing to the quantifiable benefit (days-to-pay drops from 21 to <=3 days, fewer disputes) so mid-market brokers can justify spend within one pilot lane.
2. **Simple to sell:** Avoid opaque basis-point math or FX gimmicks; brokers should understand the invoice after a 5 minute conversation.
3. **Align incentives:** ChainPay earns more when brokers push more loads through governed payouts while keeping carriers happy. Pricing should not feel like a tax on compliance.
4. **Scalable:** Start lightweight for 25-40 monthly loads, but make it easy to expand to multiple corridors without renegotiating the entire model.

## 2. Pricing Options Considered

| Option | Description | Pros | Cons |
| --- | --- | --- | --- |
| A. Per-load SaaS | Flat fee per processed load (e.g., $20/load). | Predictable for finance, easy to explain. | Does not scale with shipment value; high-value loads look underpriced relative to risk exposure. |
| B. Settlement take rate | Basis-point fee on each dollar settled (e.g., 15 bp = 0.15%). | Aligns with value (bigger loads pay more). | Brokers distrust pure % fees; looks like hidden FX markup. |
| C. Hybrid (per-load + bps) | Smaller per-load fee plus low take rate (e.g., $15 + 10 bp). | Blends predictability with value alignment; easy to discount one component. | Slightly more complex invoice, needs tooling to break down components. |
| D. Tiered SaaS | Monthly subscription with included load volume tiers. | Mirrors existing TMS pricing; easy budgeting. | Requires long-term commitment up front; overspend if volume fluctuates. |

## 3. Recommended Pilot Model

**Hybrid:** `$15 per load + 10 bp (0.10%)` on the total amount actually released during the settlement window, with a `$1,500` monthly minimum during the pilot.

Rationale:
- Brokers see line-item `$15/load` as comparable to accessorial charges, not a punitive fee.
- 10 bp on settled value is small (=$100 on a $100k month) but scales with volume/value.
- Monthly minimum ensures ChainBridge covers treasury ops, XRPL costs, and support even if volume dips below forecast.
- Carriers pay only XRPL network fees (fractions of a cent); all ChainPay fees are billed to the broker as part of the monthly invoice.

## 4. Example Economics (Pilot Corridor)

Assumptions:
- 30 loads/month average.
- Average payout per load: $18,000 (reflecting reefer freight with fuel surcharge).
- 92% of tranches auto-release without manual intervention.

Monthly revenue model:
- Per-load: `30 loads * $15 = $450`
- Take rate: `30 loads * $18,000 = $540,000` settled -> `0.10%` => `$540`
- Monthly minimum: `$1,500` floor applies, so invoice = `max($450 + $540, $1,500)` = `$1,500`
- Break-even volume for floor: ~`$1.05M` settled value or `70 loads` at assumptions above.

As corridor scales to 60 loads/month:
- Per-load: `$900`
- Take rate: `$1,080`
- Invoice: `$1,980`

Finance reporting view:
- Each invoice split into `SaaS_Fee` (per-load) and `Variable_Settlement_Fee` (bp) for analytics.
- Dashboards show revenue per corridor, per carrier, and per risk band to correlate price vs. value delivered.

## 5. Billing Mechanics

1. ChainPay ledger emits monthly summary per broker containing:
   - Total loads processed.
   - Total amount settled.
   - Count of manual overrides (used to justify discounts or surcharges).
2. Finance system generates invoice within 3 business days after month close.
3. Payment options: ACH preferred; XRPL or card payments optional later.
4. Late payment policy: 1.5% monthly finance charge if unpaid after 30 days (matches ChainBridge standard MSAs).

## 6. Future Pricing Levers

- **Enterprise tier:** Flat annual subscription covering multiple corridors plus negotiated variable fee caps.
- **Carrier-funded fast-pay:** Optional `QuickPay` mode where carriers opt to pay a 25 bp fee for instant payout versus standard T+1 netting.
- **Token incentives (v2+):** Discount variable fees when settlements occur entirely on XRPL or when carriers hold CB-USDx above a threshold (subject to compliance review).
- **FX spread capture:** If ChainBridge later provides MXN liquidity, add transparent FX markup (e.g., +25 bps) vs. broker arranging their own conversion.

## 7. Open Items & Assumptions

- Broker contract still needs a formal MSA addendum outlining fee schedule and minimum volume commitment. Pax to coordinate with legal.
- Need UI surfaces in ChainBoard for brokers to see their monthly charges in near real time (Sonny backlog).
- Finance tooling must categorize per-load vs. variable fees so Benson can reconcile against settlement volume KPIs.
