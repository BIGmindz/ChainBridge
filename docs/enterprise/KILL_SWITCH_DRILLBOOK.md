# Pilot Kill-Switch Drillbook

**PAC Reference:** PAC-JEFFREY-P46  
**Classification:** ENTERPRISE PILOT  
**Governance Mode:** HARD / FAIL-CLOSED  
**Drill Coordinator:** DAN (GID-07)  
**Version:** 1.0.0  
**Date:** 2026-01-02

---

## 1. Overview

This drillbook defines mandatory kill-switch exercises that must be completed before external pilot access is granted. These drills ensure operators are trained and the system behaves correctly under safety halt conditions.

### Core Principle

> **Kill-switch drills are prerequisite to pilots.**

No external access is granted until kill-switch competency is demonstrated.

---

## 2. Drill Requirements

### 2.1 Pre-Pilot Drill Schedule

| Drill | Frequency | Required Before |
|-------|-----------|-----------------|
| KS-DRILL-001 | Once | First external pilot |
| KS-DRILL-002 | Once | First external pilot |
| KS-DRILL-003 | Quarterly | Ongoing pilots |
| KS-DRILL-004 | Monthly | Active pilot period |

### 2.2 Drill Participants

| Role | Required | Responsibility |
|------|----------|----------------|
| Primary Operator | ✅ | Execute kill-switch |
| Secondary Operator | ✅ | Backup execution |
| Technical Lead | ✅ | System verification |
| DAN (GID-07) | ✅ | Drill coordination |
| BENSON (GID-00) | Observe | Governance compliance |

---

## 3. KS-DRILL-001: Basic Engagement

### 3.1 Objective

Verify operators can successfully arm and engage the kill-switch.

### 3.2 Prerequisites

- [ ] Test environment active
- [ ] No external pilots in session
- [ ] All operators authenticated
- [ ] Audit logging confirmed

### 3.3 Procedure

```
KS-DRILL-001: BASIC ENGAGEMENT PROCEDURE

STEP 1: PRE-DRILL CHECK
┌─────────────────────────────────────────────────────────────────┐
│ □ Confirm kill-switch state: DISARMED                          │
│ □ Confirm no active external sessions                          │
│ □ Confirm audit logging active                                 │
│ □ Notify drill observers                                       │
└─────────────────────────────────────────────────────────────────┘

STEP 2: ARM KILL-SWITCH
┌─────────────────────────────────────────────────────────────────┐
│ Action: POST /occ/kill-switch/arm                              │
│ Actor: Primary Operator                                        │
│ Expected: State changes to ARMED                               │
│                                                                 │
│ □ Verify state: ARMED                                          │
│ □ Verify audit log entry created                               │
│ □ Verify banner displayed in OCC                               │
└─────────────────────────────────────────────────────────────────┘

STEP 3: ENGAGE KILL-SWITCH
┌─────────────────────────────────────────────────────────────────┐
│ Action: POST /occ/kill-switch/engage                           │
│ Actor: Primary Operator                                        │
│ Reason: "KS-DRILL-001 - Basic Engagement Drill"                │
│ Expected: State changes to ENGAGED                             │
│                                                                 │
│ □ Verify state: ENGAGED                                        │
│ □ Verify agent operations halted                               │
│ □ Verify audit log entry created                               │
│ □ Verify external session blocking active                      │
└─────────────────────────────────────────────────────────────────┘

STEP 4: VERIFY ENGAGEMENT EFFECTS
┌─────────────────────────────────────────────────────────────────┐
│ □ New external login attempt: BLOCKED                          │
│ □ PDO creation attempt: BLOCKED                                │
│ □ Read operations: AVAILABLE                                   │
│ □ Health endpoint: AVAILABLE                                   │
└─────────────────────────────────────────────────────────────────┘

STEP 5: DISENGAGE KILL-SWITCH
┌─────────────────────────────────────────────────────────────────┐
│ Action: POST /occ/kill-switch/disengage                        │
│ Actor: Primary Operator                                        │
│ Expected: State changes to COOLDOWN                            │
│                                                                 │
│ □ Verify state: COOLDOWN                                       │
│ □ Verify cooldown timer started                                │
│ □ Verify audit log entry created                               │
└─────────────────────────────────────────────────────────────────┘

STEP 6: WAIT FOR COOLDOWN
┌─────────────────────────────────────────────────────────────────┐
│ Wait: Cooldown period (typically 15 minutes)                   │
│                                                                 │
│ □ Verify state transitions to DISARMED after cooldown          │
│ □ Verify normal operations resume                              │
│ □ Verify audit log entry created                               │
└─────────────────────────────────────────────────────────────────┘

STEP 7: POST-DRILL VERIFICATION
┌─────────────────────────────────────────────────────────────────┐
│ □ Review complete audit trail                                  │
│ □ Verify all state transitions logged                          │
│ □ Document drill completion                                    │
│ □ Sign off by all participants                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 Success Criteria

| Criterion | Required |
|-----------|----------|
| State transitions correct | ✅ |
| Audit entries complete | ✅ |
| Effects verified | ✅ |
| Cooldown completed | ✅ |
| All operators signed off | ✅ |

### 3.5 Drill Record

```json
{
  "drill_id": "KS-DRILL-001",
  "date": "YYYY-MM-DD",
  "participants": [],
  "start_time": "",
  "end_time": "",
  "steps_completed": [],
  "issues_encountered": [],
  "result": "PASS/FAIL",
  "signed_by": []
}
```

---

## 4. KS-DRILL-002: External Session Impact

### 4.1 Objective

Verify kill-switch correctly handles active external pilot sessions.

### 4.2 Prerequisites

- [ ] Test environment active
- [ ] Test external session active (simulated)
- [ ] All operators authenticated
- [ ] Audit logging confirmed

### 4.3 Procedure

```
KS-DRILL-002: EXTERNAL SESSION IMPACT PROCEDURE

