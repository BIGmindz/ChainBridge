# ChainPay USD→MXN Pilot Blueprint (V1)

## 1. Overview
This blueprint defines the pilot policy for the USD→MXN corridor (`corridor_id: USD_MXN`) using payout policy version `CHAINPAY_V1_USD_MXN_P0`. It specifies corridor scope, actors, risk tiers, payout schedule, claim windows, manual review rules, and analytics alignment so Cody (backend), Maggie (analytics), and Sonny (UI) can implement without guesswork.

## 2. Corridor & Actors
- **Corridor ID:** `USD_MXN`
- **Lane type:** US → Mexico cross-border, over-the-road full truckload (reefer focus), Laredo, TX → Monterrey, MX
- **Typical ticket size:** USD 5k–25k per shipment
- **Actors & value:**
  - **Shipper:** Transparency on payout rules, clear dispute controls
  - **Broker/3PL:** Reduced credit exposure, SLA-backed payouts, configurable holds
  - **Carrier/Driver:** Faster days-to-cash with predictable milestones
  - **ChainPay / ChainBridge:** Governance of risk → payout mapping, ledger + XRPL receipt as proof

## 3. Risk Tier Definitions (USD→MXN)
| Tier | Risk Score Band (illustrative) | Typical Profile | Manual Review Required? |
| --- | --- | --- | --- |
| LOW | 0.00 – 0.30 | Repeat shipper, clean history | No (auto payout unless flagged) |
| MEDIUM | 0.30 – 0.60 | Some history, minor past claims | Only if claim/dispute is filed |
| HIGH | 0.60 – 0.85 | Limited history, moderate volatility | Manual review for claim portion |
| CRITICAL | 0.85 – 1.00 | New/flagged shipper or hot-spot lane | Manual review for all claim payouts |

## 4. Payout Policy & Milestones (CHAINPAY_V1_USD_MXN_P0)
Global milestones: `PICKUP_CONFIRMED`, `IN_TRANSIT` (optional), `DELIVERED_CONFIRMED`, `CLAIM_WINDOW_CLOSED`.

| Tier | Pickup % | Delivery % | Claim-window % | Notes |
| --- | --- | --- | --- | --- |
| LOW | 20% | 70% | 10% | Max speed, low friction |
| MEDIUM | 15% | 65% | 20% | Slightly more back-loaded |
| HIGH | 10% | 60% | 30% | Heavier reserve for claims |
| CRITICAL | 5% | 55% | 40% | Strong back-load + reviews |

Mapping to ledger fields (Maggie spec):
- `cb_usd_reserved_initial` = total allocation at context creation.
- `cb_usd_released_pickup` maps to pickup tranche; `cb_usd_released_delivery` to delivery tranche; `cb_usd_released_claim_window` to final tranche.
- `cb_usd_loss_realized` and `cb_usd_reserved_unused` surface during/after claim window close.

## 5. Claim Windows & Manual Review
Standard claim window anchor: 7 days after `DELIVERED_CONFIRMED`, with tier-specific adjustments.

| Tier | Claim Window (days) | Manual Review Rule |
| --- | --- | --- |
| LOW | 7 | Only if claim filed |
| MEDIUM | 7 | Only if claim filed |
| HIGH | 10 | Claims > 20% of `cb_usd_total` require review |
| CRITICAL | 14 | All claims require manual review |

Operational rules:
- SLA: claims reviewed within 24–48h; CRITICAL must be queued immediately.
- Holds apply to the claim-window tranche; pickup/delivery tranches can proceed per table unless an active dispute freezes them.

## 6. Policy Versioning & Analytics Alignment
- **Policy ID:** `CHAINPAY_V1_USD_MXN_P0` (use exactly in configs and logs).
- **Corridor ID:** `USD_MXN`
- **Analytics version:** `v1` (per `docs/ai/CHAINPAY_RISK_ANALYTICS_V1.md`).

For Cody:
- Set `payout_policy_version="CHAINPAY_V1_USD_MXN_P0"` on `SettlementOutcome` for this corridor.
- Load payout/claim rules from this doc or the matrix (`docs/product/CHAINPAY_RISK_PAYOUT_MATRIX_V1.md`).

For Maggie:
- Slice KPIs by `(corridor_id="USD_MXN", payout_policy_version="CHAINPAY_V1_USD_MXN_P0", analytics_version="v1")`.

For Dan:
- Expose metrics snapshots keyed by `(corridor, payout_policy_version)` so Sonny can label UI correctly.

Naming contract for future policies: `CHAINPAY_<version>_<CORRIDOR>_<policy_slug>` (e.g., `CHAINPAY_V1_USD_MXN_P1` for a revised matrix).

## 7. Pilot KPIs & Success Criteria
- **Days to first cash:** median ≤ 2 days; p95 ≤ 5 days.
- **Reserve utilization:** healthy band 0.3–1.0 overall; monitor by tier.
- **Loss rate:** within expected tier ranges; no unexpected spikes in HIGH/CRITICAL.
- **SLA:** claim review breach rate < 10%.
- **Validation:** If thresholds hold across 500 shipments, pilot is commercially validated.

## 8. Future Evolutions (V2+)
- Dynamic payout percentages based on real-time `risk_score`, not just static tiers.
- Tier promotions/demotions driven by historical behavior.
- Corridor expansion (e.g., `USD_CAD`, `USD_EUR`) reusing the same policy/versioning pattern.
- Optional fast-pay toggle with fee-based acceleration (not in V1 scope).
