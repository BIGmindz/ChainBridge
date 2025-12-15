/**
 * 🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵
 * LIRA — GID-09 — EXPERIENCE ENGINEER
 * UI Component Library Index
 * 🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵
 *
 * Barrel exports for all UI primitives
 */

// =============================================================================
// DESIGN TOKENS
// =============================================================================
export {
  STATUS_COLORS,
  RISK_TIER_CONFIG,
  GUARDRAIL_STATUS_CONFIG,
  SETTLEMENT_PROVIDER_CONFIG,
  PROOF_STATUS_CONFIG,
  SPACING,
  TEXT_SCALES,
  TRANSITIONS,
  FOCUS_STYLES,
  getStatusClasses,
  getRiskTierConfig,
  getGuardrailConfig,
  scoreToRiskTier,
  type StatusColor,
  type RiskTier,
  type GuardrailStatus,
  type SettlementProvider,
  type ProofStatus,
} from './design-tokens';

// =============================================================================
// CORE UI PRIMITIVES
// =============================================================================
export { Badge } from './Badge';
export { Card, CardHeader, CardContent, CardFooter, CardTitle, CardDescription } from './Card';
export { Skeleton } from './Skeleton';
export {
  TableSkeleton,
  CardSkeleton,
  KPISkeleton,
  ErrorState,
  EmptyState,
} from './LoadingStates';

// =============================================================================
// TRUST STATUS COMPONENTS
// =============================================================================
export {
  StatusDot,
  RAGBadge,
  RiskTierBadge,
  GuardrailStatusCard,
  GuardrailStrip,
  PhaseGateStatus,
} from './TrustStatus';

// =============================================================================
// RISK EXPLAINABILITY COMPONENTS
// =============================================================================
export {
  RiskScoreGauge,
  FeatureContributionBar,
  RiskExplanationCard,
  RiskSummaryStrip,
  type FeatureAttribution,
  type RiskExplanation,
} from './RiskExplainability';

// =============================================================================
// PROOF STATUS COMPONENTS
// =============================================================================
export {
  ProofStatusBadge,
  ProofEntryCard,
  ProofPackCard,
  ProofChainIndicator,
  CompactProofBadge,
  type ProofEntry,
  type ProofPack,
} from './ProofStatus';

// =============================================================================
// CALM UX COMPONENTS — PAC-06-F
// =============================================================================
export {
  // All Clear States
  AllClearBadge,
  AllClearCard,
  AllClearStrip,
  type AllClearProps,
  // Operator Reassurance
  ReassuranceMessage,
  type ReassuranceMessageProps,
  ConfidenceIndicator,
  // Calm Transitions
  CalmTransition,
  CalmPulse,
  // Cognitive Load Reducers
  ProgressiveDisclosure,
  QuietLoading,
  StatusHeartbeat,
  // Visual Hierarchy
  SectionDivider,
  ImportanceHint,
} from './CalmUX';

/**
 * 🩵 LIRA — GID-09 — EXPERIENCE ENGINEER
 * 🩵🩵🩵 END OF PAC 🩵🩵🩵
 */
