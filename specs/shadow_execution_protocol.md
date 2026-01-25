# SHADOW EXECUTION PROTOCOL v1.0.0

**AUTHORITY:** JEFFREY (GID-CONST-01) Constitutional Architect  
**GOVERNANCE:** LAW-tier (Fail-Closed)  
**IMPLEMENTER:** FORGE (GID-04)  
**DOCTRINE:** Replace-Not-Patch (RNP)

---

## 1. PROTOCOL OVERVIEW

The **Shadow Execution Protocol** enables safe component replacement under the Replace-Not-Patch (RNP) doctrine by verifying behavioral equivalence between current (v1) and replacement (v2) versions.

**Core Principle:**  
*"Before replacing a component, prove the replacement is behaviorally equivalent or explicitly authorize divergences."*

---

## 2. PROTOCOL PHASES

### Phase 1: Shadow Enclave Deployment

**Objective:** Deploy candidate replacement version (v2) alongside current version (v1) in isolated shadow environment.

**Requirements:**
- v2 deployed in isolated namespace/container
- v2 has NO write access to production state
- v2 receives mirrored traffic only (read-only operations)
- Resource limits enforced (CPU, memory, network)

**Deliverable:** Shadow environment operational, v2 receiving mirrored traffic

---

### Phase 2: Traffic Mirroring

**Objective:** Mirror live production inputs to both v1 (live) and v2 (shadow).

**Implementation:**
```python
# Pseudo-code for traffic mirroring
async def handle_request(request):
    # Primary path: Execute on live version (v1)
    live_result = await execute_v1(request)
    
    # Shadow path: Mirror to candidate version (v2) — non-blocking
    asyncio.create_task(mirror_to_shadow(request, live_result))
    
    # Return live result immediately (shadow does not block)
    return live_result

async def mirror_to_shadow(request, expected_output):
    try:
        shadow_result = await execute_v2(request)
        await compare_outputs(expected_output, shadow_result)
    except Exception as e:
        log_shadow_failure(e)  # Shadow failures do not impact live traffic
```

**Invariants:**
- Live traffic (v1) is NEVER blocked by shadow execution
- Shadow failures do NOT impact production availability
- Shadow execution timeout: 2x live execution time (prevent resource exhaustion)

---

### Phase 3: Output Comparison

**Objective:** Compare Output(v1) vs Output(v2) for each mirrored request.

**Comparison Logic:**
```python
from typing import Tuple
from enum import Enum

class ComparisonResult(Enum):
    EXACT_MATCH = "exact_match"
    DIVERGENCE = "divergence"
    SHADOW_TIMEOUT = "shadow_timeout"
    SHADOW_ERROR = "shadow_error"

def compare_outputs(live_output, shadow_output) -> Tuple[ComparisonResult, dict]:
    """
    Compare live and shadow outputs with deep equality check.
    
    Returns:
        (ComparisonResult, divergence_details)
    """
    if live_output == shadow_output:
        return (ComparisonResult.EXACT_MATCH, {})
    
    # Deep comparison with semantic equivalence
    divergence_details = {
        "live_output_hash": hash_output(live_output),
        "shadow_output_hash": hash_output(shadow_output),
        "diff": compute_diff(live_output, shadow_output)
    }
    
    return (ComparisonResult.DIVERGENCE, divergence_details)
```

**Divergence Categories:**
1. **Exact Match:** Output(v1) == Output(v2) (bitwise identical)
2. **Semantic Match:** Outputs differ in irrelevant ways (e.g., timestamp fields)
3. **Authorized Divergence:** Difference explicitly allowed by Migration PAC
4. **Unauthorized Divergence:** Unexpected difference → REJECTION

---

### Phase 4: Divergence Adjudication

**Objective:** Determine if divergences are acceptable.

**Acceptance Criteria:**

| Divergence Type | Approval Condition | Authority |
|-----------------|-------------------|-----------|
| **Zero Divergence** | Automatic approval | N/A |
| **Authorized Divergence** | Migration PAC exists | JEFFREY (LAW-tier) |
| **Unauthorized Divergence** | REJECTION | Semantic Judge |

**Migration PAC Requirements:**
- Must pre-authorize specific divergence patterns (e.g., "new field: transaction_id")
- Must specify expected divergence percentage (e.g., "100% of requests will include new field")
- Must be signed by JEFFREY (GID-CONST-01) or ALEX (GID-08)