STEP 1: ESTABLISH TEST EXTERNAL SESSION
┌─────────────────────────────────────────────────────────────────┐
│ □ Create test external account (EXT-TEST-001)                  │
│ □ Authenticate as external user                                │
│ □ Verify read access functional                                │
│ □ Note session ID                                              │
└─────────────────────────────────────────────────────────────────┘

STEP 2: ARM AND ENGAGE KILL-SWITCH
┌─────────────────────────────────────────────────────────────────┐
│ □ Arm kill-switch (Primary Operator)                           │
│ □ Engage kill-switch (Primary Operator)                        │
│ □ Reason: "KS-DRILL-002 - External Session Impact Drill"       │
└─────────────────────────────────────────────────────────────────┘

STEP 3: VERIFY EXISTING SESSION BEHAVIOR
┌─────────────────────────────────────────────────────────────────┐
│ From external session:                                         │
│                                                                 │
│ □ Read operations: SHOULD WORK                                 │
│ □ Export operations: SHOULD WORK                               │
│ □ Verify operations: SHOULD WORK                               │
│ □ Create operations: SHOULD FAIL (503)                         │
│ □ Session remains active                                       │
└─────────────────────────────────────────────────────────────────┘

STEP 4: VERIFY NEW SESSION BLOCKING
┌─────────────────────────────────────────────────────────────────┐
│ □ Attempt new external login: SHOULD FAIL                      │
│ □ Verify 503 response with reason                              │
│ □ Verify no new session created                                │
└─────────────────────────────────────────────────────────────────┘

STEP 5: VERIFY EXTERNAL USER NOTIFICATION
┌─────────────────────────────────────────────────────────────────┐
│ From external session:                                         │
│                                                                 │
│ □ Banner visible: "System in safety mode"                      │
│ □ Kill-switch state visible: ENGAGED                           │
│ □ Session timer paused indicator                               │
└─────────────────────────────────────────────────────────────────┘

STEP 6: DISENGAGE AND VERIFY RECOVERY
┌─────────────────────────────────────────────────────────────────┐
│ □ Disengage kill-switch                                        │
│ □ Wait for cooldown                                            │
│ □ Verify new external login works                              │
│ □ Verify existing session continues                            │
│ □ Verify banner removed                                        │
└─────────────────────────────────────────────────────────────────┘

STEP 7: CLEANUP AND DOCUMENT
┌─────────────────────────────────────────────────────────────────┐
│ □ Terminate test external session                              │
│ □ Remove test external account                                 │
│ □ Document drill results                                       │
│ □ Sign off by all participants                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4 Success Criteria

| Criterion | Required |
|-----------|----------|
| Existing sessions continue (read-only) | ✅ |
| New sessions blocked | ✅ |
| Write operations blocked | ✅ |
| Notification displayed | ✅ |
| Recovery complete | ✅ |

---

## 5. KS-DRILL-003: Secondary Operator Handoff

### 5.1 Objective

Verify secondary operator can execute kill-switch when primary is unavailable.

### 5.2 Procedure Summary

