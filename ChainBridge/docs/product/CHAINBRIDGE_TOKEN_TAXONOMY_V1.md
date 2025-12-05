# ChainBridge Token Taxonomy (v1)

## 1. Overview

ChainBridge uses a deliberate, minimal set of on-chain representations to facilitate settlement and auditability. We avoid "token sprawl" and focus on assets that represent real-world value or state.

This document defines the canonical mapping between ChainBridge business concepts and their on-chain counterparts.

---

## 2. Core Tokens

### CB-USDx (Settlement Token)
- **Purpose:** Internal settlement IOU for USD payments.
- **Chain:** XRPL (Mainnet/Testnet).
- **Type:** Issued Currency (IOU).
- **Issuer:** `CB_ISSUER` (Cold Wallet).
- **Holders:** `CB_OPS` (Hot Wallet), Whitelisted Carrier Wallets.
- **Backing:** 100% Fiat USD.

### Future Lane Tokens (Concept / v2)
*Status: Future / Not Implemented*
- **Concept:** `CB-LANE-[CORRIDOR]-[CURRENCY]` (e.g., `CB-LANE-MX-USD`).
- **Purpose:** Represents liquidity specific to a corridor (e.g., Laredo-Monterrey).
- **Use Case:** Could allow third-party liquidity providers (LPs) to fund specific lanes in exchange for yield.

---

## 3. Shipment Representation

For v1, ChainBridge uses **Off-Chain IDs with On-Chain References**. We do **not** mint an NFT for every shipment in v1 to avoid ledger bloat and cost.

### v1 Implementation: Memo-Based Reference
- **Mechanism:** Every XRPL payment transaction includes a `Memo` field.
- **Data:** The `Memo` contains the `settlement_id` and `settlement_batch_id`.
- **Linkage:** The `settlement_id` in the Context Ledger links back to the full Shipment record (Origin, Destination, Items, IoT Data).
- **Pros:** Cheap, fast, privacy-preserving (no PII on chain).
- **Cons:** Requires access to Context Ledger to resolve details.

### v2 Future: Shipment NFTs
*Status: Future / Not Implemented*
- **Mechanism:** Mint an XRPL NFT (XLS-20) for each shipment.
- **Data:** Metadata URI points to a verifiable credential or hashed document set.
- **Use Case:** Transferable Bill of Lading (eBoL), trade finance where the NFT is collateral.

---

## 4. Mapping to Off-Chain Systems

ChainBridge acts as the translation layer between legacy logistics identifiers and blockchain states.

| ChainBridge Concept | Off-Chain ID Source | On-Chain Representation |
| :--- | :--- | :--- |
| **Shipment** | TMS Load ID (e.g., `LOAD-12345`) | `Memo: {"sid": "SET-..."}` |
| **Carrier** | ERP Vendor ID / SCAC Code | XRPL Address (`r...`) |
| **Payment** | ERP Invoice ID | XRPL Tx Hash |
| **Risk Score** | ChainIQ Inference ID | `Memo: {"risk": "LOW"}` |
| **Proof of Delivery** | EDI 214 / 990 | (Implicit in Settlement Release) |

### EDI Mapping (Reference)
- **EDI 204 (Load Tender):** Triggers `context_created`.
- **EDI 214 (Status):** Triggers `pickup` / `delivery` milestones.
- **EDI 210 (Invoice):** Replaced/Augmented by `settlement_released`.
- **EDI 997 (Ack):** Replaced by XRPL Ledger Confirmation.

---

## 5. Open Questions & Decisions

1. **Corridor Segregation:** Do we need distinct tokens for different corridors (e.g., `CB-USD-MX` vs `CB-USD-CA`) in v1?
   - *Decision:* No. Use single `CB-USDx` for all USD-denominated settlements in v1. Segregate logic off-chain.

2. **Carrier Wallets:** Do carriers manage their own keys or do we use custodial wallets?
   - *Decision:* v1 supports both, but defaults to **Custodial/Hosted** wallets for ease of onboarding. Advanced carriers can bring their own XRPL address.
