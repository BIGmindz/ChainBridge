# ChainPay On-Chain Contracts v1.5 Blueprint

## 1. Rationale

ChainPay v1 keeps settlement logic off-chain and uses XRPL strictly for final payouts. v1.5 introduces an **EVM/Chainlink layer** that notarizes settlement eligibility and optionally escrows funds for future multi-rail expansion, without replacing XRPL as the active payout rail. Goals:
- Provide programmable transparency so liquidity partners or finance teams can verify settlement states on public ledgers.
- Prepare for receivable financing, slashing, or third-party guarantees tied to ChainPay risk decisions.
- Maintain compatibility with existing `settlement_id`, `risk_band`, and CB-USDx flows.

## 2. Architecture Overview

```
Context Ledger + ChainIQ  --->  Proof Generation (Space and Time / off-chain worker)
                                          |
                                          v
                               Chainlink OCR Job / Functions
                                          |
                                          v
                            ChainPaySettlementVault (EVM L2)
                                          |
                        (optional) payment adapters / observers
```

- Context ledger continues to orchestrate milestones, payouts, and XRPL settlements.
- When `settlement_released` occurs, ChainPay emits a hashed proof package.
- Proof is verified by Space and Time (or another verifiable computation layer) and delivered to Chainlink, which writes to the EVM contract.
- EVM contract stores immutable settlement records and exposes hooks for future automated releases or financing.

## 3. ChainPaySettlementVault Contract (Concept)

### 3.1 Core Data

| Field | Description |
| --- | --- |
| `settlementId` | Bytes32 hash of the off-chain `settlement_id` (e.g., keccak256 of the string). |
| `carrier` | Address representing the carrier or liquidity recipient on EVM rail. |
| `amount` | Uint256 representing USD-equivalent amount scaled to 1e6 (micro-dollars) or token decimals. |
| `assetHash` | Bytes32 identifying the asset (e.g., CB-USDx, USDC). |
| `riskBand` | Enum (0=LOW, 1=MEDIUM, 2=HIGH, 3=CRITICAL). |
| `status` | Enum (REGISTERED, RELEASED, HELD, SLASHED). |
| `proofHash` | Bytes32 commitment to the Space and Time proof of milestone & risk compliance. |

### 3.2 Functions (Pseudo-signatures)

```solidity
function registerSettlement(
    bytes32 settlementId,
    address carrier,
    uint256 amount,
    bytes32 assetHash,
    uint8 riskBand,
    bytes32 proofHash,
    string calldata metadataURI
) external onlyBridge;

function releaseSettlement(bytes32 settlementId) external onlyOracle;

function holdSettlement(bytes32 settlementId, bytes calldata reason) external onlyBridge;

function slashSettlement(bytes32 settlementId, address beneficiary, uint256 amount, bytes calldata reason) external onlyGovernance;

function getSettlement(bytes32 settlementId) external view returns (Settlement memory);
```

- `onlyBridge`: ChainPay backend signer (Cody's service) registers settlements once off-chain eligibility is confirmed.
- `onlyOracle`: Chainlink job (or multisig) that verifies proof and triggers release transitions.
- `onlyGovernance`: Multi-sig (Benson + Pax + Sam) empowered to slash in fraud/exception cases.

### 3.3 Events

```solidity
event SettlementRegistered(bytes32 indexed settlementId, address carrier, uint256 amount, uint8 riskBand, bytes32 proofHash);
event SettlementReleased(bytes32 indexed settlementId, address carrier, uint256 amount);
event SettlementHeld(bytes32 indexed settlementId, bytes reason);
event SettlementSlashed(bytes32 indexed settlementId, address beneficiary, uint256 amount, bytes reason);
```

Events allow observers (finance dashboards, liquidity partners) to track settlement lifecycle on-chain without accessing XRPL directly.

## 4. Proof & Oracle Flow

1. **Proof Generation:**
   - When context ledger marks `settlement_released`, ChainPay computes a deterministic proof package: hash of shipment IDs, payout amounts, risk band, IoT summary (or references). This is sent to Space and Time for attestation.
2. **Proof Result:**
   - Space and Time produces `proofHash` + optional `metadataURI` that describes the data set (stored in IPFS/S3).
3. **Chainlink Job:**
   - Chainlink node watches for ready proofs, then calls `registerSettlement` supplying the hashed data and metadata URI. Alternatively, ChainPay backend can call `registerSettlement` and Chainlink later calls `releaseSettlement` when proof is verified (`onlyOracle`).
4. **Release Trigger:**
   - Once Chainlink confirms the proof and (optionally) that the corresponding XRPL transaction succeeded, it calls `releaseSettlement`. Status flips to RELEASED, enabling downstream actions like liquidity drawdowns.
5. **Hold or Slash:**
   - If subsequent investigation finds a reversal, ChainPay backend can call `holdSettlement`. Governance can `slashSettlement` to redirect funds or mark the settlement as void in the EVM ledger.

## 5. Compatibility with XRPL v1

- XRPL remains the actual payout rail in v1.5; the EVM contract is **observational/escrow** only.
- Settlement IDs are identical across systems. The EVM contract stores hashed IDs so public observers cannot read shipper details while ChainBridge can still map deterministically.
- `assetHash` references CB-USDx (or future tokens), ensuring future multi-rail payouts can align balances between XRPL IOU and EVM collateral pools.
- No requirement to lock funds on EVM in v1.5; contract can start in "notary" mode (record only). Later, we can optionally deposit stablecoins or CBDC bridges to actually release funds on EVM rails.

## 6. Future Extensions

1. **Programmable Vault:** Add ERC-20 balance accounting so funds deposited into the contract can be auto-released to carriers on EVM networks, enabling USDC payouts.
2. **Receivables Marketplace:** Emit ERC-721 or ERC-1155 tokens representing settlement claims; investors can price, buy, or finance them. Contract ensures only released settlements become tradable.
3. **Chainlink CCIP:** Use CCIP to signal XRPL escrow states or to bridge metadata to other chains securely.
4. **Automated Slashing:** Integrate with Sam's threat signals so high-risk settlements automatically move to HELD state pending review.

## 7. Open Questions & Next Steps

- Determine which EVM chain (Base, Polygon, or L2) best matches compliance + low fees for the pilot extension.
- Finalize `metadataURI` schema so Maggie can map EVM records back to detailed risk explanations without leaking shipper PII on-chain.
- Align with Cody on signer design: do we run a dedicated ChainPay signer service or reuse existing `settlement_adapter` keys?
- Confirm with legal whether public settlement hashes require anonymization beyond hashed IDs (e.g., salted hashing).
