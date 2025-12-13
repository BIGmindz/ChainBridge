# ChainPay v1 On-Chain Settlement Architecture

## 1. Overview

ChainPay v1 separates **business logic and accounting (off-chain)** from **final value transfer (on-chain)**. The context ledger remains the canonical system of record for shipments, risk decisions, and payout schedules, while XRPL acts as a **final settlement rail** for netted payouts. CB-USDx rail rollout modes and eligibility are documented in `docs/product/CHAINPAY_CB_USDX_ROLLOUT_V1.md`; production default is `MODE_INTERNAL_ONLY` with InternalLedgerRail until phased promotion.

In this phase, we explicitly **do not** push full payout and risk logic on-chain. Instead:

- All milestone accounting, risk adjustments, and payout schedule updates occur in the off-chain context ledger.
- At the end of a settlement window (e.g., daily per carrier), ChainPay aggregates net payouts and issues a single XRPL payment per carrier using a corridor IOU token (`CB-USDx`).
- The XRPL transaction hash and status are written back to the ledger so that the entire decision chain (risk → payout → settlement) remains auditable.

This design keeps ChainPay v1 fast and flexible while laying a clear path to future on-chain enhancements.

## 2. Off-Chain Components

The off-chain side consists of four primary components:

- **ContextLedger (DB + service):**
  - Stores shipment context, ledger events, payout schedules, risk snapshots, and settlement records.
  - Exposes operations like `record_event`, `record_decision`, `compute_payout_schedule`, and `mark_settlement_released`.

- **ContextLedgerRiskModel (Maggie):**
  - Consumes shipment features, historical performance, and external risk signals (e.g., ChainIQ ML outputs).
  - Produces risk scores, bands, and reasons that are attached to context ledger entries at key milestones.

- **ChainPay Scheduler/Settlement Service (Cody):**
  - Listens to ledger events and risk updates.
  - Maintains the per-shipment payout schedule (20/70/10 baseline with risk-aware adjustments).
  - Aggregates per-carrier net payouts at the end of a window and initiates on-chain settlements.

- **ChainSense IoT Health Feed:**
  - Normalizes IoT telemetry (temperature, door events, GPS, uptime).
  - Produces `signal_confidence` and health summaries that feed into risk and payout decisions.

### 2.1 High-Level Flow (Text Diagram)

"**Events → Ledger entries → Risk snapshots → Payout schedule → Settlement task → XRPL call**"

1. Operational events (pickup, IoT updates, delivery, disputes) arrive.
2. ContextLedger writes canonical entries with references to shipments, tokens, and risk snapshots.
3. ContextLedgerRiskModel and ChainIQ enrich entries with risk scores, bands, and explanations.
4. ChainPay scheduler updates payout schedules and decides when tranches can be released.
5. When a settlement window closes (e.g., end of day), a settlement task is generated per carrier.
6. Settlement service calls the XRPL adapter to issue an on-chain payment; the resulting tx hash is written back to the ledger.

## 3. XRPL Model (v1)

### 3.1 Corridor Token: `CB-USDx`

- **Asset:** `CB-USDx` is an IOU token on XRPL representing off-chain USD held in reserve.
- **Backing:** 1:1 backed by USD in a designated treasury account.
- **Purpose:** Provide a corridor-specific settlement asset for USD→MXN flows in the pilot.

### 3.2 Net Daily Payouts (Per Carrier)

In v1, **we do not perform one XRPL transaction per shipment**. Instead:

- All per-shipment payouts and adjustments (20/70/10 tranches, holds, reversals) are tracked entirely in the context ledger.
- At a configurable cadence (e.g., daily), ChainPay computes **net payable amounts per carrier**:
  - Sum of all released tranches minus any offsets (reversals, penalties, chargebacks) for that period.
- For each carrier with a positive net balance, ChainPay issues **one XRPL payment** in `CB-USDx`.

### 3.3 XRPL Settlement Writes Back to Ledger

For each XRPL settlement per carrier:

1. ChainPay calls the XRPL adapter with:
   - `settlement_id`
   - `carrier_wallet` (XRPL address)
   - `amount` (net CB-USDx to transfer)
   - `asset` (always `CB-USDx` in v1)
