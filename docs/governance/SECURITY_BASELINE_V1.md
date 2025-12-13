# ChainBridge Security Baseline v1.0
**Governance ID: GID-08-SEC | Classification: CRITICAL | Co-Authors: ALEX (GID-08) + Sam (GID-06)**

## Executive Summary

This document establishes the **security baseline** for ChainBridge as a financial-grade event settlement platform. It defines encryption standards, authentication policies, secrets management, and internal controls aligned with SOC2 and SOX-lite requirements.

**Core Principle:**
> "Security by design, quantum-ready by default, zero-trust by architecture."

---

## 1. CRYPTOGRAPHIC POSTURE

### 1.1 Post-Quantum Cryptography (PQC) Strategy

**Status: TRANSITION TO PQC (2025-2026)**

| Cryptographic Function | Classical (Deprecated) | PQC (Required) | Migration Deadline |
|------------------------|------------------------|----------------|-------------------|
| **Digital Signatures** | RSA-2048, ECDSA | SPHINCS+, Dilithium-3 | Q2 2026 |
| **Key Exchange** | DH, ECDH | Kyber-768, Kyber-1024 | Q2 2026 |
| **Encryption** | AES-256 (maintained) | AES-256 + Kyber KEM | Q3 2026 |
| **Hashing** | SHA-256 (quantum-resistant) | SHA-256, SHA-3 | N/A (already safe) |

**Migration Plan:**

```
Q1 2026:
- All new code must use PQC primitives
- Begin PQC library integration (liboqs, pqcrypto)
- Update ChainPay token signatures to SPHINCS+

Q2 2026:
- Migrate all authentication to Dilithium-3
- Replace RSA/ECDSA in existing systems
- Dual-signature mode (classical + PQC)

Q3 2026:
- Complete settlement encryption with Kyber
- Deprecate all RSA/ECDSA usage
- PQC-only mode for new deployments

Q4 2026:
- Remove classical cryptography support
- Full PQC compliance
- Security audit and certification
```

### 1.2 Prohibited Cryptographic Primitives

**ALEX blocks these in all code:**

```python
# ❌ BLOCKED (quantum-vulnerable)
from cryptography.hazmat.primitives.asymmetric import rsa, dsa, ec
from Crypto.PublicKey import RSA, DSA
import ecdsa

# ✅ ALLOWED (quantum-resistant)
from pqcrypto.sign import sphincsplus, dilithium
from pqcrypto.kem import kyber
from hashlib import sha256, sha3_256
```

### 1.3 Key Management

**All cryptographic keys must follow strict lifecycle:**

| Phase | Requirements | Responsible Agent |
|-------|-------------|------------------|
| **Generation** | Use PQC-safe random (urandom, secrets module) | System |
| **Storage** | Encrypted at rest (AWS KMS, HashiCorp Vault) | DevOps (Dan) |
| **Rotation** | Every 90 days (automated) | DevOps (Dan) |
| **Revocation** | Immediate on compromise | Security (Sam) |
| **Audit** | All key operations logged | ALEX |

---

## 2. API AUTHENTICATION & AUTHORIZATION

### 2.1 Authentication Methods

**Allowed authentication mechanisms:**

| Method | Use Case | Security Level |
|--------|----------|----------------|
| **OAuth 2.0 + PKCE** | External integrations | High |
| **JWT with PQC signatures** | Internal services | High |
| **API keys (time-limited)** | M2M communication | Medium |
| **mTLS (mutual TLS)** | Service-to-service | Very High |

**Prohibited:**
- ❌ Basic Auth over HTTP
- ❌ Long-lived API keys (> 90 days)
- ❌ Passwords in configuration files
- ❌ Tokens without expiration

### 2.2 JWT Standards

**All JWTs must follow:**

```python
# JWT structure
jwt_payload = {
    "sub": "user_id_or_service_id",
    "iss": "chainbridge.io",
    "aud": "chainiq-service",
    "iat": 1702296000,  # Issued at
    "exp": 1702299600,  # Expires in 1 hour
    "scope": ["read:shipments", "write:settlements"],
    "jti": "unique_jwt_id"  # JWT ID for revocation
}

# Signature algorithm (PQC)
signature_algorithm = "DILITHIUM3"  # Post-quantum

# ❌ BLOCKED
signature_algorithm = "RS256"  # RSA (quantum-vulnerable)
signature_algorithm = "ES256"  # ECDSA (quantum-vulnerable)
```

