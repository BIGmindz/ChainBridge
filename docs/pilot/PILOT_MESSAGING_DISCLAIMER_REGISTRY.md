# Pilot Messaging & Disclaimer Registry

**PAC Reference:** PAC-JEFFREY-P44  
**Classification:** COMPLIANCE / MESSAGING  
**Author:** PAX (GID-05)  
**Status:** CANONICAL  

---

## 1. Purpose

This registry defines all permitted messaging, required disclaimers, and forbidden claims for external pilots. Compliance with this registry is mandatory.

---

## 2. Required Disclaimers

### 2.1 Primary Pilot Disclaimer

**Must appear on:**
- Pilot onboarding materials
- All pilot communications
- Demo environments
- Any public-facing pilot content

```
═══════════════════════════════════════════════════════════════════
PILOT PROGRAM DISCLAIMER

This access is provided as part of the ChainBridge Pilot Program.

• This is NOT a production system
• No real transactions are processed
• No regulatory certification is implied
• All data shown is simulated (SHADOW classification)
• This system requires human oversight and is not autonomous

ChainBridge is a tool that assists human operators. It does not
replace compliance teams, auditors, or regulatory oversight.
═══════════════════════════════════════════════════════════════════
```

### 2.2 UI Banner Disclaimer

**Must appear persistently in pilot UI:**

```
🔒 PILOT MODE | Read-Only Access | SHADOW Data Only | Not Production
```

### 2.3 API Response Disclaimer

**Must appear in API response headers:**

```
X-ChainBridge-Mode: PILOT
X-ChainBridge-Disclaimer: This is pilot access. No production data.
X-ChainBridge-Classification: SHADOW
```

### 2.4 Documentation Disclaimer

**Must appear at top of all pilot documentation:**

```
⚠️ PILOT DOCUMENTATION

This documentation describes the ChainBridge Pilot Program.
Features described may change without notice.
This system is not production-ready and no regulatory
claims should be inferred from this documentation.
```

---

## 3. Forbidden Claims Registry

### 3.1 Absolute Forbidden Claims

These claims may **NEVER** be made by pilots:

| ID | Forbidden Claim | Risk |
|----|-----------------|------|
| FC-001 | "ChainBridge is production-ready" | Misrepresentation |
| FC-002 | "ChainBridge is auditor-certified" | False certification |
| FC-003 | "ChainBridge is regulatory-approved" | False approval |
| FC-004 | "ChainBridge processes real transactions" | False capability |
| FC-005 | "ChainBridge guarantees settlement" | False guarantee |
| FC-006 | "ChainBridge replaces compliance teams" | Autonomy claim |
| FC-007 | "ChainBridge provides autonomous compliance" | Autonomy claim |
| FC-008 | "ChainBridge eliminates manual review" | Automation claim |
| FC-009 | "ChainBridge is AI-powered compliance" | Misleading AI claim |
| FC-010 | "ChainBridge makes decisions automatically" | Autonomy claim |

### 3.2 Conditional Forbidden Claims

These claims require specific qualifications:

| Claim | Required Qualification |
|-------|----------------------|
| "ChainBridge helps with compliance" | "...as a tool assisting human operators" |
| "ChainBridge reduces risk" | "...when used with proper oversight" |
| "ChainBridge improves efficiency" | "...for certain manual processes" |
| "ChainBridge provides visibility" | "...into payment decisioning" |

---

## 4. Permitted Messaging

### 4.1 Approved Pilot Descriptions

Pilots MAY use these descriptions:

```
✅ "ChainBridge is a payment decisioning observation platform"
✅ "ChainBridge provides visibility into payment operations"
✅ "ChainBridge assists operators in reviewing transactions"
✅ "ChainBridge is currently in pilot evaluation"
✅ "ChainBridge requires human oversight for all decisions"
✅ "ChainBridge is a tool that supports compliance teams"
```

### 4.2 Approved Feature Descriptions

| Feature | Approved Description |
|---------|---------------------|
| PDO Viewer | "View payment decision records" |
| Timeline | "Review audit trails" |
| Activity Stream | "Monitor system activity" |
| Ledger Integrity | "Verify data integrity" |

### 4.3 Approved Benefit Statements

