# P58 — Customer Access Matrix

**PAC:** PAC-JEFFREY-P58  
**Artifact:** 5 of 6  
**Classification:** ACCESS CONTROL  
**Status:** DELIVERED  
**Date:** 2026-01-03  

---

## 1. Executive Summary

This matrix defines what each customer persona can access at each license tier. Clear boundaries prevent scope creep and support CFO/GC conversations.

---

## 2. Persona Definitions

| Persona | Role | Typical Actions |
|---------|------|-----------------|
| **Viewer** | Read-only analyst | View dashboards, export reports |
| **Operator** | Day-to-day user | Create PDOs, manage workflows |
| **Admin** | Team manager | User management, configuration |
| **Finance** | Settlement user | View settlements, reconciliation |
| **Executive** | Strategic oversight | High-level dashboards, ROI reports |

---

## 3. Access Matrix by Tier

### 3.1 L1 — VERIFY

| Persona | Seats | Access Level |
|---------|-------|--------------|
| Viewer | 3 | Full read access |
| Operator | 0 | Not available |
| Admin | 1 (shared) | Basic user management |
| Finance | 0 | Not available |
| Executive | 1 | Dashboard only |

### 3.2 L2 — CONTROL

| Persona | Seats | Access Level |
|---------|-------|--------------|
| Viewer | 5 | Full read access |
| Operator | 5 | Create/edit PDOs |
| Admin | 2 | Full user management |
| Finance | 0 | Not available |
| Executive | 2 | Full dashboards |

### 3.3 L3 — SETTLE

| Persona | Seats | Access Level |
|---------|-------|--------------|
| Viewer | Unlimited | Full read access |
| Operator | Unlimited | Full PDO lifecycle |
| Admin | 5 | Full management |
| Finance | 5 | Settlement access |
| Executive | Unlimited | Full access |

---

## 4. Surface Access by Tier

| Surface | L1 | L2 | L3 |
|---------|----|----|-----|
| **ChainBoard** |
| Dashboard Home | ✅ | ✅ | ✅ |
| PDO List | ✅ | ✅ | ✅ |
| PDO Create | ❌ | ✅ | ✅ |
| Operator Console | ❌ | ✅ | ✅ |
| Settlement Panel | ❌ | ❌ | ✅ |
| **ChainIQ** |
| Score Viewer | ✅ | ✅ | ✅ |
| Score Generator | ❌ | ✅ | ✅ |
| Risk Dashboard | ❌ | ✅ | ✅ |
| Settlement Risk | ❌ | ❌ | ✅ |
| **API** |
| Read Endpoints | ✅ | ✅ | ✅ |
| Write Endpoints | ❌ | ✅ | ✅ |
| Settlement API | ❌ | ❌ | ✅ |
| **Reports** |
| Basic Reports | ✅ | ✅ | ✅ |
| Custom Reports | ❌ | ✅ | ✅ |
| Settlement Reports | ❌ | ❌ | ✅ |

---

## 5. Access Enforcement

| Violation | Detection | Response |
|-----------|-----------|----------|
| Seat overage | Real-time | Soft block + upgrade prompt |
| Feature access attempt | Real-time | Hard block + tier message |
| API rate limit | Real-time | 429 response |
| Unauthorized settlement | Real-time | Block + alert |

---

## 6. Customer-Visible Messaging

### 6.1 Access Denied (Feature)

```
This feature requires [TIER NAME] license.
Your current license: [CURRENT TIER]
Contact sales to upgrade: sales@chainbridge.io
```

### 6.2 Seat Limit Reached

```
Your team has reached the seat limit for [TIER NAME].
Active seats: [X] / [MAX]
Contact your admin to manage seats or upgrade.
```

---

## 7. Admin Controls (L2+)

| Control | L2 | L3 |
|---------|----|----|
| Add/remove users | ✅ | ✅ |
| Assign seat types | ✅ | ✅ |
| View usage stats | ✅ | ✅ |
| Configure SSO | ❌ | ✅ |
| Custom roles | ❌ | ✅ |
| Settlement permissions | ❌ | ✅ |

---

## 8. Signature Block

| Agent | Role | Signature |
|-------|------|-----------|
| SONNY (GID-02) | Customer UX | ✅ SIGNED |
| PAX (GID-05) | Access Strategy | ✅ SIGNED |
| BENSON (GID-00) | Matrix Approval | ✅ SIGNED |

---

**Artifact Hash:** `sha256:p58-art5-customer-access-matrix`  
**Status:** DELIVERED
