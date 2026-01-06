# Artifact 7: Operator Trust Dashboard Specification

**PAC Reference:** PAC-JEFFREY-P52  
**Classification:** ITaaS / GOVERNED  
**Status:** DELIVERED  
**Author:** SONNY (GID-02)  
**Orchestrator:** BENSON (GID-00)

---

## 1. Overview

The Operator Trust Dashboard provides real-time visibility into ITaaS verification status, drift events, and trust scores. It is designed for IT operations teams managing verified infrastructure.

---

## 2. Dashboard Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Trust Dashboard Layout                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    HEADER BAR                           │   │
│  │  Logo | Tenant: ACME | Last Scan: 2 min ago | Status: ●│   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────────────────────┐   │
│  │   TRUST SCORE    │  │         DRIFT EVENTS             │   │
│  │                  │  │                                  │   │
│  │       A          │  │  ● HIGH: Auth config changed    │   │
│  │      91.8        │  │  ○ LOW: Version updated         │   │
│  │                  │  │                                  │   │
│  └──────────────────┘  └──────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              CHAOS COVERAGE BY DIMENSION                │   │
│  │                                                         │   │
│  │  AUTH    ████████████████████░░░  92%                  │   │
│  │  DATA    ███████████████████░░░░  88%                  │   │
│  │  STATE   ██████████████████░░░░░  85%                  │   │
│  │  TIMING  █████████████████░░░░░░  82%                  │   │
│  │  NETWORK ████████████████░░░░░░░  78%                  │   │
│  │  RESOURCE████████████████░░░░░░░  76%                  │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 RECENT TEST RESULTS                      │  │
│  │                                                          │  │
│  │  Time       | Tests | Passed | Failed | CCI   | Grade   │  │
│  │  12:00:00   | 250   | 238    | 12     | 88.3  | A       │  │
│  │  11:45:00   | 250   | 240    | 10     | 89.1  | A       │  │
│  │  11:30:00   | 250   | 235    | 15     | 87.2  | B+      │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               KILL-SWITCH STATUS                        │   │
│  │                                                         │   │
│  │  State: DISARMED  |  [ARM]  [ENGAGE]  [HISTORY]        │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Specifications

### 3.1 Trust Score Widget

| Element | Description |
|---------|-------------|
| Grade | Large letter grade (A+, A, B+, etc.) |
| Score | Numeric score (0-100) |
| Trend | Arrow indicator (↑ improving, ↓ declining, → stable) |
| Color | Green (80+), Yellow (60-79), Red (<60) |

### 3.2 Drift Events Panel

| Element | Description |
|---------|-------------|
| Severity Icon | Colored dot (Red=Critical, Orange=High, Yellow=Medium, Gray=Low) |
| Event Description | Brief description of drift |
| Timestamp | When detected |
| Action Button | View details / Acknowledge |

### 3.3 Chaos Coverage Chart

| Element | Description |
|---------|-------------|
| Dimension Label | AUTH, DATA, STATE, etc. |
| Progress Bar | Visual coverage percentage |
| Percentage | Numeric coverage |
| Color | Green (80+), Yellow (60-79), Red (<60) |

### 3.4 Test Results Table

| Column | Description |
|--------|-------------|
| Time | Scan timestamp |
| Tests | Total tests executed |
| Passed | Tests passed |
| Failed | Tests failed |
| CCI | CCI score for scan |
| Grade | Grade for scan |

### 3.5 Kill-Switch Panel

| Element | Description |
|---------|-------------|
| State Indicator | DISARMED / ARMED / ENGAGED / COOLDOWN |
| ARM Button | Arms the kill-switch |
| ENGAGE Button | Engages (requires ARMED state) |
| HISTORY Button | View audit log |

---

## 4. Real-Time Updates

### 4.1 WebSocket Events

```typescript
interface DashboardEvent {
  type: 'SCORE_UPDATE' | 'DRIFT_EVENT' | 'TEST_COMPLETE' | 'KILL_SWITCH';
  payload: any;
  timestamp: string;
}

// Score update
{
  type: 'SCORE_UPDATE',
  payload: {
    final_score: 91.8,
    grade: 'A',
    delta: +0.3
  }
}

// Drift event
{
  type: 'DRIFT_EVENT',
  payload: {
    event_id: 'drift-001',
    severity: 'HIGH',
    category: 'SECURITY',
    description: 'Auth configuration changed'
  }
}
```