```
KS-DRILL-003: SECONDARY OPERATOR HANDOFF

1. Primary operator initiates drill
2. Primary operator "becomes unavailable" (simulated)
3. Secondary operator takes control
4. Secondary operator arms and engages kill-switch
5. Secondary operator manages through cooldown
6. Document handoff procedure
```

### 5.3 Success Criteria

| Criterion | Required |
|-----------|----------|
| Secondary can arm | ✅ |
| Secondary can engage | ✅ |
| Secondary can disengage | ✅ |
| Audit trail shows handoff | ✅ |
| No operational gap | ✅ |

---

## 6. KS-DRILL-004: Rapid Response

### 6.1 Objective

Verify kill-switch can be engaged within SLA during simulated incident.

### 6.2 SLA Requirements

| Metric | Target |
|--------|--------|
| Time to arm | < 30 seconds |
| Time to engage | < 60 seconds from detection |
| Time to confirm | < 120 seconds |

### 6.3 Procedure Summary

```
KS-DRILL-004: RAPID RESPONSE

1. Drill coordinator announces simulated incident
2. Timer starts
3. Operator authenticates and arms
4. Operator engages with reason
5. Timer stops at engagement confirmation
6. Document response time
```

### 6.4 Success Criteria

| Criterion | Required |
|-----------|----------|
| Engagement within SLA | ✅ |
| Correct reason logged | ✅ |
| No authentication failures | ✅ |
| Effects verified | ✅ |

---

## 7. Drill Failure Handling

### 7.1 Failure Categories

| Category | Action |
|----------|--------|
| Operator error | Retrain + re-drill |
| System failure | Investigate + fix + re-drill |
| Process gap | Update procedure + re-drill |
| Documentation error | Correct docs + re-drill |

### 7.2 Failure Escalation

| Failure Count | Escalation |
|---------------|------------|
| 1 | Document and retry |
| 2 | Technical Lead review |
| 3 | CTO notification |
| 3+ | Block pilot launch |

---

## 8. Drill Schedule Template

### 8.1 Pre-Pilot Drill Schedule

```
WEEK -2: KS-DRILL-001 (Basic Engagement)
├─ Day 1: Dry run (documentation review)
├─ Day 2: Live drill (all operators)
└─ Day 3: Review and sign-off

WEEK -1: KS-DRILL-002 (External Session Impact)
├─ Day 1: Test account setup
├─ Day 2: Live drill (all operators + test external)
└─ Day 3: Review and sign-off

PILOT LAUNCH: Drills complete
```

### 8.2 Ongoing Drill Schedule

```
MONTHLY: KS-DRILL-004 (Rapid Response)
├─ Unannounced drill during business hours
├─ Document response time
└─ Review any delays

QUARTERLY: KS-DRILL-003 (Secondary Handoff)
├─ Scheduled drill
├─ Document handoff procedure
└─ Update runbooks if needed
```

---

## 9. Drill Documentation

### 9.1 Required Records

| Record | Retention |
|--------|-----------|
| Drill execution log | 3 years |
| Participant sign-off | 3 years |
| Failure reports | 3 years |
| Remediation records | 3 years |

### 9.2 Drill Completion Certificate

```
KILL-SWITCH DRILL COMPLETION CERTIFICATE

Drill ID: ________________
Date: ________________
Coordinator: DAN (GID-07)

Participants:
□ Primary Operator: _________________ Signed: _________
□ Secondary Operator: ________________ Signed: _________
□ Technical Lead: ____________________ Signed: _________

Results:
□ All steps completed successfully
□ All success criteria met
□ No unresolved issues

Certificate: This drill has been completed satisfactorily.

DAN (GID-07) Sign-off: _________________
Date: ________________
```

---

## 10. Pilot Launch Gate

### 10.1 Kill-Switch Readiness Checklist

```
PILOT LAUNCH KILL-SWITCH GATE

Required for pilot launch:

□ KS-DRILL-001 completed and signed
□ KS-DRILL-002 completed and signed
□ Primary operator certified
□ Secondary operator certified
□ Kill-switch currently in ARMED state
□ Audit logging verified
□ External session handling verified
□ Recovery procedure documented
□ Escalation contacts confirmed

Gate Status: _________ (PASS/FAIL)
Approved By: _________ (CTO)
Date: _________
```

---

## 11. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-02 | BENSON/DAN | Initial kill-switch drillbook |

---

**Document Authority:** PAC-JEFFREY-P46  
**Drill Coordinator:** DAN (GID-07)  
**Classification:** ENTERPRISE PILOT  
**Governance:** HARD / FAIL-CLOSED
