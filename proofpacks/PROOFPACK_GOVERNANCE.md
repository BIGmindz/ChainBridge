
# Proof Pack Governance (Customer-Controlled, ChainBridge-Executed)

## Purpose
Enterprises keep control over **what evidence is recorded, how it is redacted, where it is stored, and how long it is retained**. ChainBridge executes decisions and assembles the pack exactly to the customer’s template, then seals it with cryptographic hashes and payment receipts.

## Ownership & Roles
- **Data Controller (Customer):** Defines the proof pack template, redaction, storage location, retention period, and approval workflow.
- **Processor (ChainBridge):** Executes policy, assembles the pack per the template, routes payments, anchors integrity hashes, and returns receipts.
- **Auditors/Insurers (Read-only):** Receive export bundles or query via a read-only API.

## Pack Template
Each customer can have multiple templates (per lane, corridor, counterparty, or risk tier).  
Required elements: event lineage, policy manifest, settlement receipts, integrity hashes, timestamps & signatures.  
Optional: carrier/lane codes, risk scores, claims, attachments. Sensitive data may be hashed or dropped.

## Redaction & Data Minimization
Collect the **minimum required**. Per-field control allows `drop`, `mask`, or `hash`.  
ChainBridge keeps only non-identifying metadata (template ID, hash, tx IDs).

## Storage & Retention
- Primary: customer-owned vault (S3/Azure/GCS/on-prem). Write-only for ChainBridge.  
- Retention: customer-set (e.g., 7 yrs); ChainBridge cache default = 7 days.  
- DR: customer controls replication; we can re-emit from immutable logs.

## Integrity & Anchoring
Each pack includes a manifest hash (SHA-256).  
Anchors are written to a public or neutral ledger (e.g., XRP Ledger) so anyone can prove immutability without revealing data.

## Access & Delivery
- Delivery: customer bucket, API callback, SFTP, or audit inbox.  
- Formats: JSON, PDF summary, CSV excerpt, plus zipped `audit.zip`.  
- Query keys: shipment ID, invoice, PO, payment ID, tx ID, or date range.

## Change Control & Versioning
Templates are versioned; changes require finance/compliance approval.  
Packs embed the template ID + version; ChainBridge keeps a signed decision log.

## Runtime Modes
1. **Observe-only:** generate packs; no funds move.  
2. **Simulated:** “would-have-paid” runs.  
3. **Controlled live:** one milestone (e.g., pickup 20 %) with dual approval.  
4. **Full automation:** all milestones; alerts on exceptions.

## Security Highlights
Tenant isolation • TLS in transit • customer KMS at rest • RBAC • IP allowlists • hardware key option • SOC 2 track • DPA on request.

## API Stubs
- `POST /proofpacks/run`
- `GET /proofpacks/{pack_id}`
- `GET /proofpacks/search?key=value`
- `GET /anchors/{anchor_id}`
- `PUT /templates/{template_id}`
- `GET /templates`