**Example Migration PAC:**
```xml
<migration_authorization>
  <pac_id>PAC-MIGRATE-PAYMENT-PROCESSOR-V2</pac_id>
  <component>payment_processor</component>
  <live_version>v1.5.2</live_version>
  <shadow_version>v2.0.0</shadow_version>
  
  <authorized_divergences>
    <divergence>
      <field>transaction_id</field>
      <reason>v2.0.0 introduces UUIDv4 transaction IDs</reason>
      <expected_percentage>100.0</expected_percentage>
    </divergence>
    <divergence>
      <field>timestamp_format</field>
      <reason>v2.0.0 uses ISO 8601 instead of Unix epoch</reason>
      <expected_percentage>100.0</expected_percentage>
    </divergence>
  </authorized_divergences>
  
  <issuing_authority>
    <agent_gid>GID-CONST-01</agent_gid>
    <signature>...</signature>
  </issuing_authority>
</migration_authorization>
```

---

### Phase 5: Replacement Decision

**Objective:** Semantic Judge adjudicates replacement approval.

**Decision Logic:**
```python
def adjudicate_replacement(shadow_result: ShadowExecutionResult) -> JudgmentState:
    """
    Determine if shadow version is approved for replacement.
    
    APPROVAL CONDITIONS:
    1. divergence_percentage == 0.0 (perfect match), OR
    2. All divergences are authorized by Migration PAC
    """
    if shadow_result.divergence_percentage == 0.0:
        return JudgmentState.APPROVED
    
    if shadow_result.outputs_diverged == shadow_result.authorized_divergences:
        return JudgmentState.APPROVED
    
    return JudgmentState.REJECTED
```

**Replacement Workflow:**
```
IF JudgmentState == APPROVED:
    1. Execute RNP vaporization protocol (kill v1)
    2. Promote v2 to production
    3. Generate BER confirming replacement
    4. Archive v1 container image (retain for 90 days)

ELSE:
    1. REJECT replacement
    2. Terminate shadow environment
    3. Generate incident report
    4. Escalate to JEFFREY for review
```

---

## 3. METRICS AND REPORTING

### Required Metrics

**Per Shadow Execution:**
- Total requests mirrored: `total_requests_mirrored`
- Exact matches: `outputs_matched`
- Divergences: `outputs_diverged`
- Shadow timeouts: `shadow_timeouts`
- Shadow errors: `shadow_errors`

**Aggregate Metrics (for Replacement Decision):**
- Divergence percentage: `(outputs_diverged / total_requests_mirrored) * 100`
- Authorized divergence percentage: `(authorized_divergences / outputs_diverged) * 100`
- Shadow error rate: `(shadow_errors / total_requests_mirrored) * 100`

**Thresholds for Approval:**
```python
APPROVAL_THRESHOLDS = {
    "divergence_percentage": 0.0,  # Zero unauthorized divergences
    "shadow_error_rate": 0.1,      # Max 0.1% shadow errors (reliability check)
    "minimum_samples": 10000,      # Minimum mirrored requests for statistical significance
}
```

---

## 4. SHADOW EXECUTION EXAMPLE

### Scenario: Payment Processor Replacement

**Current Version (v1):**
```python
# v1: payment_processor_v1.py
def process_payment(amount: float, currency: str) -> dict:
    return {
        "status": "success",
        "amount": amount,
        "currency": currency,
        "timestamp": int(time.time())  # Unix epoch
    }
```

**Candidate Version (v2):**
```python
# v2: payment_processor_v2.py
import uuid
from datetime import datetime

def process_payment(amount: float, currency: str) -> dict:
    return {
        "status": "success",
        "amount": amount,
        "currency": currency,
        "transaction_id": str(uuid.uuid4()),  # NEW FIELD
        "timestamp": datetime.utcnow().isoformat()  # CHANGED FORMAT
    }
```

**Expected Divergences (Authorized by Migration PAC):**
1. New field: `transaction_id` (100% of requests)
2. Changed field: `timestamp` format (100% of requests)

**Shadow Execution Result:**
```json
{
  "shadow_id": "SHADOW-A1B2C3D4E5F6G7H8",
  "component_name": "payment_processor",
  "live_version": "v1.5.2",
  "shadow_version": "v2.0.0",
  "total_requests_mirrored": 50000,
  "outputs_matched": 0,
  "outputs_diverged": 50000,
  "divergence_percentage": 100.0,
  "authorized_divergences": 50000,
  "replacement_approved": true,
  "migration_pac_reference": "PAC-MIGRATE-PAYMENT-PROCESSOR-V2"
}
```

