# OCC Pilot UX Map — Read-Only Views

**PAC Reference:** PAC-JEFFREY-P44  
**Classification:** UX SPECIFICATION  
**Author:** SONNY (GID-02)  
**Status:** CANONICAL  

---

## 1. Overview

This document specifies the user experience for external pilots accessing the Operator Control Center (OCC). All pilot views are **READ-ONLY** with no mutation affordances.

---

## 2. Pilot View Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    OCC PILOT DASHBOARD                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ PDO List    │ │ Activity    │ │ Artifacts   │ │ Ledger    │ │
│  │ (SHADOW)    │ │ Stream      │ │ Gallery     │ │ Integrity │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    PDO DETAIL VIEW                          ││
│  │  • Read-only fields                                         ││
│  │  • Timeline visualization                                   ││
│  │  • No action buttons                                        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ PILOT MODE INDICATOR: 🔒 READ-ONLY | SHADOW DATA ONLY      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. View Specifications

### 3.1 PDO List View

| Element | Behavior | Pilot Access |
|---------|----------|--------------|
| PDO Table | Display SHADOW PDOs only | ✅ VIEW |
| Search/Filter | Filter by outcome, date, actor | ✅ USE |
| Pagination | Navigate pages | ✅ USE |
| Sort | Sort by columns | ✅ USE |
| Create Button | **HIDDEN** | ❌ HIDDEN |
| Bulk Actions | **HIDDEN** | ❌ HIDDEN |
| Export | **DISABLED** | ❌ DISABLED |

**Visual Indicators:**
- Banner: "🔒 PILOT MODE: Read-Only Access | SHADOW Data Only"
- Classification badge: "SHADOW" on each PDO row
- No hover states suggesting clickable actions

### 3.2 PDO Detail View

| Element | Behavior | Pilot Access |
|---------|----------|--------------|
| PDO ID | Display | ✅ VIEW |
| Outcome | Display (badge) | ✅ VIEW |
| Actor | Display | ✅ VIEW |
| Timestamp | Display | ✅ VIEW |
| Metadata | Display (read-only) | ✅ VIEW |
| Timeline | Display (read-only) | ✅ VIEW |
| Hash | Display (truncated) | ✅ VIEW |
| Edit Button | **HIDDEN** | ❌ HIDDEN |
| Override Button | **HIDDEN** | ❌ HIDDEN |
| Escalate Button | **HIDDEN** | ❌ HIDDEN |

**Visual Indicators:**
- All form fields disabled (grayed out)
- No pencil icons or edit affordances
- Lock icon next to each field

### 3.3 Activity Stream View

| Element | Behavior | Pilot Access |
|---------|----------|--------------|
| Activity List | Display recent activities | ✅ VIEW |
| Activity Detail | Expand for details | ✅ VIEW |
| Filters | Filter by type, date | ✅ USE |
| Real-time Updates | Disabled for pilots | ❌ DISABLED |
| Acknowledge Button | **HIDDEN** | ❌ HIDDEN |

### 3.4 Artifacts View

| Element | Behavior | Pilot Access |
|---------|----------|--------------|
| Artifact List | Display governance artifacts | ✅ VIEW |
| Artifact Detail | View artifact content | ✅ VIEW |
| Download | **DISABLED** | ❌ DISABLED |
| Create Button | **HIDDEN** | ❌ HIDDEN |

### 3.5 Ledger Integrity View

| Element | Behavior | Pilot Access |
|---------|----------|--------------|
| Integrity Status | Display (HEALTHY/UNHEALTHY) | ✅ VIEW |
| PDO Count | Display total SHADOW PDOs | ✅ VIEW |
| Hash Validity | Display valid/invalid counts | ✅ VIEW |
| Classification Breakdown | Display SHADOW only | ✅ VIEW |
| Full Audit | **DISABLED** | ❌ DISABLED |

---

## 4. Hidden Elements (Pilot Mode)

The following UI elements are **completely hidden** from pilots:

