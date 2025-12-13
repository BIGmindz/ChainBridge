# ChainPay v0.1 — Settlement Brain & Policy Catalog

> “Clear incentives, clean contracts.” — ChainPay design mantra

ChainPay is the **settlement brain of ChainBridge** — it turns shipment events and risk scores into **event‑driven, milestone‑based cash flows** with full auditability. It does **not** become a broker or carrier; it orchestrates **how and when** funds flow between parties based on risk, value, and events.

v0.1 focuses on an **off‑chain ledger representation** of settlement events and policies. Future versions may introduce tokenized rails, smart contracts, and multi‑currency on‑chain settlement.

---

## 1. What is ChainPay v0.1?

ChainPay v0.1 is a **policy engine + event‑to‑settlement mapping layer** that sits between:

- **ChainIQ (Maggie)** — risk scoring and policy recommendations per shipment.
- **ChainBridge Core APIs (Cody)** — shipment lifecycle, events, and ledgers.
- **The OC (Sonny)** — operator cockpit for risk, exceptions, and settlement approvals.

### v0.1 Scope

- **In scope**:
  - A **settlement policy catalog** keyed by risk band and shipment attributes.
  - **Event‑driven settlement flows** for milestone‑based release of funds.
  - **DecisionRecords** describing which policy was applied and why.
  - **Off‑chain settlement ledger representation** of milestones and releases.
  - **API‑facing views** (read/write contracts) so Cody can implement REST endpoints.
  - **Operator experience** guidelines so Sonny can design OC panels.

- **Out of scope for v0.1** (can be planned as roadmap):
  - On‑chain smart contracts.
  - Tokenized settlement rails or stablecoins.
  - Multi‑currency FX routing.
  - Automated policy re‑selection on mid‑journey risk changes (v0.1 logs & recommends; humans decide).

---

## 2. Core Concepts

### 2.1 SettlementPolicy

A **SettlementPolicy** is a named template describing **how shipment value is split across events** and what approvals are required. Examples:

- `LOW_RISK_FAST_V1`
- `MODERATE_BALANCED_V1`
- `HIGH_RISK_GUARDED_V1`
- `CRITICAL_REVIEW_V1`

Each policy is:

- **Versioned** (suffix `_V1`, `_V2`, …) so changes are traceable.
- **Band‑aware** — associated with a ChainIQ **risk band**.
- **Explainable** — summarized in 1–2 sentences (glass‑box requirement).

Conceptual fields:

- `code`: unique identifier, e.g. `LOW_RISK_FAST_V1`.
- `display_name`: human‑readable label, e.g. “Low Risk — Fast Track”.
- `risk_band`: `LOW`, `MODERATE`, `HIGH`, `CRITICAL`.
- `milestones`: ordered list of `SettlementMilestone` definitions.
- `approval_rules`: who must approve which milestones under what conditions.
- `description`: short narrative that can be surfaced in UI.

### 2.2 SettlementMilestone

A **SettlementMilestone** defines **when** and **how much** of the shipment value can be released.

Key attributes:

- `name`: business label, e.g. `PICKUP`, `DELIVERY`, `CLAIM_WINDOW`.
- `event_type`: canonical event that can complete this milestone, e.g.
  - `PICKUP_CONFIRMED`
  - `DELIVERY_CONFIRMED`
  - `CLAIM_WINDOW_END`
- `percentage`: fraction of total shipment value allocated to this milestone (0–100).
- `preconditions` (examples):
  - Shipment status in allowed set (e.g., `IN_TRANSIT`, `DELIVERED`).
  - No **open high‑severity exceptions**.
  - All upstream milestones `COMPLETED`.
- `postconditions` (examples):
  - A `SettlementInstruction` has been emitted.
  - Cash ledger updated.
  - DecisionRecord logged.
- `approval_requirements`: role‑based gatekeeping for release (Finance, Risk, Ops, Senior).

### 2.3 SettlementInstruction

A **SettlementInstruction** is the concrete outcome of applying a policy to events. It answers:

> “Who gets what, when, and why?”

Conceptual fields:

