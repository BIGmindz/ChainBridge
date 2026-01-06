# Observer Kill-Switch Visibility Specification

**PAC Reference:** PAC-JEFFREY-P45  
**Classification:** AUDIT-GRADE / READ-ONLY  
**Governance Mode:** HARD / FAIL-CLOSED  
**Access Isolation Agent:** DAN (GID-07)  
**Version:** 1.0.0  
**Date:** 2026-01-02

---

## 1. Overview

This specification defines what kill-switch information is visible to regulated observers and explicitly documents that **observers have ZERO control capability** over the kill-switch system.

### Core Principle

> **Visibility without control is a trust primitive.**

Observers can verify that safety mechanisms exist and function. They cannot operate them.

---

## 2. Kill-Switch States

### 2.1 State Definitions

| State | Description | Observer Visibility |
|-------|-------------|---------------------|
| `DISARMED` | Kill-switch is inactive | ✅ Visible |
| `ARMED` | Kill-switch is ready for engagement | ✅ Visible |
| `ENGAGED` | Kill-switch is active, operations halted | ✅ Visible |
| `COOLDOWN` | Post-engagement recovery period | ✅ Visible |

### 2.2 State Information Available to Observers

| Information | Visible | Format |
|-------------|---------|--------|
| Current state | ✅ | State enum |
| State since timestamp | ✅ | ISO 8601 UTC |
| Last state change by | ✅ | Agent/Operator ID |
| Engagement reason (if engaged) | ✅ | Text description |
| Cooldown remaining (if cooldown) | ✅ | Duration |
| State history | ✅ | Last 10 transitions |

### 2.3 State Information Hidden from Observers

| Information | Reason |
|-------------|--------|
| Control API endpoints | No control access |
| Engagement credentials | Security-sensitive |
| Override mechanisms | Operator-only |
| Automation rules | Internal configuration |

---

## 3. Observer Kill-Switch View

### 3.1 Read-Only Display

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  KILL-SWITCH STATUS (READ-ONLY)                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│         ╔═══════════════════════════════════════════════════════╗          │
│         ║                                                       ║          │
│         ║              KILL-SWITCH STATE: ARMED                 ║          │
│         ║                                                       ║          │
│         ╚═══════════════════════════════════════════════════════╝          │
│                                                                             │
│  CURRENT STATUS                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  State:           ARMED                                             │   │
│  │  Since:           2026-01-02 09:00:00 UTC                           │   │
│  │  Changed By:      DAN (GID-07)                                      │   │
│  │  Duration:        5h 32m 15s                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ⚠️ OBSERVER NOTICE                                                  │   │
│  │                                                                     │   │
│  │  You have VIEW-ONLY access to kill-switch status.                   │   │
│  │  Control functions (arm, engage, disengage) are NOT available.      │   │
│  │                                                                     │   │
│  │  This view demonstrates that safety mechanisms exist and are        │   │
│  │  operational. Control authority is reserved for operators.          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  STATE HISTORY (Read-Only)                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Timestamp            │ From       │ To         │ Actor             │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  2026-01-02 09:00:00  │ DISARMED   │ ARMED      │ DAN (GID-07)      │   │
│  │  2026-01-01 18:00:00  │ COOLDOWN   │ DISARMED   │ system            │   │
│  │  2026-01-01 17:45:00  │ ENGAGED    │ COOLDOWN   │ BENSON (GID-00)   │   │
│  │  2026-01-01 17:30:00  │ ARMED      │ ENGAGED    │ operator-001      │   │
│  │  2026-01-01 08:00:00  │ DISARMED   │ ARMED      │ DAN (GID-07)      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Engaged State Display

When kill-switch is ENGAGED:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  KILL-SWITCH STATUS (READ-ONLY)                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│         ╔═══════════════════════════════════════════════════════╗          │
│         ║                                                       ║          │
│         ║           ⚠️ KILL-SWITCH STATE: ENGAGED                ║          │
│         ║                                                       ║          │
│         ╚═══════════════════════════════════════════════════════╝          │
│                                                                             │
│  ENGAGEMENT DETAILS                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  State:           ENGAGED                                           │   │
│  │  Engaged At:      2026-01-02 14:32:15 UTC                           │   │
│  │  Engaged By:      operator-001                                      │   │
│  │  Reason:          Manual safety halt - anomaly detected             │   │
│  │  Duration:        0h 12m 45s                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  SYSTEM STATUS DURING ENGAGEMENT                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Agent Operations:       HALTED                                     │   │
│  │  New Sessions:           BLOCKED                                    │   │
│  │  Existing Sessions:      ACTIVE (read-only unaffected)              │   │
│  │  PDO Processing:         SUSPENDED                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ⚠️ Your observer session remains active during kill-switch engagement.     │
│     Read-only access is unaffected.                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Cooldown State Display

