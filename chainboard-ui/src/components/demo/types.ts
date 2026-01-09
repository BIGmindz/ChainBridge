/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Demo Experience Types
 * PAC-BENSON-P35R: Operator + Auditor Demo Experience
 * 
 * Type definitions for canonical demo flows.
 * 
 * CONSTRAINTS:
 * - Demo-only types (no business logic)
 * - Maps to existing API endpoints
 * - No new API contracts
 * 
 * DOCTRINE REFERENCES:
 * - Law 2: Cockpit Visibility
 * - Law 4: PDO Lifecycle
 * - Law 6: Visual Invariants
 * 
 * Author: SONNY (GID-02) — OCC Demo Flow
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// DEMO FLOW STATES
// ═══════════════════════════════════════════════════════════════════════════════

export type DemoFlowId = 
  | 'operator-happy-path'
  | 'operator-intervention'
  | 'auditor-replay'
  | 'trust-center-verify';

export type DemoStepStatus = 
  | 'pending'
  | 'active'
  | 'completed'
  | 'failed'
  | 'skipped';

export interface DemoStep {
  /** Step identifier */
  stepId: string;
  /** Step label */
  label: string;
  /** Step description */
  description: string;
  /** Current status */
  status: DemoStepStatus;
  /** Associated component/view */
  component: string;
  /** Duration in ms (for auto-advance) */
  durationMs?: number;
  /** Doctrine law reference */
  doctrineRef?: string;
}

export interface DemoFlow {
  /** Flow identifier */
  flowId: DemoFlowId;
  /** Flow title */
  title: string;
  /** Flow description */
  description: string;
  /** Persona (operator/auditor) */
  persona: 'operator' | 'auditor' | 'public';
  /** Steps in sequence */
  steps: DemoStep[];
  /** Current step index */
  currentStepIndex: number;
  /** Is flow complete */
  isComplete: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// OPERATOR DEMO TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type OperatorDemoPhase = 
  | 'INTAKE'
  | 'RISK_ASSESSMENT'
  | 'DECISION'
  | 'SETTLEMENT'
  | 'PROOF';

export type InterventionPhase =
  | 'BLOCKED'
  | 'REVIEW'
  | 'RESOLUTION'
  | 'ESCALATION';

export interface OperatorDemoState {
  /** Current phase */
  phase: OperatorDemoPhase | InterventionPhase;
  /** Mock shipment ID */
  shipmentId: string;
  /** Mock decision ID */
  decisionId: string;
  /** Is intervention path */
  isIntervention: boolean;
  /** Associated ProofPack ID */
  proofpackId?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUDITOR DEMO TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type AuditorDemoPhase =
  | 'TIMELINE_VIEW'
  | 'PROOFPACK_SELECT'
  | 'PROOFPACK_VERIFY'
  | 'EVIDENCE_REVIEW';

export interface AuditorDemoState {
  /** Current phase */
  phase: AuditorDemoPhase;
  /** Selected ProofPack ID */
  selectedProofpackId?: string;
  /** Verification result */
  verificationStatus?: 'pending' | 'verified' | 'failed';
}

// ═══════════════════════════════════════════════════════════════════════════════
// DEMO NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════════

export interface DemoNavigation {
  /** Available flows */
  flows: DemoFlow[];
  /** Active flow ID */
  activeFlowId: DemoFlowId | null;
  /** Can go to previous step */
  canGoPrevious: boolean;
  /** Can go to next step */
  canGoNext: boolean;
  /** Is demo mode active */
  isDemoMode: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// DEMO STATE BEACON (Law 6)
// ═══════════════════════════════════════════════════════════════════════════════

export type BeaconStatus = 'green' | 'yellow' | 'red';

export interface StateBeacon {
  /** Beacon ID */
  beaconId: string;
  /** Label */
  label: string;
  /** Current status (Law 6 colors) */
  status: BeaconStatus;
  /** Tooltip text */
  tooltip: string;
}
