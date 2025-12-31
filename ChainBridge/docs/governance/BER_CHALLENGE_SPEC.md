# BER Cognitive Friction Challenge Specification

> **Governance Document** — PAC-BENSON-P68-BER-COGNITIVE-FRICTION-CHALLENGE-RESPONSE-01  
> **Version:** 1.0.0  
> **Authority:** BENSON (GID-00)  
> **Status:** CANONICAL  

---

## 1. Purpose

This specification defines the **BER Cognitive Friction Challenge-Response** mechanism for ChainBridge governance. The mechanism ensures that BER approvals require demonstrable cognitive engagement, eliminating "rubber stamp" approval attacks.

**Core Principle:** Approval requires proof of understanding, not just time spent waiting.

---

## 2. Problem Statement

### 2.1 The Rubber Stamp Attack

Doctrine V1.3 introduced minimum review latency (GP-006) requiring 5000ms before BER approval. However, latency alone does not prove engagement:

```
ATTACK VECTOR: Rubber Stamp Bot
1. Receive BER notification
2. Wait 5001ms (pass latency check)
3. Auto-approve without reading
4. RESULT: Governance bypassed
```

### 2.2 Solution: Cognitive Friction

Add a challenge-response gate that requires:
1. **Content-derived questions** — Answers must come from BER data
2. **Randomized challenges** — No pre-computed answers
3. **Timing enforcement** — Still require minimum latency
4. **Proof binding** — Cryptographically bind response to BER

```
DEFENDED FLOW:
1. Receive BER notification
2. Read BER content (required to answer)
3. Answer content-derived question
4. Response + latency bound to proof
5. RESULT: Cognitive engagement verified
```

---

## 3. Challenge Types

### 3.1 Supported Challenge Types

| Type | Question Pattern | Answer Source |
|------|------------------|---------------|
| `TASK_COUNT` | "How many tasks were completed?" | `tasks_completed` count |
| `TASK_RECALL` | "Which task involved [X]?" | Task descriptions |
| `FILE_COUNT` | "How many files were created?" | `files_created` count |
| `FILE_RECALL` | "Which file contains [X]?" | File paths |
| `QUALITY_SCORE` | "What was the quality score?" | `quality_score` value |
| `SCOPE_COMPLIANCE` | "Was scope compliance achieved?" | `scope_compliant` boolean |
| `AGENT_IDENTITY` | "Which agent executed this?" | `agent_name` |
| `AGENT_GID` | "What is the agent's GID?" | `agent_gid` |
| `CONTENT_HASH_PREFIX` | "First 4 chars of hash?" | Hash prefix |

### 3.2 Challenge Selection

Challenges are selected **randomly** from available types based on BER content:

```python
# Secure random selection
available_types = [t for t in ChallengeType if extractable(ber_data, t)]
challenge_type = secrets.choice(available_types)
```

This prevents:
- Pre-computation of answers
- Challenge-type prediction
- Automation of responses

---

## 4. Schema Definitions

### 4.1 BERChallenge

```yaml
BERChallenge:
  challenge_id: "CHAL-{ber_id}-{random_hex}"
  ber_id: "BER-AGENT-Pnn-DESCRIPTION"
  challenge_type: ChallengeType
  question: "Human-readable question"
  correct_answer: "Expected answer (plaintext for validation)"
  correct_answer_hash: "sha256(answer:nonce)"
  nonce: "64-char hex (cryptographically secure)"
  created_at: "ISO-8601 timestamp"
  expires_at: "ISO-8601 timestamp (+5 minutes)"
  used: false  # Anti-replay flag
```

### 4.2 ChallengeResponse

```yaml
ChallengeResponse:
  challenge_id: "CHAL-{ber_id}-{random_hex}"
  response: "User's answer"
  response_hash: "sha256(response)"
  submitted_at: "ISO-8601 timestamp"
  latency_ms: 5500  # Time since challenge creation
```

### 4.3 BERChallengeProof

```yaml
BERChallengeProof:
  proof_id: "PROOF-{ber_id}-{random_hex}"
  ber_id: "BER-AGENT-Pnn-DESCRIPTION"
  challenge_id: "CHAL-{ber_id}-{random_hex}"
  challenge_type: ChallengeType
  question_hash: "sha256(question)"
  response_hash: "sha256(response)"
  latency_ms: 5500
  minimum_latency_met: true  # latency_ms >= 5000
  response_correct: true
  proof_hash: "sha256(proof_data)"  # Tamper-evident
  generated_at: "ISO-8601 timestamp"
  verified_by: "BENSON (GID-00)"
```

