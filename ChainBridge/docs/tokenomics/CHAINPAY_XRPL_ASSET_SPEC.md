# ChainPay XRPL Asset Specification (CB-USDx)

## 1. Purpose & Scope

CB-USDx is ChainPay's corridor IOU on XRPL, used to mirror final `settlement_released` payouts for the USD→MXN reefer pilot. All milestone logic, risk adjustments, and accrual accounting stay in the context ledger; XRPL only handles the final, netted transfer per carrier so we obtain cryptographic settlement receipts without rewriting business logic.

## 2. XRPL Account Topology

| Account | Role | Security Posture | Notes |
| --- | --- | --- | --- |
| `rCBIssuer...` (Issuer / Cold) | Mints and can redeem CB-USDx; never sends payments directly. | Held in multi-sig (2-of-3) with hardware security modules. `DefaultRipple` disabled; regular key rotated quarterly. | Only touched for setting trustline limits, flags, or mint/burn operations tied to treasury funding. |
| `rCBTreasury...` (Treasury / Hot) | Holds CB-USDx inventory for operations; submits daily payments to carriers. | Single operator key in HSM-backed signer + failover hot wallet. Limits enforced via `RequireAuth` trustline policy. | ChainPay settlement service signs XRPL payments from this wallet. |
| `rCBOps...` (Operations Buffer) | Optional buffer wallet for staging funds between cold issuer and treasury. | Same security as treasury; used for manual interventions. | Provides blast radius if treasury key is compromised. |
| Carrier wallets (e.g., `rCarrier123...`) | Receive CB-USDx payouts. | Either carrier-owned XRPL address or custodial subwallet managed by ChainBridge (mapped via `carrier_id`). | Must complete onboarding (KYC + trustline) before receiving funds. |

### 2.1 Key Management & Recovery

- Issuer: 2-of-3 multi-sig with keys split between ChainBridge treasury, finance controller, and emergency custodian. Recovery plan documented with Sam (GID-06).
- Treasury: Hot wallet but with:
  - Daily spending limits enforced by the settlement service (configurable max per carrier/day).
  - Optional `DepositAuth` flag to reject unexpected deposits.
  - Regular key rotated monthly.
- All wallets use XRPL `regular_key` delegation so compromised signing keys can be swapped without changing classic addresses.

## 3. Currency Code & Corridor Policy

- Currency code: `CB-USDx` (ISO base `USD` + suffix `x` to denote XRPL IOU).
- Pilot corridors (Laredo → Monterrey) share this single IOU; corridor metadata lives in context ledger + XRPL memo fields.
- Future corridors can either reuse CB-USDx (preferred) or introduce variants like `CB-USD2` if regulatory needs require isolation. Decision deferred until we add a second corridor.

## 4. Trustlines, KYC, and Allowlisting

1. **Carrier Onboarding Steps**
   - Complete KYC / KYB with ChainBridge finance team.
   - Provide XRPL address (or request custodial wallet).
   - Establish trustline to issuer account:
     ```
     TrustSet
       Account: rCarrier123...
       LimitAmount: { currency: "CB-USDx", issuer: rCBIssuer..., value: "50000" }
     ```
   - ChainBridge sets `RequireAuth` on the issuer so only approved wallets can hold CB-USDx; onboarding includes an allowlist flag.
2. **Trustline Limits**
   - Default pilot limit: USD 50k equivalent per carrier (adjustable).
   - Raising limits requires Pax approval + finance confirmation.
3. **Offboarding / Revocation**
   - Set trustline limit to `0`; request carrier to clear balance.
   - If carrier is non-responsive, issuer can claw back via `tfGlobalFreeze` followed by a redemption to treasury (see Section 5).

## 5. Freeze & Safety Policy

