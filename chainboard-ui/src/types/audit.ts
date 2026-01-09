/**
 * Audit Types — TypeScript DTOs for Audit OC Components
 * ════════════════════════════════════════════════════════════════════════════════
 *
 * PAC Reference: PAC-013A (CORRECTED · GOLD STANDARD)
 * Agent: Sonny (GID-02) — Audit UI
 * Order: ORDER 3
 * Effective Date: 2025-12-30
 *
 * ════════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// ENUMS
// ═══════════════════════════════════════════════════════════════════════════════

export enum ChainLinkType {
  PROOF = "PROOF",
  DECISION = "DECISION",
  OUTCOME = "OUTCOME",
  SETTLEMENT = "SETTLEMENT",
  PDO = "PDO",
}

export enum VerificationStatus {
  VERIFIED = "VERIFIED",
  FAILED = "FAILED",
  PENDING = "PENDING",
  UNAVAILABLE = "UNAVAILABLE",
}

export enum AuditExportFormat {
  JSON = "json",
  CSV = "csv",
}

export enum ChainCompleteness {
  FULL = "FULL",
  PARTIAL = "PARTIAL",
  MINIMAL = "MINIMAL",
  EMPTY = "EMPTY",
}

// ═══════════════════════════════════════════════════════════════════════════════
// CHAIN RECONSTRUCTION TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface ChainLink {
  link_id: string;
  link_type: ChainLinkType;
  parent_link_id: string | null;
  content_hash: string;
  previous_hash: string;
  timestamp: string;
  sequence_number: number;
  verification_status: VerificationStatus;
  content_summary: Record<string, unknown>;
}

export interface ChainReconstruction {
  chain_id: string;
  root_link_id: string;
  terminal_link_id: string;
  total_links: number;
  chain_integrity: VerificationStatus;
  links: ChainLink[];
  earliest_timestamp: string;
  latest_timestamp: string;
  reconstruction_timestamp: string;
  api_version: string;
}

export interface ChainVerificationResult {
  chain_id: string;
  verified: boolean;
  total_links: number;
  verified_links: number;
  failed_links: string[];
  verification_timestamp: string;
  integrity_hash: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUDIT EXPORT TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface AuditTrailEntry {
  entry_id: string;
  timestamp: string;
  pdo_id: string;
  proof_id: string;
  decision_id: string;
  outcome_id: string;
  settlement_id: string;
  proof_hash: string;
  decision_hash: string;
  outcome_hash: string;
  ledger_hash: string;
  chain_verified: boolean;
  issuer_gid: string;
  pac_id: string;
}

export interface AuditExportResponse {
  export_id: string;
  export_timestamp: string;
  format: AuditExportFormat;
  total_records: number;
  data_start: string;
  data_end: string;
  export_hash: string;
  api_version: string;
  entries: AuditTrailEntry[] | null;
}

// ═══════════════════════════════════════════════════════════════════════════════
// REGULATORY SUMMARY TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface RegulatoryMetrics {
  period_start: string;
  period_end: string;
  total_pdos: number;
  total_decisions: number;
  total_outcomes: number;
  total_settlements: number;
  verified_chains: number;
  unverified_chains: number;
  failed_verifications: number;
  governance_violations: number;
  human_interventions: number;
  fail_closed_triggers: number;
  verification_rate: number;
  chain_completeness_rate: number;
}

export interface RegulatorySummary {
  summary_id: string;
  generated_at: string;
  metrics: RegulatoryMetrics;
  system_version: string;
  governance_mode: string;
  data_complete: boolean;
  no_hidden_state: boolean;
  api_version: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUDIT METADATA
// ═══════════════════════════════════════════════════════════════════════════════

export interface AuditCapabilities {
  chain_reconstruction: boolean;
  hash_verification: boolean;
  json_export: boolean;
  csv_export: boolean;
  regulatory_summary: boolean;
}

export interface AuditInvariants {
  "INV-AUDIT-001": string;
  "INV-AUDIT-002": string;
  "INV-AUDIT-003": string;
  "INV-AUDIT-004": string;
  "INV-AUDIT-005": string;
  "INV-AUDIT-006": string;
}

export interface AuditMetadata {
  api_version: string;
  pac_reference: string;
  agent: string;
  governance_mode: string;
  execution_lane: string;
  runtime_id: string;
  capabilities: AuditCapabilities;
  invariants: AuditInvariants;
  supported_export_formats: string[];
  max_export_records: number;
  timestamp: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// AGGREGATION TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface RegistryReference {
  registry_type: string;
  entry_id: string;
  entry_hash: string;
  timestamp: string;
  sequence_number: number;
  metadata: Record<string, unknown>;
}

export interface CrossRegistryJoin {
  join_id: string;
  left_ref: RegistryReference;
  right_ref: RegistryReference;
  join_key: string;
  join_timestamp: string;
  join_type: string;
}

export interface AuditChainAggregate {
  chain_id: string;
  completeness: ChainCompleteness;
  pdo_ref: RegistryReference | null;
  proof_ref: RegistryReference | null;
  decision_ref: RegistryReference | null;
  outcome_ref: RegistryReference | null;
  settlement_ref: RegistryReference | null;
  joins: CrossRegistryJoin[];
  earliest_timestamp: string;
  latest_timestamp: string;
  temporal_order: string[];
  aggregate_hash: string;
  aggregation_timestamp: string;
  aggregation_status: string;
}

export interface AggregationMetrics {
  total_chains: number;
  complete_chains: number;
  partial_chains: number;
  failed_aggregations: number;
  pdo_entries: number;
  decision_entries: number;
  outcome_entries: number;
  settlement_entries: number;
  proof_entries: number;
  total_joins: number;
  completeness_rate: number;
}
