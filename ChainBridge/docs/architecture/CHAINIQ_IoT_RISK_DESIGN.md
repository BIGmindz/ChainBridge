# ChainIQ IoT Risk Design (Glass-Box)

**Status:** PRODUCTION READY
**Version:** 2.0.0
**Owner:** GID-10 Maggie (ML Lead)
**Phase:** Production / LST-01 Integration
**Last Updated:** 2025-12-02
**Cross-refs:**
- [ChainBridge Reality Baseline](../product/CHAINBRIDGE_REALITY_BASELINE.md)
- [ChainSense IoT Integration](../product/ChainSense_IoT_Integration.md)
- [ALEX Governance Gate](../ci/ALEX_GOVERNANCE_GATE.md)
- [LST-01 Token Specification](../../chainbridge/tokens/)

---

## Document Index

| Section | Description |
|---------|-------------|
| [1. Overview](#1-overview) | Executive summary and system purpose |
| [2. LST-01 Token Integration](#2-lst-01-token-integration) | Token lifecycle and ChainIQ linkages |
| [3. Commercial Audit](#3-commercial-audit-the-so-what) | Business impact and decision points |
| [4. Data Interrogation](#4-data-interrogation-feature-map) | Feature engineering specification |
| [5. Glass-Box Risk Logic](#5-glass-box-risk-logic) | Deterministic scoring rules |
| [6. IoT → ChainIQ → Settlement Pipeline](#6-iot--chainiq--settlement-pipeline) | End-to-end data flow |
| [7. ALEX Governance Rules](#7-alex-governance-rules) | Governance gates and thresholds |
| [8. Adversarial Scenarios](#8-adversarial-scenarios) | Attack vectors and mitigations |
| [9. Risk Contract API](#9-risk-contract-api) | Output schema specification |
| [10. Integration Points](#10-integration-points) | Backend implementation targets |
| [11. Failure Modes](#11-failure-modes) | Error handling and escalation |
| [12. ML Evolution Roadmap](#12-ml-evolution-roadmap) | Future ML enhancements |

---

## 1. Overview

ChainIQ is the **intelligence layer** of ChainBridge—a Glass-Box risk scoring engine that:

1. **Detects anomalies** in IoT telemetry (GPS, ELD, temperature, shock)
2. **Predicts detention** and reweigh risk
3. **Identifies fraudulent accessorials** (AT-02 claims without proof)
4. **Flags IoT spoofing** and route deviations
5. **Scores carrier/shipper integrity** for overbilling patterns
6. **Gates payments** through ALEX-governed settlement logic

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Interpretability** | Every risk score includes SHAP-style feature contributions |
| **Determinism** | Same input → Same output (versioned, reproducible) |
| **Token-Aligned** | All outputs link to LST-01 primitives (MT-01, AT-02, IT-01) |
| **Adversarially Tested** | All scoring paths stress-tested against fraud vectors |
| **ALEX-Governed** | Settlement gates require ALEX approval |

### ChainBridge Mantra (ALEX-Enforced)

> **Speed without proof gets blocked.**
> **Proof without pipes doesn't scale.**
> **Pipes without cash don't settle.**
> **You need all three.**

ChainIQ provides the **proof** component. If proof is missing or suspect, ALEX blocks the flow.

---

## 2. LST-01 Token Integration

ChainIQ does not operate in isolation—it is **token-aware**. Every risk decision maps to the LST-01 lifecycle.

### Token Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LST-01 TOKEN LIFECYCLE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────┐                                                               │
│   │  ST-01  │ Shipment Root Token                                          │
│   │ CREATED │ ─────────────────────────────────────────────────────────────│
│   └────┬────┘                                                               │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────┐    ┌─────────────────────────────────────────────────────┐   │
│   │  MT-01  │◄───│ IoT Events (ChainSense) + Seeburger EDI Events     │   │
│   │CREATED  │    │ GPS, ELD, Temperature, Door, Shock, ETA             │   │
│   └────┬────┘    └─────────────────────────────────────────────────────┘   │
│        │                                                                    │
│        │ validate()                                                         │
│        ▼                                                                    │
│   ┌─────────┐    ┌─────────────────────────────────────────────────────┐   │
│   │  MT-01  │◄───│ ChainIQ Risk Scoring                                │   │
│   │VERIFIED │    │ risk_score, confidence, anomaly_flags               │   │
│   └────┬────┘    └─────────────────────────────────────────────────────┘   │
│        │                                                                    │
│        │ apply()                                                            │
│        ▼                                                                    │
│   ┌─────────┐                                                               │
│   │  AT-02  │ Accessorial Proposal (detention, fuel, lumper)               │
│   │PROPOSED │                                                               │
│   └────┬────┘                                                               │
│        │                                                                    │
│        │ attach_proof() ──► ChainIQ validates MT-01 linkage                │
│        ▼                                                                    │
│   ┌─────────────┐    ┌─────────────────────────────────────────────────┐   │
│   │    AT-02    │◄───│ SxT ProofPack (hash, source, metadata)          │   │
│   │PROOF_ATTACHED│    │ proof_hash links to verifiable on-chain proof   │   │
│   └──────┬──────┘    └─────────────────────────────────────────────────┘   │
│          │                                                                  │
│          │ verify() ──► ALEX governance check + policy_match_id            │
│          ▼                                                                  │
│   ┌─────────┐    ┌─────────────────────────────────────────────────────┐   │
│   │  AT-02  │◄───│ ALEX Governance Gate                                │   │
│   │VERIFIED │    │ policy_match_id required                            │   │
│   └────┬────┘    └─────────────────────────────────────────────────────┘   │
│        │                                                                    │
│        │ publish()                                                          │
│        ▼                                                                    │
│   ┌─────────┐                                                               │
│   │  IT-01  │ Invoice Token (computed from AT-02 + MT-01)                  │
│   │COMPUTED │                                                               │
│   └────┬────┘                                                               │
│        │                                                                    │
│        │ publish() ──► requires alex_governance_id                         │
│        ▼                                                                    │
│   ┌──────────┐                                                              │
│   │  IT-01   │                                                              │
│   │PUBLISHED │                                                              │
│   └────┬─────┘                                                              │
│        │                                                                    │
│        │ settle() ──► requires PT-01 linkage                               │
│        ▼                                                                    │
│   ┌─────────┐                                                               │
│   │  PT-01  │ Payment Token (XRPL escrow)                                  │
│   │INITIATED│                                                               │
│   └────┬────┘                                                               │
│        │                                                                    │
│        │ fund() → escrow() → release()                                     │
│        ▼                                                                    │
│   ┌─────────┐                                                               │
│   │  PT-01  │ Settlement Complete                                          │
│   │COMPLETE │                                                               │
│   └─────────┘                                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Token-Risk Mappings

| Token | ChainIQ Role | Risk Gates |
|-------|--------------|------------|
| **ST-01** | Root anchor for all risk scores | Cannot settle without PT-01 linkage |
| **MT-01** | Primary IoT/EDI event source | Must link to `iot_event_id` or `seeburger_event_id` |
| **AT-02** | Accessorial fraud detection target | Requires proof_hash beyond PROPOSED; ALEX policy_match_id for VERIFIED |
| **IT-01** | Invoice accuracy scoring | Requires ALEX alex_governance_id for PUBLISHED |
| **PT-01** | Settlement gate | Requires XRPL tx_hash; release_schedule for partial/final release |
| **CCT-01** | Carrier claim reconciliation | Tracks unproven AT-02 accessorials |

---

## 3. Commercial Audit: The "So What?"

Why does IoT data matter for ChainBridge? It is the physical **Proof** in our **Proof → Pay** mantra.

### Key Decisions Affected

| Decision | Current State | New (ChainIQ-Enabled) |
|----------|---------------|----------------------|
| **Payment Release** | Released if documents complete | **BLOCKED** if critical IoT alerts exist |
| **Reserve Requirement** | Static % based on shipper tier | **Dynamic Uplift** (+5-10%) on corridor instability |
| **Operator Attention** | Sort by static risk score | **Interrupt-driven** sorting on fresh anomalies |
| **AT-02 Approval** | Manual review | **Auto-reject** if MT-01 contradicts claim |
| **Carrier Scoring** | Historical reputation | **Real-time** overbilling pattern detection |

### Cognitive Loop: Commercial Audit

1. **Hypothesis:** Gating payments on telemetry health forces better device compliance.
2. **Risk:** False positives (bad sensor data) block legitimate payments.
3. **Mitigation:** Glass-box rules + manual override codes (`SENSOR_MALFUNCTION`).
4. **Validation:** Track false positive rate; target <2% override frequency.

---

## 4. Data Interrogation: Feature Map

ChainIQ derives features from multiple sources, organized into the **60-120 Core Feature Model** (Maggie PAC Task 1).

### 4.1 Feature Categories

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CHAINIQ FEATURE TAXONOMY                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐  │
│  │  IoT REAL-TIME (20)  │  │  OPERATIONAL (15)    │  │  ACCESSORIAL (15)│  │
│  │  ─────────────────── │  │  ─────────────────── │  │  ───────────────  │  │
│  │  GPS position        │  │  MT-01 milestones    │  │  AT-02 type       │  │
│  │  ELD hours           │  │  Terminal events     │  │  AT-02 amount     │  │
│  │  Temperature         │  │  Driver behavior     │  │  Proof presence   │  │
│  │  Door events         │  │  ETA deviation       │  │  Historical freq  │  │
│  │  Shock/impact        │  │  Route adherence     │  │  Carrier patterns │  │
│  │  Battery level       │  │  Dwell time          │  │  Time variance    │  │
│  │  Signal quality      │  │  Geofence triggers   │  │  Policy match     │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────┘  │
│                                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐  │
│  │  SPATIAL-TEMPORAL(15)│  │  CARRIER BEHAVIOR(10)│  │  INVOICE (10)    │  │
│  │  ─────────────────── │  │  ─────────────────── │  │  ───────────────  │  │
│  │  Corridor risk       │  │  Historical variance │  │  Line item count │  │
│  │  Weather conditions  │  │  Overbilling freq    │  │  Total vs quote  │  │
│  │  Traffic patterns    │  │  Proof compliance    │  │  Currency risk   │  │
│  │  Seasonal factors    │  │  On-time delivery    │  │  Payment terms   │  │
│  │  Geopolitical risk   │  │  Claim frequency     │  │  Dispute history │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Shipment-Level Features (Direct Impact)

*Used for individual `calculate_risk_score` calls. Linked to MT-01 tokens.*

| Feature Name | Definition | Source | Token Link | Intended Effect |
|:-------------|:-----------|:-------|:-----------|:----------------|
| `iot_critical_count_24h` | Count of `CRITICAL` alerts in last 24h | `snapshot.critical_alerts_24h` | MT-01.telemetry_snapshot | **+40 pts** (Hold Payment) |
| `iot_silence_hours` | Hours since `latest_reading` | `now() - snapshot.latest_readings[0].timestamp` | MT-01.timestamp | **+15-50 pts** (Ghosting) |
| `iot_temp_deviation` | Abs diff between `current_temp` and `set_point` | `snapshot.latest_readings` | MT-01.telemetry_snapshot | **Variable** (Spoilage risk) |
| `iot_device_battery` | Battery % of primary device | `snapshot.latest_readings` | MT-01.telemetry_snapshot | **+10 pts** (Warning) |
| `iot_door_events_anomaly` | Unexpected door open/close pattern | Door sensor timeline | MT-01 sequence | **+25 pts** (Tampering risk) |
| `iot_shock_detected` | Impact events above threshold | Shock sensor | MT-01.telemetry_snapshot | **+30 pts** (Damage risk) |
| `iot_gps_deviation` | Distance from expected route | GPS vs planned route | MT-01.location | **+20 pts** (Route deviation) |

### 4.3 Corridor-Level Features (Contextual Impact)

*Used for "Market Regime" adjustments. No direct token link—aggregated context.*

| Feature Name | Definition | Source | Intended Effect |
|:-------------|:-----------|:-------|:----------------|
| `corridor_instability_index` | % of active shipments with >1 critical alert | Aggregated from `live_positions` | **+10 pts** (Systemic risk) |
| `corridor_silence_ratio` | % of devices with >4h silence | Aggregated from `live_positions` | **Confidence ↓** |
| `corridor_weather_risk` | Severe weather probability | Weather API + route | **+5-15 pts** (Conditional) |
| `corridor_traffic_risk` | Congestion/accident probability | Traffic API + route | **+5-10 pts** (Conditional) |

### 4.4 Fleet-Level Features (System Health)

*Used for "Circuit Breakers". Affects all shipments under a carrier/broker.*

| Feature Name | Definition | Source | Intended Effect |
|:-------------|:-----------|:-------|:----------------|
| `fleet_offline_ratio` | `1 - (active_sensors / total_sensors)` | `IoTHealthSummary` | **Suspend Auto-Release** (If >20%) |
| `fleet_critical_rate` | % of fleet with critical alerts | `IoTHealthSummary` | **Reserve Uplift** (If >30%) |

### 4.5 Accessorial-Specific Features (AT-02 Fraud Detection)

*Used for AT-02 verification. Maggie PAC Task 4.*

| Feature Name | Definition | Source | Token Link | Fraud Signal |
|:-------------|:-----------|:-------|:-----------|:-------------|
| `at02_mt01_time_match` | AT-02 timestamp vs MT-01 timeline | AT-02.timestamp, MT-01 sequence | AT-02.relations.mt01_id | Mismatch → **+35 pts** |
| `at02_mt01_location_match` | AT-02 location vs MT-01 GPS | AT-02.metadata, MT-01.location | AT-02.relations.mt01_id | Mismatch → **+40 pts** |
| `at02_proof_present` | ProofPack attached | AT-02.proof_hash | AT-02.proof | Missing → **+30 pts** |
| `at02_historical_freq` | Carrier's AT-02 claim frequency | Historical AT-02 by carrier | CCT-01.at02_ids | >2σ → **+20 pts** |
| `at02_amount_variance` | Deviation from typical amount | Historical AT-02 amounts | CCT-01 | >2σ → **+15 pts** |

### 4.6 Invoice Integrity Features (IT-01 Accuracy)

*Used for IT-01 validation. Maggie PAC Task 5.*

| Feature Name | Definition | Source | Token Link | Integrity Signal |
|:-------------|:-----------|:-------|:-----------|:-----------------|
| `it01_total_vs_qt01` | Invoice total vs original quote | IT-01.total, QT-01.quoted_total | IT-01.relations.qt01_id | >15% variance → **+25 pts** |
| `it01_mileage_variance` | Invoiced miles vs actual GPS | IT-01.line_items, MT-01 path | IT-01.relations.mt01_ids | >10% variance → **+20 pts** |
| `it01_accessorial_ratio` | Accessorial % of total | IT-01.line_items (AT-02 sum) | IT-01.relations.at02_ids | >40% → **Flag** |
| `carrier_overbilling_score` | Historical overbilling frequency | IT-01 history by carrier | CCT-01 | >0.7 → **+30 pts** |

---

## 5. Glass-Box Risk Logic

We extend the existing `RISK_WEIGHTS` in `risk_engine.py` with explicit IoT rules and token-aware validation.

### 5.1 The Ruleset (IoT-Derived)

**Rule 1: The "Fresh Damage" Rule (IOT_CRITICAL_ALERT)**
```
IF iot_critical_count_24h > 0
THEN risk_score += 40
     severity = HIGH/CRITICAL
     reason_code = "IOT_CRITICAL_ALERT"
     recommended_action = "HOLD_PAYMENT"
     requires_proof = true
```

**Rule 2: The "Ghosting" Rule (IOT_SILENCE)**
```
IF iot_silence_hours >= 24
THEN risk_score += 50
     severity = HIGH
     reason_code = "IOT_SILENCE_CRITICAL"
     recommended_action = "HOLD_PAYMENT"

ELSE IF iot_silence_hours >= 4
THEN risk_score += 15
     reason_code = "IOT_SILENCE_WARNING"
     recommended_action = "MANUAL_REVIEW"
```

**Rule 3: The "Dying Battery" Pre-empt (IOT_BATTERY_RISK)**
```
IF iot_device_battery < 10% AND days_to_dest > 2
THEN risk_score += 10
     reason_code = "IOT_BATTERY_RISK"
     recommended_action = "ALERT_OPS"
```

**Rule 4: The "Corridor Chaos" Uplift (CORRIDOR_INSTABILITY)**
```
IF corridor_instability_index >= 0.30
THEN risk_score += 10
     reason_code = "CORRIDOR_INSTABILITY"
     reserve_uplift = +5%
```

**Rule 5: The "Route Deviation" Flag (ROUTE_DEVIATION)**
```
IF iot_gps_deviation > 50_miles AND NOT authorized_detour
THEN risk_score += 20
     reason_code = "ROUTE_DEVIATION"
     anomaly_flags.append("POTENTIAL_DIVERSION")
```

### 5.2 The Ruleset (Token-Aware)

**Rule 6: The "AT-02 Without Proof" Rule (AT02_PROOF_MISSING)**
```
IF at02.state IN ["PROOF_ATTACHED", "VERIFIED", "PUBLISHED"]
   AND at02.proof_hash IS NULL
THEN risk_score += 30
     reason_code = "AT02_PROOF_MISSING"
     recommended_action = "REJECT_ACCESSORIAL"
     anomaly_flags.append("PROOF_VIOLATION")
```

**Rule 7: The "MT-01 Mismatch" Rule (AT02_MT01_MISMATCH)**
```
IF at02_mt01_time_match = false OR at02_mt01_location_match = false
THEN risk_score += 35
     reason_code = "AT02_MT01_MISMATCH"
     anomaly_flags.append("TIMELINE_FRAUD")
     recommended_action = "ESCALATE_COMPLIANCE"
```

**Rule 8: The "Invoice Variance" Rule (IT01_VARIANCE_HIGH)**
```
IF it01_total_vs_qt01 > 0.15
THEN risk_score += 25
     reason_code = "IT01_VARIANCE_HIGH"
     requires_proof = true
```

**Rule 9: The "Carrier Overbilling" Rule (CARRIER_OVERBILLING)**
```
IF carrier_overbilling_score > 0.70
THEN risk_score += 30
     reason_code = "CARRIER_OVERBILLING_PATTERN"
     anomaly_flags.append("HISTORICAL_FRAUD_INDICATOR")
```

### 5.3 Scorecard Summary

| Factor | Condition | Points | Reason Code | Action |
|:-------|:----------|:-------|:------------|:-------|
| **IoT Integrity** | Critical Alert (Shock/Door) | +40 | `IOT_CRITICAL_ALERT` | HOLD |
| **IoT Visibility** | No signal >24h | +50 | `IOT_SILENCE_CRITICAL` | HOLD |
| **IoT Visibility** | No signal >4h | +15 | `IOT_SILENCE_WARNING` | REVIEW |
| **IoT Equipment** | Battery <10% | +10 | `IOT_BATTERY_RISK` | ALERT |
| **IoT Route** | GPS deviation >50mi | +20 | `ROUTE_DEVIATION` | FLAG |
| **Corridor** | Instability >30% | +10 | `CORRIDOR_INSTABILITY` | RESERVE↑ |
| **AT-02 Proof** | Missing proof_hash | +30 | `AT02_PROOF_MISSING` | REJECT |
| **AT-02 Timeline** | MT-01 mismatch | +35 | `AT02_MT01_MISMATCH` | ESCALATE |
| **IT-01 Accuracy** | >15% quote variance | +25 | `IT01_VARIANCE_HIGH` | PROOF_REQ |
| **Carrier History** | Overbilling score >0.7 | +30 | `CARRIER_OVERBILLING_PATTERN` | FLAG |

### 5.4 Risk Level Classification

| Score Range | Severity | Recommended Action | ALEX Gate |
|:------------|:---------|:-------------------|:----------|
| 0-29 | `LOW` | `RELEASE_PAYMENT` | Auto-approve |
| 30-59 | `MEDIUM` | `MANUAL_REVIEW` | Operator decision |
| 60-79 | `HIGH` | `HOLD_PAYMENT` | ALEX review required |
| 80-100 | `CRITICAL` | `ESCALATE_COMPLIANCE` | ALEX block + audit |

---

## 6. IoT → ChainIQ → Settlement Pipeline

The deterministic chain from raw IoT signal to XRPL settlement.

### 6.1 Pipeline Sequence Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    IoT → ChainIQ → AT-02 → Settlement Pipeline                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌────────────┐                                                                     │
│  │ ChainSense │  IoT Device (GPS, ELD, Temp, Door, Shock)                          │
│  │   Device   │                                                                     │
│  └─────┬──────┘                                                                     │
│        │ (1) Raw telemetry event                                                    │
│        ▼                                                                            │
│  ┌────────────┐                                                                     │
│  │ Seeburger  │  EDI Gateway (normalize + validate)                                │
│  │  Gateway   │                                                                     │
│  └─────┬──────┘                                                                     │
│        │ (2) Normalized event + event_id                                            │
│        ▼                                                                            │
│  ┌────────────┐  ┌───────────────────────────────────────────────────────────┐     │
│  │   MT-01    │◄─│ CREATE milestone token                                    │     │
│  │  CREATED   │  │ relations: { st01_id, iot_event_id OR seeburger_event_id }│     │
│  └─────┬──────┘  └───────────────────────────────────────────────────────────┘     │
│        │                                                                            │
│        │ (3) validate()                                                             │
│        ▼                                                                            │
│  ┌────────────┐  ┌───────────────────────────────────────────────────────────┐     │
│  │  ChainIQ   │◄─│ POST /chainiq/risk/score                                  │     │
│  │Risk Engine │  │ Input: ShipmentRiskRequest + IoTSignals                   │     │
│  └─────┬──────┘  └───────────────────────────────────────────────────────────┘     │
│        │                                                                            │
│        │ (4) Risk assessment output                                                 │
│        ▼                                                                            │
│  ┌────────────────────────────────────────────────────────────────────────────┐    │
│  │ ChainIQ Risk Output                                                        │    │
│  │ {                                                                          │    │
│  │   "risk_score": 82,                                                        │    │
│  │   "risk_label": "CRITICAL",                                                │    │
│  │   "confidence": 0.91,                                                      │    │
│  │   "explanation": "Detention claim contradicts MT-01 timeline",             │    │
│  │   "feature_contributions": { "at02_mt01_time_match": 35, ... },            │    │
│  │   "anomaly_flags": ["TIMELINE_FRAUD", "PROOF_MISSING"],                    │    │
│  │   "recommended_action": "ESCALATE_COMPLIANCE",                             │    │
│  │   "requires_proof": true                                                   │    │
│  │ }                                                                          │    │
│  └─────┬──────────────────────────────────────────────────────────────────────┘    │
│        │                                                                            │
│        │ (5) MT-01 transition + risk metadata                                       │
│        ▼                                                                            │
│  ┌────────────┐                                                                     │
│  │   MT-01    │  metadata: { chainiq_risk_score, chainiq_reason_codes }            │
│  │  VERIFIED  │                                                                     │
│  └─────┬──────┘                                                                     │
│        │                                                                            │
│        │ (6) AT-02 proposal (detention, fuel, lumper)                               │
│        ▼                                                                            │
│  ┌────────────┐  ┌───────────────────────────────────────────────────────────┐     │
│  │   AT-02    │◄─│ ChainIQ validates against MT-01 sequence                  │     │
│  │  PROPOSED  │  │ If mismatch → REJECT with reason_codes                    │     │
│  └─────┬──────┘  └───────────────────────────────────────────────────────────┘     │
│        │                                                                            │
│        │ (7) attach_proof() → SxT ProofPack                                         │
│        ▼                                                                            │
│  ┌──────────────┐  ┌───────────────────────────────────────────────────────────┐   │
│  │    AT-02     │◄─│ SxT generates proof_hash                                  │   │
│  │PROOF_ATTACHED│  │ proof: { hash, source: "SxT", metadata }                  │   │
│  └──────┬───────┘  └───────────────────────────────────────────────────────────┘   │
│         │                                                                           │
│         │ (8) ALEX governance check                                                 │
│         ▼                                                                           │
│  ┌────────────┐  ┌───────────────────────────────────────────────────────────┐     │
│  │    ALEX    │◄─│ Check: wrapper_state, digital_supremacy, kill_switch      │     │
│  │ Governance │  │ Assign: policy_match_id                                   │     │
│  │    Gate    │  │ Mantra: Proof ✓ Pipes ✓ Cash ✓                           │     │
│  └─────┬──────┘  └───────────────────────────────────────────────────────────┘     │
│        │                                                                            │
│        │ (9) AT-02 verification                                                     │
│        ▼                                                                            │
│  ┌────────────┐                                                                     │
│  │   AT-02    │  metadata: { policy_match_id }  ← ALEX REQUIRED                    │
│  │  VERIFIED  │                                                                     │
│  └─────┬──────┘                                                                     │
│        │                                                                            │
│        │ (10) Publish + Invoice computation                                         │
│        ▼                                                                            │
│  ┌────────────┐                                                                     │
│  │   IT-01    │  relations: { st01_id, qt01_id, at02_ids, mt01_ids }               │
│  │  COMPUTED  │  metadata: { total, line_items, due_date }                         │
│  └─────┬──────┘                                                                     │
│        │                                                                            │
│        │ (11) ALEX governance approval                                              │
│        ▼                                                                            │
│  ┌────────────┐                                                                     │
│  │   IT-01    │  metadata: { alex_governance_id }  ← ALEX REQUIRED                 │
│  │ PUBLISHED  │                                                                     │
│  └─────┬──────┘                                                                     │
│        │                                                                            │
│        │ (12) Settlement initiation                                                 │
│        ▼                                                                            │
│  ┌────────────┐  ┌───────────────────────────────────────────────────────────┐     │
│  │   PT-01    │◄─│ XRPL escrow creation                                      │     │
│  │ INITIATED  │  │ relations: { st01_id, it01_id }                           │     │
│  └─────┬──────┘  └───────────────────────────────────────────────────────────┘     │
│        │                                                                            │
│        │ (13) Fund → Escrow → Release                                               │
│        ▼                                                                            │
│  ┌────────────┐                                                                     │
│  │   PT-01    │  metadata: { xrpl_tx_hash, release_schedule, completion_at }       │
│  │  COMPLETE  │                                                                     │
│  └─────┬──────┘                                                                     │
│        │                                                                            │
│        │ (14) Shipment settlement                                                   │
│        ▼                                                                            │
│  ┌────────────┐                                                                     │
│  │   ST-01    │  relations: { pt01_ids }                                           │
│  │  SETTLED   │                                                                     │
│  └────────────┘                                                                     │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Pipeline Checkpoints

| Step | Token State | ChainIQ Role | ALEX Gate |
|:-----|:------------|:-------------|:----------|
| 1-2 | Raw Event | N/A | N/A |
| 3 | MT-01 CREATED | Validate event structure | N/A |
| 4 | MT-01 VERIFIED | Risk scoring + anomaly detection | N/A |
| 5 | AT-02 PROPOSED | MT-01 timeline validation | N/A |
| 6-7 | AT-02 PROOF_ATTACHED | ProofPack verification | N/A |
| 8-9 | AT-02 VERIFIED | N/A | **ALEX REQUIRED** |
| 10-11 | IT-01 PUBLISHED | Invoice accuracy scoring | **ALEX REQUIRED** |
| 12-14 | PT-01 COMPLETE | N/A | Settlement audit |

---

## 7. ALEX Governance Rules

ALEX is the deterministic governance gatekeeper for ChainBridge. ChainIQ outputs **must** pass ALEX gates before settlement.

### 7.1 ALEX Governance Thresholds

| Gate | Condition | ALEX Action |
|:-----|:----------|:------------|
| **Risk Score ≥80** | CRITICAL severity | Block settlement, require compliance review |
| **Risk Score 60-79** | HIGH severity | Hold payment, require ALEX approval |
| **Missing Proof** | AT-02 without proof_hash | Block AT-02 verification |
| **Missing Policy Match** | AT-02 without policy_match_id | Block AT-02 publication |
| **Invoice Variance >20%** | IT-01 total vs QT-01 | Block IT-01 publication |
| **Wrapper State ≠ ACTIVE** | Ricardian wrapper frozen/terminated | Block all flows |
| **Digital Supremacy = BLOCKED** | Compliance violation | Block all flows |
| **Kill Switch = UNSAFE** | Safety violation | Block all flows |

### 7.2 ALEX Mantra Enforcement

```
┌─────────────────────────────────────────────────────────────────┐
│                     ALEX MANTRA CHECK                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│  │  PROOF   │    │  PIPES   │    │   CASH   │                  │
│  │  ✓ / ✗   │ →  │  ✓ / ✗   │ →  │  ✓ / ✗   │                  │
│  └──────────┘    └──────────┘    └──────────┘                  │
│       │               │               │                         │
│       ▼               ▼               ▼                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ IF any component = ✗                                     │  │
│  │ THEN ALEX.block() + return reason                        │  │
│  │ ELSE ALEX.approve() + issue governance_id                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  PROOF = ChainIQ risk_score < threshold                         │
│        + AT-02.proof_hash present                               │
│        + MT-01 timeline validated                               │
│                                                                 │
│  PIPES = Seeburger integration active                           │
│        + IoT telemetry flowing                                  │
│        + Token state machine valid                              │
│                                                                 │
│  CASH  = XRPL escrow funded                                     │
│        + PT-01 linkage established                              │
│        + release_schedule defined                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 ALEX Override Conditions

Operators can override ChainIQ risk scores under specific conditions:

| Override Code | Condition | Audit Trail |
|:--------------|:----------|:------------|
| `SENSOR_MALFUNCTION` | IoT device known-bad | Device ID + maintenance ticket |
| `CARRIER_VERIFIED` | Manual carrier verification | Verification timestamp + operator ID |
| `SHIPPER_WAIVER` | Shipper accepts risk | Waiver document + signature |
| `COMPLIANCE_APPROVED` | Compliance team approval | Approval ID + reviewer |
| `ALEX_EXECUTIVE` | Executive override | Executive ID + justification |

All overrides are logged to SxT ProofPack for audit trail.

### 7.4 ALEX Dispute Triggers

ChainIQ anomaly flags can trigger ALEX dispute flows:

| Anomaly Flag | Dispute Type | Resolution Path |
|:-------------|:-------------|:----------------|
| `TIMELINE_FRAUD` | AT-02 dispute | CCT-01 reconciliation |
| `PROOF_MISSING` | Proof dispute | Carrier proof submission |
| `ROUTE_DEVIATION` | Route dispute | GPS audit |
| `CARRIER_OVERBILLING_PATTERN` | Invoice dispute | Historical audit |
| `IOT_SPOOFING_DETECTED` | Fraud investigation | Security escalation |

---

## 8. Adversarial Scenarios

ChainIQ must be hardened against known fraud vectors. Maggie PAC requires adversarial stress testing.

### 8.1 GPS Spoofing Attack

**Attack Vector:** Carrier manipulates GPS device to show false location, claiming detention at shipper facility while actually delayed elsewhere.

```
┌─────────────────────────────────────────────────────────────────┐
│ ATTACK: GPS Spoofing                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Attacker Goal: Claim detention without actual detention        │
│                                                                 │
│  Attack Steps:                                                  │
│  1. Spoof GPS to show truck at shipper facility                │
│  2. Submit AT-02 DETENTION claim                               │
│  3. Profit from fraudulent accessorial                         │
│                                                                 │
│  ChainIQ Detection:                                             │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Feature: iot_gps_consistency_score                        │ │
│  │ Rule: IF gps_signal_variance > threshold                  │ │
│  │       OR gps_position_jumps > expected                    │ │
│  │       OR eld_hours != gps_movement                        │ │
│  │       THEN anomaly_flags.append("GPS_SPOOFING_SUSPECTED") │ │
│  │            risk_score += 45                               │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Cross-Validation:                                              │
│  - ELD hours vs GPS movement                                   │
│  - Cell tower triangulation vs reported GPS                    │
│  - Fuel consumption vs distance traveled                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 False Early Arrival Attack

**Attack Vector:** Carrier manipulates arrival timestamp to appear early, reducing legitimate detention claims by shipper.

```
┌─────────────────────────────────────────────────────────────────┐
│ ATTACK: False Early Arrival                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Attacker Goal: Shift blame for detention to shipper           │
│                                                                 │
│  Attack Steps:                                                  │
│  1. Report early arrival timestamp                             │
│  2. Claim shipper caused detention                             │
│  3. Submit AT-02 DETENTION against shipper                     │
│                                                                 │
│  ChainIQ Detection:                                             │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Feature: arrival_timestamp_consistency                    │ │
│  │ Rule: IF reported_arrival_time < last_gps_enroute_time    │ │
│  │       OR arrival_time_delta > 30_minutes                  │ │
│  │       THEN anomaly_flags.append("ARRIVAL_TIME_FRAUD")     │ │
│  │            risk_score += 40                               │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Cross-Validation:                                              │
│  - Terminal gate check-in timestamp                            │
│  - Seeburger EDI 214 arrival message                          │
│  - Geofence entry timestamp                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 False Detention Claim Attack

**Attack Vector:** Carrier claims detention that did not occur or exaggerates duration.

```
┌─────────────────────────────────────────────────────────────────┐
│ ATTACK: False Detention                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Attacker Goal: Collect detention fees without basis           │
│                                                                 │
│  Attack Steps:                                                  │
│  1. Complete pickup/delivery within free time                  │
│  2. Submit AT-02 claiming detention occurred                   │
│  3. Profit from fraudulent accessorial                         │
│                                                                 │
│  ChainIQ Detection:                                             │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Feature: detention_duration_vs_mt01                       │ │
│  │ Rule: IF at02.detention_minutes > (mt01_departure -       │ │
│  │          mt01_arrival - free_time_minutes)                │ │
│  │       THEN anomaly_flags.append("DETENTION_OVERCLAIM")    │ │
│  │            risk_score += 35                               │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Cross-Validation:                                              │
│  - MT-01 arrival/departure timestamps                          │
│  - Terminal appointment system                                 │
│  - Driver check-in/check-out records                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.4 Route Tampering Attack

**Attack Vector:** Carrier deviates from approved route for personal benefit, then claims additional mileage or fuel.

```
┌─────────────────────────────────────────────────────────────────┐
│ ATTACK: Route Tampering                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Attacker Goal: Collect excess mileage/fuel accessorials       │
│                                                                 │
│  Attack Steps:                                                  │
│  1. Deviate from planned route                                 │
│  2. Submit AT-02 for additional mileage                        │
│  3. Claim fuel surcharge on inflated miles                     │
│                                                                 │
│  ChainIQ Detection:                                             │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Feature: route_adherence_score                            │ │
│  │ Rule: IF actual_miles > planned_miles * 1.15              │ │
│  │       AND NOT authorized_detour                           │ │
│  │       THEN anomaly_flags.append("ROUTE_INFLATION")        │ │
│  │            risk_score += 25                               │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Cross-Validation:                                              │
│  - Planned route vs GPS breadcrumb                             │
│  - Authorized detour documentation                             │
│  - Weather/traffic diversion records                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.5 Time-Warping Attack

**Attack Vector:** Carrier manipulates device clock to shift timestamps, creating false timeline narratives.

```
┌─────────────────────────────────────────────────────────────────┐
│ ATTACK: Time-Warping                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Attacker Goal: Create false timeline to support fraud         │
│                                                                 │
│  Attack Steps:                                                  │
│  1. Manipulate device clock                                    │
│  2. Generate events with false timestamps                      │
│  3. Submit claims based on false timeline                      │
│                                                                 │
│  ChainIQ Detection:                                             │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Feature: timestamp_consistency_score                      │ │
│  │ Rule: IF device_timestamp_drift > 5_minutes               │ │
│  │       OR event_sequence_impossible = true                 │ │
│  │       THEN anomaly_flags.append("TIME_MANIPULATION")      │ │
│  │            risk_score += 50                               │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Cross-Validation:                                              │
│  - Server receipt timestamp vs device timestamp                │
│  - NTP sync status                                             │
│  - Event sequence logical validation                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.6 Rate Manipulation Attack

**Attack Vector:** Carrier inflates rates or applies unauthorized accessorials.

```
┌─────────────────────────────────────────────────────────────────┐
│ ATTACK: Rate Manipulation                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Attacker Goal: Overbill through rate/accessorial inflation    │
│                                                                 │
│  Attack Steps:                                                  │
│  1. Apply higher rate than contracted                          │
│  2. Add unauthorized accessorials                              │
│  3. Submit inflated invoice                                    │
│                                                                 │
│  ChainIQ Detection:                                             │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Feature: rate_vs_contract_variance                        │ │
│  │ Rule: IF invoice_rate > contract_rate * 1.05              │ │
│  │       OR unauthorized_accessorial_present = true          │ │
│  │       THEN anomaly_flags.append("RATE_MANIPULATION")      │ │
│  │            risk_score += 30                               │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Cross-Validation:                                              │
│  - QT-01 quoted rates vs IT-01 invoice rates                  │
│  - Contract rate database                                      │
│  - Historical lane rate analysis                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.7 IoT Device Substitution Attack

**Attack Vector:** Carrier substitutes compliant IoT device with non-compliant or dummy device.

```
┌─────────────────────────────────────────────────────────────────┐
│ ATTACK: Device Substitution                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Attacker Goal: Avoid IoT monitoring while appearing compliant │
│                                                                 │
│  Attack Steps:                                                  │
│  1. Register compliant device                                  │
│  2. Substitute with dummy/non-functional device                │
│  3. Operate without true monitoring                            │
│                                                                 │
│  ChainIQ Detection:                                             │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Feature: device_behavior_anomaly_score                    │ │
│  │ Rule: IF signal_pattern != historical_pattern             │ │
│  │       OR sensor_correlation_breakdown = true              │ │
│  │       THEN anomaly_flags.append("DEVICE_SUBSTITUTION")    │ │
│  │            risk_score += 40                               │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Cross-Validation:                                              │
│  - Device fingerprinting                                       │
│  - Signal pattern analysis                                     │
│  - Multi-sensor correlation (GPS + ELD + Temp)                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.8 Adversarial Testing Matrix

| Attack Vector | Detection Feature | Test Cases | Pass Criteria |
|:--------------|:------------------|:-----------|:--------------|
| GPS Spoofing | `iot_gps_consistency_score` | 50 synthetic + 10 real | 95% detection rate |
| False Early Arrival | `arrival_timestamp_consistency` | 30 synthetic | 90% detection rate |
| False Detention | `detention_duration_vs_mt01` | 40 synthetic | 92% detection rate |
| Route Tampering | `route_adherence_score` | 25 synthetic | 88% detection rate |
| Time-Warping | `timestamp_consistency_score` | 20 synthetic | 95% detection rate |
| Rate Manipulation | `rate_vs_contract_variance` | 35 synthetic | 90% detection rate |
| Device Substitution | `device_behavior_anomaly_score` | 15 synthetic | 85% detection rate |

---

## 9. Risk Contract API

ChainIQ outputs follow a strict contract (Maggie PAC Task 6).

### 9.1 Risk Output Schema

```json
{
  "risk_score": 82,
  "risk_label": "CRITICAL",
  "confidence": 0.91,
  "explanation": "Detention claim timeline contradicts MT-01 sequence. GPS shows truck departed facility at 14:23 but AT-02 claims detention until 16:45.",
  "feature_contributions": {
    "at02_mt01_time_match": 35,
    "at02_proof_present": 0,
    "iot_critical_count_24h": 0,
    "corridor_instability_index": 5,
    "carrier_overbilling_score": 20,
    "route_risk": 22
  },
  "anomaly_flags": [
    "TIMELINE_FRAUD",
    "CARRIER_OVERBILLING_PATTERN"
  ],
  "recommended_action": "ESCALATE_COMPLIANCE",
  "requires_proof": true,
  "token_context": {
    "st01_id": "ST01-2025-001234",
    "mt01_ids": ["MT01-A", "MT01-B", "MT01-C"],
    "at02_id": "AT02-DET-5678",
    "at02_state": "PROPOSED"
  },
  "alex_gate": {
    "can_proceed": false,
    "blocking_reason": "CRITICAL risk score requires compliance review",
    "required_action": "compliance_review"
  },
  "metadata": {
    "engine_version": "2.0.0",
    "scored_at": "2025-12-02T15:30:00Z",
    "latency_ms": 45
  }
}
```

### 9.2 Required Fields

| Field | Type | Description | Required |
|:------|:-----|:------------|:---------|
| `risk_score` | int (0-100) | Composite risk score | ✓ |
| `risk_label` | enum | LOW/MEDIUM/HIGH/CRITICAL | ✓ |
| `confidence` | float (0-1) | Model confidence | ✓ |
| `explanation` | string | Human-readable explanation | ✓ |
| `feature_contributions` | object | SHAP-style breakdown | ✓ |
| `anomaly_flags` | array[string] | Detected anomalies | ✓ |
| `recommended_action` | enum | Action code | ✓ |
| `requires_proof` | boolean | Proof requirement flag | ✓ |

### 9.3 API Endpoints (Cody Integration)

```
POST /chainiq/risk/score
  Request: ShipmentRiskRequest + IoTSignals
  Response: RiskOutput
  Latency: <200ms (Maggie PAC requirement)

POST /chainiq/risk/bulk-score
  Request: Array[ShipmentRiskRequest]
  Response: Array[RiskOutput]
  Latency: <500ms for 10 shipments

GET /chainiq/risk/history/{shipment_id}
  Response: EntityHistoryResponse

POST /chainiq/risk/validate-at02
  Request: AT02Token + Array[MT01Token]
  Response: AT02ValidationResult

GET /chainiq/risk/proofpack/{shipment_id}
  Response: ProofPackResponse (SxT integration)
```

---

## 10. Integration Points

Backend implementation targets for Cody.

### 10.1 File Targets

| File | Purpose | Owner |
|:-----|:--------|:------|
| `chainiq-service/app/schemas.py` | Pydantic models for API | Cody |
| `chainiq-service/app/risk_engine.py` | Scoring logic | Maggie |
| `chainiq-service/app/api.py` | FastAPI endpoints | Cody |
| `chainbridge/chainiq/features.py` | Feature engineering | Maggie |
| `chainbridge/chainiq/inference.py` | Model inference | Maggie |
| `chainbridge/chainiq/explanations.py` | SHAP explanations | Maggie |
| `chainbridge/chainiq/anomaly.py` | Anomaly detection | Maggie |
| `chainbridge/chainiq/risk_contract.py` | Output contract | Maggie |
| `chainbridge/tokens/at02.py` | AT-02 validation hooks | Cody |
| `chainbridge/tokens/mt01.py` | MT-01 risk integration | Cody |

### 10.2 Schema Updates Required

```python
# chainiq-service/app/schemas.py - ADDITIONS

class IoTSignals(BaseModel):
    """IoT-derived features for risk adjustment."""
    critical_count_24h: int = 0
    silence_hours: float = 0.0
    corridor_instability_index: float = 0.0
    battery_health_score: Optional[float] = None
    gps_deviation_miles: Optional[float] = None
    door_events_anomaly: bool = False
    shock_detected: bool = False

class TokenContext(BaseModel):
    """Token linkages for risk output."""
    st01_id: str
    mt01_ids: List[str] = []
    at02_id: Optional[str] = None
    at02_state: Optional[str] = None
    it01_id: Optional[str] = None

class ALEXGate(BaseModel):
    """ALEX governance gate result."""
    can_proceed: bool
    blocking_reason: Optional[str] = None
    required_action: Optional[str] = None
    governance_id: Optional[str] = None

class RiskOutput(BaseModel):
    """Complete ChainIQ risk output."""
    risk_score: int
    risk_label: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    confidence: float
    explanation: str
    feature_contributions: Dict[str, float]
    anomaly_flags: List[str]
    recommended_action: str
    requires_proof: bool
    token_context: Optional[TokenContext] = None
    alex_gate: Optional[ALEXGate] = None
    metadata: Dict[str, Any]
```

### 10.3 Engine Logic Updates Required

```python
# chainiq-service/app/risk_engine.py - ADDITIONS

def _apply_token_rules(
    base_score: int,
    reason_codes: List[str],
    at02_token: Optional[AT02Token],
    mt01_tokens: List[MT01Token],
) -> Tuple[int, List[str], List[str]]:
    """Apply token-aware risk rules."""
    anomaly_flags = []

    if at02_token:
        # Rule 6: AT-02 proof check
        if at02_token.state in {"PROOF_ATTACHED", "VERIFIED"} and not at02_token.proof_hash:
            base_score += 30
            reason_codes.append("AT02_PROOF_MISSING")
            anomaly_flags.append("PROOF_VIOLATION")

        # Rule 7: MT-01 timeline validation
        if not _validate_at02_timeline(at02_token, mt01_tokens):
            base_score += 35
            reason_codes.append("AT02_MT01_MISMATCH")
            anomaly_flags.append("TIMELINE_FRAUD")

    return base_score, reason_codes, anomaly_flags

def _apply_adversarial_checks(
    base_score: int,
    reason_codes: List[str],
    iot_signals: IoTSignals,
    mt01_tokens: List[MT01Token],
) -> Tuple[int, List[str], List[str]]:
    """Apply adversarial scenario detection."""
    anomaly_flags = []

    # GPS spoofing detection
    if _detect_gps_spoofing(iot_signals, mt01_tokens):
        base_score += 45
        reason_codes.append("GPS_SPOOFING_SUSPECTED")
        anomaly_flags.append("GPS_SPOOFING_DETECTED")

    # Time manipulation detection
    if _detect_time_manipulation(mt01_tokens):
        base_score += 50
        reason_codes.append("TIME_MANIPULATION_DETECTED")
        anomaly_flags.append("TIME_MANIPULATION")

    return base_score, reason_codes, anomaly_flags
```

---

## 11. Failure Modes

### 11.1 Failure Mode Matrix

| Failure | Detection | Mitigation | Escalation |
|:--------|:----------|:-----------|:-----------|
| IoT data unavailable | `fleet_offline_ratio > 0.2` | Suspend auto-release | Alert ops |
| ChainIQ service down | Health check failure | Fallback to manual review | Page on-call |
| SxT proof unavailable | Proof generation timeout | Hold AT-02 at PROPOSED | Alert compliance |
| ALEX governance timeout | Governance API timeout | Hold settlement | Alert ops |
| Risk score drift | Drift detection alert | Trigger model recalibration | Alert Maggie |
| Adversarial attack detected | Anomaly flag cluster | Block settlement, audit | Alert Sam |

### 11.2 Circuit Breaker Thresholds

| Metric | Warning | Critical | Action |
|:-------|:--------|:---------|:-------|
| `fleet_offline_ratio` | >10% | >20% | Suspend auto-release |
| `avg_latency_ms` | >150ms | >200ms | Scale service |
| `error_rate` | >1% | >5% | Fallback mode |
| `anomaly_rate` | >5% | >10% | Security review |

### 11.3 Risk Escalation Path

```
┌─────────────────────────────────────────────────────────────────┐
│                    RISK ESCALATION PATH                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  risk_score 0-29 (LOW)                                         │
│       │                                                         │
│       └──► Auto-approve → Settlement                           │
│                                                                 │
│  risk_score 30-59 (MEDIUM)                                     │
│       │                                                         │
│       └──► Operator review → Approve/Reject                    │
│                                                                 │
│  risk_score 60-79 (HIGH)                                       │
│       │                                                         │
│       └──► ALEX review → Approve/Reject/Escalate               │
│                                                                 │
│  risk_score 80-100 (CRITICAL)                                  │
│       │                                                         │
│       └──► Compliance team → Audit → Legal review              │
│                                                                 │
│  Adversarial flags detected                                     │
│       │                                                         │
│       └──► Sam (Security) → Investigation → Potential block    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 12. ML Evolution Roadmap

Once real data is accumulated (Phase 2+), ChainIQ evolves from Glass-Box to Glass-Box + ML.

### 12.1 Phase 1: Glass-Box Rules (Current)

- Deterministic scoring rules
- Explicit thresholds
- Manual feature engineering
- No training required

### 12.2 Phase 2: Calibrated Glass-Box

- Logistic regression to weight features
- Historical data calibration
- Bayesian confidence intervals
- Drift detection

### 12.3 Phase 3: Glass-Box + GBM

- Gradient Boosted Machine for pattern detection
- SHAP explanations mandatory
- Ensemble with rule-based baseline
- Adversarial stress testing

### 12.4 Phase 4: Anomaly Detection

- Isolation Forest for unsupervised anomaly detection
- Time-series anomaly detection for IoT patterns
- Causal inference for root cause analysis

### 12.5 ML Constraints (Permanent)

From Maggie PAC:

1. **No black-box models** without SHAP/LIME wrapper
2. **All training data versioned** and deterministic
3. **Bayesian uncertainty** always computed
4. **200ms max inference latency**
5. **Adversarial testing** before deployment
6. **Drift monitoring** in production

---

## Appendix A: Agent Responsibilities (RACI)

| Task | Maggie | Cody | Sam | Pax | Dan | ALEX |
|:-----|:-------|:-----|:----|:----|:----|:-----|
| Feature engineering | R | C | I | I | I | I |
| Risk engine logic | R | A | C | I | I | C |
| API implementation | C | R | I | I | A | I |
| Adversarial testing | R | C | A | I | I | C |
| Token integration | C | R | I | I | I | A |
| Governance rules | C | I | C | C | I | R |
| Security review | I | C | R | I | C | A |
| Deployment | I | C | C | I | R | A |
| UI integration | I | C | I | R | I | I |

R = Responsible, A = Accountable, C = Consulted, I = Informed

---

## Appendix B: Version History

| Version | Date | Author | Changes |
|:--------|:-----|:-------|:--------|
| 1.0 | 2025-11-01 | Maggie | Initial Glass-Box design |
| 2.0 | 2025-12-02 | Maggie | LST-01 integration, ALEX governance, adversarial scenarios, Benson-grade refactor |

---

## Appendix C: Related Documents

| Document | Purpose |
|:---------|:--------|
| [ALEX_GOVERNANCE_GATE.md](../ci/ALEX_GOVERNANCE_GATE.md) | ALEX governance specification |
| [LST-01 Token Models](../../chainbridge/tokens/) | Token lifecycle definitions |
| [ChainSense IoT Integration](../product/ChainSense_IoT_Integration.md) | IoT data source specification |
| [ChainBridge Reality Baseline](../product/CHAINBRIDGE_REALITY_BASELINE.md) | System baseline |
| [SECURITY_AGENT_FRAMEWORK.md](../SECURITY_AGENT_FRAMEWORK.md) | Security threat model |
