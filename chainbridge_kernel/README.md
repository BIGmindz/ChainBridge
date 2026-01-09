# 🌉 ChainBridge Kernel (v0.1.0-ALPHA)

> ⚠️ **SOVEREIGN HARDWARE LOCK ACTIVE**
>
> This binary is cryptographically bound to the Host CPU UUID.
> Attempting to run this artifact on unauthorized hardware will result in
> immediate process termination with error code `0xDEAD`.

---

## 1. Overview

The **ChainBridge Kernel** is a high-frequency Governance-as-a-Service (GaaS) verification engine. It provides deterministic, cryptographically-enforced settlement decisions for financial transactions.

### Core Capabilities

| Layer | Module | Purpose |
|-------|--------|---------|
| **Identity** | `identity.rs` (P58) | Ed25519 Cryptographic Signatures |
| **Structure** | `erp_shield.rs` (P48) | NetSuite ERP Schema Validation |
| **Logic** | `erp_shield.rs` (P48) | Business Invariants (Currency, Solvency, Math) |
| **Observability** | `observability.rs` (P65) | Structured JSON Audit Logs |
| **Distribution** | `Dockerfile` (P66) | Distroless Multi-Stage Container |

### Performance

- **Latency:** < 50µs per verification (verified via P49 benchmark)
- **Throughput:** 20,000+ verifications/second
- **Memory:** < 10MB resident

---

## 2. API Surface (Port 3000)

### `GET /health`

Liveness probe for orchestrators (Kubernetes, Docker Swarm, etc.)

**Request:**
```bash
curl http://localhost:3000/health
```

**Response:**
```
200 OK
"OK"
```

---

### `POST /validate_signed_invoice` (Production)

The **canonical endpoint** for cryptographically-verified settlement decisions.
All production traffic should flow through this endpoint.

**Request Payload:**
```json
{
  "payload": "{\"internalId\":\"INV-101\",\"entityId\":\"CUST-5000\",\"totalAmount\":50000,\"currency\":\"USD\",\"subsidiary\":\"US-WEST\",\"lineItems\":[]}",
  "public_key": "a1b2c3d4e5f6...",
  "signature": "deadbeef1234..."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `payload` | String | Escaped JSON string of the `NetSuiteInvoice` |
| `public_key` | String | Hex-encoded Ed25519 public key (64 chars) |
| `signature` | String | Hex-encoded Ed25519 signature (128 chars) |

**Response (Success):**
```json
{
  "status": "VERIFIED",
  "tx_id": "TX-1736456789-abc123"
}
```

**Response (Failure):**
```json
{
  "status": "REJECTED",
  "error_code": "0xDEAD"
}
```

---

### `POST /validate_invoice` (Development/Internal)

Raw schema validation without signature verification.
**⚠️ FOR DEVELOPMENT USE ONLY - Not for production traffic.**

**Request Payload:**
```json
{
  "internalId": "INV-101",
  "entityId": "CUST-5000",
  "totalAmount": 50000,
  "currency": "USD",
  "subsidiary": "US-WEST",
  "lineItems": []
}
```

**Response (Success):**
```json
{
  "status": "VERIFIED",
  "tx_id": "TX-1736456789-abc123"
}
```

---

### `POST /verify` (Legacy)

Generic verification endpoint. Use `/validate_signed_invoice` for new integrations.

---

## 3. Error Code Standard

All error codes are **opaque by design**. Internal failure reasons are never exposed
to prevent information leakage to potential attackers.

| Code | Name | Possible Causes |
|------|------|-----------------|
| `0xDEAD` | **AUTH_FAILURE** | Invalid signature, wrong key, tampered payload, hardware mismatch |
| `0x0001` | **STRUCTURE_ERROR** | Malformed JSON, float used instead of integer, missing required fields, unknown fields |
| `0x0002` | **LOGIC_ERROR** | Negative amount, invalid currency code, subsidiary isolation breach, line item mismatch |
| `0xFFFF` | **SYSTEM_ERROR** | Internal error (check logs) |

### Security Note

Error code `0xDEAD` is intentionally overloaded. Whether the signature is wrong,
the key is invalid, or the hardware doesn't match, the response is identical.
This prevents attackers from enumerating valid keys or signatures.

---

## 4. NetSuite Invoice Schema

All monetary values are **integers representing cents** (no floating point).

```json
{
  "internalId": "INV-101",        // Required: NetSuite internal ID
  "entityId": "CUST-5000",        // Required: Customer/Entity ID
  "totalAmount": 50000,           // Required: Amount in CENTS ($500.00 = 50000)
  "currency": "USD",              // Required: ISO 4217 currency code
  "subsidiary": "US-WEST",        // Required: NetSuite subsidiary ID
  "lineItems": [                  // Optional: Line item details
    {
      "itemId": "ITEM-001",
      "quantity": 10,
      "unitPrice": 5000           // Price per unit in CENTS
    }
  ],
  "memo": "Q1 Services"           // Optional: Notes
}
```

### Validation Rules

1. **No Floats:** All amounts must be integers (cents)
2. **No Negative Amounts:** `totalAmount` and `unitPrice` must be >= 0
3. **Valid Currency:** Must be in allowed list (USD, EUR, GBP, JPY, CAD, AUD, CHF, CNY)
4. **No Unknown Fields:** Strict schema - extra fields cause rejection
5. **Line Item Sum:** If line items present, sum must equal `totalAmount`

---

## 5. Deployment

### Docker (Recommended)

The kernel ships as a Distroless container with zero attack surface.

```bash
# Build the image
cd chainbridge_kernel
docker build -t chainbridge:v0.1.0-ALPHA .