**Judgment:** **APPROVED** (all divergences authorized by Migration PAC)

---

## 5. FAILURE MODES AND HANDLING

### Failure Mode 1: Unauthorized Divergence

**Symptom:** Shadow outputs differ from live outputs in unexpected ways.

**Response:**
1. REJECT replacement immediately
2. Terminate shadow environment
3. Generate incident report with divergence examples
4. Escalate to JEFFREY for constitutional review

**Example:**
```json
{
  "failure_type": "unauthorized_divergence",
  "divergence_percentage": 15.2,
  "authorized_divergences": 0,
  "sample_divergence": {
    "live_output": {"status": "success", "amount": 100.00},
    "shadow_output": {"status": "error", "amount": 100.00}
  },
  "judgment": "REJECTED",
  "escalation": "JEFFREY (GID-CONST-01)"
}
```

---

### Failure Mode 2: Shadow Performance Degradation

**Symptom:** Shadow version (v2) executes slower than live version (v1).

**Response:**
1. Monitor shadow execution time vs. live execution time
2. If shadow_time > 2x live_time for >5% of requests → PERFORMANCE_DEGRADATION flag
3. REJECT replacement if performance regression detected
4. Optimization required before re-submission

**Threshold:**
```python
PERFORMANCE_THRESHOLD = {
    "max_shadow_latency_multiplier": 2.0,
    "max_degraded_requests_percentage": 5.0
}
```

---

### Failure Mode 3: Shadow Resource Exhaustion

**Symptom:** Shadow environment consumes excessive resources (CPU, memory, network).

**Response:**
1. Enforce resource limits on shadow environment (Kubernetes resource quotas)
2. If shadow exceeds limits → RESOURCE_EXHAUSTION flag
3. Terminate shadow execution gracefully
4. REJECT replacement, require resource optimization

**Resource Limits:**
```yaml
# Kubernetes PodSpec for shadow environment
resources:
  limits:
    cpu: "2"          # Max 2 CPU cores
    memory: "4Gi"     # Max 4GB RAM
  requests:
    cpu: "1"          # Request 1 CPU core
    memory: "2Gi"     # Request 2GB RAM
```

---

## 6. INTEGRATION WITH TEST GOVERNANCE LAYER

**Shadow Execution → TestExecutionManifest:**

After shadow execution completes, generate a `TestExecutionManifest` for the replacement:

```python
manifest = TestExecutionManifest(
    manifest_id=str(uuid.uuid4()),
    git_commit_hash=get_v2_commit_hash(),
    agent_gid="GID-04",  # FORGE
    tests_executed=shadow_result.total_requests_mirrored,
    tests_passed=shadow_result.outputs_matched + shadow_result.authorized_divergences,
    tests_failed=shadow_result.outputs_diverged - shadow_result.authorized_divergences,
    coverage=CoverageMetrics(
        line_coverage=get_code_coverage(),
        branch_coverage=get_branch_coverage(),
        mcdc_percentage=100.0  # Must be verified separately
    ),
    merkle_root=compute_merkle_root_of_shadow_logs(),
    signature=sign_manifest(manifest_data)
)

# Submit to Semantic Judge
judgment = semantic_judge.adjudicate(manifest)

if judgment == JudgmentState.APPROVED:
    execute_rnp_replacement(v1, v2)
else:
    reject_replacement()
```

---

## 7. CONSTITUTIONAL ATTESTATION

**ATTESTATION:**

*"This protocol embodies the Replace-Not-Patch doctrine. Components are not patched; they are replaced. But replacement is not blind faith—it is empirical proof.*

*The Shadow Execution Protocol requires candidates to prove behavioral equivalence before assuming production authority. Divergence is permitted only with explicit authorization.*

*This is the Law of Safe Replacement."*

— **JEFFREY (GID-CONST-01), Constitutional Architect**  
— **2026-01-25**

---

## 8. REFERENCES

- **Test Governance Layer (TGL):** `core/governance/test_governance_layer.py`
- **Semantic Judge Specification:** `specs/semantic_judge.tla`
- **Replace-Not-Patch Doctrine:** `docs/RNP_DOCTRINE.md`
- **PAC-OPS-P810-RNP-SWARM-DRILL:** `active_pacs/PAC-OPS-P810-RNP-SWARM-DRILL.xml`

---

**END SHADOW EXECUTION PROTOCOL v1.0.0**
