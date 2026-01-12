# Blockchain Audit Anchoring Specification
## PAC-SEC-P822-B Technical Documentation

**Version:** 1.0.0  
**Status:** ACTIVE  
**Authors:** LEXICON (GID-08), ChainBridge Security Team  
**Last Updated:** 2026-01-12

---

## Executive Summary

PAC-SEC-P822-B implements dual-chain blockchain anchoring for ChainBridge's immutable audit log system. This specification details the integration with XRP Ledger and Hedera Consensus Service for cryptographic anchoring that enables:

- **Forensic Sovereignty**: Third-party verification without ChainBridge involvement
- **Quantum Resistance**: ML-DSA-65 post-quantum signatures (FIPS 204)
- **Cost Efficiency**: <$0.01 per anchor on XRP Ledger
- **High Throughput**: 10,000+ TPS on Hedera for burst scenarios

---

## 1. Architecture Overview

### 1.1 Dual-Chain Strategy

```
┌──────────────────────────────────────────────────────────────────┐
│                    CHAINBRIDGE AUDIT EVENTS                       │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     ANCHOR COORDINATOR                            │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐  │
│  │ Batch Manager  │  │ Retry Logic    │  │ Failover Manager   │  │
│  │ (100 events    │  │ (3 attempts,   │  │ (XRP→Hedera        │  │
│  │  or 5 minutes) │  │  exp backoff)  │  │  auto-switch)      │  │
│  └────────────────┘  └────────────────┘  └────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│   XRP LEDGER (PRIMARY)  │     │  HEDERA CONSENSUS SVC   │
│   ─────────────────     │     │  ───────────────────    │
│   • Memo Field Anchor   │     │  • Topic-Based Anchor   │
│   • <$0.01 per tx       │     │  • Nanosecond Precision │
│   • 3-5s Finality       │     │  • Running Hash Chain   │
│   • Public Explorer     │     │  • 10K+ TPS             │
└─────────────────────────┘     └─────────────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                  IMMUTABLE BLOCKCHAIN RECORD                     │
│   • Merkle Root Hash (64 chars)                                  │
│   • ISO 8601 Timestamp                                           │
│   • Transaction Reference (for verification)                     │
│   • ML-DSA-65 Post-Quantum Signature                            │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Hierarchy

| Component | File | Purpose |
|-----------|------|---------|
| XRPLConnector | `xrp_connector.py` | XRP Ledger integration |
| HederaConnector | `hedera_connector.py` | Hedera Consensus Service |
| ProofGenerator | `proof_generator.py` | Merkle proof generation |
| PQCAnchor | `pqc_anchor.py` | Post-quantum signatures |
| AnchorCoordinator | `anchor_coordinator.py` | Dual-chain orchestration |

---

## 2. Invariants (MUST ENFORCE)

### INV-ANCHOR-001: Timeliness
> Audit events MUST anchor to blockchain within 5 minutes of recording.

**Enforcement:**
- Batch interval: 300 seconds maximum
- Time-trigger check every 60 seconds
- Critical events trigger immediate anchor

### INV-ANCHOR-002: Privacy-Preserving
> Only cryptographic hashes anchor to blockchain, NEVER event content.

**Enforcement:**
- Merkle root is SHA-256 of event hashes
- No PII, credentials, or raw data transmitted
- Content remains in local immutable store

### INV-ANCHOR-003: Dual-Chain Redundancy
> System MUST maintain capability to anchor to both XRP Ledger and Hedera.

**Enforcement:**
- Both connectors initialized at startup
- Failover strategy: XRP → Hedera (configurable)
- Dual-chain mode anchors to both simultaneously

### INV-ANCHOR-004: Third-Party Verifiable
> Proofs MUST enable verification without ChainBridge access.

**Enforcement:**
- Merkle inclusion proofs exportable
- Blockchain explorer URLs provided
- No proprietary formats or tools required

### INV-ANCHOR-005: Quantum-Resistant
> Signatures MUST use NIST FIPS 204 (ML-DSA-65) post-quantum algorithm.

**Enforcement:**
- PQCAnchor signs all Merkle roots
- Hybrid mode: Ed25519 + ML-DSA-65
- Public key exported for verification

### INV-ANCHOR-006: Graceful Degradation
> Failover MUST activate automatically when primary chain fails.

**Enforcement:**
- 3 consecutive failures trigger failover
- Auto-recovery check every 60 seconds
- Alert on failover activation

### INV-ANCHOR-007: Retry Before Fail
> System MUST retry 3 times with exponential backoff before failing.

**Enforcement:**
- Initial delay: 1 second
- Backoff multiplier: 2x
- Maximum delay: 30 seconds

---

## 3. XRP Ledger Integration

### 3.1 Configuration

```yaml
xrpl:
  active_network: testnet
  networks:
    testnet:
      websocket_url: "wss://s.altnet.rippletest.net:51233"
      json_rpc_url: "https://s.altnet.rippletest.net:51234"
      explorer_url: "https://testnet.xrpl.org"
