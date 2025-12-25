/**
 * Governance Components — PAC-DIGGI-05-FE + PAC-SONNY-02 + PAC-SONNY-03 + PAC-SONNY-G1-PHASE-2 + PAC-SONNY-G2-PHASE-2
 *
 * Components for rendering governance decisions and visual language.
 *
 * @see PAC-DIGGI-05-FE — Diggi Operator UX
 * @see PAC-SONNY-02 — Governance Timeline (Read-Only) UI
 * @see PAC-SONNY-03 — Risk Annotation (Read-Only)
 * @see PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 * @see PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 */

export { GovernanceDecisionsPanel } from './GovernanceDecisionsPanel';
export { GovernanceDecisionDetailDrawer } from './GovernanceDecisionDetailDrawer';
export { ALEXGovernanceFooter } from './ALEXGovernanceFooter';

// PAC-SONNY-G1-PHASE-2 — Governance State Panel & Enforcement
export {
  GovernanceStatePanel,
  GovernanceStateIndicator,
  type GovernanceStatePanelProps,
} from './GovernanceStatePanel';
export {
  EscalationTimeline,
  EscalationSummaryBadge,
  type EscalationTimelineProps,
} from './EscalationTimeline';
export {
  GovernanceGuard,
  GovernanceButton,
  GovernanceBlockedOverlay,
  useGovernanceAction,
  type GovernanceGuardProps,
  type GovernanceButtonProps,
  type GovernanceBlockedOverlayProps,
} from './GovernanceGuard';

// PAC-SONNY-G2-PHASE-2 — Governance Ledger & OC Integration
export {
  GovernanceLedgerPanel,
  type GovernanceLedgerPanelProps,
} from './GovernanceLedgerPanel';
export {
  PacTimelineView,
  type PacTimelineViewProps,
} from './PacTimelineView';
export {
  CorrectionCycleStepper,
  type CorrectionCycleStepperProps,
} from './CorrectionCycleStepper';
export {
  PositiveClosureBadge,
  ClosureIndicator,
  type PositiveClosureBadgeProps,
} from './PositiveClosureBadge';
export {
  GovernanceStateSummaryCard,
  type GovernanceStateSummaryCardProps,
} from './GovernanceStateSummaryCard';

// PAC-DIGGI-05-FE additions
export {
  GovernanceLockedBanner,
  GovernanceDenyBanner,
  GovernanceLockBanner,
  GovernanceProposeBanner,
  type GovernanceLockStatus,
  type GovernanceLockedBannerProps,
} from './GovernanceLockedBanner';

// PAC-SONNY-02 additions
export {
  GovernanceTimelinePanel,
  type GovernanceTimelinePanelProps,
} from './GovernanceTimelinePanel';
export {
  GovernanceEventRow,
  type GovernanceEventRowProps,
} from './GovernanceEventRow';
export {
  GovernanceTimelineEmptyState,
  type GovernanceTimelineEmptyStateProps,
} from './GovernanceTimelineEmptyState';

// PAC-SONNY-03 additions
export {
  GovernanceRiskBadge,
  GovernanceRiskDisclaimer,
  type GovernanceRiskBadgeProps,
} from './GovernanceRiskBadge';
export {
  GovernanceRiskEmptyState,
  type GovernanceRiskEmptyStateProps,
} from './GovernanceRiskEmptyState';

// PAC-SONNY-P30 — Governance UI Parity Shield
export {
  GovernanceShield,
  GovernanceShieldBadge,
  GovernanceShieldIcon,
  deriveShieldStatus,
  type ShieldStatus,
  type GovernanceShieldProps,
} from './GovernanceShield';
export {
  LastEvaluatedBadge,
  LastEvaluatedCompact,
  calculateFreshness,
  formatTimestamp,
  formatRelativeTime,
  type FreshnessLevel,
  type LastEvaluatedBadgeProps,
} from './LastEvaluatedBadge';
export {
  GovernanceStatusCard,
  GovernanceStatusStrip,
  deriveGlyphPattern,
  type TerminalGlyphPattern,
  type GovernanceStatusCardProps,
} from './GovernanceStatusCard';

// PAC-SONNY-P30 — Terminal-UI Parity Visual Governance
export {
  type SignalStatus,
  type SignalSeverity,
  type ReviewState,
  SIGNAL_STATUS_CODES,
  SEVERITY_LEVELS,
  TERMINAL_GLYPHS,
  TERMINAL_BANNERS,
  GOVERNANCE_COLORS,
  SEVERITY_COLORS,
  getSignalVisualConfig,
  getSeverityVisualConfig,
  formatTerminalSignal,
  formatTerminalSummary,
  generateTerminalBanner,
  type SignalVisualConfig,
} from './GovernanceVisualLanguage';
export {
  GovernanceSignalBadge,
  SeverityBadge,
  GovernanceSignalRow,
  ValidationSummary,
  GateIndicator,
  type GovernanceSignalBadgeProps,
  type SeverityBadgeProps,
  type GovernanceSignalRowProps,
  type ValidationSummaryProps,
  type GateIndicatorProps,
} from './GovernanceSignalBadge';
export { TerminalUIParityDemo } from './TerminalUIParityDemo';