```
✅ "Provides visibility into payment decisions"
✅ "Creates audit trails for review"
✅ "Supports compliance team workflows"
✅ "Enables operator oversight"
✅ "Facilitates decision documentation"
```

---

## 5. Communication Templates

### 5.1 Pilot Welcome Email

```
Subject: Welcome to ChainBridge Pilot Program

Dear [Pilot Name],

Welcome to the ChainBridge Pilot Program.

IMPORTANT DISCLAIMERS:
• This is a pilot evaluation, not a production system
• All data is simulated (SHADOW classification)
• No regulatory certification is implied
• Human oversight is required for all operations

Your access includes:
• Read-only viewing of SHADOW PDOs
• Activity stream observation
• Ledger integrity verification

Your access does NOT include:
• Creating or modifying PDOs
• Access to production data
• Configuration changes
• Kill-switch operations

Please review the Pilot Agreement before proceeding.

Questions? Contact: pilot-support@chainbridge.io

Best regards,
ChainBridge Pilot Team
```

### 5.2 Pilot Demo Script Opening

```
"Thank you for joining this ChainBridge pilot demonstration.

Before we begin, I want to be clear about what you're seeing:

1. This is a PILOT system, not production
2. All data shown is simulated
3. ChainBridge is a tool that assists human operators
4. No regulatory certification is implied
5. This system requires human oversight

With that context, let me show you..."
```

### 5.3 Pilot Feedback Request

```
Subject: ChainBridge Pilot Feedback Request

Dear [Pilot Name],

Thank you for participating in the ChainBridge Pilot Program.

We value your feedback on your pilot experience.

Please note:
• Your feedback will be used to improve our pilot program
• No production commitment is implied by this feedback request
• ChainBridge remains in pilot evaluation phase

[Feedback Form Link]

Best regards,
ChainBridge Pilot Team
```

---

## 6. Social Media Guidelines

### 6.1 Permitted Posts

```
✅ "Evaluating ChainBridge for payment visibility"
✅ "Interesting pilot of ChainBridge payment platform"
✅ "Testing ChainBridge's audit trail features"
```

### 6.2 Forbidden Posts

```
❌ "ChainBridge is revolutionizing compliance"
❌ "ChainBridge replaces our compliance team"
❌ "ChainBridge is now handling our transactions"
❌ "ChainBridge is fully automated"
```

### 6.3 Required Hashtag/Disclosure

Any public mention must include:
```
#ChainBridgePilot #NotProduction
```

---

## 7. Presentation Guidelines

### 7.1 Required Slides

Every pilot presentation MUST include:

**Slide 1: Disclaimer**
```
PILOT PROGRAM DISCLAIMER

• Not production
• Simulated data only
• No regulatory certification
• Human oversight required
• Tool, not replacement
```

**Final Slide: Reminder**
```
REMINDER

This demonstration showed pilot functionality.
ChainBridge is a tool supporting human operators.
No production or certification claims are made.
```

### 7.2 Forbidden Slide Content

- Screenshots without PILOT MODE banner
- Claims of automation or autonomy
- Regulatory certification mentions
- Production deployment timelines
- Pricing or commercial terms

---

## 8. Enforcement

### 8.1 Violation Consequences

| Severity | Violation | Consequence |
|----------|-----------|-------------|
| CRITICAL | Autonomy/certification claim | Immediate pilot termination |
| HIGH | Production claim | Warning + review |
| MEDIUM | Missing disclaimer | Correction required |
| LOW | Incomplete qualification | Guidance provided |

### 8.2 Monitoring

| Channel | Monitoring Method |
|---------|-------------------|
| Social media | Brand mention alerts |
| Press/blogs | Google alerts |
| Presentations | Slide review (pre-approval) |
| Demos | Recording review |

---

## 9. Compliance Checklist

Before any pilot communication:

- [ ] Primary disclaimer included
- [ ] No forbidden claims present
- [ ] Conditional claims properly qualified
- [ ] PILOT MODE visible in screenshots
- [ ] "Human oversight" mentioned
- [ ] "Not production" clearly stated
- [ ] No certification/regulatory claims

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-03 | Initial release (PAC-P44) |

---

**Document Hash:** `sha256:pilot-messaging-registry-v1.0.0`  
**Status:** CANONICAL