```

### 3.2 Memo Field Structure

```json
{
  "type": "audit/merkle-root",
  "version": "1.0",
  "merkle_root": "a1b2c3d4...64_hex_chars",
  "event_count": 100,
  "timestamp": "2026-01-12T00:00:00.000Z"
}
```

### 3.3 Transaction Cost

| Network | Fee (XRP) | Fee (USD @ $0.50) |
|---------|-----------|-------------------|
| Testnet | 0.000010 | Free |
| Mainnet | 0.000010-0.000020 | $0.000005-$0.00001 |

---

## 4. Hedera Consensus Service Integration

### 4.1 Topic Structure

- **Topic ID**: `0.0.XXXXXX` (created per environment)
- **Topic Memo**: "ChainBridge Audit Log"
- **Admin Key**: Required for topic management
- **Submit Key**: Not required (open submission)

### 4.2 Message Format

```json
{
  "version": "1.0",
  "merkle_root": "a1b2c3d4...64_hex_chars",
  "event_count": 100,
  "batch_id": "uuid-here",
  "timestamp": "2026-01-12T00:00:00.000000000Z"
}
```

### 4.3 Consensus Timestamp Precision

Hedera provides nanosecond-precision consensus timestamps:

```
Seconds: 1704931200
Nanoseconds: 123456789
ISO 8601: 2026-01-12T00:00:00.123456789Z
```

---

## 5. Proof Generation

### 5.1 Merkle Tree Construction

```
              Root Hash
             /        \
         H(0-1)      H(2-3)
         /    \      /    \
       H(0)  H(1)  H(2)  H(3)
        │      │     │     │
     Event0 Event1 Event2 Event3
```

### 5.2 Inclusion Proof Format

```json
{
  "proof_type": "inclusion",
  "algorithm": "sha256",
  "leaf_hash": "event_hash_here",
  "root_hash": "merkle_root_here",
  "proof_path": [
    {"hash": "sibling_hash", "position": "left"},
    {"hash": "parent_sibling", "position": "right"}
  ],
  "timestamp": "2026-01-12T00:00:00Z"
}
```

### 5.3 Verification Algorithm

```python
def verify_inclusion(proof):
    current = proof.leaf_hash
    for node in proof.proof_path:
        if node.position == "left":
            current = sha256(node.hash + current)
        else:
            current = sha256(current + node.hash)
    return current == proof.root_hash