### 2.3 Authorization Model

**Role-Based Access Control (RBAC):**

| Role | Permissions | Services |
|------|-------------|----------|
| **Admin** | All operations | All |
| **Analyst** | Read-only | ChainIQ, ChainBoard |
| **Operator** | Settlement execution | ChainPay |
| **Auditor** | Read-only + logs | All |
| **Service** | Specific scope | Defined in JWT |

---

## 3. SECRETS MANAGEMENT

### 3.1 Secrets Storage

**All secrets must be stored securely:**

| Secret Type | Storage Location | Rotation |
|-------------|------------------|----------|
| **Database credentials** | AWS Secrets Manager | 90 days |
| **API keys** | HashiCorp Vault | 90 days |
| **Encryption keys** | AWS KMS | 90 days |
| **TLS certificates** | AWS Certificate Manager | 365 days |
| **PQC keys** | Hardware Security Module (HSM) | 90 days |

**Prohibited:**
- ❌ Secrets in source code
- ❌ Secrets in environment variables (production)
- ❌ Secrets in Docker images
- ❌ Secrets in configuration files committed to Git

### 3.2 Secrets Rotation

**Automated rotation schedule:**

```yaml
# scripts/security/rotate_secrets.sh
rotation_schedule:
  database_credentials:
    interval: 90_days
    services: [chainiq, chainpay, chainboard]

  api_keys:
    interval: 90_days
    services: [external_integrations]

  jwt_signing_keys:
    interval: 30_days
    services: [all]

  pqc_signing_keys:
    interval: 90_days
    services: [chainpay, chainiq]
```

---

## 4. DATABASE SECURITY

### 4.1 Encryption

**All databases must use:**

| Layer | Encryption | Key Management |
|-------|------------|----------------|
| **At Rest** | AES-256 | AWS KMS |
| **In Transit** | TLS 1.3 | Let's Encrypt + PQC migration |
| **Column-Level** | AES-256 (sensitive columns) | Application-managed |

**Sensitive columns requiring encryption:**

```python
# chainiq-service/app/models/shipment.py
class Shipment(CanonicalBaseModel):
    __tablename__ = 'shipments'

    # Plain text (searchable)
    shipment_id = Column(String, nullable=False)
    status = Column(String, nullable=False)

    # Encrypted (sensitive)
    shipper_tax_id = Column(EncryptedString, nullable=True)  # SSN/EIN
    carrier_tax_id = Column(EncryptedString, nullable=True)
    financial_terms = Column(EncryptedJSON, nullable=True)
    collateral_details = Column(EncryptedJSON, nullable=True)
```

### 4.2 Access Control

**Database access restricted to:**

- Application service accounts (least privilege)
- DBA accounts (MFA required)
- Read-only replica for analytics
- Auditor read-only access

**Prohibited:**
- ❌ Direct database access from developer machines
- ❌ Shared database credentials
- ❌ Root/superuser access in production

---

## 5. NETWORK SECURITY

### 5.1 Zero-Trust Architecture

**All inter-service communication:**

- ✅ Mutual TLS (mTLS)
- ✅ Service mesh (Istio or Linkerd)
- ✅ Network policies (deny by default)
- ✅ Egress filtering (allow-list only)

**No implicit trust:**

```yaml
# k8s/network-policies/chainiq-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: chainiq-service-policy
spec:
  podSelector:
    matchLabels:
      app: chainiq-service
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
      - podSelector:
          matchLabels:
            app: api-gateway
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
      - podSelector:
          matchLabels:
            app: postgres
      ports:
        - protocol: TCP
          port: 5432
```

### 5.2 Firewall Rules

**Default deny, explicit allow:**

| Source | Destination | Port | Protocol | Status |
|--------|-------------|------|----------|--------|
| Internet | API Gateway | 443 | HTTPS | ✅ Allowed |
| API Gateway | ChainIQ | 8000 | HTTP/mTLS | ✅ Allowed |
| ChainIQ | PostgreSQL | 5432 | PostgreSQL/TLS | ✅ Allowed |
| ChainIQ | Internet | * | * | ❌ Blocked |

---

## 6. LOGGING & MONITORING

### 6.1 Security Event Logging

