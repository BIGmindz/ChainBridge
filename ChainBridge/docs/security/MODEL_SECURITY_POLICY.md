# ChainIQ ML Model Security Policy

**Author:** SAM (GID-06) — Security & Threat Engineer
**Date:** 2025-12-11
**Version:** 2.0-PQC
**Status:** ENFORCED
**Policy ID:** PAC-SAM-SEC-018

---

## Executive Summary

This policy establishes security requirements for all ML model artifacts in ChainBridge's ChainIQ system. All models must be cryptographically signed using **SHA256 + PQC Kyber hybrid signatures** and verified before deployment to production.

**CRITICAL REQUIREMENTS:**
- NO MODEL SHALL BE LOADED IN PRODUCTION WITHOUT SIGNATURE VERIFICATION
- ALL UNSIGNED OR MODIFIED MODELS → AUTOMATIC QUARANTINE
- POST-QUANTUM CRYPTOGRAPHY (ML-KEM-768) FOR FUTURE-PROOF PROTECTION

---

## Threat Model

### Primary Threats

| Threat | Risk Level | Mitigation |
|--------|-----------|------------|
| **Model Poisoning** | CRITICAL | SHA256 + PQC hybrid signature verification |
| **Shadow Mode Corruption** | HIGH | Advanced anomaly detection heuristics |
| **Adversarial Inputs** | HIGH | Input validation (separate module) |
| **Malware-Embedded Pickle** | CRITICAL | Pickle import inspection + magic byte validation |
| **Supply Chain Attacks** | HIGH | Dependency version tracking + chain of trust |
| **Model Integrity Failure** | HIGH | Automated CI integrity checks |
| **Unauthorized Model Swapping** | CRITICAL | Signature enforcement + quarantine |
| **Harvest-Now-Decrypt-Later** | HIGH | **PQC ML-KEM-768 quantum-resistant signatures** |

### Attack Vectors

1. **Direct File Replacement**: Attacker replaces `.pkl` file with poisoned model
2. **Man-in-the-Middle**: Model intercepted during transfer/download
3. **Insider Threat**: Malicious employee uploads compromised model
4. **Dependency Confusion**: Compromised sklearn/numpy packages
5. **Pickle Deserialization**: Malicious code executed via pickle exploit
6. **Quantum Computing Attack**: Future quantum decryption of classical signatures

---

## Security Architecture

### Component Overview (v2.0-PQC)

```
┌─────────────────────────────────────────────────────────────┐
│           ML Model Security Layer v2.0-PQC                  │
│              SAM (GID-06) / PAC-SAM-SEC-018                 │
└─────────────────────────────────────────────────────────────┘
                              │
     ┌────────────────────────┼────────────────────────┐
     │                        │                        │
     ▼                        ▼                        ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   SHA256 +   │    │   Anomaly    │    │  Quarantine  │
│   PQC Kyber  │    │  Detection   │    │    Mode      │
│   Signing    │    │   Engine     │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
     │                        │                        │
     │                        │                        │
     ▼                        ▼                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Chain of Trust Verification                     │
│   Policy: PAC-SAM-SEC-018 | Trust Level: VERIFIED           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Secure Model Storage                            │
│         .chainbridge/models/ (signed artifacts)             │
│      .chainbridge/quarantine/ (suspicious models)           │
└─────────────────────────────────────────────────────────────┘
```

---

## Post-Quantum Cryptography (PQC) Implementation

### Why PQC?

**Harvest-Now-Decrypt-Later (HNDL) Attack:**
- Adversaries collect encrypted/signed data today
- Store it until quantum computers become available
- Decrypt using Shor's algorithm (breaks RSA, ECC)
- ML models could be stolen/replaced retroactively

**Our Solution:** Hybrid SHA256 + ML-KEM-768 (Kyber) signatures

### PQC Algorithm: ML-KEM-768

| Property | Value |
|----------|-------|
| **Algorithm** | ML-KEM-768 (NIST FIPS 203) |
| **Previous Name** | Kyber768 |
| **Security Level** | NIST Level 3 (AES-192 equivalent) |
| **Public Key Size** | 1,184 bytes |
| **Ciphertext Size** | 1,088 bytes |
| **Shared Secret** | 32 bytes |

