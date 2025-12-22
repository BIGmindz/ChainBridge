/**
 * Trust Components — PAC-SONNY-TRUST-HARDEN-01
 *
 * Hardened evidence registry. Read-only. Evidence-only.
 * No interpretation. No summaries. No claims.
 *
 * @see PAC-SONNY-TRUST-HARDEN-01 — Trust Center Evidence-Only Hardening
 */

// PAC-SONNY-TRUST-HARDEN-01 — Hardened components (active)
export {
  GovernanceArtifact,
  type GovernanceArtifactProps,
} from './GovernanceArtifact';

export {
  AuditBundle,
  type AuditBundleProps,
} from './AuditBundle';

export {
  AdversarialTesting,
  type AdversarialTestingProps,
} from './AdversarialTesting';

export {
  NonClaims,
  type NonClaimsProps,
} from './NonClaims';

// PAC-SONNY-TRUST-HARDEN-01 — PDO artifacts as first-class evidence
export {
  PDOArtifacts,
  type PDORecord,
  type PDOArtifactsProps,
} from './PDOArtifacts';

// Legacy components — retained for compatibility only
export {
  TrustEmptyState,
  type TrustEmptyStateProps,
} from './TrustEmptyState';

export {
  EvidenceArtifacts,
  type EvidenceArtifactsProps,
} from './EvidenceArtifacts';

export {
  ObservedControls,
  type ObservedControl,
  type ObservedControlsProps,
} from './ObservedControls';

export {
  TestProvenance,
  type TestSuite,
  type TestProvenanceProps,
} from './TestProvenance';

export {
  ExplicitNonClaims,
  type ExplicitNonClaimsProps,
} from './ExplicitNonClaims';

export {
  TrustFingerprintCard,
  type TrustFingerprintCardProps,
} from './TrustFingerprintCard';

export {
  TrustCoverageList,
  type TrustCoverageListProps,
} from './TrustCoverageList';

export {
  TrustAuditBundleCard,
  type TrustAuditBundleCardProps,
} from './TrustAuditBundleCard';

export {
  TrustGamedaySummary,
  type TrustGamedaySummaryProps,
} from './TrustGamedaySummary';

export {
  TrustNonClaims,
  type TrustNonClaimsProps,
} from './TrustNonClaims';

export {
  TrustOverview,
  type TrustOverviewProps,
} from './TrustOverview';

export {
  ControlCoverage,
  type ControlCoverageItem,
  type ControlCoverageProps,
} from './ControlCoverage';

export {
  AuditVerifiability,
  type AuditVerifiabilityProps,
} from './AuditVerifiability';

export {
  GamedayStatus,
  type GamedayStatusProps,
} from './GamedayStatus';

export {
  TrustDisclaimer,
  type TrustDisclaimerProps,
} from './TrustDisclaimer';
