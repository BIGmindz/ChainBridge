# ChainBridge Governance & Decision Rights Policy (V0)

Audience: tenant executives, operations, risk, finance leaders, and internal product / engineering teams.

## 1. Core Governance Principles

ChainBridge is built as a **neutral logistics OS and risk/settlement brain**, not as a freight company or broker. Governance focuses on clarity, safety, and auditability:

- **Neutral OS**: ChainBridge does not move freight and does not compete with carriers or brokers. Policies and models must not systematically favor any specific carrier, broker, or counterparty.
- **Role Clarity**: Decisions are made by people in defined roles, with explicit permissions and thresholds in the product.
- **Auditability**: Every material action—risk override, payout override, policy change, model change—is logged and attributable.
- **Separation of Concerns**: Operational, risk, and financial responsibilities are separated, with different roles and checks.
- **Glass-Box AI**: ChainIQ’s risk and settlement recommendations must be explainable and reviewable; no unreviewable black-box automation around money.

## 2. Primary Roles (Within a Tenant)

Role names may vary by customer, but v0 assumes the following standard roles:

### 2.1 Operator

- Works in the OC cockpit day-to-day.
- Manages exceptions assigned to them.
- Can add notes, attach supporting documents, and trigger **standard, pre-approved playbooks**.
- Cannot change core risk or settlement policies.

### 2.2 Ops Manager

- Oversees a team of Operators.
- Can reassign exceptions and monitor queues.
- Can approve escalated playbooks and mark exceptions as resolved within configured thresholds (e.g., low/medium risk, low dollar impact).
- Cannot change tenant-wide risk tolerance or settlement curves.

### 2.3 Risk Officer

- Owns the tenant’s risk posture for shipments, credit, fraud, and counterparties.
- Can adjust risk tolerance parameters within allowed guardrails (e.g., default thresholds, allowed lanes, risk appetite bands).
- Can override ChainIQ decisions (e.g., HOLD → APPROVE) within pre-defined policy bounds, with mandatory reasoning and logging.
- Collaborates with Finance on high-value or sensitive overrides.

### 2.4 Finance / Settlement Officer

- Owns financial exposure, payouts, and settlement rules.
- Can configure SettlementPolicies (curves, delays, conditions) within tenant and platform bounds.
- Can approve or override payout holds and release funds, subject to multi-step approval where configured.
- Works closely with Risk Officer for high-risk, high-value settlements.

### 2.5 Admin / Tenant Owner

- Highest level of control within a tenant.
- Can manage user accounts, role assignments, and SSO / identity integrations.
- Can enable or disable data use modes (e.g., Mode A vs Mode B for data/model policy).
- Can approve major policy changes and integrations (e.g., ChainPay activation, new external data sources).

(Additional specialized roles such as **ESG Officer** or **Compliance Officer** may be added in future versions.)

## 3. Decision Rights Matrix (V0)

The following matrix outlines who is typically allowed to perform which actions. Tenants can refine this matrix, but the product will ship with these defaults and recommended guardrails.

| Action | Operator | Ops Manager | Risk Officer | Finance Officer | Admin / Tenant Owner |
|-------|----------|------------|-------------|----------------|----------------------|
| Trigger standard playbook on an Exception | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mark Exception as RESOLVED (low/medium risk) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Reassign Exception between queues/users | ❌ | ✅ | ✅ | ✅ | ✅ |
| Edit Exception notes / attach documents | ✅ | ✅ | ✅ | ✅ | ✅ |
| Override high-risk HOLD → APPROVE | ❌ | ❌ | ✅ (within guardrails) | ✅ (co-approval) | ✅ (co-approval) |
| Change a SettlementPolicy (within platform bounds) | ❌ | ❌ | ✅ (recommend) | ✅ (approve) | ✅ (approve) |
| Enable/disable Mode B (global data contribution) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Configure new integration (e.g., ERP, TMS, bank) | ❌ | ❌ | ✅ (review) | ✅ (review) | ✅ (approve) |
| Adjust tenant-level risk tolerance bands | ❌ | ❌ | ✅ | ✅ (for financial limits) | ✅ |
| Create / edit Playbooks | ❌ | ✅ (operational) | ✅ (risk-related) | ✅ (finance-related) | ✅ |
| Edit ESG flags / EsgEvidence | ❌ | ❌ | ✅ | ✅ (for financial products) | ✅ |