### Hybrid Signature Format

```json
{
  "signature_version": "2.0-PQC",
  "sha256": "a3f5d8c9e2b1f4a7d6e8c3b9f1a2d5e8...",
  "pqc": {
    "enabled": true,
    "algorithm": "SHA256+ML-KEM-768",
    "variant": "ML-KEM-768",
    "ciphertext": "<base64-encoded-kyber-ciphertext>",
    "mac": "<hmac-sha256-with-pqc-shared-secret>",
    "public_key": "<base64-encoded-public-key>"
  },
  "chain_of_trust": {
    "signer": "SAM-GID-06",
    "policy": "PAC-SAM-SEC-018",
    "trust_level": "VERIFIED"
  }
}
```

### PQC Graceful Degradation

If PQC libraries (liboqs) are not installed:
1. System falls back to SHA256-only signatures
2. Warning logged: "PQC libraries not available"
3. Classical security maintained
4. Upgrade path preserved

---

## Model Lifecycle Requirements

### 1. Model Training (Maggie/Cody)

**Requirements:**
- Record training environment details:
  - scikit-learn version
  - NumPy version
  - Training date/time
  - Training dataset hash (optional)
- Save model to temporary location first
- Do NOT deploy directly to production

**Example:**
```python
from app.ml.training_v02 import train_ml_models_v02

# Train models
train_ml_models_v02(
    save_models=True,
    output_dir="ml_models"
)

# Models saved to:
# - ml_models/risk_v0.2.0.pkl
# - ml_models/anomaly_v0.2.0.pkl
```

---

### 2. Model Signing (REQUIRED)

**Who:** Security Engineer (SAM) or automated CI pipeline
**When:** Immediately after training, before deployment
**Where:** On secure build server or developer workstation

**Process:**

```bash
# Sign risk model
python3 -m app.ml.model_security sign \
  ChainBridge/chainiq-service/app/ml/models/risk_model_v0.2.pkl \
  --model-name "risk_model" \
  --model-version "v0.2.0" \
  --sklearn-version "1.3.0" \
  --numpy-version "1.24.3"

# Sign anomaly model
python3 -m app.ml.model_security sign \
  ml_models/anomaly_v0.2.0.pkl \
  --model-name "anomaly_model" \
  --model-version "v0.2.0" \
  --sklearn-version "1.3.0" \
  --numpy-version "1.24.3"
```

**Output:**
- `risk_model_v0.2.pkl.sig.json` - Signature metadata
- SHA256 hash recorded in signature file

**Signature File Format:**
```json
{
  "signature_version": "1.0",
  "model_name": "risk_model",
  "model_version": "v0.2.0",
  "sha256": "a3f5d8c9e2b1f4a7d6e8c3b9f1a2d5e8...",
  "file_size_mb": 1.623,
  "signed_at": "2025-12-11T14:32:00Z",
  "signed_by": "SAM-GID-06-ModelSecurityManager",
  "training_date": "2025-12-11",
  "dependencies": {
    "sklearn": "1.3.0",
    "numpy": "1.24.3"
  }
}
```

---

### 3. Model Deployment

**Requirements:**
- Model and signature files MUST be deployed together
- Model MUST be placed in secure storage: `.chainbridge/models/`
- Deployment script MUST verify signature before activation

**Deployment Process:**

```bash
# 1. Copy model + signature to secure storage
cp ml_models/risk_v0.2.0.pkl .chainbridge/models/
cp ml_models/risk_v0.2.0.pkl.sig.json .chainbridge/models/

# 2. Verify integrity
python3 -m app.ml.model_security verify \
  .chainbridge/models/risk_v0.2.0.pkl

# 3. Inspect for threats
python3 -m app.ml.model_security inspect \
  .chainbridge/models/risk_v0.2.0.pkl

# 4. Only if all checks pass, activate for production
ln -sf .chainbridge/models/risk_v0.2.0.pkl \
       ChainBridge/chainiq-service/app/ml/models/risk_model_v0.2.pkl
```