| Element | Location | Reason |
|---------|----------|--------|
| Kill-Switch Panel | Header | Operator-only |
| Agent Control Panel | Sidebar | Operator-only |
| Configuration Settings | Settings | Operator-only |
| Production PDOs | PDO List | Classification barrier |
| Mutation Buttons | All views | Read-only mode |
| Admin Menu | Navigation | Operator-only |
| Operator Console | Navigation | Operator-only |
| Real-time WebSocket | Activity | Security |

---

## 5. Visual Differentiation

### 5.1 Pilot Mode Banner

```html
<div class="pilot-banner">
  <span class="lock-icon">🔒</span>
  <span class="mode">PILOT MODE</span>
  <span class="access">Read-Only Access</span>
  <span class="data">SHADOW Data Only</span>
</div>
```

**Styling:**
- Background: `#FFF3CD` (amber/warning)
- Border: `1px solid #FFE69C`
- Text: `#856404`
- Position: Fixed top (always visible)

### 5.2 Disabled Field Styling

```css
.pilot-mode input:disabled,
.pilot-mode select:disabled,
.pilot-mode textarea:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
  opacity: 0.7;
}

.pilot-mode .field-lock-icon {
  display: inline-block;
  margin-left: 4px;
  color: #6c757d;
}
```

### 5.3 SHADOW Badge

```css
.classification-badge.shadow {
  background-color: #6c757d;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  text-transform: uppercase;
}
```

---

## 6. Navigation Structure

```
┌─────────────────────────────────────────┐
│ 🔒 PILOT MODE                           │
├─────────────────────────────────────────┤
│ 📋 PDO List                             │
│ 📊 Activity Stream                      │
│ 📁 Artifacts                            │
│ ✅ Ledger Integrity                     │
├─────────────────────────────────────────┤
│ ❌ Operator Console (HIDDEN)            │
│ ❌ Kill-Switch (HIDDEN)                 │
│ ❌ Agent Control (HIDDEN)               │
│ ❌ Settings (HIDDEN)                    │
└─────────────────────────────────────────┘
```

---

## 7. Error States

### 7.1 Permission Denied

When a pilot attempts a forbidden action:

```
┌─────────────────────────────────────────┐
│ ⚠️ Action Not Permitted                 │
├─────────────────────────────────────────┤
│ This action is not available in         │
│ Pilot Mode.                             │
│                                         │
│ Pilot access is read-only.              │
│                                         │
│ [Close]                                 │
└─────────────────────────────────────────┘
```

### 7.2 Rate Limit Exceeded

```
┌─────────────────────────────────────────┐
│ 🚫 Rate Limit Exceeded                  │
├─────────────────────────────────────────┤
│ You have exceeded the request limit.    │
│                                         │
│ Please wait 60 seconds before           │
│ making another request.                 │
│                                         │
│ [OK]                                    │
└─────────────────────────────────────────┘
```

---

## 8. Accessibility

| Requirement | Implementation |
|-------------|----------------|
| Screen reader | ARIA labels for pilot mode |
| Keyboard navigation | Tab order preserved |
| Color contrast | WCAG AA compliant |
| Focus indicators | Visible focus rings |

---

## 9. Implementation Checklist

- [ ] Pilot mode banner component
- [ ] PDO list with SHADOW filter
- [ ] PDO detail read-only view
- [ ] Activity stream (polling, not WebSocket)
- [ ] Artifacts gallery
- [ ] Ledger integrity display
- [ ] Hidden navigation items
- [ ] Disabled form fields
- [ ] Permission denied modal
- [ ] Rate limit modal

---

## 10. Governance References

- **INV-PILOT-001**: Pilots are capability-constrained
- **INV-PILOT-002**: Read-only access only
- **INV-UX-001**: No mutation affordances in pilot mode

---

**Document Hash:** `sha256:occ-pilot-ux-map-v1.0.0`  
**Status:** CANONICAL