### 4.4 BERApprovalResult

```yaml
BERApprovalResult:
  ber_id: "BER-AGENT-Pnn-DESCRIPTION"
  approved: true | false
  proof: BERChallengeProof | null
  error_code: BERChallengeErrorCode | null
  error_message: "Human-readable error" | null
  timestamp: "ISO-8601 timestamp"
```

---

## 5. Error Codes

### 5.1 Challenge Generation Errors (GS_300-309)

| Code | Name | Description |
|------|------|-------------|
| `GS_300` | CHALLENGE_GENERATION_FAILED | Generic challenge creation failure |
| `GS_301` | BER_DATA_INSUFFICIENT | BER lacks data for challenge generation |
| `GS_302` | CHALLENGE_TYPE_INVALID | Unsupported challenge type requested |
| `GS_303` | NONCE_GENERATION_FAILED | Cryptographic nonce generation failed |

### 5.2 Response Validation Errors (GS_310-319)

| Code | Name | Description |
|------|------|-------------|
| `GS_310` | RESPONSE_INCORRECT | Answer does not match expected |
| `GS_311` | RESPONSE_TIMEOUT | Response submitted after timeout |
| `GS_312` | RESPONSE_REPLAY_DETECTED | Challenge already used |
| `GS_313` | RESPONSE_FORMAT_INVALID | Response format invalid |
| `GS_314` | CHALLENGE_EXPIRED | Challenge past expiry time |
| `GS_315` | MINIMUM_LATENCY_NOT_MET | Response too fast (<5000ms) |

### 5.3 Proof Binding Errors (GS_320-329)

| Code | Name | Description |
|------|------|-------------|
| `GS_320` | PROOF_BINDING_FAILED | Could not bind proof to BER |
| `GS_321` | PROOF_HASH_MISMATCH | Proof hash verification failed |
| `GS_322` | PROOF_TAMPERED | Proof integrity check failed |

### 5.4 Approval Errors (GS_330-339)

| Code | Name | Description |
|------|------|-------------|
| `GS_330` | APPROVAL_WITHOUT_CHALLENGE | Attempted approval without challenge |
| `GS_331` | APPROVAL_CHALLENGE_INCOMPLETE | Challenge not fully completed |
| `GS_332` | APPROVAL_UNAUTHORIZED | Approver not authorized |

---

## 6. Validation Flow

### 6.1 Challenge Generation

```
Input: ber_id, ber_data
Output: BERChallenge

1. VERIFY ber_data is non-empty
2. GENERATE cryptographically secure nonce (32 bytes)
3. DETERMINE available challenge types from ber_data
4. SELECT random challenge type (secrets.choice)
5. EXTRACT answer from ber_data for selected type
6. GENERATE question text
7. HASH answer with nonce
8. CREATE BERChallenge object
9. RETURN challenge
```

### 6.2 Response Validation

```
Input: challenge, response, timestamp
Output: (ChallengeResponse, is_correct, error_code)

1. CHECK challenge.used == false (anti-replay)
   → If used: RETURN (response, false, GS_312)
2. CHECK timestamp < challenge.expires_at
   → If expired: RETURN (response, false, GS_314)
3. CALCULATE latency_ms from challenge.created_at
4. NORMALIZE response (strip, uppercase)
5. COMPARE normalized response to challenge.correct_answer
   → If mismatch: RETURN (response, false, GS_310)
6. SET challenge.used = true
7. RETURN (response, true, null)
```

### 6.3 Proof Creation

```
Input: challenge, response, is_correct
Output: BERChallengeProof

1. CHECK minimum_latency_met = (latency_ms >= 5000)
2. GENERATE proof_id
3. COMPUTE question_hash = sha256(question)
4. CREATE BERChallengeProof object
5. COMPUTE proof_hash = sha256(all_proof_fields)
6. RETURN proof
```

### 6.4 Full Approval Flow