2. XRPL returns:
   - `tx_hash`
   - On-ledger timestamp (or confirmed ledger index / close time).
3. ContextLedger updates the corresponding `settlement_released` entry with:
   - `tx_hash`
   - `onchain_status = CONFIRMED | SUBMITTED | FAILED`
   - XRPL timestamp or ledger index.

This ensures that off-chain and on-chain states remain tightly coupled without forcing business logic into XRPL smart contracts.

## 4. CB-USDx Token Specification (XRPL)

### 4.1 Issuer & Wallet Model

- **`CB_ISSUER` (cold issuer account):** Holds the master supply of CB-USDx, configured with `RequireAuth` so only allowlisted trustlines can hold the IOU. Multi-sig custody (2-of-3) with hardware-backed keys; used only for mint/burn, trustline authorization, and emergency flags.
- **`CB_OPS` (operational hot wallet):** Holds working inventory and submits settlement payments. Signs XRPL `Payment` transactions triggered by ChainPay’s settlement service; regular keys rotated monthly.
- **Optional buffer (`CB_TREASURY`):** Intermediate wallet that receives newly issued CB-USDx from `CB_ISSUER` before topping up `CB_OPS`, reducing blast radius if a hot key is compromised.
- **Carrier wallets:** Either carrier-owned XRPL addresses or custodial wallets mapped to `carrier_id`. Every carrier must KYC off-chain before receiving authorization from `CB_ISSUER`.

### 4.2 Backing & Reserves

- CB-USDx is a USD IOU fully backed by fiat reserves held in a segregated commercial account.
- Policy: **CB-USDx total supply ≤ USD reserves at all times**; no fractional reserve or rehypothecation.
- Treasury ops perform daily reconciliation between XRPL supply (via `account_lines`) and bank balances; discrepancies trigger an automated alert to Pax + finance.

### 4.3 Trustlines & Limits

- Carriers establish an XRPL trustline to `CB_ISSUER` with a limit sized to roughly **2× their average monthly payout** (default pilot value: USD 50k).
- ChainPay may increase or decrease trustline limits based on ChainIQ risk bands, dispute history, or contractual caps; adjustments are logged in the context ledger with operator + reason.
- Trustline authorization is revoked (limit set to zero) when a carrier exits the program or falls out of compliance; any remaining balance must be redeemed before revocation completes.

### 4.4 Freeze & Clawback Policy

- XRPL global freeze remains **disabled by default**. It may only be toggled on if there is confirmed fraud, sanctions exposure, or a compromised issuer/treasury key; every action must be mirrored in the governance log with approvals from Pax, finance, and Sam.
- Per-trustline freeze is a last-resort control when a specific carrier wallet is compromised. Issuer freezes the trustline, redeems funds back to treasury, and documents the action in the context ledger.
- Clawbacks (negative payments) are only performed to correct erroneous or fraudulent credits and must reference the originating `settlement_id` so the ledger shows the full audit chain.

### 4.5 Ledger ↔ XRPL Field Mapping

| Context Ledger Field | XRPL Object / Field | Notes |
| --- | --- | --- |
| `settlement_id` | `Memos[].MemoData` | Hex-encoded JSON memo, e.g., `{ "sid": "SET-2025-12-001" }`. |
| `carrier_wallet` | `Destination` | XRPL classic address receiving the IOU. |
| `amount` | `Amount` | Issued currency object `{ currency: "CB-USDx", value: "...", issuer: "CB_ISSUER" }`. |
| `risk_band` | `Memos[].MemoData` | Included alongside settlement_id so on-chain observers can see max risk level involved in the batch. |
| `settlement_batch_id` | `Memos[].MemoData` or `DestinationTag` | Optional field for grouping multiple settlements in a daily net batch. |

### 4.6 IOU vs. Bank Deposit Disclaimer

- Carriers hold a **tokenized IOU**, not an insured bank deposit. Value is redeemable via ChainBridge treasury operations pursuant to the pilot agreement.
- ChainPay remains a **payment rail and workflow layer**; it is not a bank and does not promise interest or custody services beyond settlement delivery.

## 5. Settlement Flows on XRPL (v1)

