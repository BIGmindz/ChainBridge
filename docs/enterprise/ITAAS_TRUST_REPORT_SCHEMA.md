# Artifact 5: Tenant-Isolated Trust Report Schema

**PAC Reference:** PAC-JEFFREY-P52  
**Classification:** ITaaS / GOVERNED  
**Status:** DELIVERED  
**Author:** SONNY (GID-02)  
**Orchestrator:** BENSON (GID-00)

---

## 1. Overview

The Tenant-Isolated Trust Report Schema defines the structure of verification reports delivered to ITaaS clients. Reports are generated per-tenant with complete isolation guarantees.

---

## 2. Schema Version

```yaml
schema_id: ITAAS_TRUST_REPORT_SCHEMA
version: "1.0.0"
pac_reference: PAC-JEFFREY-P52
classification: GOVERNED
```

---

## 3. Report Structure

```json
{
  "$schema": "https://chainbridge.io/schemas/trust-report/v1.0.0",
  "report_id": "string (UUID)",
  "tenant_id": "string",
  "api_id": "string",
  "api_title": "string",
  "generated_at": "ISO8601 datetime",
  "report_type": "VERIFICATION | DRIFT | CHAOS | FULL",
  
  "scores": {
    "base_score": "number (0-100)",
    "cci_score": "number (0-100)",
    "safety_score": "number (0-100)",
    "final_score": "number (0-100)",
    "grade": "A+ | A | B+ | B | C+ | C | D | F"
  },
  
  "dimension_coverage": [
    {
      "dimension": "AUTH | TIMING | STATE | RESOURCE | NETWORK | DATA",
      "tests_executed": "number",
      "tests_passed": "number",
      "coverage_percentage": "number (0-100)",
      "edge_cases_found": "number"
    }
  ],
  
  "test_summary": {
    "total": "number",
    "passed": "number",
    "failed": "number",
    "blocked": "number"
  },
  
  "drift_events": [
    {
      "event_id": "string",
      "category": "string",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW | INFO",
      "description": "string",
      "path": "string (JSONPath)"
    }
  ],
  
  "recommendations": [
    {
      "priority": "CRITICAL | HIGH | MEDIUM | LOW",
      "category": "string",
      "description": "string",
      "action": "string"
    }
  ],
  
  "legal_disclaimer": {
    "disclaimer_id": "string",
    "version": "string",
    "statements": {
      "not_certification": "string",
      "not_security_guarantee": "string",
      "not_compliance": "string",
      "liability_limitation": "string",
      "scope_limitation": "string"
    }
  },
  
  "metadata": {
    "baseline_id": "string",
    "execution_time_ms": "number",
    "engine_version": "string",
    "schema_version": "string"
  }
}
```

---

## 4. Trust Grade Mapping

| Grade | Score | Trust Level | Description |
|-------|-------|-------------|-------------|
| A+ | 95-100 | VERIFIED_EXCELLENT | Comprehensive verification passed |
| A | 90-94 | VERIFIED_EXCELLENT | Excellent verification results |
| B+ | 85-89 | VERIFIED_GOOD | Good verification with minor gaps |
| B | 80-84 | VERIFIED_GOOD | Adequate verification |
| C+ | 75-79 | VERIFIED_ACCEPTABLE | Acceptable with recommendations |
| C | 70-74 | VERIFIED_ACCEPTABLE | Minimum acceptable threshold |
| D | 60-69 | NEEDS_ATTENTION | Significant gaps identified |
| F | <60 | HIGH_RISK | Critical issues detected |

---

## 5. Tenant Isolation Guarantees

### 5.1 Data Isolation
- Each tenant has dedicated namespace
- No cross-tenant data access
- Report data encrypted at rest

### 5.2 Execution Isolation
- Separate execution contexts
- Resource quotas per tenant
- Independent kill-switch capability

### 5.3 Report Isolation
- Reports bound to tenant_id
- Access control enforced
- Audit trail per tenant

---

## 6. Legal Disclaimer (MANDATORY)

**CRITICAL:** Every report MUST include the legal disclaimer. The disclaimer cannot be removed, modified, or hidden.