These defaults are implemented in the product as permissions and can be customized per tenant, but core safety guardrails (e.g., no single low-level user can release large payouts) remain enforced.

## 4. Platform-Level Governance (ChainBridge as Provider)

ChainBridge, as the platform provider, commits to the following:

- **No Raw Data Selling**: ChainBridge does not sell raw tenant data (shipments, invoices, contracts, etc.).
- **Neutrality**: ChainBridge does not use tenant data to favor any particular carrier, broker, 3PL, or shipper. Recommendations focus on risk, reliability, and performance, not on steering volume for ChainBridge’s financial benefit.
- **Strict Access Controls**: Production data access for ChainBridge staff is tightly limited to specific roles (e.g., SRE, support) and logged, with least-privilege and need-to-know as guiding principles.
- **Environment Separation**: Sandboxes, staging, and production environments are logically separated, with controls to prevent cross-tenant data leakage.
- **Security Baselines**: Encryption in transit and at rest, regular access reviews, and incident response procedures are standard.

## 5. Policy & Model Change Management

Changes to risk and settlement logic must be controlled and transparent.

- **Versioned Policies & Models**:
  - New model versions (e.g., ChainIQ risk model v0.2) and policy templates (SettlementPolicies, Playbooks) are versioned and tagged.
  - DecisionRecords reference the model and policy versions active at the time of each decision.

- **Change Proposals & Approvals**:
  - For tenant-specific changes (e.g., adjusting a SettlementPolicy), the relevant roles (Risk Officer, Finance Officer, Admin) propose and approve changes in the product.
  - The system records who proposed, who approved, and when the change became effective.

- **Communication of Platform-Wide Changes**:
  - For platform defaults (e.g., new base model, new default thresholds), ChainBridge communicates changes, effective dates, and expected impact.
  - Where changes could materially affect risk/settlement outcomes, tenants may have the option to test in sandbox or phased rollout before full adoption.

## 6. Audit & Exportability

ChainBridge is designed to be **audit-friendly** from day one.

- **Exportable Records**: Tenants can export, via API or UI, at least the following for a defined period:
  - DecisionRecords (including explanations).
  - Settlement histories and payout timelines.
  - Key model outputs for shipments or invoices (e.g., risk scores, recommended actions).

- **Traceability**: For each decision, auditors should be able to trace:
  - Which model and policy versions were active.
  - Which inputs were considered (at a summary level).
  - Who, if anyone, overrode the model’s recommendation and why.

- **Support for Regulatory & Customer Audits**: Reports and exports can be aligned to regulatory needs (e.g., financial controls, ESG reporting) and customer-specific audit scopes.

## 7. Abuse & Misalignment Handling (V0 Outline)

ChainBridge is built for aligned, good-faith usage, but the system must be robust to abuse.

- **Suspicious Behavior Detection**:
  - The platform may flag patterns that suggest attempts to game metrics or bypass controls (e.g., systematically mislabeling events, overriding every HOLD, misconfiguring policies to always APPROVE).
  - Such flags can trigger additional review workflows or temporary limits.

- **Protecting Counterparties & the Network**:
  - Where enabled by agreements, ChainBridge may apply additional risk checks or friction when behavior endangers settlement safety or broader network trust.

- **Escalation & Remediation**:
  - In severe cases, ChainBridge may restrict certain features, require additional approvals, or suspend integrations while issues are investigated.
  - Long-term abuse policies will be developed with legal/compliance guidance in V1+.

## 8. Snippets for Decks & POCs

### 8.1 Governance & Decision Rights Summary

> ChainBridge ships with opinionated, auditable decision rights: operators work the cockpit, risk and finance own thresholds and payouts, and admins control data sharing and integrations. Every override and policy change is logged, so you always know who did what, when, and why.

### 8.2 Neutral OS & Data Governance Summary

> ChainBridge is a neutral logistics OS, not a broker. We do not sell raw tenant data and we do not use it to favor specific carriers or brokers. Our governance model keeps roles, permissions, and AI decisions transparent and auditable from day one.

### 8.3 Model & Policy Change Management Summary

> Risk and settlement logic in ChainBridge is versioned like code. New models and policies are tagged, testable in sandbox, and tied to DecisionRecords so you can reconstruct exactly which brain and which rules were active for any shipment, payout, or exception.