> Payout amounts at each milestone are **not hard-coded**; they are derived from the risk/corridor config defined in `docs/product/CHAINPAY_RISK_PAYOUT_MATRIX_V1.md` (risk_score → tier → payout split + claim window). ChainPay annotates each settlement task with the selected tier and percentages before sending any XRPL payment.

### 5.1 Flow A – Daily Net Payout (Recommended)

1. **Milestones & risk logic stay off-chain.** Context ledger tracks every tranche release, hold, and reversal per shipment.
2. **End-of-day aggregation.** For each carrier, ChainPay sums all released amounts and subtracts holds/reversals to compute a net balance.
3. **If net > 0, submit one XRPL payment:**
   - `Account`: `CB_OPS`
   - `Destination`: carrier wallet on XRPL
   - `Amount`: CB-USDx IOU equal to the net total
   - `Memos`: hex-encoded JSON
     ```jsonc
     {
       "type": "chainpay_settlement",
       "settlement_batch_id": "SET-BATCH-2025-12-04-A",
       "carrier_id": "CARR-7781",
       "risk_band_max": "MEDIUM",
       "load_count": 14
     }
     ```
4. **Write-back:** Store `tx_hash`, memo JSON, and ledger timestamp on every `settlement_id` folded into the batch so `GET /chainpay/settlements/{settlement_id}` surfaces the on-chain receipt.
5. **Reconcile:** Dashboards confirm that the batch payment amount equals the sum of included settlements; discrepancies trigger an alert before the next window closes.

Flow A is the default because it minimizes on-chain noise and XRPL fees while still giving carriers predictable end-of-day cash flow.

### 5.2 Flow B – Immediate Single-Load Payout (Optional)

1. Triggered right after `settlement_released` for a specific shipment (e.g., high-value or VIP lanes).
2. ChainPay submits an XRPL payment per settlement rather than batching.
3. Memo payload includes the specific `settlement_id`, `shipper_id`, `risk_band`, and `load_value` so auditors can tie the payment to a single job without cross-referencing batch data.
4. Recommended only when:
   - The lane demands near-real-time visibility (e.g., insurance trials).
   - Payment amounts justify the extra XRPL fees and operational overhead.
5. Trade-offs: higher fee spend, more XRPL transactions to monitor, but faster per-load acknowledgement when a pilot customer insists on immediate payout.

## 6. Data Flows

### 6.1 Flow A – Milestone Accounting (Off-Chain Only)

**Objective:** Maintain accurate, risk-aware accounting for every shipment and payout tranche in the context ledger.

Sequence:

1. **Decision or Event:**
   - An operational event (`pickup_confirmed`, `mid_transit_verified`, `delivery_confirmed`, `reversal_detected`) or a risk decision occurs.

2. **`record_decision` / `record_event`:**
   - ContextLedger writes an entry capturing:
     - Shipment / token IDs
     - Event type and timestamp
     - Risk snapshot (band, score, reasons, trace_id)
     - IoT health summary (uptime, temp compliance, GPS quality)

3. **Risk Seam Attachment:**
   - A risk snapshot is attached to that ledger record, either from ChainIQ or a rules-based risk model.

4. **Payout Schedule Update:**
   - ChainPay scheduler recomputes:
     - How much of each tranche (20/70/10) is now unlocked.
     - What remains held or frozen due to risk or IoT issues.

5. **Internal State Only:**
   - No on-chain activity occurs at this step; all accounting is off-chain.

### 6.2 Flow B – On-Chain Settlement (Final Step)

**Objective:** Convert accumulated off-chain entitlements into a single, verifiable on-chain payment per carrier.

Sequence:

1. **Settlement Window Close:**
   - At end-of-day (or configured interval), ChainPay computes net payouts per carrier based on all `settlement_released`-eligible entries.

2. **Settlement Task Creation:**
   - For each carrier with a positive net amount:
     - A `settlement_id` is generated and persisted in the context ledger.
     - A settlement task is created with references to the aggregated shipments and payouts.

3. **XRPL Adapter Call:**
   - ChainPay calls the XRPL adapter/API with:
     - `settlement_id`
     - `carrier_wallet`
     - `amount`
     - `asset` (e.g., `CB-USDx`)