- `shipment_id`
- `instruction_id`
- `policy_code`
- `milestone_name`
- `event_id` (that triggered this instruction)
- `amount_usd` (or currency‑aware amount)
- `percentage`
- `beneficiary` (carrier, broker, other party)
- `status`: `PENDING`, `EXECUTED`, `REJECTED`, `ON_HOLD`.
- `created_at`, `executed_at`
- `explanation`: 1–2 sentence reason string (glass‑box requirement), e.g.
  - “Released 70% at delivery under LOW_RISK_FAST_V1 — risk band LOW, no open exceptions, approvals satisfied.”

---

## 3. First Use Case — 20/70/10 for Low‑Risk Shipments

The canonical low‑risk pattern for ChainPay v0.1 is **20/70/10**:

- **20% at pickup**
  - Purpose: provide working‑capital liquidity to driver/carrier.
  - Event: `PICKUP_CONFIRMED`.
  - Preconditions: shipment created, pickup confirmed, no critical exceptions.

- **70% at confirmed delivery**
  - Purpose: release the bulk of funds when service is substantially fulfilled.
  - Event: `DELIVERY_CONFIRMED`.
  - Preconditions: delivery confirmed, no high‑severity open claims, all required approvals present.

- **10% after claim window end**
  - Purpose: retain a small safety margin for late claims/adjustments.
  - Event: `CLAIM_WINDOW_END`.
  - Preconditions: claim window lapsed, no unresolved disputes that would block final release.

Default policy mapping:

- Low‑risk shipments (risk band `LOW`, value ≤ high‑value threshold) map to:
  - `LOW_RISK_FAST_V1` with milestones: 20% / 70% / 10%.

---

## 4. How ChainIQ Influences ChainPay

### 4.1 Risk Bands

ChainIQ (Maggie) produces a `ShipmentRiskAssessment` with a numeric risk score and band. v0.1 assumes the following bands:

- `LOW`
- `MODERATE`
- `HIGH`
- `CRITICAL`

Each band has a **default SettlementPolicy** and an associated milestone pattern.

### 4.2 Risk Band → Default SettlementPolicy Mapping

High‑level mapping:

- `LOW` → `LOW_RISK_FAST_V1`
- `MODERATE` → `MODERATE_BALANCED_V1`
- `HIGH` → `HIGH_RISK_GUARDED_V1`
- `CRITICAL` → `CRITICAL_REVIEW_V1`

ChainIQ may additionally provide a **`SettlementPolicyRecommendation`** object containing:

- `recommended_policy_code` (e.g., `HIGH_RISK_GUARDED_V1`)
- `risk_band`
- `risk_score`
- `explanation` (top factors, rationale)

ChainPay v0.1 behavior:

1. **On shipment creation**:
   - ChainIQ scores the shipment and returns `ShipmentRiskAssessment` (+ optional `SettlementPolicyRecommendation`).
   - ChainPay chooses the **default policy** for that risk band, optionally adjusted for value thresholds (see catalog below).
   - ChainPay logs a **DecisionRecord**:
     - “Policy selected = LOW_RISK_FAST_V1. Reason: risk band LOW, value < 100k, no overrides.”

2. **On mid‑journey re‑score**:
   - ChainIQ may rescore a shipment.
   - v0.1: ChainPay **logs the new assessment and a recommendation** (e.g., “consider switching to HIGH_RISK_GUARDED_V1”), but **does not auto‑switch** policy.
   - Any policy change is a **governed action** requiring human approval (Risk + Finance) and is tracked as a separate DecisionRecord.

---

## 5. Settlement Policy Catalog (v0.1)

This section defines the initial **policy catalog** for ChainPay v0.1.

### 5.1 Risk Band → Policy Table

| Risk Band | Policy Code           | Milestones (Value Split)                            | Who Approves?                              | Narrative                                  |
|----------:|-----------------------|------------------------------------------------------|--------------------------------------------|--------------------------------------------|
| LOW       | `LOW_RISK_FAST_V1`    | 20% PICKUP / 70% DELIVERY / 10% CLAIM_WINDOW        | Finance auto‑approve under value threshold | “Trusted lanes, fast cash.”                |
| MODERATE  | `MODERATE_BALANCED_V1`| 10% PICKUP / 60% DELIVERY / 30% CLAIM_WINDOW        | Finance + Ops for overrides                | “Normal freight, balanced risk.”           |
| HIGH      | `HIGH_RISK_GUARDED_V1`| 0% PICKUP / 60% DELIVERY / 40% CLAIM_WINDOW         | Risk + Finance for releases                | “Guarded flows; keep powder dry.”          |
| CRITICAL  | `CRITICAL_REVIEW_V1`  | 0% PICKUP / 40% DELIVERY / 60% CLAIM_WINDOW         | Senior Risk/Finance approval               | “Red corridor; human in the loop.”         |