```
Input: ber_id, ber_data, response
Output: BERApprovalResult

1. TRY:
   a. GENERATE challenge from ber_data
   b. VALIDATE response against challenge
   c. CREATE proof from challenge + response
   d. CHECK proof.minimum_latency_met
      → If false: RETURN rejected(GS_315)
   e. CHECK proof.response_correct
      → If false: RETURN rejected(GS_310)
   f. RETURN approved(proof)
2. CATCH any error:
   → RETURN rejected(GS_300)  # FAIL_CLOSED
```

---

## 7. Security Properties

### 7.1 Anti-Automation

| Property | Mechanism |
|----------|-----------|
| No pre-computation | Randomized challenge type selection |
| No replay | Single-use challenge flag |
| No timing attack | Minimum latency enforcement |
| No content guessing | Content-derived answers |

### 7.2 Tamper Evidence

| Component | Protection |
|-----------|------------|
| Answer | Hashed with per-challenge nonce |
| Response | SHA-256 hash bound to proof |
| Proof | Self-verifying hash of all fields |

### 7.3 Audit Trail

| Artifact | Purpose |
|----------|---------|
| BERChallenge | Records what was asked |
| ChallengeResponse | Records what was answered |
| BERChallengeProof | Records verification outcome |

---

## 8. Integration Points

### 8.1 BER Review Flow

```
BEFORE (V1.3):
  BER Generated → Wait 5000ms → Approve → WRAP

AFTER (V1.4):
  BER Generated → Present Challenge → Wait for Response
  → Validate Response → If correct + latency met → Approve → WRAP
```

### 8.2 Ledger Integration

Challenge proofs are bound to BER entries:

```yaml
ledger_entry:
  entry_type: "BER_APPROVED"
  artifact_id: "BER-AGENT-Pnn"
  challenge_proof:
    proof_id: "PROOF-BER-xxx"
    proof_hash: "sha256..."
    latency_ms: 5500
    response_correct: true
```

### 8.3 WRAP Integration

WRAP emission requires valid challenge proof:

```yaml
wrap_requirements:
  - ber_generated: true
  - challenge_completed: true
  - proof_valid: true
  - minimum_latency_met: true
```

---

## 9. Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `MINIMUM_REVIEW_LATENCY_MS` | 5000 | Minimum time before response accepted |
| `CHALLENGE_EXPIRY_SECONDS` | 300 | Challenge valid for 5 minutes |
| `NONCE_LENGTH` | 32 bytes | Cryptographic nonce size |

---

## 10. Usage Example

```python
from ber_challenge import (
    generate_ber_challenge,
    approve_ber_with_challenge,
    verify_approval_proof,
)

# Generate challenge for reviewer
ber_data = {
    'agent': 'BENSON',
    'gid': 'GID-00',
    'tasks_completed': 7,
    'quality_score': 1.0,
}

challenge = generate_ber_challenge('BER-BENSON-P68', ber_data)
print(f"Question: {challenge.question}")
# Output: "Which agent executed this PAC?"

# ... reviewer reads BER, answers question after 6 seconds ...

result = approve_ber_with_challenge(
    ber_id='BER-BENSON-P68',
    ber_data=ber_data,
    response='BENSON',
    challenge=challenge
)

if result.approved:
    print(f"Approved! Proof: {result.proof.proof_id}")
    # Bind proof to BER, proceed to WRAP
else:
    print(f"Rejected: {result.error_code} - {result.error_message}")
    # FAIL_CLOSED: No WRAP emission
```

---

## 11. Failure Modes

| Scenario | Outcome | Error Code |
|----------|---------|------------|
| Incorrect answer | Rejected | GS_310 |
| Answer too fast (<5s) | Rejected | GS_315 |
| Challenge expired (>5m) | Rejected | GS_314 |
| Challenge reused | Rejected | GS_312 |
| BER data missing | Generation fails | GS_301 |
| Any unexpected error | Rejected | GS_300 |

**Enforcement Mode:** FAIL_CLOSED — Any error results in rejection.

---

## 12. Lock Declaration

```yaml
BER_CHALLENGE_SPEC_LOCK:
  version: "1.0.0"
  status: "LOCKED"
  enforcement: "PHYSICS"
  override_allowed: false
  bypass_paths: 0
  gold_standard: true
```

---

🟦🟩 **BENSON (GID-00)** — Chief Architect & Orchestrator