4. **XRPL Response:**
   - The adapter submits an XRPL payment transaction and returns:
     - `tx_hash`
     - `xrpl_timestamp` / ledger index.

5. **Ledger Update:**
   - ContextLedger updates the `settlement_released` entry for the given `settlement_id` with:
     - `tx_hash`
     - `onchain_status = SUBMITTED | CONFIRMED | FAILED`
     - `xrpl_timestamp`.

6. **Reconciliation & Monitoring:**
   - Dashboards and monitors confirm that on-chain and off-chain records match within SLA (e.g., ≤15 minutes for the pilot).

## 7. EVM & Chainlink Extension (v2 Preview)

ChainPay remains **ledger-centric** even as we prepare additional rails:

1. **Target use case:** Corridors where XRPL is unavailable or customers require stablecoins on an EVM chain. ChainPay still decides payouts off-chain but mirrors eligibility on-chain for transparency and programmable finance.
2. **On-chain contract:** `ChainPaySettlementEscrow` (conceptual successor to the vault blueprint) stores a minimal record per `settlement_id`:
  - `carrierAddress`, `amount`, `assetHash`, `riskBand`, `corridorId`, and a `status` enum.
  - Emits `SettlementRegistered` / `SettlementReleased` events so finance teams and liquidity partners can subscribe.
  - Optional balance holding: contract may custody USDC/USDT in v2 to disburse directly on EVM rails, but this is additive to XRPL.
3. **Chainlink / oracle loop:**
  - ChainBridge backend publishes a proof (e.g., Space and Time result) summarizing settlements ready for release.
  - Chainlink job reads the proof and calls the contract to register or release settlements, ensuring an external verifier wrote the data.
4. **Logged fields:**
  - **On-chain:** settlement hash, carrier address, amount, risk band, corridor ID, proof hash, status.
  - **Off-chain:** Full context ledger snapshot (shipment IDs, IoT status, override notes). These are referenced via `metadataURI` but not stored directly on-chain to avoid leaking PII.
5. **XRPL compatibility:** XRPL remains the live payout rail in v1/v1.5; the EVM contract is a parallel receipt layer that can eventually control alternative payouts. The shared identifiers (`settlement_id`, `risk_band`, `assetHash`) guarantee the two worlds stay in sync.

## 8. Security & Audibility

ChainPay v1 is designed so that every settlement decision is **replayable and explainable**:

- **Risk Snapshots:**
  - Each key ledger entry stores a structured risk snapshot:
    - Risk band and score.
    - Top reasons / features (e.g., high dispute rate, IoT anomalies).
    - Trace ID linking back to ChainIQ or rules-based engine runs.

- **IoT Health Summary:**
  - For milestones that depend on IoT, the ledger stores:
    - Uptime metrics and offline windows.
    - Summary band for `signal_confidence`.
    - Any threshold crossings that triggered band downgrades or freezes.

- **On-Chain Linkage:**
  - Every XRPL settlement has:
    - `tx_hash` stored in the context ledger.
    - Optionally, ledger index / close time.
  - This provides a cryptographic anchor tying together:
    - Shipment context → risk decisions → payout schedule → actual payment.

- **Audit Trails:**
  - Manual overrides and governance decisions are recorded as ledger entries with operator IDs, reason codes, and timestamps.
  - This supports internal audits, regulatory review, and ML retraining.

## 9. Future Extensions

ChainPay v1 explicitly keeps most logic off-chain, but the architecture is intended to support richer blockchain integrations over time:

- **Native XRPL Escrow / Conditional Payments:**
  - Move some milestone checks (e.g., POD or time locks) into XRPL escrow primitives.
  - Enable partial releases on-chain keyed to Oracles or event proofs.

- **EVM / Chainlink Actuation:**
  - Support additional settlement rails (e.g., EVM chains) using Chainlink or similar oracles to read context ledger state.
  - Allow multi-rail payouts while retaining a single off-chain context ledger as the canonical source of truth.

- **Tokenized Receivables / Factoring:**
  - Issue receivable tokens backed by context ledger claims for financing partners.
  - Use ChainPay’s risk and payout history to drive pricing, advance rates, and eligibility.

These future steps build on the same core pattern: **context ledger as truth; chains as payment and liquidity rails**.
