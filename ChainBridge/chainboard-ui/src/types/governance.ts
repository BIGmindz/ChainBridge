/**
 * Governance Decision Types
 *
 * Types for the GID Kernel governance decisions that appear in ChainBoard.
 * These reflect the backend GovernanceDecision schema from CODI (GID-01).
 */

export type GovernanceDecisionStatus = "APPROVE" | "FREEZE" | "REJECT";

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