When kill-switch is in COOLDOWN:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  KILL-SWITCH STATUS (READ-ONLY)                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│         ╔═══════════════════════════════════════════════════════╗          │
│         ║                                                       ║          │
│         ║            KILL-SWITCH STATE: COOLDOWN                ║          │
│         ║                                                       ║          │
│         ╚═══════════════════════════════════════════════════════╝          │
│                                                                             │
│  COOLDOWN DETAILS                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  State:           COOLDOWN                                          │   │
│  │  Cooldown Started:2026-01-02 14:45:00 UTC                           │   │
│  │  Cooldown Ends:   2026-01-02 15:00:00 UTC                           │   │
│  │  Remaining:       12m 30s                                           │   │
│  │  Previous State:  ENGAGED                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ℹ️ Cooldown is a mandatory recovery period after disengagement.            │
│     Normal operations will resume automatically when cooldown expires.      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. API Specification

### 4.1 Permitted Endpoint

**GET /occ/kill-switch/state** (Observer Accessible)

```json
{
  "state": "ARMED",
  "since": "2026-01-02T09:00:00Z",
  "changed_by": {
    "type": "agent",
    "id": "DAN",
    "gid": "GID-07"
  },
  "duration_seconds": 19935,
  "engagement_reason": null,
  "cooldown_remaining_seconds": null,
  "history": [
    {
      "timestamp": "2026-01-02T09:00:00Z",
      "from_state": "DISARMED",
      "to_state": "ARMED",
      "actor": "DAN (GID-07)"
    }
  ]
}
```

### 4.2 Denied Endpoints (HARD BLOCK)

| Endpoint | Method | Response |
|----------|--------|----------|
| `/occ/kill-switch/arm` | POST | 403 Forbidden |
| `/occ/kill-switch/engage` | POST | 403 Forbidden |
| `/occ/kill-switch/disengage` | POST | 403 Forbidden |
| `/occ/kill-switch/override` | POST | 403 Forbidden |
| `/occ/kill-switch/config` | GET/PUT | 403 Forbidden |

### 4.3 Error Response for Denied Operations

```json
{
  "error": "FORBIDDEN",
  "code": "OBSERVER_NO_CONTROL",
  "message": "Observer role does not have kill-switch control authority",
  "permitted_operations": ["view_state"],
  "denied_operation": "engage"
}
```

---

## 5. Permission Matrix

### 5.1 Kill-Switch Operations

| Operation | Operator | Observer | Reason |
|-----------|----------|----------|--------|
| View current state | ✅ | ✅ | Transparency |
| View state history | ✅ | ✅ | Audit trail |
| View engagement reason | ✅ | ✅ | Transparency |
| Arm kill-switch | ✅ | ❌ | Control authority |
| Engage kill-switch | ✅ | ❌ | Control authority |
| Disengage kill-switch | ✅ | ❌ | Control authority |
| Override cooldown | ✅ | ❌ | Control authority |
| Configure kill-switch | ✅ | ❌ | Configuration authority |

### 5.2 Information Access

| Information | Observer Access | Notes |
|-------------|-----------------|-------|
| State enum | ✅ READ | ARMED, DISARMED, ENGAGED, COOLDOWN |
| State timestamp | ✅ READ | When state last changed |
| Actor ID | ✅ READ | Who changed state |
| Engagement reason | ✅ READ | Why engaged (if applicable) |
| Cooldown duration | ✅ READ | Remaining cooldown time |
| State history | ✅ READ | Last 10 transitions |
| Control API docs | ❌ HIDDEN | Not exposed to observers |
| Configuration | ❌ HIDDEN | Internal settings |
| Automation rules | ❌ HIDDEN | Internal logic |

---

## 6. UI Components

### 6.1 State Indicator