- The issuer account sets `RequireAuth` so only allowlisted trustlines are active.
- Global freeze policy:
  - `tfGlobalFreeze` remains **disabled** by default.
  - Trigger conditions for enabling freeze:
    1. Confirmed fraud or sanctions issue involving the CB-USDx pool.
    2. Lost or compromised treasury key.
    3. Regulatory directive requiring immediate halt.
  - Activation requires Pax + finance controller + Sam approval (documented in incident log). Once resolved, freeze is lifted and event recorded in ChainPay governance log.
- Per-trustline freeze:
  - Treated as last resort when a carrier wallet is compromised. Issuer uses `AccountSet` with `asfGlobalFreeze` off but `HookOn` and trustline-specific flags to lock the balance.

## 6. Settlement Flow Mapping

1. Context ledger marks `settlement_released` for carrier ABC with `settlement_id = SET-2025-12-001`, amount `12,345.67` USD.
2. ChainPay scheduler aggregates daily totals and invokes the XRPL adapter with payload (mirrors `POST /chainpay/settle-onchain`).
3. Treasury wallet submits an XRPL Payment:
   - `Account`: `rCBTreasury...`
   - `Destination`: `rCarrierABC...`
   - `Amount`: `{ currency: "CB-USDx", value: "12345.67", issuer: "rCBIssuer..." }`
   - `DestinationTag`: optional numeric `carrier_id`.
   - `Memos`: structured JSON (hex-encoded) per Section 7.
4. Adapter returns `tx_hash` and ledger timestamp; context ledger updates settlement record.
5. Carrier cashes out CB-USDx off-ledger via ACH/wire handled by finance or trades CB-USDx for XRP/MXN with a liquidity partner (outside v1 scope).

## 7. XRPL Memo Schema

Suggested memo payload attached to every treasury payment:

```json
{
  "sid": "SET-2025-12-001",
  "shp": "SHIP-7781",
  "lane": "Laredo-Monterrey",
  "risk": "MEDIUM",
  "ver": "CHAINIQ-PINK-01"
}
```

Encoding rules:
- Memo tagged as `MemoType = "chainpay"`.
- JSON serialized, UTF-8 encoded, then hex-encoded per XRPL convention.
- `ver` mirrors the risk model version recorded in the context ledger so future audits can correlate payouts to models.

## 8. Example XRPL Payment (Pseudo)

```
Payment
  Account: rCBTreasury...
  Destination: rCarrierABC...
  Amount:
    currency: CB-USDx
    value: "12345.67"
    issuer: rCBIssuer...
  DestinationTag: 42017          ; carrier_id encoded
  Fee: 12 drops
  Sequence: 381920
  SigningPubKey: ...
  TxnSignature: ...
  Memos:
    - MemoType: 636861696e706179   ("chainpay")
      MemoData: 7b22736964223a225345542d323032352d31322d303031222c22736870223a22534849502d37373831222c226c616e65223a224c617265646f2d4d6f6e746572726579222c227269736b223a224d454449554d222c22766572223a22434841494e49512d50494e4b2d3031227d
```

## 9. Operational Controls & Monitoring

- **Reconciliation:** Every XRPL `tx_hash` must be attached to the matching `settlement_id` within 15 minutes. Monitor lag via ChainBoard Ops panel.
- **Balance Tracking:** Finance monitors issuer and treasury balances daily to ensure 1:1 backing vs. off-chain USD escrow. Alert thresholds at 80% (refill needed) and 110% (excess).
- **Fee Handling:** XRPL fees (drops of XRP) are paid from treasury wallet's XRP balance; keep at least 20 XRP to avoid `tecUNFUNDED_PAYMENT` errors.
- **Audit Logging:** All treasury submissions log operator ID, settlement batch, and XRPL response to `immediate_actions_executed_*` entries.

## 10. Open Decisions

1. Corridor tagging on-chain: we currently encode corridor in memo; revisit if regulators require distinct IOUs per corridor.
2. Custodial wallets: final UX for carriers without XRPL experience (use ChainBridge-managed wallets vs. partner custodian) to be confirmed with Benson/Sam.
3. Automated freeze playbooks: need joint document with Sam (GID-06) for regulator-ready language.