**All security events must be logged:**

```python
# Security event types
SECURITY_EVENTS = [
    "AUTHENTICATION_SUCCESS",
    "AUTHENTICATION_FAILURE",
    "AUTHORIZATION_DENIED",
    "API_KEY_CREATED",
    "API_KEY_REVOKED",
    "SECRET_ACCESSED",
    "ENCRYPTION_KEY_ROTATED",
    "SETTLEMENT_EXECUTED",
    "GOVERNANCE_VIOLATION",
    "ADMIN_ACTION"
]

# Logging format
security_log = {
    "timestamp": "2025-12-11T10:30:00Z",
    "event": "AUTHENTICATION_FAILURE",
    "user_id": "user_123",
    "ip_address": "203.0.113.42",
    "service": "chainiq-service",
    "details": {"reason": "Invalid JWT signature"},
    "severity": "MEDIUM"
}
```

### 6.2 Centralized Logging

**All logs forwarded to:**

- ELK Stack (Elasticsearch, Logstash, Kibana)
- CloudWatch Logs (AWS)
- Splunk (enterprise customers)

**Retention:**
- Security logs: 7 years
- Application logs: 1 year
- Debug logs: 30 days

### 6.3 Alerting Rules

```yaml
alerts:
  - name: "Multiple Failed Auth Attempts"
    condition: "authentication_failure_count > 5 in 5 minutes"
    action: "Block IP + alert security team"

  - name: "Unauthorized Admin Action"
    condition: "admin_action from non_admin_role"
    action: "Page security on-call + lock account"

  - name: "Encryption Key Access Anomaly"
    condition: "encryption_key_accessed from unusual_service"
    action: "Alert security team + audit logs"

  - name: "Governance Violation"
    condition: "alex_governance_violation detected"
    action: "Block PR + alert ALEX + notify Benson"
```

---

## 7. VULNERABILITY MANAGEMENT

### 7.1 Dependency Scanning

**Automated scanning (CI/CD):**

- Snyk (Python dependencies)
- npm audit (Node.js dependencies)
- Trivy (Docker images)
- OWASP Dependency-Check

**Frequency:**
- Every commit (CI pipeline)
- Daily scheduled scans
- Weekly comprehensive reports

**Action on vulnerabilities:**

| Severity | Action | Timeline |
|----------|--------|----------|
| **CRITICAL** | Immediate patch or hotfix | 24 hours |
| **HIGH** | Priority patch in next sprint | 7 days |
| **MEDIUM** | Patch in regular release | 30 days |
| **LOW** | Review and decide | 90 days |

### 7.2 Penetration Testing

**Schedule:**
- Quarterly internal pen-tests
- Annual external pen-tests
- Continuous automated scanning

---

## 8. DATA PROTECTION

### 8.1 Data Classification

| Classification | Examples | Protection |
|----------------|----------|------------|
| **CRITICAL** | Settlement amounts, signatures | Encrypted + audited |
| **SENSITIVE** | Tax IDs, financial terms | Encrypted |
| **INTERNAL** | Risk scores, shipment data | Access-controlled |
| **PUBLIC** | API documentation | None |

### 8.2 Data Retention

```yaml
retention_policy:
  settlements:
    duration: 7_years  # Regulatory requirement
    location: "encrypted S3 + Glacier"

  risk_scores:
    duration: 3_years
    location: "encrypted PostgreSQL"

  logs:
    duration: 1_year
    location: "CloudWatch + S3"

  proofpacks:
    duration: 7_years
    location: "immutable S3"
```

### 8.3 Data Deletion

**Right to deletion (GDPR/CCPA):**

```python
def delete_user_data(user_id: str, reason: str) -> DeletionResult:
    """
    Delete all user data (GDPR Article 17)
    """
    # Log deletion request
    log_security_event({
        "event": "DATA_DELETION_REQUEST",
        "user_id": user_id,
        "reason": reason
    })

    # Delete across all services
    deleted_records = []
    deleted_records.extend(delete_from_chainiq(user_id))
    deleted_records.extend(delete_from_chainpay(user_id))
    deleted_records.extend(delete_from_chainboard(user_id))

    # Anonymize instead of delete (financial records)
    anonymize_financial_records(user_id)

    # Generate deletion certificate
    certificate = generate_deletion_certificate(user_id, deleted_records)

    return DeletionResult(success=True, certificate=certificate)
```

