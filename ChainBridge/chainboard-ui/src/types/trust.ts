/**
 * Trust Center Types — PAC-TRUST-CENTER-01
 *
 * Type definitions for Trust Center data.
 * Read-only — mirrors backend data exactly.
 *
 * @see PAC-TRUST-CENTER-01 — Public Trust Center (Read-Only)
 */

/**
 * Governance fingerprint data.
 * Source: governance_fingerprint.json
 */
export type GovernanceFingerprint = {
  /** SHA-256 hash of governance configuration */
  fingerprint_hash: string;
  /** ISO 8601 timestamp of fingerprint generation */
  timestamp: string;
  /** Schema version */
  schema_version: string;
};

/**
 * Governance coverage item.
 * Presence-only — no metrics, no counts.
 */
export type GovernanceCoverageItem = {
  /** Feature identifier */
  feature_id: string;
  /** Human-readable name */
  name: string;
  /** Whether the feature is present */
  present: boolean;
};

/**
 * Audit bundle metadata.
 * Source: latest audit export
 */
export type AuditBundleMetadata = {
  /** Bundle identifier */
  bundle_id: string;
  /** ISO 8601 timestamp of creation */
  created_at: string;
  /** SHA-256 hash of bundle */
  bundle_hash: string;
  /** Verification status */
  status: 'offline-verifiable' | 'pending' | 'unavailable';
};

/**
 * Gameday testing summary.
 * Source: PAC-GOV-GAMEDAY-01 results
 */
export type GamedaySummary = {
  /** Total scenarios tested */
  scenarios_tested: number;
  /** Silent failures detected */
  silent_failures: number;
  /** Whether all cases fail-closed */
  fail_closed_all: boolean;
};

/**
 * Trust Center data aggregation.
 */
export type TrustCenterData = {
  fingerprint?: GovernanceFingerprint;
  coverage?: GovernanceCoverageItem[];
  audit_bundle?: AuditBundleMetadata;
  gameday?: GamedaySummary;
};

/**
 * Status for data availability.
 */
export type TrustDataStatus = 'available' | 'unavailable' | 'loading';
