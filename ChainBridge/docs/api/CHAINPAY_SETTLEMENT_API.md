# ChainPay Settlement API (v1)

## 1. Purpose

The ChainPay Settlement API exposes a small, explicit surface for **triggering** and **monitoring** final settlements that may be mirrored on XRPL. It is designed for internal services (ChainPay scheduler, batch jobs) and, later, external orchestrators that need to:

- Initiate an on-chain payout (backed by the off-chain context ledger).
- Retrieve the current settlement status and associated on-chain metadata.
- Acknowledge that settlement information has been successfully written and propagated.

All APIs assume that **settlement eligibility and amounts** have already been computed by the context ledger and ChainPay services.

## 2. Common Concepts

- **`settlement_id`**
  - A unique identifier for a netted payout event, typically representing the aggregate of multiple shipments for a single carrier over a window (e.g., a day).
  - Generated and persisted by ChainPay when a settlement task is created.

- **`risk_band`**
  - Discrete risk classification at time of settlement: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
  - Derived from ChainIQ / ContextLedgerRiskModel and used for governance and monitoring; settlement itself should already respect band-based rules.

- **`trace_id`**
  - A correlation ID linking this settlement back to the risk and decision pipeline (e.g., a ChainIQ trace or context ledger decision ID).
  - Useful for debugging and audit trails (who/what produced the band and payout decision).

- **`asset`**
  - The settlement asset used on-chain, e.g., `CB-USDx` for the pilot corridor.
  - Represents an IOU or tokenized asset whose off-chain backing is managed separately.

- **`carrier_wallet`**
  - The on-chain address (e.g., XRPL classic address) belonging to the carrier receiving the payout.
  - Example format on XRPL: `rXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`.

These concepts tie this API back to:

- Product spec: `docs/product/CHAINPAY_V1_SPEC.md`
- Architecture spec: `docs/architecture/CHAINPAY_ONCHAIN_SETTLEMENT.md`

## 3. Endpoints

### 3.1 `POST /chainpay/settle-onchain`

**Description:**

Trigger an on-chain settlement for a previously computed net payout. This endpoint assumes the settlement has been marked as releasable in the context ledger.

**Request Body (JSON):**

```json
{
  "settlement_id": "string",
  "carrier_wallet": "rXXXXXXXX",
  "amount": 1234.56,
  "asset": "CB-USDx",
  "risk_band": "LOW",
  "trace_id": "ctx-risk-uuid",
  "memo": "optional free-text"
}
```

- `settlement_id` (string, required): Must reference an existing settlement record in releasable state.
- `carrier_wallet` (string, required): Destination wallet on the settlement rail (XRPL in v1).
- `amount` (number, required): Net amount to be settled for this `settlement_id`.
- `asset` (string, required): Settlement asset symbol, e.g., `CB-USDx`.
- `risk_band` (string, required): `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` at settlement time.
- `trace_id` (string, required): Correlation ID linking back to risk/decision context.
- `memo` (string, optional): Free-text note for internal audit (e.g., settlement window or batch name).

**Behavior:**

- Validates that:
  - The given `settlement_id` exists in the ledger.
  - The settlement is in a **releasable** state based on prior decisions (not frozen/voided).
  - The `amount` matches the computed net payout for that `settlement_id`.
- Submits an on-chain payment via the configured settlement rail adapter (XRPL in v1):
  - Constructs and sends a transaction for `amount` of `asset` to `carrier_wallet`.
- Persists the on-chain result back into the ledger as metadata on the settlement record:
  - `tx_hash`
  - `xrpl_timestamp` (or equivalent chain timestamp)
  - `status` / `onchain_status`.

**Response – 200 OK:**

```json
{
  "settlement_id": "string",
  "tx_hash": "ABC123...",
  "xrpl_timestamp": "2025-12-04T18:51:42Z",
  "status": "SUBMITTED"
}
```

- `status` values (canonical set):
  - `SUBMITTED` – Transaction submitted but not yet confirmed.
  - `CONFIRMED` – Transaction validated and considered final on-chain.
  - `FAILED` – Transaction rejected or permanently failed.

**Error Responses:**