---

## 9. INCIDENT RESPONSE

### 9.1 Incident Classification

| Severity | Definition | Response Time |
|----------|------------|---------------|
| **P0 - CRITICAL** | Active breach, data exposed | Immediate |
| **P1 - HIGH** | Vulnerability exploited | 1 hour |
| **P2 - MEDIUM** | Potential vulnerability | 4 hours |
| **P3 - LOW** | Security concern | 24 hours |

### 9.2 Incident Response Plan

```
1. DETECTION (Sam GID-06 + monitoring)
   ↓
2. CONTAINMENT (Isolate affected systems)
   ↓
3. INVESTIGATION (Forensics + log analysis)
   ↓
4. REMEDIATION (Patch vulnerability, rotate keys)
   ↓
5. RECOVERY (Restore services)
   ↓
6. POST-MORTEM (Root cause analysis + improvements)
```

### 9.3 Breach Notification

**If data breach occurs:**

- Notify affected users: 72 hours
- Notify regulators (if required): 72 hours
- Public disclosure (if material): Per legal guidance
- Post-mortem published internally: 7 days

---

## 10. COMPLIANCE & AUDITING

### 10.1 SOC2 Type II Controls

**ChainBridge implements SOC2 Type II controls:**

| Control Category | Implementation | Status |
|------------------|----------------|--------|
| **Access Control** | RBAC + MFA | ✅ Active |
| **Change Management** | Git + CI/CD + ALEX governance | ✅ Active |
| **Data Protection** | Encryption + DLP | ✅ Active |
| **Monitoring** | ELK + alerts | ✅ Active |
| **Incident Response** | Runbooks + on-call | ✅ Active |

### 10.2 SOX-Lite Internal Controls

**Financial controls for settlement integrity:**

- Segregation of duties (settlement approval workflow)
- Dual authorization for large settlements (> $500K)
- Immutable audit trails (event sourcing)
- ProofPack generation for all transactions
- Quarterly internal audits

### 10.3 Audit Logging

**Immutable audit trail:**

```python
audit_log = {
    "timestamp": "2025-12-11T10:30:00Z",
    "event": "SETTLEMENT_EXECUTED",
    "user": "operator_456",
    "action": "execute_settlement",
    "resource": "settlement_001",
    "details": {
        "shipment_id": "ship_001",
        "amount": 250000.00,
        "risk_score": 0.23,
        "approver": "admin_789"
    },
    "hash": "sha256:...",
    "previous_hash": "sha256:..."  # Chain of custody
}
```

---

## 11. SECURE DEVELOPMENT LIFECYCLE

### 11.1 Development Standards

**All code must follow:**

- OWASP Top 10 mitigation
- SANS Top 25 mitigation
- Secure coding guidelines (CERT)
- ALEX governance rules

### 11.2 Code Review Requirements

**All PRs must have:**

- Security review (for sensitive changes)
- ALEX governance approval
- Dependency scan passing
- Unit tests passing
- Integration tests passing

### 11.3 Security Training

**Required for all developers:**

- OWASP Top 10 training (annual)
- Secure coding practices (annual)
- PQC awareness training (Q1 2026)
- Incident response procedures (annual)

---

## 12. ACCEPTANCE CRITERIA

**Security baseline is fully active when:**

1. ✅ PQC migration plan documented and in progress
2. ✅ All secrets in secure storage (no hardcoded secrets)
3. ✅ Database encryption enabled (at rest + in transit)
4. ✅ API authentication using JWT with PQC signatures
5. ✅ Centralized logging and alerting active
6. ✅ Vulnerability scanning in CI/CD
7. ✅ Incident response plan documented
8. ✅ SOC2/SOX controls implemented

---

## 13. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2025-12-11 | Initial Security Baseline (ALEX GID-08 + Sam GID-06) |

---

## 14. REFERENCES

- [ALEX Protection Manual](./ALEX_PROTECTION_MANUAL.md)
- [ChainPay Governance Rules](./CHAINPAY_GOVERNANCE_RULES.md)
- [Cryptography Registry](./CRYPTO_REGISTRY.md)
- [Incident Response Runbook](../security/incident_response.md)

---

**ALEX (GID-08) + Sam (GID-06) - Security by Design • Quantum-Ready • Zero-Trust**
