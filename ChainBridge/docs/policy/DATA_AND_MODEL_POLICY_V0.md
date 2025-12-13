# ChainBridge Data & Model Policy (V0)

Audience: customers, partners, and internal product / engineering teams.

## 1. Purpose & Scope

This policy describes how ChainBridge and ChainIQ handle operational data and models. It covers:

- How shipment, operational, and financial data is collected, used, and protected.
- How ChainIQ models are trained, evaluated, and served in production and sandbox environments.
- How sandbox / retrospective pilots work, and how they relate to long-term learning.

This is a **product policy**, not a legal contract. It is intended to guide product, engineering, and customer conversations. Formal legal terms will live in customer agreements and DPA/MLA documents.

## 2. Data Types & Ownership

### 2.1 Data Types

- **Customer Data**
  Shipment records, events, documents, invoices, rates, contracts, counterparties, and any other operational data that belongs to a specific tenant.

- **Derived Data**
  Features, embeddings, aggregates, risk scores, performance metrics, and other transformations that are computed from Customer Data.

- **Model Artifacts**
  Model weights, parameters, prompts, rules, explanations, and evaluation metrics that power ChainIQ and related decisioning systems.

### 2.2 Ownership

- **Customer Data Ownership**: Each tenant owns its underlying operational data. ChainBridge processes that data only to provide the ChainBridge platform and related services, as agreed with the tenant.
- **Platform & Model IP**: ChainBridge owns the platform code, model architectures, generic model components, and generic features and metrics that are not uniquely tied to a single tenant.
- **Usage Boundaries**: Even where ChainBridge owns model artifacts, use of Customer Data to create or update those artifacts is constrained by the data use modes and tenant choices defined in this policy.

## 3. Two-Layer Brain (Model Architecture)

ChainIQ is designed as a **two-layer brain**:

- **Global Base Model (Layer 1)**
  - Learns anonymized, aggregated patterns across multiple tenants **who explicitly opt in**.
  - Captures general logistics relationships: lane-level risk, seasonality, macro patterns, modality differences, typical exception patterns, etc.
  - Does **not** retain raw customer identifiers (names, full addresses, contract rates, or other directly identifying fields) in its training corpus.

- **Tenant-Specific Overlays (Layer 2)**
  - Fine-tunes, rules, thresholds, and configuration specific to a single tenant’s history and preferences.
  - Examples: tenant-specific risk tolerances, preferred carriers, custom exception playbooks, bespoke settlement rules.
  - Not shared with other tenants.

**Opt-out tenants** can still fully use ChainBridge: their data trains **only** their tenant-specific overlays and is not contributed to the Global Base Model.

**Opt-in tenants** allow anonymized and aggregated patterns from their data (including sandbox / retrospective pilots) to be used to improve the Global Base Model, subject to the anonymization rules below.

## 4. Data Use Options for Tenants

Tenants can choose how their data is used for model training. Names and defaults may change in V1+, but V0 defines two clear modes:

### Mode A – Private-Only Training

- Tenant data is used **only** to train and update models that serve that tenant.
- No features, labels, or patterns derived from the tenant’s data are used to train or fine-tune the Global Base Model.
- The tenant still benefits from the current Global Base Model trained from other opt-in tenants (if available), but does not contribute to it.

### Mode B – Network-Contribution Training

- Tenant data (including sandbox / retrospective data) is used to:
  - Train and update tenant-specific overlays; **and**
  - Contribute anonymized, aggregated patterns to the Global Base Model.
- Only aggregated, de-identified signals are used for the Global Base Model (see Anonymization & Aggregation).
- Opt-in can be configured at the tenant level and, in future versions, may be configurable at dataset or use-case level.

### Default Mode (TBD)

- **TBD**: The default mode for new tenants is a product / legal decision and will be finalized before GA.
- Regardless of the default, tenants must have a clear, in-product way to view and change their mode.

## 5. Sandbox & Retrospective Pilots

### 5.1 Definition

- A **sandbox** or **retrospective pilot** uses 3–6+ months of historical shipment and financial data to simulate how ChainBridge and ChainIQ would have behaved.
- No real money moves in sandbox: ChainPay and all financial / payout actions are simulated only.
- Sandbox environments are governed by the **same privacy and security standards** as production.

### 5.2 Data Usage in Sandbox

- If a tenant is in **Mode A – Private-Only**:
  - Sandbox data is used to tune and evaluate that tenant’s overlays only.
  - Sandbox data does **not** contribute to the Global Base Model.