### 5.2 High‑Value Shipments

**High‑value threshold assumption (v0.1):**

- `HIGH_VALUE_USD_THRESHOLD = 100_000` (can be made tenant‑configurable later).

Behavior:

- If `total_value_usd > HIGH_VALUE_USD_THRESHOLD`, ChainPay **escalates one band up** for settlement behavior, even if the risk band is lower.
  - `LOW` risk, value > 100k → use `MODERATE_BALANCED_V1` pattern by default.
  - `MODERATE` risk, value > 100k → use `HIGH_RISK_GUARDED_V1` pattern.
  - `HIGH` risk, value > 100k → use `CRITICAL_REVIEW_V1` pattern.
  - `CRITICAL` risk remains `CRITICAL_REVIEW_V1`.

A DecisionRecord must capture this escalation, e.g.:

> “Policy escalated from LOW_RISK_FAST_V1 to MODERATE_BALANCED_V1 due to value 250k > 100k threshold.”

### 5.3 Defaults vs Tenant Overlays

- These v0.1 policies are **system defaults**.
- Tenants may later define **overlays** that adjust percentages or approvals while inheriting from a base policy.
- All policies are **versioned**:
  - E.g. `LOW_RISK_FAST_V1`, `LOW_RISK_FAST_V2`.
  - Changes must be backward‑compatible for existing shipments or require explicit migration rules.

---

## 6. Event → Settlement Flow (v0.1)

This section describes how **events** are translated into **settlement actions** under ChainPay.

### 6.1 Inputs

At minimum, ChainPay needs:

- **Shipment identity & value**
  - `shipment_id`
  - `total_value_usd`
  - Parties (payer, payee(s))

- **Events**
  - `PICKUP_CONFIRMED`
  - `DELIVERY_CONFIRMED`
  - `CLAIM_WINDOW_END`
  - (Future: `PARTIAL_DELIVERY`, `CANCELLATION`, etc.)

- **Risk inputs** (from ChainIQ)
  - `ShipmentRiskAssessment` (score, band, factors).
  - `SettlementPolicyRecommendation` (recommended policy code, explanation).

- **Governance context**
  - Required approvals by role (Risk, Finance, Ops, Senior).
  - Open exceptions or disputes.

### 6.2 Flow: Shipment Creation

1. Shipment is created in ChainBridge core.
2. ChainBridge calls ChainIQ `/api/v1/risk/score` to obtain `ShipmentRiskAssessment`.
3. ChainIQ may also provide a `SettlementPolicyRecommendation`.
4. ChainPay evaluates:
   - `risk_band` from assessment.
   - `total_value_usd` vs `HIGH_VALUE_USD_THRESHOLD`.
   - Any tenant or product overlays.
5. ChainPay selects effective policy:
   - Base: band → default policy.
   - Adjusted: escalate band if high‑value.
   - Optional: override with explicit recommendation if governance allows.
6. ChainPay logs a **DecisionRecord**:
   - `decision_type`: `SETTLEMENT_POLICY_SELECTION`.
   - `policy_code`.
   - `risk_band`, `risk_score`.
   - `value_usd`.
   - `reason`: explainable narrative.

### 6.3 Flow: Event Handling (e.g., DELIVERY_CONFIRMED)

When a relevant event arrives:

1. **Locate shipment & policy**
   - Load `ShipmentSettlementView` for `shipment_id`.
   - Identify the milestone tied to the event, e.g. `DELIVERY`.

2. **Check preconditions**
   - Previous milestones in this policy are `COMPLETED`.
   - No **open high‑severity exceptions** (from OC / exception engine).
   - Event payload is valid and not already processed (idempotency).

3. **Check approvals**
   - Based on `risk_band`, `policy_code`, `total_value_usd`, and milestone.
   - Ensure required roles have approved (e.g., Finance only, or Risk + Finance).

4. **If all checks pass**:
   - Compute release amount: `percentage * total_value_usd`.
   - Emit a **SettlementInstruction**:
     - “Release 70% ($X) to carrier Y under LOW_RISK_FAST_V1 on DELIVERY.”
   - Update settlement ledger and mark milestone `COMPLETED`.
   - Update `ShipmentSettlementView`:
     - `released_total_usd`.
     - `cash_in_flight_usd`.
   - Log a **DecisionRecord**:
     - `decision_type`: `SETTLEMENT_RELEASE`.
     - `policy_code`, `milestone_name`, `amount_usd`.
     - `reason` string (glass‑box explanation).

