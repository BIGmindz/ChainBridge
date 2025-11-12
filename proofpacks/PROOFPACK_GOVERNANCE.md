# Proof Pack Governance (Customer-Controlled, ChainBridge-Executed)

## Purpose

Enterprises maintain control over **what evidence is recorded, how it is redacted, where it is stored, and how long it is retained**. ChainBridge executes these decisions and assembles the proof pack exactly according to the customer's template, then seals it with cryptographic hashes and payment receipts.

## Ownership & Roles

- **Data Controller (Customer):** Defines the proof pack template, redaction rules, storage location, retention period, and approval workflow.
- **Data Processor (ChainBridge):** Executes the policy, assembles the proof pack according to the template, routes payments, anchors integrity hashes, and returns receipts.
- **Auditors/Insurers (Read-Only):** Receive export bundles or query via a read-only API.

## Pack Template

Each customer can define multiple templates (per lane, corridor, counterparty, or risk tier).  
**Required elements:** event lineage, policy manifest, settlement receipts, integrity hashes, timestamps, and signatures.  
**Optional elements:** carrier/lane codes, risk scores, claims, attachments. Sensitive data may be hashed or dropped per customer policy.

## Redaction & Data Minimization

Collect the **minimum data required** to satisfy regulatory and business needs. Customers have per-field control to specify one of the following actions:

- **drop:** The field is omitted entirely from the proof pack.
- **mask:** The field is partially obscured (e.g., `"email": "u***@example.com"`, `"account": "****5678"`).
- **hash:** The field value is replaced with a cryptographic hash (SHA-256 recommended). When hashing, consider using a salt unique to the customer or field to prevent rainbow table attacks.

**Privacy considerations:** Metadata (timestamps, transaction IDs, template IDs) can sometimes be identifying when combined with external data. Customers are advised to perform a Data Protection Impact Assessment (DPIA) or apply pseudonymization techniques when processing personal data.

**ChainBridge data retention:** ChainBridge retains only non-identifying metadata necessary for service operation:

- Template ID and version
- Manifest hash (SHA-256)
- Anchor transaction IDs
- Short-lived cache: default 7 days for performance optimization

ChainBridge does **not** retain Personally Identifiable Information (PII) beyond the customer-configured retention period unless required by law or for troubleshooting purposes, in which case access is logged in an audit trail with a defined time-to-live (TTL).

## Storage & Retention

**Primary storage:** Customer-owned vault (S3, Azure Blob Storage, Google Cloud Storage, or on-premises). ChainBridge has **write-only** access to these storage locations.

**Enforcement mechanisms:**

- Presigned PUT URLs with expiration (for S3/Azure/GCS)
- Customer-managed IAM roles with minimal permissions
- Server-side encryption using customer-managed KMS keys
- No read access granted to ChainBridge

**Retention policy:** Customer-set retention (example: 7 years for regulatory compliance). ChainBridge cache: default 7 days for performance; immutable manifests and anchors persisted in audit logs or on public ledger per customer policy.

**Disaster recovery:** Customers control replication and backup strategies. ChainBridge can re-emit proof packs from immutable logs if needed.

## Integrity & Anchoring

Each proof pack includes a manifest hash computed using **SHA-256**. This hash provides cryptographic proof of the pack's contents without revealing any data.

**Anchoring destinations:** Customers can choose to anchor the manifest hash to a public or neutral ledger, such as:

- Ethereum
- XRP Ledger  
- Customer-specified blockchain or distributed ledger

Only the **manifest hash** is anchored to the ledger; no raw data is published.

**Technical details:**

- **Hash algorithm:** SHA-256 (customers may request SHA-3 or other approved algorithms)
- **Canonicalization:** JSON fields are sorted alphabetically before hashing to ensure consistency
- **Merkle trees:** Optional per-field Merkle tree construction for granular verification proofs

Anyone with the manifest hash can verify the immutability and timestamp of the proof pack without accessing the underlying data.

## Access & Delivery

**Delivery options:**

- Customer-owned storage bucket (S3/Azure/GCS)
- API callback (webhook)
- SFTP upload to customer server
- Audit inbox (email or secure portal)

**Data formats:** JSON manifest, PDF summary, CSV excerpt, plus zipped `audit.zip` bundle containing all artifacts.

**Query capabilities:** Search by shipment ID, invoice number, purchase order (PO), payment ID, transaction ID, or date range.

**API behaviors:**

- `POST /proofpacks/run` returns **202 Accepted** with a job ID for asynchronous processing
- `GET /proofpacks/{pack_id}` returns **200 OK** with JSON manifest or **404 Not Found** if pack does not exist
- `GET /proofpacks/search` returns **200 OK** with paginated results

**Authentication & authorization:** All API endpoints require authentication (OAuth2, JWT, or API key). Role-Based Access Control (RBAC) enforces permissions based on user roles (e.g., admin, auditor, read-only).

## Change Control & Versioning

Templates are versioned using semantic versioning (e.g., v1.0.0, v1.1.0). Changes to templates require approval from finance and compliance stakeholders according to the customer's governance workflow.

**Approval workflow:**

1. Template change is proposed
2. Finance and compliance teams review
3. Authorized approver signs off
4. New version is published

Each proof pack embeds the template ID and version number. ChainBridge maintains a **signed decision log** that records all template changes, approvals, and the identity of approvers. These logs are stored in:

- Customer-controlled vault (recommended)
- ChainBridge audit log with cryptographic signature verification
- Optionally anchored to ledger for tamper-proof history

## Runtime Modes

1. **Observe-Only:** Generate proof packs and log decisions, but no funds are moved. **Use case:** testing templates, auditing data flows, compliance validation.

2. **Simulated:** Execute "would-have-paid" dry runs showing what payments would occur. **Use case:** validating payment logic before production deployment.