- If a tenant is in **Mode B – Network-Contribution**:
  - Sandbox data may contribute anonymized, aggregated signals to the Global Base Model, in addition to tuning tenant-specific overlays.
  - Contributions follow the anonymization and aggregation safeguards in this document.

## 6. Anonymization & Aggregation

When tenant data is used to train or update the Global Base Model (Mode B), ChainBridge applies the following high-level safeguards:

- **No Raw Identifiers**: Global training pipelines do not use raw names, full street addresses, contract IDs, or other direct identifiers as model inputs.
- **Aggregation by Lane / Region / Counterparty Class**: Features are aggregated to levels such as lane, region, carrier-code, or service-class, not specific shipment IDs.
- **Hashing / Tokenization**: Where identifiers must be tracked for quality or deduplication, they are hashed or tokenized so they cannot be trivially reversed without internal keys.
- **Minimum Group Sizes**: Aggregations used for training and analytics must meet minimum group sizes to reduce the risk of exposing information about a single tenant or counterparty.
- **Model Design**: We avoid architectures and prompts that are likely to memorize or regurgitate specific contract terms, private rates, or other sensitive data.

These safeguards will be expanded and hardened in future versions in collaboration with customers and legal/compliance advisors.

## 7. Explainability, Logging & Decision Records

ChainBridge aims for **glass-box**, explainable decisions, particularly where risk and money are involved.

- Each material risk decision or settlement recommendation includes:
  - A set of `top_factors` describing which inputs most influenced the outcome.
  - A human-readable `summary_reason` suitable for operators, risk officers, and auditors.

- **DecisionRecords**:
  - Every key decision (e.g., HOLD vs APPROVE, payout amount, exception route) is logged as a DecisionRecord.
  - DecisionRecords include at least: timestamp, tenant, relevant entities (e.g., shipment, invoice, exception), model version, key inputs, outputs, and explanations.

- **Access for Tenants**:
  - Tenants can review DecisionRecords via APIs and cockpit views, subject to role-based access.
  - DecisionRecords are retained according to the retention policy (see below) to support internal and external audits.

## 8. Retention & Deletion (V0 Outline)

The exact timelines and regulatory mappings will be defined with customers and counsel. V0 commits to the following principles:

- **Operational Data Retention**:
  - Operational records (shipments, exceptions, settlements) are retained according to customer agreements and applicable regulations.
  - Retention periods may vary by tenant and region.

- **Derived Data & Training Sets**:
  - Where feasible, derived features and training snapshots are tagged so they can respect tenant-level deletion or non-retention requests.
  - ChainBridge will maintain processes to remove or mask tenant data from future training cycles upon a verified deletion request.

- **Tenant Offboarding**:
  - When a tenant leaves, ChainBridge removes or anonymizes their raw Customer Data from active systems within an agreed timeline.
  - Global models may continue to benefit from non-attributable patterns learned while the tenant participated, but those models will not retain accessible raw samples or identifiers.

These principles will be expanded in V1+ with explicit timelines and regulatory references.

## 9. Versioning & Changes

- This document is **V0** and may evolve as the product matures and regulatory requirements change.
- Material changes to how tenant data can be used for training (especially for the Global Base Model) will:
  - Be versioned and documented in product changelogs and policy updates.
  - Require explicit opt-in for broader or materially different data usage.
  - Be communicated with reasonable notice before taking effect.

## 10. Snippets for Decks & POCs

### 10.1 Two-Layer Brain (Global + Tenant)

> ChainIQ uses a two-layer brain: a neutral global base model that learns anonymized patterns across opt-in customers, and tenant-specific overlays that capture each shipper or broker’s unique rules and risk tolerances. Opt-out tenants still benefit from ChainBridge but keep their data siloed to their own models.

### 10.2 Data Options (Private vs Network Contribution)

> Every tenant can choose how their data trains ChainIQ. In Private-Only mode, your data only trains models that serve your org. In Network-Contribution mode, anonymized patterns from your lanes and history help strengthen a shared global brain—without exposing your contracts or counterparties.

### 10.3 Sandbox & Retrospective Pilots

> ChainBridge supports safe sandbox pilots using 3–6 months of history: money never moves, but the same privacy controls apply. Depending on your data mode, your sandbox runs can either stay private or anonymously strengthen the global base model while you evaluate value and fit.
