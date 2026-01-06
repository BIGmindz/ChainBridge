# Pilot Threat & Abuse Register

**PAC Reference:** PAC-JEFFREY-P44  
**Classification:** SECURITY / THREAT MODEL  
**Authors:** MIRA-R (GID-03) + SAM (GID-06)  
**Status:** CANONICAL  

---

## 1. Purpose

This register enumerates potential threats, abuse scenarios, and failure modes for external pilots. Each scenario includes mitigations implemented or required.

---

## 2. Threat Categories

| Category | Code | Risk Level |
|----------|------|------------|
| Authentication | AUTH | HIGH |
| Authorization | AUTHZ | HIGH |
| Data Exposure | DATA | CRITICAL |
| Rate Abuse | RATE | MEDIUM |
| Enumeration | ENUM | MEDIUM |
| Reputation | REP | HIGH |
| Compliance | COMP | CRITICAL |

---

## 3. Threat Register

### 3.1 Authentication Threats (AUTH)

#### AUTH-001: Token Theft
| Field | Value |
|-------|-------|
| **Threat** | Pilot token stolen and reused by unauthorized party |
| **Risk Level** | HIGH |
| **Attack Vector** | Network interception, client-side theft, social engineering |
| **Impact** | Unauthorized access to pilot data |
| **Mitigation** | 24-hour token expiry, no auto-refresh, IP binding (optional) |
| **Detection** | Anomalous IP, concurrent sessions |
| **Status** | ✅ MITIGATED |

#### AUTH-002: Token Forgery
| Field | Value |
|-------|-------|
| **Threat** | Attacker forges pilot JWT |
| **Risk Level** | HIGH |
| **Attack Vector** | Weak signing key, algorithm confusion |
| **Impact** | Unauthorized access |
| **Mitigation** | RS256 signing, key rotation, audience validation |
| **Detection** | Invalid signature, wrong issuer |
| **Status** | ✅ MITIGATED |

#### AUTH-003: Session Fixation
| Field | Value |
|-------|-------|
| **Threat** | Attacker fixates pilot session |
| **Risk Level** | MEDIUM |
| **Attack Vector** | URL manipulation, cookie injection |
| **Impact** | Session hijacking |
| **Mitigation** | Token-based auth (no sessions), secure token storage |
| **Detection** | Token reuse patterns |
| **Status** | ✅ MITIGATED |

---

### 3.2 Authorization Threats (AUTHZ)

#### AUTHZ-001: Privilege Escalation
| Field | Value |
|-------|-------|
| **Threat** | Pilot attempts to gain operator permissions |
| **Risk Level** | CRITICAL |
| **Attack Vector** | Parameter tampering, role injection |
| **Impact** | Unauthorized mutations |
| **Mitigation** | Server-side role validation, capability-based access |
| **Detection** | Forbidden operation attempts logged |
| **Status** | ✅ MITIGATED |

#### AUTHZ-002: Scope Bypass
| Field | Value |
|-------|-------|
| **Threat** | Pilot accesses endpoints outside permitted scope |
| **Risk Level** | HIGH |
| **Attack Vector** | Direct URL access, API probing |
| **Impact** | Access to operator functions |
| **Mitigation** | Endpoint allowlist, fail-closed policy |
| **Detection** | 403/404 response logging |
| **Status** | ✅ MITIGATED |

#### AUTHZ-003: Classification Bypass
| Field | Value |
|-------|-------|
| **Threat** | Pilot accesses PRODUCTION PDOs |
| **Risk Level** | CRITICAL |
| **Attack Vector** | Direct PDO ID access, enumeration |
| **Impact** | Production data exposure |
| **Mitigation** | Return 404 (not 403) for PRODUCTION PDOs |
| **Detection** | Attempted access to non-SHADOW IDs |
| **Status** | ✅ MITIGATED |

---

### 3.3 Data Exposure Threats (DATA)

