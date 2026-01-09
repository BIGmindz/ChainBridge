# ChainBridge KYB Document Vault

## ⚠️ SECURITY WARNING ⚠️

**This directory is subject to GID-13 (Lira) and GID-15 (Vera) oversight.**

**NO PLAIN TEXT DOCUMENTS ALLOWED.**

Any document containing sensitive information must be cryptographically hashed before storage or anchoring.

## Overview

This vault contains Know Your Business (KYB) compliance documentation for the ChainBridge enterprise logistics & settlement platform. All documents must comply with constitutional governance rules and ISO-20022 standards.

## GID-13 (Lira) Compliance Requirements

**Lira** is the document verification agent responsible for ensuring KYB document integrity and authenticity.

### Document Handling Protocol

1. **NO PLAIN TEXT**: All sensitive documents must be hashed using approved cryptographic functions
2. **Approved Hash Algorithms**: SHA-256, SHA-512, or stronger
3. **Verification Quorum**: 3-of-5 HSM (Hardware Security Module) signature required
4. **Fail-Closed Mode**: Any verification failure immediately terminates operations

### Document Types Subject to Lira Oversight

- Employer Identification Numbers (EIN) - **MUST BE HASHED**
- Articles of Incorporation - **MUST BE HASHED**
- Operating Agreements - **MUST BE HASHED**
- Business Licenses - **MUST BE HASHED**
- Beneficial Owner Information - **MUST BE HASHED**
- Tax Documentation - **MUST BE HASHED**

### Hashing Requirements

**Correct Format** (hashed):
```json
{
  "document_type": "ein",
  "hash_algorithm": "SHA-256",
  "hash_value": "a3b2c1d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
  "timestamp": "2026-01-09T00:00:00Z",
  "verified_by": "LIRA-GID-13"
}
```

**PROHIBITED Format** (plain text):
```
EIN: 12-3456789  ❌ VIOLATION
```

### Document Anchoring Workflow

1. **Preparation**: Hash sensitive document using approved algorithm
2. **Metadata**: Create document metadata with hash reference
3. **Verification Gate**: Submit to Lira (GID-13) for verification
4. **Quorum Validation**: Await 3-of-5 HSM signature approval
5. **Blockchain Anchor**: Record hash on immutable ledger
6. **Audit Trail**: Log verification event

### Fail-Closed Verification Gate

The verification gate operates in **FAIL-CLOSED** mode:

- **Default State**: DENY (no access)
- **Success Condition**: 3-of-5 HSM quorum achieved
- **Failure Condition**: Any signature fails, missing quorum, invalid hash
- **Failure Action**: Immediate termination, manual review required
- **No Override**: No automatic retry or fallback

## GID-15 (Vera) Compliance Requirements

**Vera** is the compliance oversight agent responsible for enforcing governance policies.

### Oversight Scope

1. **Constitutional Compliance**: Verify adherence to governance rules
2. **Security Posture**: Enforce fail-closed requirements
3. **Audit Trail**: Maintain immutable logs of all operations
4. **Policy Enforcement**: Block non-compliant actions
5. **Escalation**: Alert on violations

### Vera Enforcement Actions

- Monitor all document uploads to this directory
- Scan for plain-text sensitive information
- Block commits containing unhashed documents
- Generate alerts for policy violations
- Require manual review for overrides

## ISO-20022 Identity Mapping

All KYB documents must conform to ISO-20022 standard `acmt.023.001.03` (Account Management Identity Verification Request).

### Required Fields

- **Legal Entity Identifier (LEI)**: If applicable
- **Organization Name**: Official registered name
- **Jurisdiction**: State/country of incorporation
- **Document Shards**: Hashed references to constituent documents
  - EIN Hash
  - Articles of Incorporation Hash
  - Operating Agreement Hash
- **Verification Agent**: LIRA-GID-13
- **Verification Quorum**: 3-of-5-HSM

### Schema Reference

See `/core/iso20022_mapping_p160.json` for the canonical schema definition.

## Directory Structure

```
/docs/legal/kyb/
├── README.md              # This file
├── .gitkeep              # Directory anchor
└── metadata/             # Hashed document metadata (future)
    ├── ein_hash.json
    ├── articles_hash.json
    └── operating_agreement_hash.json
```

## CI/CD Protection

This directory is protected by the ChainBridge constitutional CI/CD pipeline:

- **Path-Based Gating**: Additional verification required for changes
- **Secret Scanning**: Automated detection of plain-text sensitive data
- **Fail-Closed Enforcement**: Build termination on violations
- **Manual Approval**: Required for all changes to this path

### Detected Patterns (Auto-Reject)

The CI/CD pipeline will automatically reject commits containing:

- `BEGIN RSA PRIVATE KEY`
- `BEGIN PRIVATE KEY`
- `BEGIN ENCRYPTED PRIVATE KEY`
- EIN patterns: `\d{2}-\d{7}` (unhashed format)
- Social Security Numbers: `\d{3}-\d{2}-\d{4}`
- API keys, tokens, passwords (various patterns)

## Usage Guidelines

### For Developers

1. **NEVER commit plain-text sensitive documents**
2. Always hash documents before adding to this directory
3. Use approved hash algorithms (SHA-256 or stronger)
4. Include metadata with hash algorithm and timestamp
5. Test locally with secret scanner before committing

### For Compliance Officers

1. Verify all documents have proper hashing
2. Ensure ISO-20022 compliance for identity documents
3. Validate 3-of-5 HSM quorum signatures
4. Review audit logs regularly
5. Escalate violations immediately

### For Auditors

1. All document operations are logged immutably
2. Audit trail includes actor, action, timestamp, result
3. Verification gates are tamper-evident
4. No modification of historical records permitted
5. Export capabilities for compliance reporting

## Incident Response

### If Plain-Text Document Detected

1. **Immediate Action**: CI/CD pipeline terminates build
2. **Notification**: Security team alerted automatically
3. **Investigation**: Manual review of commit history
4. **Remediation**: Remove plain-text document, replace with hash
5. **Post-Incident**: Document in audit log, update training

### If Verification Fails

1. **Fail-Closed**: Operations immediately suspended
2. **Manual Review**: Security team investigates failure cause
3. **Root Cause**: Determine if technical or policy issue
4. **Resolution**: Fix underlying issue, re-verify
5. **Resume**: Manual approval required to restart

## Roadmap Integration

### P154 (Current Phase): Foundation Anchor

- Establish directory structure ✓
- Document compliance requirements ✓
- Configure CI/CD protection ✓

### P165 (Next Phase): KYB Document Anchoring

- Upload hashed EIN document
- Upload hashed Articles of Incorporation
- Upload hashed Operating Agreement
- Complete ISO-20022 mapping
- Achieve 3-of-5 HSM verification
- Anchor hashes to blockchain

### P170 (Following Phase): $1.00 Ingress

- Requires P165 verification completion
- First real settlement transaction
- Live KYB validation

## Contact & Support

**Security Issues**: Escalate to Chief Architect (Benson)  
**Compliance Questions**: Contact GID-15 (Vera) oversight team  
**Technical Support**: Reference `.github/chainbridge-rules.md`  

## Legal Notice

This directory contains business-critical compliance documentation. Unauthorized access, modification, or disclosure may result in:

- Legal penalties
- Regulatory sanctions
- Contract violations
- Immediate termination of access

All access is logged and monitored.

---

**Classification**: RESTRICTED - COMPLIANCE CRITICAL  
**Oversight**: GID-13 (Lira), GID-15 (Vera)  
**Last Updated**: 2026-01-09  
**Version**: 1.0
