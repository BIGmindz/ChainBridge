/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Doctrine Component Types
 * PAC-BENSON-P32: UI Implementation (Operator Experience Doctrine Apply)
 * 
 * Type definitions for Doctrine-compliant OCC components.
 * 
 * DOCTRINE REFERENCES:
 * - Law 1: Complete State Capture
 * - Law 2: Cockpit Visibility
 * - Law 4: Mandatory UI Surfaces
 * 
 * Author: SONNY (GID-02)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// SETTLEMENT PIPELINE TYPES (Law 4, §4.1)
// ═══════════════════════════════════════════════════════════════════════════════

export type PipelineStage = 
  | 'INTAKE'
  | 'RISK'
  | 'DECISION'
  | 'PROOF'
  | 'SETTLEMENT'
  | 'AUDIT';

export type StageStatus = 
  | 'IDLE'
  | 'ACTIVE'
  | 'COMPLETE'
  | 'BLOCKED'
  | 'ERROR';

export interface PipelineStageData {
  stage: PipelineStage;
  status: StageStatus;
  count: number;
  alertCount: number;
  lastUpdated: string;
}

export interface SettlementPipelineState {
  stages: PipelineStageData[];
  totalInPipeline: number;
  blockedCount: number;
  lastRefresh: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// PROOFPACK VIEWER TYPES (Law 4, §4.2)
// ═══════════════════════════════════════════════════════════════════════════════

export type SignatureStatus = 
  | 'VERIFIED'
  | 'PENDING'
  | 'FAILED'
  | 'NOT_CHECKED';

export type HashChainStatus =
  | 'INTACT'
  | 'BROKEN'
  | 'PENDING';

export interface ProofPackSignature {
  algorithm: string;
  status: SignatureStatus;
  verifiedAt: string | null;
  signerGid: string | null;
}

export interface ProofPackHashChain {
  status: HashChainStatus;
  blockCount: number;
  rootHash: string;
}

export interface ProofPackTimestamp {
  attested: boolean;
  timestamp: string;
  source: string;
}

export interface ProofPackData {
  proofPackId: string;
  pacId: string;
  signature: ProofPackSignature;
  hashChain: ProofPackHashChain;
  timestamp: ProofPackTimestamp;
  quantumSafe: boolean;
  contents: Record<string, unknown>;
  createdAt: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// DECISION TIMELINE TYPES (Law 4, §4.3)
// ═══════════════════════════════════════════════════════════════════════════════

export type DecisionType =
  | 'SETTLEMENT'
  | 'RISK_ASSESSMENT'
  | 'APPROVAL'
  | 'REJECTION'
  | 'OVERRIDE'
  | 'ESCALATION';

export interface DecisionTimelineEntry {
  decisionId: string;
  type: DecisionType;
  timestamp: string;
  entityId: string | null;
  agentGid: string;
  agentName: string;
  outcome: string;
  inputStateHash: string;
  modelVersion: string | null;
  proofPackRef: string | null;
  humanOverride: boolean;
}

export interface DecisionDiff {
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  changedFields: string[];
}

// ═══════════════════════════════════════════════════════════════════════════════
// GOVERNANCE HEALTH TYPES (Law 4, §4.4)
// ═══════════════════════════════════════════════════════════════════════════════

export interface GovernanceHealthState {
  alexRulesCount: number;
  alexViolations: number;
  activePacCount: number;
  pendingWrapsCount: number;
  openBersCount: number;
  driftStatus: 'ZERO' | 'DETECTED' | 'UNKNOWN';
  lastHealthCheck: string;
  overallStatus: 'GOVERNED' | 'WARNING' | 'CRITICAL';
}

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT ROSTER TYPES (Law 4, §4.5)
// ═══════════════════════════════════════════════════════════════════════════════

export type AgentStatus = 
  | 'ACTIVE'
  | 'IDLE'
  | 'BLOCKED'
  | 'OFFLINE';

export type ComplianceIndicator =
  | 'COMPLIANT'
  | 'WARNING'
  | 'VIOLATION';

export interface AgentRosterEntry {
  gid: string;
  name: string;
  status: AgentStatus;
  lastPacExecuted: string | null;
  lastPacTimestamp: string | null;
  complianceIndicator: ComplianceIndicator;
  tasksPending: number;
  tasksCompleted: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// DOCTRINE COMPLIANCE TYPES (Law 6)
// ═══════════════════════════════════════════════════════════════════════════════

export interface DoctrineComplianceState {
  lawsChecked: number;
  lawsCompliant: number;
  violations: Array<{
    lawId: string;
    description: string;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  }>;
  lastCheck: string;
}