```python
class LegalDisclaimer:
    """
    Legal disclaimer attached to all reports.
    
    MANDATORY — cannot be removed or modified.
    """
    
    NOT_CERTIFICATION = (
        "This report is a VERIFICATION report, NOT a certification. "
        "ChainVerify does not certify, guarantee, or warrant the security, "
        "reliability, or fitness for purpose of any API or system."
    )
    
    NOT_SECURITY_GUARANTEE = (
        "Verification scores reflect observed behavior during automated testing only. "
        "They do NOT guarantee protection against security vulnerabilities, data breaches, "
        "or system failures."
    )
    
    NOT_COMPLIANCE = (
        "This report does NOT constitute compliance with any regulatory framework "
        "including but not limited to SOC2, HIPAA, PCI-DSS, GDPR, or ISO 27001."
    )
    
    LIABILITY_LIMITATION = (
        "ChainVerify and its operators accept NO LIABILITY for any damages, losses, "
        "or consequences arising from reliance on this report or the verified API."
    )
```

---

## 7. Report Generation API

```python
from core.chainverify import TrustReporter, generate_trust_report

reporter = TrustReporter(tenant_id="tenant-abc")
report = generate_trust_report(
    api_id="api-123",
    verification_score=score,
    drift_events=drift_events,
    format=ReportFormat.JSON,
)
```

---

## 8. Output Formats

| Format | MIME Type | Use Case |
|--------|-----------|----------|
| JSON | application/json | API integration |
| MARKDOWN | text/markdown | Documentation |
| HTML | text/html | Web display |
| PDF | application/pdf | Formal reports |

---

## 9. Retention Policy

| Data Type | Retention | Tenant Control |
|-----------|-----------|----------------|
| Reports | 90 days | Configurable |
| Audit logs | 365 days | Read-only |
| Raw results | 30 days | Configurable |
| Baselines | Until replaced | Full |

---

## 10. Sample Report

```json
{
  "report_id": "rpt-2026-01-03-abc123",
  "tenant_id": "tenant-acme",
  "api_id": "acme-payments-v2",
  "api_title": "ACME Payments API",
  "generated_at": "2026-01-03T12:00:00Z",
  "report_type": "FULL",
  
  "scores": {
    "base_score": 92.5,
    "cci_score": 88.3,
    "safety_score": 100.0,
    "final_score": 91.8,
    "grade": "A"
  },
  
  "dimension_coverage": [
    {
      "dimension": "AUTH",
      "tests_executed": 25,
      "tests_passed": 24,
      "coverage_percentage": 96.0,
      "edge_cases_found": 3
    },
    {
      "dimension": "DATA",
      "tests_executed": 50,
      "tests_passed": 48,
      "coverage_percentage": 94.0,
      "edge_cases_found": 5
    }
  ],
  
  "test_summary": {
    "total": 250,
    "passed": 238,
    "failed": 12,
    "blocked": 0
  },
  
  "drift_events": [],
  
  "recommendations": [
    {
      "priority": "MEDIUM",
      "category": "AUTH",
      "description": "Token expiry handling could be improved",
      "action": "Review token refresh logic"
    }
  ],
  
  "legal_disclaimer": {
    "disclaimer_id": "CHAINVERIFY-LEGAL-001",
    "version": "1.0.0",
    "statements": {
      "not_certification": "This report is a VERIFICATION report, NOT a certification..."
    }
  },
  
  "metadata": {
    "baseline_id": "baseline-v1.0.0",
    "execution_time_ms": 45230,
    "engine_version": "1.0.0",
    "schema_version": "1.0.0"
  }
}
```

---

## 11. Invariants

| ID | Invariant | Status |
|----|-----------|--------|
| INV-REPORT-001 | Legal disclaimer mandatory | ENFORCED |
| INV-REPORT-002 | Tenant isolation enforced | ENFORCED |
| INV-REPORT-003 | No certification claims | ENFORCED |
| INV-REPORT-004 | Report schema validated | ENFORCED |

---

**ARTIFACT STATUS: DELIVERED ✅**