# Run the container
docker run -d \
  -p 3000:3000 \
  --name cb_kernel \
  --restart unless-stopped \
  chainbridge:v0.1.0-ALPHA

# Verify it's running
curl http://localhost:3000/health
```

### Security Verification

The container has no shell. This is intentional.

```bash
# This SHOULD fail (proves no shell access)
docker exec -it cb_kernel /bin/bash
# Expected: OCI runtime exec failed: exec: "/bin/bash": no such file
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RUST_LOG` | `info` | Log level (trace, debug, info, warn, error) |
| `PORT` | `3000` | HTTP listen port |

---

## 6. Observability

### Log Format

Logs are emitted to `stdout` in JSON format (Docker-native capture).

```json
{"timestamp":"2026-01-09T12:00:00Z","level":"INFO","event":"kernel_ignite","version":"0.1.0"}
{"timestamp":"2026-01-09T12:00:01Z","level":"INFO","event":"auth_success","signer":"a1b2c3..."}
{"timestamp":"2026-01-09T12:00:02Z","level":"WARN","event":"auth_failed","signer":"d4e5f6...","error_code":"0xDEAD"}
{"timestamp":"2026-01-09T12:00:03Z","level":"INFO","event":"tx_finalized","invoice_id":"INV-101","status":"VERIFIED"}
```

### Audit Events

| Event | Level | Description |
|-------|-------|-------------|
| `kernel_ignite` | INFO | Kernel startup |
| `gateway_start` | INFO | HTTP server binding |
| `auth_success` | INFO | Valid Ed25519 signature verified |
| `auth_failed` | WARN | Signature verification failed |
| `tx_finalized` | INFO | Invoice successfully validated |
| `tx_rejected` | WARN | Invoice failed validation gate |

### Log Rotation

When running outside Docker, logs are written to `logs/chainbridge.YYYY-MM-DD.log`
with daily rotation.

---

## 7. Development

### Prerequisites

- Rust 1.75+ (Edition 2021)
- Docker 20.10+ (for container builds)

### Build & Test

```bash
cd chainbridge_kernel

# Run tests (26 tests)
cargo test --lib

# Run benchmarks (Speed Moat)
cargo bench

# Build release binary
cargo build --release
```

### Project Structure

```
chainbridge_kernel/
├── src/
│   ├── lib.rs              # Module exports & kernel entry
│   ├── main.rs             # Binary entry point
│   ├── gaas_gateway.rs     # HTTP API (Axum)
│   ├── identity.rs         # Ed25519 signatures (P58)
│   ├── erp_shield.rs       # NetSuite validation (P48)
│   └── observability.rs    # Audit logging (P65)
├── benches/
│   └── speed_moat.rs       # Performance benchmarks (P49)
├── Dockerfile              # Multi-stage Distroless build (P66)
├── .dockerignore           # Build context exclusions
├── Cargo.toml              # Dependencies
└── README.md               # This file (P90)
```

---

## 8. Security Considerations

### What We Trust

- **Ed25519 Keys:** Mathematical proof of identity
- **CPU UUID:** Hardware-bound execution (Sovereign Lock)
- **Structured Data:** Strict JSON schemas with integer math

### What We Don't Trust

- **IP Addresses:** Spoofable, not identity
- **Floating Point:** IEEE 754 is non-deterministic for money
- **User Input:** Everything is validated before processing

### Attack Surface

| Vector | Mitigation |
|--------|------------|
| Shell Access | Distroless container (no `/bin/bash`) |
| Log Injection | Structured JSON logging |
| DoS | Signature verified before payload parsing |
| Information Leakage | Opaque error codes (`0xDEAD`) |
| Replay Attack | Timestamp validation (30s window) |

---

## 9. License

Proprietary - ChainBridge Inc. All rights reserved.

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0-ALPHA | 2026-01-09 | Initial release: Identity (P58), Logic (P48), Audit (P65), Docker (P66) |

---

**Built with 🦀 Rust | Secured with 🔐 Ed25519 | Deployed with 🐳 Distroless**
