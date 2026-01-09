/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Trust Center Component Types
 * PAC-BENSON-P34: Trust Center (Public Audit Interface)
 * 
 * Type definitions for public-facing Trust Center components.
 * 
 * CONSTRAINTS:
 * - All types are for READ-ONLY public data
 * - No private/sensitive fields exposed
 * - No authentication-dependent types
 * 
 * DOCTRINE REFERENCE:
 * - Law 2: Cockpit Visibility (external adaptation)
 * - Law 6: Visual Invariants
 * - Law 8: ProofPack Completeness
 * 
 * Author: SONNY (GID-02) — Trust Center UI
 * Security: SAM (GID-06) — Public exposure review
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// VERIFICATION STATUS TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type VerificationStatus = 
  | 'VERIFIED'
  | 'PENDING'
  | 'FAILED'
  | 'EXPIRED'
  | 'UNKNOWN';

export type SignatureAlgorithm = 
  | 'Ed25519'
  | 'ECDSA-P256'
  | 'RSA-SHA256';

export type HashAlgorithm = 
  | 'SHA-256'
  | 'SHA-384'
  | 'SHA-512';

// ═══════════════════════════════════════════════════════════════════════════════
// PROOFPACK PUBLIC VIEW TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface PublicProofPackSummary {
  /** ProofPack unique identifier */
  proofpackId: string;
  /** When the ProofPack was generated (ISO-8601) */
  generatedAt: string;
  /** Schema version */
  schemaVersion: string;
  /** Number of audit events included */
  eventCount: number;
  /** Whether the ProofPack is cryptographically signed */
  isSigned: boolean;
  /** Signature algorithm if signed */
  signatureAlgorithm?: SignatureAlgorithm;
  /** Hash of the manifest for verification */
  manifestHash: string;
  /** Download URL for the full ProofPack */
  downloadUrl: string;
}

export interface PublicVerificationResult {
  /** Whether verification passed */
  verified: boolean;
  /** Verification status */
  status: VerificationStatus;
  /** Human-readable message */
  message: string;
  /** When verification was performed (ISO-8601) */
  verifiedAt: string;
  /** Hash algorithm used */
  hashAlgorithm: HashAlgorithm;
  /** The hash that was verified */
  manifestHash: string;
  /** Whether signature was verified (if applicable) */
  signatureValid?: boolean;
  /** Whether content hash matches */
  hashValid?: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// GOVERNANCE TRUST TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface TrustFingerprint {
  /** Governance root hash */
  fingerprintHash: string;
  /** When fingerprint was computed (ISO-8601) */
  generatedAt: string;
  /** Schema version */
  schemaVersion: string;
}

export interface TrustCoverage {
  /** Access Control Matrix enforcement active */
  acmEnforced: boolean;
  /** Denial Rejection Correction Protocol active */
  drcpActive: boolean;
  /** Diggi bounded correction enabled */
  diggiEnabled: boolean;
  /** Build artifact verification active */
  artifactVerification: boolean;
  /** Repository scope enforcement active */
  scopeGuard: boolean;
  /** Fail-closed execution model active */
  failClosedExecution: boolean;
}

export interface GamedayResults {
  /** Number of adversarial scenarios tested */
  scenariosTested: number;
  /** Count of silent failures detected */
  silentFailures: number;
  /** Whether fail-closed behavior was verified */
  failClosed: boolean;
  /** Last gameday execution date (ISO-8601) */
  lastRun: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUDIT BUNDLE TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface AuditBundleMetadata {
  /** Bundle unique identifier */
  bundleId: string | null;
  /** When bundle was created (ISO-8601) */
  createdAt: string | null;
  /** Hash of bundle contents */
  bundleHash: string | null;
  /** Schema version */
  schemaVersion: string | null;
  /** Whether bundle can be verified offline */
  offlineVerifiable: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// PUBLIC EXPLAINABILITY TYPES (Redacted for Public)
// ═══════════════════════════════════════════════════════════════════════════════

export interface PublicDecisionSummary {
  /** Decision identifier (not the full internal ID) */
  decisionRef: string;
  /** Decision outcome (APPROVED/REJECTED/ESCALATED) */
  outcome: 'APPROVED' | 'REJECTED' | 'ESCALATED';
  /** When decision was made (ISO-8601) */
  timestamp: string;
  /** Whether decision has ProofPack */
  hasProofPack: boolean;
  /** Public reason (redacted for sensitive info) */
  publicReason: string;
}

export interface PublicAuditTimeline {
  /** Timeline entries (public-safe only) */
  entries: PublicTimelineEntry[];
  /** Total entry count */
  totalCount: number;
  /** Whether more entries exist */
  hasMore: boolean;
}

export interface PublicTimelineEntry {
  /** Entry identifier */
  entryId: string;
  /** Entry type */
  entryType: 'DECISION' | 'VERIFICATION' | 'EXPORT' | 'SYSTEM';
  /** When entry was created (ISO-8601) */
  timestamp: string;
  /** Public-safe description */
  description: string;
  /** Associated ProofPack ID if any */
  proofpackId?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TRUST CENTER STATE
// ═══════════════════════════════════════════════════════════════════════════════

export interface TrustCenterState {
  /** Governance fingerprint */
  fingerprint: TrustFingerprint | null;
  /** Governance coverage */
  coverage: TrustCoverage | null;
  /** Latest audit bundle metadata */
  latestAudit: LatestAuditSummary | null;
  /** Gameday results */
  gamedayResults: GamedayResults | null;
  /** Public audit timeline */
  timeline: PublicAuditTimeline | null;
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
}

export interface LatestAuditSummary {
  /** Bundle unique identifier */
  bundleId: string;
  /** When bundle was generated (ISO-8601) */
  generatedAt: string;
  /** Number of items in bundle */
  itemCount: number;
}