3. **Controlled Live:** Execute payments for specific milestones (e.g., 20% on pickup) with dual approval required. **Use case:** phased rollout, high-value transactions, risk mitigation.

4. **Full Automation:** All milestones execute automatically with alerts on exceptions. **Safeguards:** transaction limits per time period, anomaly detection, automatic circuit breakers on suspicious activity, real-time monitoring dashboards.

## Security Highlights

ChainBridge implements comprehensive security controls to protect customer data and operations:

- **Encryption in transit:** TLS 1.2+ for all API communications
- **Encryption at rest:** Server-side encryption using customer-managed KMS keys
- **Tenant isolation:** Logical separation of customer environments with dedicated resources
- **Role-Based Access Control (RBAC):** Granular permissions based on user roles
- **IP allowlists:** Restrict API access to approved IP ranges
- **Hardware Security Module (HSM):** Optional HSM integration for cryptographic signing operations
- **SOC 2 compliance:** ChainBridge maintains SOC 2 Type II certification
- **Data Processing Addendum (DPA):** Available upon request for GDPR and privacy compliance

## API Reference

### POST /proofpacks/run

Execute a proof pack generation based on a template.

**Authentication:** Required (OAuth2, JWT, or API key)  
**Authorization:** `proofpack:write` permission

**Request body:**

```json
{
  "template_id": "template-abc-123",
  "template_version": "1.2.0",
  "event_data": {
    "shipment_id": "SHIP-2024-001",
    "invoice_number": "INV-98765",
    "payment_amount": 50000.00,
    "currency": "USD"
  },
  "redaction_rules": {
    "customer_email": "mask",
    "account_number": "hash"
  }
}
```

**Response (202 Accepted):**

```json
{
  "job_id": "job-xyz-789",
  "status": "processing",
  "estimated_completion": "2024-11-12T16:15:00Z",
  "status_url": "/proofpacks/jobs/job-xyz-789"
}
```

### GET /proofpacks/{pack_id}

Retrieve a specific proof pack by ID.

**Authentication:** Required (OAuth2, JWT, or API key)  
**Authorization:** `proofpack:read` permission

**Response (200 OK):**

```json
{
  "pack_id": "pack-456-def",
  "template_id": "template-abc-123",
  "template_version": "1.2.0",
  "manifest_hash": "a3f5b9c2d8e1f4a7b6c9d2e5f8a1b4c7d0e3f6a9b2c5d8e1f4a7b0c3d6e9f2a5",
  "anchor_tx_id": "0x1234567890abcdef",
  "created_at": "2024-11-12T16:10:00Z",
  "storage_location": "s3://customer-bucket/proofpacks/pack-456-def.json"
}
```

**Response (404 Not Found):**

```json
{
  "error": "proof_pack_not_found",
  "message": "Proof pack with ID 'pack-456-def' does not exist"
}
```

### GET /proofpacks/search

Search for proof packs using query parameters.

**Authentication:** Required (OAuth2, JWT, or API key)  
**Authorization:** `proofpack:read` permission

**Query parameters:**

- `shipment_id` (optional): Filter by shipment ID
- `invoice_number` (optional): Filter by invoice number
- `date_from` (optional): ISO 8601 date (inclusive)
- `date_to` (optional): ISO 8601 date (inclusive)
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Results per page (default: 20, max: 100)

**Response (200 OK):**

```json
{
  "results": [
    {
      "pack_id": "pack-456-def",
      "template_id": "template-abc-123",
      "manifest_hash": "a3f5b9c2d8e1f4a7...",
      "created_at": "2024-11-12T16:10:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_results": 157,
    "total_pages": 8
  }
}
```

### GET /anchors/{anchor_id}

Retrieve anchor transaction details for a proof pack.

**Authentication:** Required (OAuth2, JWT, or API key)  
**Authorization:** `anchor:read` permission

**Response (200 OK):**

```json
{
  "anchor_id": "anchor-789-ghi",
  "manifest_hash": "a3f5b9c2d8e1f4a7b6c9d2e5f8a1b4c7d0e3f6a9b2c5d8e1f4a7b0c3d6e9f2a5",
  "ledger": "ethereum",
  "tx_id": "0x1234567890abcdef",
  "block_number": 18123456,
  "timestamp": "2024-11-12T16:10:30Z",
  "confirmation_count": 12
}
```

### PUT /templates/{template_id}

Update or create a proof pack template.

**Authentication:** Required (OAuth2, JWT, or API key)  
**Authorization:** `template:write` permission (requires finance/compliance approval)

**Request body:**

```json
{
  "template_id": "template-abc-123",
  "version": "1.3.0",
  "name": "Standard Shipment Proof Pack",
  "required_fields": ["shipment_id", "invoice_number", "payment_amount"],
  "optional_fields": ["carrier_code", "risk_score"],
  "default_redaction_rules": {
    "customer_email": "mask",
    "account_number": "hash"
  }
}
```

**Response (200 OK):**

```json
{
  "template_id": "template-abc-123",
  "version": "1.3.0",
  "status": "active",
  "approved_by": "compliance@example.com",
  "approved_at": "2024-11-12T15:00:00Z"
}
```

### GET /templates

List all available proof pack templates.

**Authentication:** Required (OAuth2, JWT, or API key)  
**Authorization:** `template:read` permission

**Response (200 OK):**

```json
{
  "templates": [
    {
      "template_id": "template-abc-123",
      "version": "1.2.0",
      "name": "Standard Shipment Proof Pack",
      "status": "active"
    },
    {
      "template_id": "template-def-456",
      "version": "2.0.0",
      "name": "High-Value Transaction Pack",
      "status": "active"
    }
  ]
}
```
