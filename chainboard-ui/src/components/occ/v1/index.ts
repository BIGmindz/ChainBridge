/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * OCC v1.0 Components — Barrel Exports
 * PAC-JEFFREY-P03: OCC UI Execution
 * 
 * Exports all OCC v1.0 UI components and types for integration.
 * 
 * Author: SONNY (GID-02) — Frontend
 * Constitutional Reference: OCC_CONSTITUTION_v1.0
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// TYPE EXPORTS
// ═══════════════════════════════════════════════════════════════════════════════

export type {
  // Core OCC Types
  OCCv1DashboardState,
  
  // Operator Types
  OperatorContext,
  OperatorTier,
  
  // Queue Types
  QueueState,
  QueueItem,
  QueueMetrics,
  QueuePriority,
  QueueActionType,
  
  // PDO State Machine Types
  PDOStateMachineState,
  PDOState,
  PDORecord,
  PDOTransition,
  PDOTransitionType,
  PDOStateMachineMetrics,
  
  // Audit Types
  AuditLogState,
  AuditRecord,
  AuditRecordType,
  AuditStatistics,
  AuditFilters,
  
  // Replay Types
  ReplayResult,
  ReplayStatus,
  ReplayStep,
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENT EXPORTS
// ═══════════════════════════════════════════════════════════════════════════════

export { QueuePanel } from './QueuePanel';
export { StateMachinePanel } from './StateMachinePanel';
export { AuditPanel } from './AuditPanel';
export { OCCv1Dashboard } from './OCCv1Dashboard';

// ═══════════════════════════════════════════════════════════════════════════════
// PAC REJECTION EXPORTS (PAC-JEFFREY-C05)
// ═══════════════════════════════════════════════════════════════════════════════

export { PACRejectionFeedback, PACRejectionList } from './PACRejectionFeedback';
export {
  REJECTION_CODES,
  CATEGORY_ICONS,
  CATEGORY_PREFIXES,
  SEVERITY_COLORS,
  getRejectionCode,
  getRejectionCodesByCategory,
  formatOperatorFeedback,
  formatResolution,
  createRejection,
} from './pacRejectionTypes';
export type {
  RejectionCategory,
  RejectionSeverity,
  RejectionCodeDefinition,
  PACUploadResponse,
  PACUploadSuccess,
  PACUploadRejection,
} from './pacRejectionTypes';

// ═══════════════════════════════════════════════════════════════════════════════
// HOOK EXPORTS (READ-ONLY per INV-OCC-UI-001)
// ═══════════════════════════════════════════════════════════════════════════════

export {
  useOCCQueue,
  useOCCStateMachine,
  useOCCTransitions,
  useOCCAuditLog,
  useOCCReplay,
  useOCCDashboard,
} from './useOCCApi';

// Default export is the main dashboard
export { OCCv1Dashboard as default } from './OCCv1Dashboard';
