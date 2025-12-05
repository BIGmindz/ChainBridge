# ChainPay Risk-Tiered Payout Matrix (V1)

## 1) Purpose
This document defines the **risk-aware payout matrix** and **corridor configuration** used by ChainPay V1. Cody can load these values as config (JSON/YAML) and apply them at runtime; Maggie can treat `tier` and `corridor` as modeling features; Sonny can surface the selected tier, payout pattern, and claim window in the UI. The USD→MXN pilot uses policy ID `CHAINPAY_V1_USD_MXN_P0` (see `docs/product/CHAINPAY_USD_MXN_PILOT_V1.md`).

For analytics and calibration guidance, see `docs/ai/CHAINPAY_RISK_ANALYTICS_V1.md`.

## 2) Risk Tiers (numeric bands)
ChainIQ `risk_score` maps to four discrete tiers. Bands are inclusive of the lower bound and exclusive of the upper bound, except `CRITICAL` which includes 1.0.

| Tier | risk_score_min | risk_score_max | Meaning | Operational posture |
| --- | --- | --- | --- | --- |
| LOW | 0.00 | < 0.30 | Very low fraud/ops risk | Standard flow, shortest claim window |
| MEDIUM | 0.30 | < 0.60 | Normal trade risk | Slightly larger reserve and claim window |
| HIGH | 0.60 | < 0.85 | Elevated risk | Larger reserve, manual review flag for final release |
| CRITICAL | 0.85 | ≤ 1.00 | Acute risk | Payouts frozen pending manual approval |

> Note: These bands align with prior risk narratives (HIGH/CRITICAL triggering manual review). If backend tests use different cutoffs, adjust here and note the required test update.

## 3) Payout Matrix (per tier)
Percentages apply to the **total CB-USDx amount allocated for the shipment**. Claim window defines when the final tranche can be released (or remains held) after delivery confirmation.

| Tier | Pickup % | Delivered % | Claim % | Claim Window (days) | Reserve / Manual Rules |
| --- | --- | --- | --- | --- | --- |
| LOW | 20% | 70% | 10% | 7 | Standard; auto-release after window. |
| MEDIUM | 15% | 65% | 20% | 7 | Slightly more reserve; auto-release after window. |
| HIGH | 10% | 60% | 30% | 10 | Review required for claim portion >20% of `cb_usd_total`. |
| CRITICAL | 5% | 55% | 40% | 14 | Manual review required; strong back-load; can freeze if risk worsens. |

Business rationale:
- **LOW:** Optimize carrier cash flow; minimal hold.
- **MEDIUM:** Slightly more in reserve to cover moderate dispute probability.
- **HIGH:** Protect treasury; keep significant reserve and force human confirmation.
- **CRITICAL:** Do not pay without explicit approval; reserve everything.

## 4) Corridor Configuration Schema (JSON shape)
Cody can represent corridor-specific policies with the following shape. `risk_tiers` entries must align with the table above; per-corridor overrides are allowed if needed.

```jsonc
{
  "version": "1.0",
  "corridors": [
    {
      "id": "USD_MXN",
      "description": "US → Mexico cross-border reefer",
      "currency_pair": "USD/MXN",
      "default_risk_tier": "MEDIUM",
      "claim_window_override_days": null,
      "risk_tiers": {
        "LOW": {
          "score_min": 0.0,
          "score_max": 0.30,
          "payout": { "pickup_percent": 0.20, "delivered_percent": 0.70, "claim_percent": 0.10, "claim_window_days": 7 },
          "requires_manual_review": false
        },
        "MEDIUM": {
          "score_min": 0.30,
          "score_max": 0.60,
          "payout": { "pickup_percent": 0.15, "delivered_percent": 0.65, "claim_percent": 0.20, "claim_window_days": 7 },
          "requires_manual_review": false
        },
        "HIGH": {
          "score_min": 0.60,
          "score_max": 0.85,
          "payout": { "pickup_percent": 0.10, "delivered_percent": 0.60, "claim_percent": 0.30, "claim_window_days": 10 },
          "requires_manual_review": true
        },
        "CRITICAL": {
          "score_min": 0.85,
          "score_max": 1.0,
          "payout": { "pickup_percent": 0.05, "delivered_percent": 0.55, "claim_percent": 0.40, "claim_window_days": 14 },
          "requires_manual_review": true,
          "freeze_all_payouts": true
        }
      }
    }
  ]
}
```