5. **If checks fail**:
   - Mark milestone as `ON_HOLD` or keep `PENDING`.
   - Log a DecisionRecord with reason (e.g., missing approvals, open exceptions).
   - Surface status + reason in OC for operator action.

### 6.4 Flow: Claim Window End

On `CLAIM_WINDOW_END` event:

1. Repeat the same flow as above with the final `CLAIM_WINDOW` milestone.
2. Ensure there are **no unresolved disputes** that block release.
3. If approvals and conditions are met, emit final `SettlementInstruction`.
4. Log DecisionRecord such as:

> “Released remaining 10% at claim window end under LOW_RISK_FAST_V1 — no open claims, approvals satisfied.”

### 6.5 Fallbacks & Holds

- If ChainIQ risk score **increases mid‑journey**:
  - v0.1 logs a new DecisionRecord:
    - `decision_type`: `RISK_REASSESSMENT`.
    - `previous_band`, `new_band`, `reason`.
  - v0.1 may **freeze remaining milestones** (no auto‑release) or provide a **recommendation**:
    - “Recommend switching to HIGH_RISK_GUARDED_V1; require Risk + Finance approval.”
  - Actual policy switch is a **manual action** via OC and backend API (governed by ALEX).

- If a severe exception or dispute is raised:
  - ChainPay can mark future milestones as `ON_HOLD` pending resolution.
  - No further SettlementInstructions are emitted until the hold is cleared.

---

## 7. API‑Facing Structures (for Cody)

This section describes how ChainPay state should be exposed over the API. It is a **specification**, not an implementation.

### 7.1 ShipmentSettlementView

A **ShipmentSettlementView** is what OC and external clients use to see the current settlement state for a single shipment.

Example shape:

```json
{
  "shipment_id": "SH123",
  "total_value_usd": 100000,
  "currency": "USD",
  "policy_code": "LOW_RISK_FAST_V1",
  "risk_band": "LOW",
  "risk_score": 22.5,
  "high_value_escalated": false,
  "milestones": [
    {
      "name": "PICKUP",
      "event_type": "PICKUP_CONFIRMED",
      "percentage": 20.0,
      "status": "COMPLETED",
      "allocated_amount_usd": 20000,
      "released_amount_usd": 20000,
      "event_id": "EVT_PICKUP_1",
      "completed_at": "2025-12-07T12:34:56Z",
      "requires_approvals": ["FINANCE"],
      "approvals": [
        { "role": "FINANCE", "approved_by": "user123", "approved_at": "2025-12-07T12:30:00Z" }
      ]
    },
    {
      "name": "DELIVERY",
      "event_type": "DELIVERY_CONFIRMED",
      "percentage": 70.0,
      "status": "PENDING",
      "allocated_amount_usd": 70000,
      "released_amount_usd": 0,
      "event_id": null,
      "completed_at": null,
      "requires_approvals": ["FINANCE"],
      "approvals": []
    },
    {
      "name": "CLAIM_WINDOW",
      "event_type": "CLAIM_WINDOW_END",
      "percentage": 10.0,
      "status": "PENDING",
      "allocated_amount_usd": 10000,
      "released_amount_usd": 0,
      "requires_approvals": ["FINANCE"],
      "approvals": []
    }
  ],
  "cash_in_flight_usd": 80000,
  "released_total_usd": 20000,
  "held_total_usd": 0,
  "last_decision": {
    "decision_type": "SETTLEMENT_RELEASE",
    "policy_code": "LOW_RISK_FAST_V1",
    "milestone_name": "PICKUP",
    "reason": "Released 20% at pickup under LOW_RISK_FAST_V1 — risk band LOW, value < threshold, approvals satisfied.",
    "decided_at": "2025-12-07T12:34:56Z"
  }
}
```

Notes:

- `cash_in_flight_usd` = **total_value_usd − released_total_usd**.
- `held_total_usd` can be non‑zero if funds are allocated but deliberately held due to exceptions or governance.

### 7.2 Policy Catalog API

**Endpoint (read‑only):**

