# ChainPay CB-USDx Product Map

## 1. Product Overview

**CB-USDx** is the internal settlement token for ChainPay v1. It solves the "slow cash" problem in logistics by providing a near-instant, auditable settlement rail that runs parallel to traditional banking but settles in minutes, not days.

### The Problem
- **Friction:** Carriers wait 21-45 days for payment.
- **Trust:** Disputes over "check is in the mail" vs. "invoice lost".
- **Reconciliation:** Finance teams struggle to match bank wires to specific loads and risk adjustments.

### The Solution
CB-USDx acts as a **digital receipt of value**. When ChainPay says a load is settled, it issues CB-USDx to the carrier immediately. The carrier can hold it (as proof of funds) or redeem it for fiat.

### Actors
- **Shipper/Broker:** Funds the settlement pool (USD).
- **ChainPay Treasury:** Mints CB-USDx 1:1 against funded USD.
- **Carrier:** Receives CB-USDx upon milestone completion.
- **Factoring Partner (Future):** May buy CB-USDx claims for early liquidity.

---

## 2. Token Definition (CB-USDx)

### Nature
- **Closed-Loop Settlement Token:** Not a speculative crypto asset. It is an accounting tool on the XRPL ledger.
- **Stable Value:** 1 CB-USDx = $1.00 USD.
- **Permissioned:** Only KYC'd carriers and brokers with whitelisted XRPL trustlines can hold or transact CB-USDx.

### Backing
- **1:1 Fiat Backed:** Every unit of CB-USDx in circulation is backed by $1.00 USD held in a segregated ChainBridge treasury account.
- **Audit:** Daily reconciliation ensures On-Chain Supply = Off-Chain Fiat Reserves.

### Access Control
- **Trustlines:** Carriers must explicitly trust the ChainPay Issuer Account.
- **Freeze Authority:** ChainPay retains the right to freeze tokens in cases of confirmed fraud or regulatory mandate (see `CHAINPAY_ONCHAIN_SETTLEMENT.md` for policy).

---

## 3. Lifecycle

1. **Minting (Inbound Liquidity):**
   - Broker wires $100k to ChainPay Treasury.
   - Treasury mints 100k CB-USDx to the `CB_OPS` hot wallet.

2. **Allocation (Escrow/Lock):**
   - A shipment is booked (`context_created`).
   - ChainPay "locks" the estimated payout amount in the internal ledger (off-chain).
   - *Note: In v1, we do not lock funds on-chain per shipment to save fees. We rely on the `CB_OPS` balance covering the daily float.*

3. **Release (Settlement):**
   - Milestones are met (`pickup`, `delivery`).
   - Risk checks pass.
   - CB-USDx is transferred from `CB_OPS` to `Carrier_Wallet`.

4. **Redemption (Outbound Liquidity):**
   - Carrier requests fiat withdrawal.
   - ChainPay burns the CB-USDx from the carrier's wallet.
   - Treasury wires USD to the carrier's bank account.

---

## 4. Event → Action Matrix

| Event | Condition | On-Chain Action (XRPL) | CB-USDx Movement | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Shipment_Picked_Up** | `risk_score` ≤ Low/Med | None (Off-chain accrual) | None | 20% accrued in ledger. |
| **Mid_Transit_Verified** | `risk_score` ≤ Low/Med, IoT OK | None (Off-chain accrual) | None | 70% accrued in ledger. |
| **Delivery_Confirmed** | POD verified, No Claims | None (Off-chain accrual) | None | Final 10% accrued. |
| **Settlement_Released** | End-of-day Batch | **Payment Transaction** | `CB_OPS` → `Carrier` | Net total of all accrued milestones sent in one tx. |
| **Claim_Open** | Dispute active | **None** | Funds stay in `CB_OPS` | Payout withheld until resolved. |
| **Reversal_Detected** | Fraud/Error confirmed | **Clawback (if enabled)** or Offset | `Carrier` → `CB_OPS` | Future payouts reduced to cover debt. |

*Note: v1 uses "Flow A - Daily Net Payout" to minimize transaction fees. Real-time per-event settlement is available for premium lanes.*

---

## 5. Risk-Adjusted Payout Patterns

ChainIQ `risk_score` directly impacts **when** CB-USDx moves, protecting the settlement pool.

### Low Risk (Score 0-34)
- **Standard Schedule:** 20/70/10.
- **Settlement:** Immediate inclusion in the next daily batch.

### Medium Risk (Score 35-64)
- **Modified Schedule:** 15/65/20 (more weight on delivery).
- **Settlement:** Standard daily batch, but flagged for post-audit.

### High Risk (Score 65-79)
- **Conservative Schedule:** 10/60/30.
- **Settlement:** **Manual Review Required.** Funds do not move on-chain until a human operator approves the batch in the OC.

### Critical Risk (Score 80+)
- **Frozen:** 0/0/0.
- **Settlement:** No payout. Investigation triggered.

---

## 6. Monetization (How this makes money)

1. **SaaS Fee:** Broker pays per-load fee for the ChainPay platform.
2. **Float:** ChainBridge earns interest on the fiat float held in the treasury (standard fintech model).
3. **Premium Settlement:** Carriers can pay a small bps fee (e.g., 0.5%) for **Instant Real-Time Settlement** (Flow B) instead of Daily Netting (Flow A).