```
KILL-SWITCH STATE INDICATOR

┌─────────────────────────────┐
│  State: ARMED               │
│  ●━━━━━━━━━━━━━━━━━━━━━━●   │
│  DISARMED           ENGAGED │
└─────────────────────────────┘

Visual states:
- DISARMED: Gray indicator, left position
- ARMED: Yellow indicator, center-left position
- ENGAGED: Red indicator, right position
- COOLDOWN: Blue indicator, center position
```

### 6.2 Hidden UI Elements

The following UI elements are **NOT RENDERED** for observers:

- ARM button
- ENGAGE button
- DISENGAGE button
- Configuration panel
- Override controls
- Automation settings
- Emergency contacts

### 6.3 Observer Notice Badge

Always displayed on kill-switch views:

```
┌─────────────────────────────────────────────────────────────┐
│  👁️ VIEW-ONLY | No control capability                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Audit Requirements

### 7.1 Logged Events

| Event | Logged For Observer |
|-------|---------------------|
| View kill-switch state | ✅ |
| View state history | ✅ |
| Attempt control operation | ✅ (with alert) |
| Export state data | ✅ |

### 7.2 Audit Log Entry Format

```json
{
  "timestamp": "2026-01-02T10:45:22Z",
  "observer_id": "obs-12345",
  "observer_org": "SEC",
  "action": "kill_switch:view_state",
  "result": "success",
  "data_returned": {
    "state": "ARMED",
    "history_entries": 5
  }
}
```

### 7.3 Control Attempt Alert

When observer attempts control operation:

```json
{
  "timestamp": "2026-01-02T10:46:00Z",
  "alert_type": "OBSERVER_CONTROL_ATTEMPT",
  "severity": "HIGH",
  "observer_id": "obs-12345",
  "observer_org": "SEC",
  "attempted_operation": "engage",
  "result": "BLOCKED",
  "notification_sent_to": ["security-team", "cto"]
}
```

---

## 8. Observer Impact During Kill-Switch States

### 8.1 Normal Operation (ARMED/DISARMED)

| Observer Function | Status |
|-------------------|--------|
| Session active | ✅ |
| Read operations | ✅ |
| Export operations | ✅ |
| Verification | ✅ |

### 8.2 During ENGAGED State

| Observer Function | Status | Notes |
|-------------------|--------|-------|
| Existing sessions | ✅ ACTIVE | Read-only unaffected |
| New sessions | ❌ BLOCKED | No new logins |
| Read operations | ✅ AVAILABLE | Data still accessible |
| Export operations | ✅ AVAILABLE | Exports still work |
| Verification | ✅ AVAILABLE | Verification still works |
| Real-time data | ⚠️ STALE | No new data during halt |

### 8.3 During COOLDOWN State

| Observer Function | Status |
|-------------------|--------|
| Sessions | ✅ ACTIVE |
| Read operations | ✅ |
| New sessions | ⚠️ ALLOWED (cautiously) |
| Data freshness | Gradually restoring |

---

## 9. Governance Invariants

### INV-KS-OBS-001: View-Only Access
Observer role has zero kill-switch control paths.

### INV-KS-OBS-002: No UI Controls
Kill-switch control UI elements are never rendered for observers.

### INV-KS-OBS-003: API Hard Block
Kill-switch control API endpoints return 403 for observers.

### INV-KS-OBS-004: Control Attempt Logging
All control attempts by observers are logged and alerted.

### INV-KS-OBS-005: State Transparency
Current kill-switch state is always visible to observers.

---

## 10. Verification Checklist

For auditors verifying kill-switch observer access:

- [ ] Observer can view current kill-switch state
- [ ] Observer can view state history
- [ ] Observer cannot access ARM endpoint
- [ ] Observer cannot access ENGAGE endpoint  
- [ ] Observer cannot access DISENGAGE endpoint
- [ ] Control buttons are not visible in UI
- [ ] Observer notice badge is displayed
- [ ] Control attempts are blocked and logged
- [ ] Session remains active during ENGAGED state

---

## 11. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-02 | BENSON/DAN | Initial kill-switch visibility spec |

---

**Document Authority:** PAC-JEFFREY-P45  
**Access Isolation Agent:** DAN (GID-07)  
**Classification:** AUDIT-GRADE  
**Governance:** HARD / FAIL-CLOSED