- `400 Bad Request` – Validation errors (e.g., unknown `risk_band`, negative `amount`).
- `404 Not Found` – `settlement_id` not recognized.
- `409 Conflict` – State mismatch (e.g., settlement not in releasable state, or `amount` mismatch).
- `502 Bad Gateway` / `503 Service Unavailable` – XRPL adapter or node unavailable.

Error payloads use the standard envelope defined in Section 4.

---

### 3.2 `GET /chainpay/settlements/{settlement_id}`

**Description:**

Retrieve the current settlement state, including on-chain metadata if present.

**Path Parameters:**

- `settlement_id` (string, required): ID of the settlement to query.

**Response – 200 OK:**

```json
{
  "settlement_id": "string",
  "status": "PENDING",
  "amount": 1234.56,
  "asset": "CB-USDx",
  "carrier_wallet": "rXXXXXXXX",
  "risk_band": "HIGH",
  "risk_trace_id": "ctx-risk-uuid",
  "tx_hash": "ABC123...",
  "xrpl_timestamp": "2025-12-04T18:51:42Z"
}
```

- `status` lifecycle (canonical values):
  - `PENDING` – Settlement is defined but not yet released for on-chain payment.
  - `RELEASED` – Settlement has been approved and is eligible for on-chain execution.
  - `ONCHAIN_CONFIRMED` – On-chain transaction confirmed and reconciled.
  - `FAILED` – Settlement failed or was canceled (e.g., persistent XRPL failure, governance reversal).

- `risk_trace_id`: back-reference to the risk decision that produced the settlement (e.g., ChainIQ inference or rules engine run).
- `tx_hash` / `xrpl_timestamp`: present only if an on-chain payment has been attempted.

**Error Responses:**

- `404 Not Found` – No settlement with the given `settlement_id`.

Error payloads follow the common error envelope.

---

### 3.3 `POST /chainpay/settlements/{settlement_id}/ack`

**Description:**

Acknowledge that settlement information (including on-chain metadata) has been successfully attached, processed, or mirrored by a downstream system. Intended for async workers or external orchestrators.

This endpoint does **not** initiate payment; it confirms handling of an existing settlement record.

**Path Parameters:**

- `settlement_id` (string, required): ID of the settlement to acknowledge.

**Request Body (JSON, optional but recommended):**

```json
{
  "trace_id": "ctx-risk-uuid",
  "consumer_id": "chainboard-ui|finance-batch-job|external-system",
  "notes": "optional human-readable message"
}
```

**Behavior:**

- Records an acknowledgement event in the context ledger for the given `settlement_id`:
  - Associates it with `trace_id` and `consumer_id` for audit.
  - Can be used to track which systems have seen/processed the settlement.
- Idempotent: repeated acknowledgements for the same combination are safe and should not error.

**Response – 200 OK:**

```json
{
  "ok": true,
  "settlement_id": "string"
}
```

**Error Responses:**

- `404 Not Found` – Settlement does not exist.

Error payloads follow the common error envelope.

## 4. Error Handling

All endpoints return a consistent error envelope on non-2xx responses:

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Human readable detail"
}
```

- `error` (string, required): Machine-readable category:
  - `VALIDATION_ERROR` – Invalid inputs (missing fields, type errors, invalid state transitions).
  - `NOT_FOUND` – Unknown `settlement_id` or referenced object.
  - `XRPL_FAILURE` – Upstream XRPL or settlement-rail error.
  - `INTERNAL_ERROR` – Catch-all for unexpected conditions.

- `message` (string, required): Human-readable explanation suitable for logs and operator consoles.

Additional optional fields (e.g., `details`, `trace_id`) MAY be included as the implementation matures but should not be required by clients.

## 5. Auth & Permissions (Placeholder)

For ChainPay v1, access is assumed to be **internal-only** (e.g., within the ChainBridge stack or a trusted VPC). A future iteration will formalize authentication and authorization. Planned directions include:

- **Service-level auth:**
  - Mutual TLS or signed JWTs for services like ChainFreight, ChainIQ, ChainPay scheduler, and ChainBoard.

- **Operator-level auth:**
  - API keys or OAuth/JWT for UIs and operator tools, with role-based access to sensitive endpoints.

Until that model is finalized, treat this API as **not exposed to untrusted clients** and rely on infrastructure-level network controls.