### 4.2 Polling Fallback

| Data | Poll Interval |
|------|---------------|
| Trust Score | 30 seconds |
| Drift Events | 15 seconds |
| Test Results | 60 seconds |
| Kill-Switch | 10 seconds |

---

## 5. Operator Actions

### 5.1 Available Actions

| Action | Permission | Effect |
|--------|------------|--------|
| View Score | READ | Display current scores |
| View Drift | READ | List drift events |
| Acknowledge Drift | WRITE | Mark drift as reviewed |
| ARM Kill-Switch | ARM_ONLY | Arm for engagement |
| ENGAGE Kill-Switch | FULL_ACCESS | Halt all execution |
| Download Report | READ | Export trust report |
| Configure Alerts | WRITE | Set alert thresholds |

### 5.2 Permission Levels

| Level | Capabilities |
|-------|-------------|
| VIEWER | View-only access |
| OPERATOR | View + acknowledge + reports |
| ADMIN | Full access including kill-switch |

---

## 6. Alert Configuration

### 6.1 Alert Types

| Alert | Default Threshold | Action |
|-------|-------------------|--------|
| Score Drop | >10 points | Email + Dashboard |
| Critical Drift | Any | Email + SMS + Dashboard |
| High Drift | Any | Email + Dashboard |
| Test Failure Spike | >20% | Dashboard |
| Kill-Switch Engaged | Any | Email + SMS + Dashboard |

### 6.2 Alert Schema

```json
{
  "alert_id": "alert-001",
  "type": "SCORE_DROP",
  "severity": "HIGH",
  "threshold": 10,
  "current_value": 15.2,
  "message": "Trust score dropped by 15.2 points",
  "timestamp": "2026-01-03T12:00:00Z",
  "actions": ["email", "dashboard"]
}
```

---

## 7. Report Export

### 7.1 Export Formats

| Format | Use Case |
|--------|----------|
| PDF | Formal reports, audits |
| JSON | API integration |
| CSV | Spreadsheet analysis |
| Markdown | Documentation |

### 7.2 Export API

```http
GET /api/itaas/reports/export
Authorization: Bearer <token>
Query Parameters:
  - format: pdf | json | csv | markdown
  - from: ISO8601 date
  - to: ISO8601 date
  - include_drift: boolean
  - include_tests: boolean
```

---

## 8. Mobile Responsiveness

### 8.1 Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1200px) | Full layout |
| Tablet (768-1200px) | Stacked panels |
| Mobile (<768px) | Single column |

### 8.2 Mobile Priority

1. Trust Score (always visible)
2. Critical Drift Events
3. Kill-Switch Status
4. Test Summary
5. Detailed Charts

---

## 9. Accessibility

| Requirement | Implementation |
|-------------|----------------|
| Screen Reader | ARIA labels on all elements |
| Keyboard Nav | Tab navigation, shortcuts |
| Color Blind | Patterns + colors |
| High Contrast | Supported mode |
| Focus Indicators | Visible focus rings |

---

## 10. Integration API

### 10.1 Dashboard Data Endpoint

```http
GET /api/itaas/dashboard
Authorization: Bearer <token>

Response:
{
  "tenant_id": "tenant-acme",
  "current_score": {
    "final": 91.8,
    "grade": "A",
    "base": 92.5,
    "cci": 88.3,
    "safety": 100.0
  },
  "drift_events": [...],
  "recent_tests": [...],
  "kill_switch": {
    "state": "DISARMED"
  },
  "last_updated": "2026-01-03T12:00:00Z"
}
```

---

## 11. Invariants

| ID | Invariant | Status |
|----|-----------|--------|
| INV-DASH-001 | Real-time updates < 30s | ENFORCED |
| INV-DASH-002 | Kill-switch always visible | ENFORCED |
| INV-DASH-003 | Critical alerts immediate | ENFORCED |
| INV-DASH-004 | Reports include disclaimer | ENFORCED |

---

**ARTIFACT STATUS: DELIVERED ✅**