- `GET /api/v1/settlement/policies/catalog`

Response shape (conceptual):

```json
[
  {
    "code": "LOW_RISK_FAST_V1",
    "display_name": "Low Risk — Fast Track",
    "risk_band": "LOW",
    "milestones": [
      { "name": "PICKUP", "event_type": "PICKUP_CONFIRMED", "percentage": 20.0 },
      { "name": "DELIVERY", "event_type": "DELIVERY_CONFIRMED", "percentage": 70.0 },
      { "name": "CLAIM_WINDOW", "event_type": "CLAIM_WINDOW_END", "percentage": 10.0 }
    ],
    "approval_rules": {
      "default": ["FINANCE"],
      "high_value_override": ["RISK", "FINANCE"]
    },
    "description": "Trusted lanes, fast cash. 20/70/10 with Finance auto‑approval under value threshold.",
    "version": 1,
    "active": true
  },
  {
    "code": "MODERATE_BALANCED_V1",
    "display_name": "Moderate Risk — Balanced",
    "risk_band": "MODERATE",
    "milestones": [
      { "name": "PICKUP", "event_type": "PICKUP_CONFIRMED", "percentage": 10.0 },
      { "name": "DELIVERY", "event_type": "DELIVERY_CONFIRMED", "percentage": 60.0 },
      { "name": "CLAIM_WINDOW", "event_type": "CLAIM_WINDOW_END", "percentage": 30.0 }
    ],
    "approval_rules": {
      "default": ["FINANCE"],
      "overrides": ["FINANCE", "OPS"]
    },
    "description": "Normal freight, balanced risk.",
    "version": 1,
    "active": true
  },
  {
    "code": "HIGH_RISK_GUARDED_V1",
    "display_name": "High Risk — Guarded",
    "risk_band": "HIGH",
    "milestones": [
      { "name": "DELIVERY", "event_type": "DELIVERY_CONFIRMED", "percentage": 60.0 },
      { "name": "CLAIM_WINDOW", "event_type": "CLAIM_WINDOW_END", "percentage": 40.0 }
    ],
    "approval_rules": {
      "default": ["RISK", "FINANCE"]
    },
    "description": "Guarded flows; keep powder dry.",
    "version": 1,
    "active": true
  },
  {
    "code": "CRITICAL_REVIEW_V1",
    "display_name": "Critical — Human Review",
    "risk_band": "CRITICAL",
    "milestones": [
      { "name": "DELIVERY", "event_type": "DELIVERY_CONFIRMED", "percentage": 40.0 },
      { "name": "CLAIM_WINDOW", "event_type": "CLAIM_WINDOW_END", "percentage": 60.0 }
    ],
    "approval_rules": {
      "default": ["SENIOR_RISK", "SENIOR_FINANCE"]
    },
    "description": "Red corridor; human in the loop.",
    "version": 1,
    "active": true
  }
]
```

### 7.3 Shipment Settlement API

**Endpoint (read‑only):**

- `GET /api/v1/settlement/shipments/{shipment_id}` → returns `ShipmentSettlementView`.

**Approvals (future, write):**

- `POST /api/v1/settlement/shipments/{shipment_id}/approve-milestone`

  - Request body (conceptual):

    ```json
    {
      "milestone_name": "DELIVERY",
      "role": "FINANCE",
      "approved_by": "user123",
      "comment": "OK to release delivery funds."
    }
    ```

  - Backend must integrate with ALEX governance and Cody’s auth stack to ensure:
    - Role is allowed to approve for this tenant and shipment.
    - Approval is logged and auditable.

  - On success, milestone approval state is updated and may **unblock** pending releases.

---

## 8. Operator Experience (OC — Sonny)

The OC should feel like a **pilot cockpit** or **train conductor panel**: a clear view of what is safe to release vs. what is being held for turbulence.

### 8.1 Settlement Panel Layout

For a selected shipment, show **two adjacent panels**:

1. **Risk Panel (ChainIQ)**
   - Risk band & score (e.g., “LOW — 22.5”).
   - Key factors / explanation.
   - Any recent re‑scores and band changes.

2. **Settlement Panel (ChainPay)**
   - Policy name & band, e.g.: `LOW_RISK_FAST_V1 — Low risk`.
   - Short narrative: e.g., “Trusted lanes, fast cash. 20/70/10 pattern.”
   - Progress bar across milestones (e.g., 20 / 70 / 10 segments).
   - Status labels per segment:
     - `Released`
     - `In Flight`
     - `Held`
   - Totals:
     - `Released total`
     - `Cash in flight`
     - `Held` (if applicable).