```

---

## 6. Post-Quantum Cryptography

### 6.1 Algorithm Selection

| Algorithm | Standard | Security Level | Signature Size |
|-----------|----------|----------------|----------------|
| ML-DSA-65 | FIPS 204 | Level 3 | 3,309 bytes |
| ML-DSA-44 | FIPS 204 | Level 2 | 2,420 bytes |
| ML-DSA-87 | FIPS 204 | Level 5 | 4,627 bytes |

**Selected: ML-DSA-65** (NIST Level 3, balanced security/performance)

### 6.2 Hybrid Signature Mode

For transition compatibility, we use hybrid signatures:

1. **Classical**: Ed25519 (for current systems)
2. **Post-Quantum**: ML-DSA-65 (for future-proofing)

Both signatures must verify for anchor to be valid.

### 6.3 Key Management

- Keys rotate every 90 days
- Previous keys retained for 365 days
- Key material stored in `keys/pqc/`

---

## 7. Third-Party Verification Guide

### 7.1 Verification Steps

1. **Obtain Anchor Reference**
   - XRP Ledger: Transaction hash (64 hex chars)
   - Hedera: Topic ID + Sequence Number

2. **Retrieve Blockchain Record**
   - XRP: Query XRPL node or explorer
   - Hedera: Query Mirror Node API

3. **Extract Merkle Root**
   - Parse memo/message content
   - Extract `merkle_root` field

4. **Obtain Inclusion Proof**
   - Request from ChainBridge API
   - Or use exported proof file

5. **Verify Inclusion**
   - Compute path from leaf to root
   - Compare computed root with anchored root

6. **Verify PQC Signature** (optional)
   - Obtain public key
   - Verify ML-DSA-65 signature

### 7.2 Explorer URLs

| Network | Explorer |
|---------|----------|
| XRP Testnet | https://testnet.xrpl.org/transactions/{tx_hash} |
| XRP Mainnet | https://livenet.xrpl.org/transactions/{tx_hash} |
| Hedera Testnet | https://hashscan.io/testnet/topic/{topic_id} |
| Hedera Mainnet | https://hashscan.io/mainnet/topic/{topic_id} |

---

## 8. Compliance Mapping

### 8.1 SOC2 AU-9 (Protection of Audit Information)

| Requirement | Implementation |
|-------------|----------------|
| Integrity Protection | Blockchain immutability + Merkle proofs |
| Unauthorized Modification | Only hashes anchored, content separate |
| Retention | Blockchain permanent, proofs 365 days |
| Access Control | Proof generation requires authentication |

### 8.2 NIST 800-53

| Control | Mapping |
|---------|---------|
| AU-10 | Non-repudiation via blockchain anchoring |
| AU-11 | Audit record retention (permanent on-chain) |
| SC-28 | Protection of information at rest (hash-only) |

---

## 9. Operational Procedures

### 9.1 Startup Sequence

```python
coordinator = create_anchor_coordinator(
    priority=ChainPriority.XRPL_PRIMARY,
    batch_size=100,
    batch_interval_seconds=300,
)
coordinator.start()  # Connects to both chains
```

### 9.2 Event Anchoring

```python
# Add events as they occur
result = coordinator.add_event(event_hash)
if result:
    print(f"Batch anchored: {result.merkle_root}")

# Periodic time-based check
result = coordinator.check_time_trigger()
```

### 9.3 Graceful Shutdown

```python
coordinator.force_anchor()  # Anchor remaining events
coordinator.stop()  # Disconnect from chains
```

### 9.4 Monitoring Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `anchor_latency_ms` | Time to anchor batch | > 10,000 ms |
| `anchor_failures` | Consecutive failures | > 3 |
| `pending_events` | Events awaiting anchor | > 500 |
| `chain_connected` | Blockchain connectivity | False |

---

## 10. API Reference

### 10.1 AnchorCoordinator

```python
class AnchorCoordinator:
    def start() -> bool
    def stop() -> None
    def add_event(event_hash: str) -> Optional[AnchorResult]
    def anchor(merkle_root: str, event_count: int) -> AnchorResult
    def force_anchor() -> Optional[AnchorResult]
    def verify_anchor(merkle_root: str) -> Tuple[bool, Dict]
    def get_anchor_status() -> AnchorStatus
```

### 10.2 XRPLConnector

```python
class XRPLConnector:
    def connect() -> bool
    def disconnect() -> None
    def anchor_to_xrpl(merkle_root: str) -> TransactionReceipt
    def verify_xrpl_anchor(tx_hash: str, merkle_root: str) -> Tuple[bool, str]
    def get_transaction_proof(tx_hash: str) -> AnchorProof
```

### 10.3 HederaConnector

```python
class HederaConnector:
    def connect() -> bool
    def disconnect() -> None
    def create_topic(memo: str) -> str
    def anchor_to_hedera(merkle_root: str) -> MessageReceipt
    def verify_hedera_anchor(...) -> Tuple[bool, str]
    def get_consensus_timestamp(...) -> ConsensusTimestamp
```

---

## 11. Troubleshooting

### 11.1 Common Issues

| Issue | Cause | Resolution |
|-------|-------|------------|
| `ConnectionError: XRPL` | Network unreachable | Check firewall, use testnet first |
| `InsufficientBalance` | Wallet empty | Fund testnet wallet via faucet |
| `TopicNotFound` | Invalid topic ID | Recreate topic, update config |
| `SignatureInvalid` | Key mismatch | Verify public key distribution |

### 11.2 Debug Mode

```yaml
logging:
  level: DEBUG
  log_transaction_details: true
```

---

## 12. Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-12 | Initial release (PAC-SEC-P822-B) |

---

## 13. References

- [XRP Ledger Documentation](https://xrpl.org/docs.html)
- [Hedera Consensus Service](https://hedera.com/consensus-service)
- [NIST FIPS 204 (ML-DSA)](https://csrc.nist.gov/pubs/fips/204/final)
- [SOC2 Type II AU Controls](https://www.aicpa.org/soc2)
