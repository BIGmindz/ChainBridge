/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * OCC Module — Barrel Export
 * PAC-BENSON-P21-C / P22-C: OCC Intensive Multi-Agent Execution
 * 
 * Exports all OCC (Operator Control Center) components and types
 * for clean import paths throughout the application.
 * 
 * Author: SONNY (GID-02) — Frontend Lead
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// TYPE EXPORTS
// ═══════════════════════════════════════════════════════════════════════════════

export type {
  // Agent types
  AgentLane,
  AgentHealthState,
  AgentExecutionState,
  AgentLaneTile,

  // Decision types
  DecisionType,
  DecisionOutcome,
  PDOCard,
  BERCard,
  BERStatus,
  WRAPProgress,
  DecisionStreamItem,

  // Governance types
  InvariantClass,
  InvariantStatus,
  InvariantDisplay,
  GovernanceRailState,

  // Kill switch types
  KillSwitchState,
  KillSwitchAuthLevel,
  KillSwitchStatus,

  // Aggregate types
  OCCDashboardState,
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// CORE COMPONENT EXPORTS (P21-C)
// ═══════════════════════════════════════════════════════════════════════════════

export { LaneGrid } from './LaneGrid';
export { DecisionStream } from './DecisionStream';
export { GovernanceRail } from './GovernanceRail';
export { KillSwitchUI } from './KillSwitchUI';
export { OCCDashboard } from './OCCDashboard';

// ═══════════════════════════════════════════════════════════════════════════════
// DEEPENING COMPONENT EXPORTS (P22-C)
// ═══════════════════════════════════════════════════════════════════════════════

// Timeline View module
export * from './timeline';

// Agent Drilldown module
export * from './drilldown';

// Decision Diff module
export * from './diff';

// Execution Banner module
export * from './banner';

// Default export for lazy loading
export { default } from './OCCDashboard';