### 8.2 Approvals & Actions

v0.1 may primarily **visualize** and log approvals rather than fully orchestrate them. UI patterns:

- For each milestone row:
  - Show **status** (`PENDING`, `COMPLETED`, `ON_HOLD`).
  - Show **required roles** for approval.
  - If the current user has the right role and milestone is `PENDING` but unapproved:
    - Show a button such as **“Approve milestone”** (even if v0.1 only simulates or records the intent).

- Once all approvals are in place and preconditions satisfied:
  - The OC can display a **call‑to‑action**:
    - “Ready to release 70% ($X) at DELIVERY.”

### 8.3 Copy Hints

- **Low risk** (LOW_RISK_FAST_V1):
  - “Fast track settlement enabled. Remaining funds held for standard claims.”

- **Moderate risk** (MODERATE_BALANCED_V1):
  - “Balanced settlement pattern. More value held until claims window closes.”

- **High risk** (HIGH_RISK_GUARDED_V1):
  - “Guarded settlement in effect. Additional funds held until risk clears or claims window closes.”

- **Critical risk** (CRITICAL_REVIEW_V1):
  - “Critical lane under review. Releases require senior approval and may be staged.”

Glass‑box requirement: The OC should always be able to show a concise explanation near the top of the panel:

> “Policy LOW_RISK_FAST_V1 selected because risk band LOW, value < $100k, standard fast track enabled.”

---

## 9. Future On‑Chain Roadmap (Out of Scope for v0.1)

This section describes a **roadmap** only. v0.1 remains **internal ledger only**.

- **Stage 1 — Internal Ledger Only (v0.1)**
  - Settlement events and policies represented in an internal off‑chain ledger.
  - All flows, approvals, and DecisionRecords are stored in ChainBridge databases.

- **Stage 2 — Tokenized IOUs / Stablecoin Rails (XRPL)**
  - Represent settlement obligations as tokenized IOUs or stablecoins on XRPL.
  - Map internal `SettlementInstruction` objects to XRPL payments or token transfers.
  - Support programmable holds and releases tied to milestones.

- **Stage 3 — Chainlink‑Enabled Smart Contracts for Multi‑Chain Payouts**
  - Use Chainlink and smart contracts to orchestrate payouts across multiple chains.
  - Encode SettlementPolicies directly into contract logic.
  - Integrate off‑chain risk signals (from ChainIQ) as oracles feeding on‑chain rules.

All on‑chain evolution must preserve **glass‑box explanations** and respect governance rules defined by ALEX.

---

## 10. Role Expectations & Assumptions

### Maggie (ChainIQ)

- Produces `ShipmentRiskAssessment` and `SettlementPolicyRecommendation` for each shipment.
- Provides an explanation string and key factors that can be surfaced in OC.
- May trigger mid‑journey re‑scores that suggest more guarded policies (logged as recommendations).

### Cody (ChainPay API / Backend)

- Implements storage for:
  - Settlement policies and versions.
  - Shipment‑level settlement state (`ShipmentSettlementView`).
  - SettlementInstructions and DecisionRecords.
- Exposes APIs:
  - `GET /api/v1/settlement/policies/catalog`.
  - `GET /api/v1/settlement/shipments/{shipment_id}`.
  - `POST /api/v1/settlement/shipments/{shipment_id}/approve-milestone` (future / governed).
- Enforces role‑based approvals in coordination with ALEX governance.

### Sonny (OC / Frontend)

- Builds the Settlement panel alongside the Risk panel.
- Visualizes policies, milestones, cash in flight, and approvals.
- Gives operators clear, glass‑box explanations of **why** funds are released or held.
- Provides intuitive controls for approvals and, in future, policy overrides.

### Assumptions (v0.1)

- **High value** is defined as **shipments with `total_value_usd` > $100,000**; this can later become a tenant‑configurable threshold.
- Risk bands are **mutually exclusive** and **exhaustive** (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`).
- ChainIQ remains the **source of truth** for risk bands and scores.
- ALEX defines who can approve which milestones and policy changes; Cody enforces; Sonny exposes the interactions.

---

End of ChainPay v0.1 product spec & settlement policy catalog.