**Automated Deployment (CI/CD):**
See `.github/workflows/model-integrity-check.yml`

---

### 4. Model Loading (Runtime)

**Who:** ChainIQ API (via Cody's `load_real_risk_model_v02()`)
**When:** On-demand (lazy loading)
**Where:** Production API server

**Security Enforcement:**

The model loader now automatically:
1. ✓ Verifies SHA256 signature
2. ✓ Detects size anomalies
3. ✓ Inspects pickle for dangerous imports
4. ✓ Quarantines suspicious models
5. ✓ Logs all security events

**Code Example:**
```python
from app.ml.training_v02 import load_real_risk_model_v02

# Secure loading with automatic verification
model = load_real_risk_model_v02()

if model is None:
    # Model failed security checks or not found
    # Shadow mode automatically disabled
    pass
```

**IMPORTANT:** Direct pickle.load() is FORBIDDEN. Always use `load_verified_model()`.

---

## Threat Detection Heuristics

### Automated Checks

| Check | Threshold | Action |
|-------|-----------|--------|
| **File Size** | > 50 MB | WARNING |
| **Missing Signature** | N/A | QUARANTINE |
| **Signature Mismatch** | N/A | QUARANTINE |
| **Unknown Dependencies** | N/A | WARNING |
| **Suspicious Imports** | Any dangerous module | QUARANTINE |
| **Pickle Inspection Fail** | N/A | WARNING |

### Dangerous Imports (Auto-Detected)

The following imports in pickle files trigger quarantine:
- `os`, `sys`, `subprocess` — System access
- `socket`, `urllib`, `requests` — Network access
- `eval`, `exec`, `compile` — Code execution
- `__builtin__` — Python internals

**Example Detection:**
```
⚠️  Threats detected in ml_models/risk_v0.2.0.pkl:
   - SUSPICIOUS_IMPORTS: os.system, subprocess.call
   - SIZE_ANOMALY: Model size 78.3MB exceeds threshold 50MB

✗ Model QUARANTINED to .chainbridge/quarantine/
```

---

## Model Quarantine Protocol

### When Quarantine Triggers

1. Signature verification fails
2. Critical threats detected (size, imports)
3. Metadata tampering detected
4. Failed to load/deserialize

### Quarantine Process

1. **Immediate Isolation:**
   - Model moved to `.chainbridge/quarantine/`
   - Timestamped: `risk_model_v0.2_20251211_143200.pkl`

2. **Incident Report Generated:**
   - `risk_model_v0.2_20251211_143200.quarantine.json`
   - Contains: original path, timestamp, reason, operator

3. **Production Impact:**
   - `load_real_risk_model_v02()` returns `None`
   - Shadow mode automatically disabled
   - Alert logged to security monitoring

4. **Recovery:**
   - Security team notified
   - Model re-trained if necessary
   - New signature generated
   - Re-deployment after review

**Example Quarantine Report:**
```json
{
  "original_path": "ChainBridge/chainiq-service/app/ml/models/risk_model_v0.2.pkl",
  "quarantined_at": "2025-12-11T14:32:00Z",
  "reason": "Signature verification failed: SHA256 mismatch",
  "quarantined_by": "SAM-GID-06-ModelSecurityManager"
}
```

---

## Integration Points

### Cody (Training Module)

**File:** `ChainBridge/chainiq-service/app/ml/training_v02.py`

**Changes Made:**
- ✓ `load_real_risk_model_v02()` now uses `ModelSecurityManager`
- ✓ Automatic signature verification on load
- ✓ Graceful fallback if security fails
- ✓ No performance impact (lazy loading preserved)

**Responsibilities:**
- Call `ModelSecurityManager.sign_model()` after training
- Include sklearn/numpy versions in metadata

---

### Maggie (Prediction API)

**File:** `ChainBridge/chainiq-service/app/api_iq_ml.py`

**Integration:**
```python
from app.ml.training_v02 import load_real_risk_model_v02

# Shadow mode with automatic security checks
real_model = load_real_risk_model_v02()

if real_model is None:
    # Security failure or model not found
    # Use mock model only
    pass
```

**No changes required** — security is transparent.

---

### CI/CD Pipeline

**File:** `.github/workflows/model-integrity-check.yml` (to be created)

**Requirements:**
- Run on every PR that modifies `.pkl` files
- Run nightly on production models
- Block merge if integrity fails
- Report security violations to #security-alerts

---

## Security Best Practices

### For Data Scientists (Cody/Maggie)

1. **Never commit `.pkl` files without signatures**
2. **Always sign models immediately after training**
3. **Record dependency versions** (sklearn, numpy)
4. **Test models in development environment first**
5. **Never use `pickle.load()` directly** — use `load_verified_model()`

### For DevOps/SRE

1. **Verify signatures before deployment**
2. **Check quarantine directory regularly**
3. **Monitor security logs for anomalies**
4. **Rotate model keys/signatures periodically**
5. **Backup signature files with models**

### For Security Team (SAM)

1. **Audit model signatures weekly**
2. **Review quarantine incidents**
3. **Update threat detection rules**
4. **Maintain signature key security**
5. **Coordinate with Cody/Maggie on security updates**

---

## Incident Response

### Level 1: Unsigned Model Detected

**Severity:** MEDIUM
**Action:**
- Block deployment
- Notify model owner (Cody/Maggie)
- Sign model properly
- Re-deploy

**Timeline:** 1 hour

---

### Level 2: Signature Mismatch

**Severity:** HIGH
**Action:**
- QUARANTINE immediately
- Alert security team (SAM)
- Investigate tampering
- Review access logs
- Re-train if necessary

**Timeline:** 4 hours

---

### Level 3: Malicious Imports Detected

**Severity:** CRITICAL
**Action:**
- QUARANTINE immediately
- Disable shadow mode
- Full security audit
- Review all recent model deployments
- Forensic analysis
- Incident report to leadership

**Timeline:** 24 hours

---

## Compliance & Auditing

### Security Audit Log

All model security events are logged:

```
2025-12-11 14:32:00 [INFO] ✓ Signed model: risk_model_v0.2.pkl
2025-12-11 14:33:15 [INFO] ✓ Model signature verified: risk_model_v0.2.pkl
2025-12-11 14:35:22 [ERROR] ⚠️  MODEL SECURITY VIOLATION: Signature mismatch
2025-12-11 14:35:23 [ERROR] ⚠️  QUARANTINED: risk_model_v0.2.pkl
```

**Log Location:** `logs/model_security.log`

### Monthly Security Review

SAM (GID-06) conducts monthly reviews:
- ✓ All production models have valid signatures
- ✓ No quarantine incidents unresolved
- ✓ Dependency versions up to date
- ✓ Threat detection rules effective

---

## Tools & Commands

### Sign a Model

```bash
python3 -m app.ml.model_security sign <model.pkl> \
  --model-name <name> \
  --model-version <version> \
  --sklearn-version <version> \
  --numpy-version <version>
```

### Verify a Model

```bash
python3 -m app.ml.model_security verify <model.pkl>
```

### Inspect for Threats

```bash
python3 -m app.ml.model_security inspect <model.pkl>
```

### Load Securely (Python)

```python
from app.ml.model_security import ModelSecurityManager

manager = ModelSecurityManager()
model = manager.load_verified_model(Path("model.pkl"))
```

---

## References

- [OWASP ML Security Top 10](https://owasp.org/www-project-machine-learning-security-top-10/)
- [Adversarial ML Threat Matrix](https://github.com/mitre/advmlthreatmatrix)
- [Python Pickle Security](https://docs.python.org/3/library/pickle.html#restricting-globals)
- [ChainIQ ML Lifecycle Governance](../governance/ML_LIFECYCLE_GOVERNANCE.md)

---

## Contact

**Security Issues:**
SAM (GID-06) — Security & Threat Engineer
Email: security@chainbridge.io
Slack: #security-alerts

**Model Training:**
Cody (GID-03) — ML Engineer
Maggie (GID-04) — Prediction API Engineer

---

## Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-11 | SAM (GID-06) | Initial security policy |

---

**END OF POLICY**

🔒 This document is part of ChainBridge's ML Security Framework
Maintained by SAM (GID-06) — Security & Threat Engineer