#### DATA-001: Production Data Leak
| Field | Value |
|-------|-------|
| **Threat** | PRODUCTION PDOs visible to pilots |
| **Risk Level** | CRITICAL |
| **Attack Vector** | Classification filter bypass, query injection |
| **Impact** | Real transaction data exposed |
| **Mitigation** | Query-level classification filter, no PRODUCTION in pilot DB |
| **Detection** | Classification mismatch in logs |
| **Status** | ✅ MITIGATED |

#### DATA-002: Metadata Leakage
| Field | Value |
|-------|-------|
| **Threat** | Sensitive metadata exposed in PDOs |
| **Risk Level** | MEDIUM |
| **Attack Vector** | Verbose error messages, metadata inspection |
| **Impact** | Internal system details exposed |
| **Mitigation** | Metadata sanitization for pilot views |
| **Detection** | Metadata field inspection |
| **Status** | ⚠️ PARTIAL (review metadata schema) |

#### DATA-003: Bulk Data Extraction
| Field | Value |
|-------|-------|
| **Threat** | Pilot extracts all SHADOW data |
| **Risk Level** | MEDIUM |
| **Attack Vector** | Automated scraping, pagination abuse |
| **Impact** | Complete dataset extraction |
| **Mitigation** | Rate limits, no export function, pagination limits |
| **Detection** | High request volume |
| **Status** | ✅ MITIGATED |

---

### 3.4 Rate Abuse Threats (RATE)

#### RATE-001: API Flooding
| Field | Value |
|-------|-------|
| **Threat** | Pilot floods API with requests |
| **Risk Level** | MEDIUM |
| **Attack Vector** | Automated requests, parallel connections |
| **Impact** | Service degradation |
| **Mitigation** | 30 req/min, 500 req/hour limits |
| **Detection** | Rate limit triggers |
| **Status** | ✅ MITIGATED |

#### RATE-002: Burst Abuse
| Field | Value |
|-------|-------|
| **Threat** | Rapid bursts to evade rate limits |
| **Risk Level** | MEDIUM |
| **Attack Vector** | Timed bursts within window |
| **Impact** | Temporary service impact |
| **Mitigation** | Burst limit of 10 in 10s window |
| **Detection** | Burst pattern detection |
| **Status** | ✅ MITIGATED |

---

### 3.5 Enumeration Threats (ENUM)

#### ENUM-001: PDO ID Enumeration
| Field | Value |
|-------|-------|
| **Threat** | Pilot enumerates all PDO IDs |
| **Risk Level** | MEDIUM |
| **Attack Vector** | Sequential ID guessing, brute force |
| **Impact** | Discovery of PRODUCTION PDO IDs |
| **Mitigation** | UUIDs, 404 response for non-SHADOW |
| **Detection** | High 404 rate |
| **Status** | ✅ MITIGATED |

#### ENUM-002: Endpoint Discovery
| Field | Value |
|-------|-------|
| **Threat** | Pilot discovers hidden endpoints |
| **Risk Level** | LOW |
| **Attack Vector** | Path fuzzing, documentation leakage |
| **Impact** | Knowledge of internal API structure |
| **Mitigation** | No endpoint listing, consistent 404 responses |
| **Detection** | Path fuzzing patterns |
| **Status** | ✅ MITIGATED |

---

### 3.6 Reputation Threats (REP)

#### REP-001: False Claims
| Field | Value |
|-------|-------|
| **Threat** | Pilot makes false claims about ChainBridge capabilities |
| **Risk Level** | HIGH |
| **Attack Vector** | Public statements, marketing materials |
| **Impact** | Regulatory risk, reputation damage |
| **Mitigation** | Forbidden claims registry, pilot agreement, monitoring |
| **Detection** | Public mention monitoring |
| **Status** | ⚠️ REQUIRES LEGAL AGREEMENT |

#### REP-002: Demo Misrepresentation
| Field | Value |
|-------|-------|
| **Threat** | Pilot presents demo as production system |
| **Risk Level** | HIGH |
| **Attack Vector** | Screenshot manipulation, narration |
| **Impact** | Misleading stakeholders |
| **Mitigation** | Persistent PILOT MODE banner, watermarks |
| **Detection** | Manual review |
| **Status** | ✅ MITIGATED (via UX) |

