/**
 * Governance Decision Types
 *
 * Types for the GID Kernel governance decisions that appear in ChainBoard.
 * These reflect the backend GovernanceDecision schema from CODI (GID-01).
 *
 * @see PAC-SONNY-02 — Governance Timeline (Read-Only) UI
 * @see PAC-SONNY-03 — Governance Event Timeline + Risk Annotation
 */

export type GovernanceDecisionStatus = "APPROVE" | "FREEZE" | "REJECT";

/**
 * Risk Annotation — PAC-SONNY-03
 *
 * Risk signal attached to governance events.
 * INFORMATIONAL ONLY — does not affect decision.
 * No frontend reinterpretation permitted.
 *
 * @see PAC-SONNY-03 — Risk Annotation (Read-Only)
 */
export type RiskAnnotation = {
  /** Risk category (verbatim from backend) */
  category: string;
  /** Risk rationale — short, verbatim */
  rationale: string;
  /** Confidence interval if present (e.g., "0.85-0.92") */
  confidence_interval?: string;
  /** Source of risk signal */
  source?: string;
  /** Timestamp of risk assessment */
  assessed_at?: string;
};

/**
 * Risk annotation status for UI display.
 */
export type RiskAnnotationStatus =
  | 'present'      // Risk annotation available
  | 'unavailable'  // Risk engine unavailable
  | 'none';        // No risk annotation for this event

/**
 * Governance Event — PAC-SONNY-02 + PAC-SONNY-03
 *
 * Mirrors backend GovernanceEvent exactly.
 * No frontend reinterpretation permitted.
 *
 * @see PAC-GOV-OBS-01 — Governance Observability
 * @see PAC-SONNY-03 — Risk Annotation (Read-Only)
 */
export type GovernanceEvent = {
  /** Unique event identifier */
  event_id: string;
  /** ISO 8601 timestamp (UTC) */
  timestamp: string;
  /** Event type — rendered verbatim */
  event_type: string;
  /** Agent GID that triggered/received the event */
  agent_gid: string;
  /** Verb if present (e.g., EXECUTE, PROPOSE) */
  verb?: string;
  /** Target resource if present */
  target?: string;
  /** Decision outcome if present (e.g., ALLOW, DENY) */
  decision?: string;
  /** Reason code if present */
  reason_code?: string;
  /** Audit reference — always visible if present */
  audit_ref?: string;
  /** Risk annotation — informational only, does not affect decision */
  risk_annotation?: RiskAnnotation;
  /** Risk annotation status — explicit state handling */
  risk_annotation_status?: RiskAnnotationStatus;
  /** Additional metadata — opaque, no frontend interpretation */
  metadata: Record<string, unknown>;
};

export type GovernanceDecision = {
  id: string;
  createdAt: string; // ISO timestamp
  decisionType: "settlement_precheck" | "payment_authorization" | "risk_override" | string;
  status: GovernanceDecisionStatus;
  shipmentId?: string;
  payerId: string;
  payeeId: string;
  amount: number;
  currency: string;
  corridor?: string;
  riskScore: number;
  reasonCodes: string[];
  policiesApplied: string[];
  economicJustification?: string;
  agentId?: string;   // e.g., "CODI", "GID-Kernel"
  gid?: string;       // e.g., "GID-01"
  gidVersion?: string; // e.g., "1.0"
  raw?: Record<string, unknown>;      // optional raw nested object for detail debug view
};

export type GovernanceDecisionFilter = {
  status?: GovernanceDecisionStatus | "ALL";
  searchQuery?: string;
  decisionType?: string;
};

export type GovernanceDecisionApiResponse = {
  decisions: GovernanceDecision[];
  total: number;
  page: number;
  limit: number;
};
