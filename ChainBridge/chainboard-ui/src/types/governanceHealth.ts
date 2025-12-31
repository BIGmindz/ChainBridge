/**
 * Governance Health Types — PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 *
 * Types for the Governance Health Dashboard visualization.
 * All types are READ-ONLY and derived from governance artifacts.
 *
 * Settlement Chain: PAC → BER → PDO → WRAP
 *
 * @see PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 * @see GOVERNANCE_DOCTRINE_V1.1
 */

/**
 * Settlement artifact status in the governance flow.
 */
export type ArtifactStatus =
  | 'PENDING'
  | 'ACTIVE'
  | 'AWAITING_REVIEW'
  | 'FINALIZED'
  | 'REJECTED'
  | 'BLOCKED';

/**
 * Settlement stage in the PAC → BER → PDO → WRAP flow.
 */
export type SettlementStage =
  | 'PAC_DISPATCH'
  | 'AGENT_EXECUTION'
  | 'BER_GENERATION'
  | 'HUMAN_REVIEW'
  | 'PDO_FINALIZATION'
  | 'WRAP_GENERATION'
  | 'WRAP_ACCEPTED'
  | 'LEDGER_COMMIT';

/**
 * Enterprise compliance framework mapping.
 */
export interface EnterpriseMapping {
  framework: 'SOX' | 'SOC2' | 'NIST_CSF' | 'ISO_27001';
  control: string;
  description: string;
  artifact: 'PAC' | 'BER' | 'PDO' | 'WRAP' | 'LEDGER';
}

/**
 * Settlement flow node for visualization.
 */
export interface SettlementFlowNode {
  stage: SettlementStage;
  status: ArtifactStatus;
  timestamp?: string;
  artifactId?: string;
  authority?: string;
  details?: string;
}

/**
 * Governance health metrics for dashboard cards.
 */
export interface GovernanceHealthMetrics {
  // PAC metrics
  totalPacs: number;
  activePacs: number;
  blockedPacs: number;
  positiveClosures: number;

  // BER metrics
  totalBers: number;
  pendingBers: number;
  approvedBers: number;

  // PDO metrics
  totalPdos: number;
  finalizedPdos: number;

  // WRAP metrics
  totalWraps: number;
  acceptedWraps: number;

  // Settlement metrics
  settlementRate: number; // percentage of PACs reaching WRAP_ACCEPTED
  avgSettlementTimeMs: number;
  pendingSettlements: number;

  // Health indicators
  ledgerIntegrity: 'HEALTHY' | 'DEGRADED' | 'CRITICAL';
  lastLedgerSync: string;
  sequenceGaps: number;
}

/**
 * Artifact in the settlement timeline.
 */
export interface SettlementArtifact {
  id: string;
  type: 'PAC' | 'BER' | 'PDO' | 'WRAP';
  status: ArtifactStatus;
  createdAt: string;
  updatedAt: string;
  agentGid: string;
  agentName: string;
  agentColor: string;
  linkedArtifacts: {
    pacId?: string;
    berId?: string;
    pdoId?: string;
    wrapId?: string;
  };
}

/**
 * Settlement chain representing a complete PAC → WRAP flow.
 */
export interface SettlementChain {
  chainId: string;
  pacId: string;
  berId?: string;
  pdoId?: string;
  wrapId?: string;
  currentStage: SettlementStage;
  status: 'IN_PROGRESS' | 'COMPLETED' | 'BLOCKED' | 'REJECTED';
  startedAt: string;
  completedAt?: string;
  nodes: SettlementFlowNode[];
}

/**
 * Enterprise compliance summary for the dashboard.
 */
export interface EnterpriseComplianceSummary {
  mappings: EnterpriseMapping[];
  lastAuditDate?: string;
  complianceScore: number; // 0-100
  frameworkCoverage: {
    sox: number;
    soc2: number;
    nist: number;
    iso27001: number;
  };
}

/**
 * Governance health dashboard state.
 */
export interface GovernanceHealthState {
  metrics: GovernanceHealthMetrics;
  recentChains: SettlementChain[];
  complianceSummary: EnterpriseComplianceSummary;
  isLoading: boolean;
  error: Error | null;
  lastUpdated: string;
}

/**
 * Agent color mapping for consistent UI.
 */
export const AGENT_COLORS: Record<string, string> = {
  TEAL: 'bg-teal-500',
  BLUE: 'bg-blue-500',
  YELLOW: 'bg-yellow-500',
  PURPLE: 'bg-purple-500',
  CYAN: 'bg-cyan-500',
  DARK_RED: 'bg-red-700',
  GREEN: 'bg-green-500',
  WHITE: 'bg-slate-200',
  PINK: 'bg-pink-500',
  MAGENTA: 'bg-pink-600',
  CRIMSON: 'bg-red-600',
  ORANGE: 'bg-orange-500',
};

/**
 * Stage display configuration.
 */
export const STAGE_CONFIG: Record<SettlementStage, { label: string; icon: string }> = {
  PAC_DISPATCH: { label: 'PAC Dispatch', icon: '📋' },
  AGENT_EXECUTION: { label: 'Agent Execution', icon: '⚙️' },
  BER_GENERATION: { label: 'BER Generation', icon: '📊' },
  HUMAN_REVIEW: { label: 'Human Review', icon: '👁️' },
  PDO_FINALIZATION: { label: 'PDO Finalization', icon: '🔐' },
  WRAP_GENERATION: { label: 'WRAP Generation', icon: '📦' },
  WRAP_ACCEPTED: { label: 'WRAP Accepted', icon: '✅' },
  LEDGER_COMMIT: { label: 'Ledger Commit', icon: '📖' },
};

/**
 * Status color mapping.
 */
export const STATUS_COLORS: Record<ArtifactStatus, string> = {
  PENDING: 'text-slate-400 bg-slate-500/10',
  ACTIVE: 'text-blue-400 bg-blue-500/10',
  AWAITING_REVIEW: 'text-amber-400 bg-amber-500/10',
  FINALIZED: 'text-emerald-400 bg-emerald-500/10',
  REJECTED: 'text-rose-400 bg-rose-500/10',
  BLOCKED: 'text-red-400 bg-red-500/10',
};