---

### 3.7 Compliance Threats (COMP)

#### COMP-001: Autonomy Claims
| Field | Value |
|-------|-------|
| **Threat** | Pilot claims ChainBridge is autonomous |
| **Risk Level** | CRITICAL |
| **Attack Vector** | Marketing materials, verbal claims |
| **Impact** | Regulatory violation, legal liability |
| **Mitigation** | Forbidden claims enforcement, disclaimer requirements |
| **Detection** | Public mention monitoring |
| **Status** | ⚠️ REQUIRES LEGAL AGREEMENT |

#### COMP-002: Certification Claims
| Field | Value |
|-------|-------|
| **Threat** | Pilot claims ChainBridge is certified/audited |
| **Risk Level** | CRITICAL |
| **Attack Vector** | Marketing materials |
| **Impact** | False advertising, regulatory action |
| **Mitigation** | Forbidden claims list, pilot termination clause |
| **Detection** | Public mention monitoring |
| **Status** | ⚠️ REQUIRES LEGAL AGREEMENT |

---

## 4. Abuse Scenarios

### Scenario A: Competitive Intelligence
| Field | Value |
|-------|-------|
| **Actor** | Competitor posing as pilot |
| **Objective** | Extract product intelligence |
| **Method** | Systematic data extraction |
| **Mitigation** | Rate limits, pilot vetting, NDA |
| **Detection** | Extraction patterns |

### Scenario B: Pilot-to-Public Leak
| Field | Value |
|-------|-------|
| **Actor** | Malicious pilot |
| **Objective** | Leak demo data publicly |
| **Method** | Screenshots, recordings |
| **Mitigation** | Watermarks, NDA, legal action |
| **Detection** | Public monitoring |

### Scenario C: Denial of Service
| Field | Value |
|-------|-------|
| **Actor** | Hostile pilot |
| **Objective** | Degrade service |
| **Method** | Rate limit abuse from multiple IPs |
| **Mitigation** | Per-pilot limits, IP rotation detection |
| **Detection** | Correlated request patterns |

---

## 5. Failure Mode Register

| ID | Failure Mode | Impact | Mitigation |
|----|--------------|--------|------------|
| FM-001 | Auth service unavailable | Pilots locked out | Graceful degradation message |
| FM-002 | Rate limiter failure | No rate protection | Default-deny on limiter error |
| FM-003 | Classification filter bypass | PRODUCTION exposure | Defense in depth (query + app layer) |
| FM-004 | Logging failure | No audit trail | Alert on log pipeline failure |
| FM-005 | Token signing key leak | Auth compromise | Key rotation, emergency revocation |

---

## 6. Monitoring Requirements

| Monitor | Threshold | Action |
|---------|-----------|--------|
| 403 responses | >10/min/pilot | Alert |
| 404 responses | >50/min/pilot | Alert + Review |
| Rate limit triggers | >5/hour/pilot | Review |
| Failed auth | >3/hour/IP | Block IP |
| Concurrent sessions | >5/pilot | Alert |

---

## 7. Risk Summary

| Risk Level | Count | Status |
|------------|-------|--------|
| CRITICAL | 4 | 2 mitigated, 2 require legal |
| HIGH | 5 | 5 mitigated |
| MEDIUM | 6 | 5 mitigated, 1 partial |
| LOW | 1 | 1 mitigated |

**Overall Pilot Risk Posture:** ⚠️ ACCEPTABLE (with legal agreements)

---

## 8. Required Actions

| Priority | Action | Owner |
|----------|--------|-------|
| P0 | Implement pilot legal agreement | Legal + PAX |
| P0 | Public mention monitoring | Marketing |
| P1 | Metadata sanitization audit | CODY |
| P1 | Pilot vetting process | Operations |

---

**Document Hash:** `sha256:pilot-threat-register-v1.0.0`  
**Status:** CANONICAL