### YAML equivalent (for readability)
```yaml
version: "1.0"
corridors:
  - id: USD_MXN
    description: US → Mexico cross-border reefer
    currency_pair: USD/MXN
    default_risk_tier: MEDIUM
    claim_window_override_days: null
    risk_tiers:
      LOW:
        score_min: 0.0
        score_max: 0.30
        payout:
          pickup_percent: 0.20
          delivered_percent: 0.70
          claim_percent: 0.10
          claim_window_days: 7
        requires_manual_review: false
      MEDIUM:
        score_min: 0.30
        score_max: 0.60
        payout:
          pickup_percent: 0.15
          delivered_percent: 0.65
          claim_percent: 0.20
          claim_window_days: 7
        requires_manual_review: false
      HIGH:
        score_min: 0.60
        score_max: 0.85
        payout:
          pickup_percent: 0.10
          delivered_percent: 0.60
          claim_percent: 0.30
          claim_window_days: 10
        requires_manual_review: true
      CRITICAL:
        score_min: 0.85
        score_max: 1.0
        payout:
          pickup_percent: 0.05
          delivered_percent: 0.55
          claim_percent: 0.40
          claim_window_days: 14
        requires_manual_review: true
        freeze_all_payouts: true
```

Notes:
- `claim_window_override_days`: if set, applies to all tiers for that corridor (e.g., special regulatory hold). Otherwise each tier’s own window applies.
- Percent values must sum to 1.0 for each tier.
- `requires_manual_review` allows Cody to route settlements to an approval queue before moving funds on-chain.
- `freeze_all_payouts` is an explicit flag for CRITICAL tiers to stop auto-disbursements.

## 5) Example Corridor: USD_MXN (Pilot)
- **ID:** `USD_MXN`
- **Corridor:** Laredo, TX → Monterrey, MX (reefer)
- **Default tier:** MEDIUM
- **Risk bands:** as defined above (0–0.30 LOW, 0.30–0.60 MEDIUM, 0.60–0.85 HIGH, 0.85–1.0 CRITICAL)
- **Payout pattern:** 20/70/10 (LOW), 15/65/20 (MEDIUM), 10/60/30 (HIGH), 5/55/40 (CRITICAL)
- **Claim windows:** 7d / 7d / 10d / 14d respectively

## 6) Implementation Notes
- **Cody (backend):**
  - Load this schema from a config file (e.g., `chainpay_config/risk_payouts.json`).
  - Given `risk_score` and `corridor_id`, derive `tier` and select the payout pattern + claim window.
  - Annotate `settlement_id` records with `tier`, `payout_plan`, and `claim_window_days`; surface in API responses for Sonny.
  - For `requires_manual_review` tiers, route to an approval queue before triggering XRPL settlement.

- **Maggie (ML):**
  - Use `tier` and `corridor_id` as features for model training/evaluation (e.g., predicting reversals or disputes).
  - Track outcomes by tier to recalibrate band thresholds later.

- **Sonny (UI):**
  - Display the selected tier and payout split in settlement views, e.g., `Tier: HIGH — 10/60/30, claim 10d`.
  - Indicate when a settlement is in `requires_manual_review` or `freeze_all_payouts` state.

## 7) Open Questions & Decisions Needed
1. Should HIGH always require manual approval for the final tranche, or only when IoT confidence is degraded? (Current spec: always requires manual review.)
2. Do we need corridor-specific overrides for claim windows (e.g., refrigerated vs dry goods) beyond the per-tier defaults? (Schema supports it via `claim_window_override_days`.)
3. If corridor expansion introduces local regulatory holds, should we add a `regulatory_hold_days` field separate from the claim window? (Not included yet; add if required.)
