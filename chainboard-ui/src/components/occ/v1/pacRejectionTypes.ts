/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * PAC Upload Rejection Types — OCC UI Binding
 * PAC-JEFFREY-C05: Corrective PAC for deterministic rejection feedback
 * 
 * INVARIANTS:
 * - INV-PAC-010: Rejection reasons MUST be enumerable
 * - INV-PAC-011: Schema MUST be machine-verifiable
 * - INV-PAC-012: Operator feedback MUST be deterministic
 * 
 * Author: SONNY (GID-02) — Frontend
 * Constitutional Reference: OCC_CONSTITUTION_v1.0
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// REJECTION CATEGORIES
// ═══════════════════════════════════════════════════════════════════════════════

export type RejectionCategory =
  | 'SCHEMA'
  | 'STRUCTURE'
  | 'BLOCK'
  | 'INTEGRITY'
  | 'GOVERNANCE'
  | 'AUTHORITY'
  | 'SEMANTIC';

export type RejectionSeverity = 'HARD' | 'SOFT';

export const CATEGORY_PREFIXES: Record<RejectionCategory, string> = {
  SCHEMA: 'REJ-SCH',
  STRUCTURE: 'REJ-STR',
  BLOCK: 'REJ-BLK',
  INTEGRITY: 'REJ-INT',
  GOVERNANCE: 'REJ-GOV',
  AUTHORITY: 'REJ-AUT',
  SEMANTIC: 'REJ-SEM',
};

export const CATEGORY_ICONS: Record<RejectionCategory, string> = {
  SCHEMA: '📋',
  STRUCTURE: '🏗️',
  BLOCK: '📦',
  INTEGRITY: '🔐',
  GOVERNANCE: '⚖️',
  AUTHORITY: '🔑',
  SEMANTIC: '📝',
};

export const SEVERITY_COLORS: Record<RejectionSeverity, string> = {
  HARD: '#DC2626', // red-600
  SOFT: '#F59E0B', // amber-500
};

// ═══════════════════════════════════════════════════════════════════════════════
// REJECTION CODE DEFINITIONS
// ═══════════════════════════════════════════════════════════════════════════════

export interface RejectionCodeDefinition {
  code: string;
  category: RejectionCategory;
  severity: RejectionSeverity;
  message: string;
  description: string;
  operatorFeedback: string;
  resolution: string;
  hasFieldParam?: boolean;
}

export const REJECTION_CODES: Record<string, RejectionCodeDefinition> = {
  // Schema validation
  'REJ-SCH-001': {
    code: 'REJ-SCH-001',
    category: 'SCHEMA',
    severity: 'HARD',
    message: 'Invalid schema version',
    description: 'PAC schema_version does not match required CHAINBRIDGE_PAC_SCHEMA_v1.0.0',
    operatorFeedback: 'Upload failed: Schema version mismatch. Required: CHAINBRIDGE_PAC_SCHEMA_v1.0.0',
    resolution: 'Update pac.schema_version to CHAINBRIDGE_PAC_SCHEMA_v1.0.0',
  },
  'REJ-SCH-002': {
    code: 'REJ-SCH-002',
    category: 'SCHEMA',
    severity: 'HARD',
    message: 'Missing required field',
    description: 'One or more required top-level fields are missing',
    operatorFeedback: "Upload failed: Missing required field '{field_name}'",
    resolution: 'Add the missing field to the PAC document',
    hasFieldParam: true,
  },
  'REJ-SCH-003': {
    code: 'REJ-SCH-003',
    category: 'SCHEMA',
    severity: 'HARD',
    message: 'Invalid field type',
    description: 'Field value does not match expected type',
    operatorFeedback: "Upload failed: Field '{field_name}' must be type '{expected_type}', got '{actual_type}'",
    resolution: 'Correct the field type',
    hasFieldParam: true,
  },
  'REJ-SCH-004': {
    code: 'REJ-SCH-004',
    category: 'SCHEMA',
    severity: 'HARD',
    message: 'Invalid enum value',
    description: 'Field value not in allowed enum set',
    operatorFeedback: "Upload failed: Field '{field_name}' must be one of {allowed_values}",
    resolution: 'Use a valid enum value',
    hasFieldParam: true,
  },
  'REJ-SCH-005': {
    code: 'REJ-SCH-005',
    category: 'SCHEMA',
    severity: 'HARD',
    message: 'Invalid PAC ID format',
    description: 'pac_id does not match pattern PAC-{ISSUER}-{TYPE}{SEQ}',
    operatorFeedback: 'Upload failed: Invalid PAC ID format. Expected: PAC-{ISSUER}-{TYPE}{SEQ}',
    resolution: 'Format pac_id as PAC-ISSUER-X00 (e.g., PAC-JEFFREY-P03)',
  },
  'REJ-SCH-006': {
    code: 'REJ-SCH-006',
    category: 'SCHEMA',
    severity: 'HARD',
    message: 'Invalid timestamp format',
    description: 'Timestamp field is not valid ISO 8601 format',
    operatorFeedback: "Upload failed: Field '{field_name}' must be ISO 8601 datetime",
    resolution: 'Use format: YYYY-MM-DDTHH:MM:SSZ',
    hasFieldParam: true,
  },
  'REJ-SCH-007': {
    code: 'REJ-SCH-007',
    category: 'SCHEMA',
    severity: 'HARD',
    message: 'Additional properties not allowed',
    description: 'PAC contains fields not defined in schema',
    operatorFeedback: "Upload failed: Unknown field '{field_name}' not permitted",
    resolution: 'Remove the unknown field',
    hasFieldParam: true,
  },
  
  // Structure validation
  'REJ-STR-001': {
    code: 'REJ-STR-001',
    category: 'STRUCTURE',
    severity: 'HARD',
    message: 'Incorrect block count',
    description: 'PAC must contain exactly 20 blocks',
    operatorFeedback: 'Upload failed: PAC must have exactly 20 blocks, found {actual_count}',
    resolution: 'Ensure blocks array contains exactly 20 blocks (indices 0-19)',
  },
  'REJ-STR-002': {
    code: 'REJ-STR-002',
    category: 'STRUCTURE',
    severity: 'HARD',
    message: 'Missing block index',
    description: 'One or more block indices are missing from the sequence',
    operatorFeedback: 'Upload failed: Missing block index {missing_index}',
    resolution: 'Add the missing block at index {missing_index}',
  },
  'REJ-STR-003': {
    code: 'REJ-STR-003',
    category: 'STRUCTURE',
    severity: 'HARD',
    message: 'Duplicate block index',
    description: 'Block index appears more than once',
    operatorFeedback: 'Upload failed: Duplicate block index {duplicate_index}',
    resolution: 'Remove duplicate block at index {duplicate_index}',
  },
  'REJ-STR-004': {
    code: 'REJ-STR-004',
    category: 'STRUCTURE',
    severity: 'HARD',
    message: 'Out-of-order blocks',
    description: 'Blocks are not in sequential order',
    operatorFeedback: 'Upload failed: Blocks must be in sequential order (0-19)',
    resolution: 'Reorder blocks to sequential indices',
  },
  'REJ-STR-005': {
    code: 'REJ-STR-005',
    category: 'STRUCTURE',
    severity: 'HARD',
    message: 'Empty blocks array',
    description: 'PAC blocks array is empty or null',
    operatorFeedback: 'Upload failed: PAC must contain 20 blocks',
    resolution: 'Populate blocks array with all 20 required blocks',
  },
  
  // Block validation
  'REJ-BLK-001': {
    code: 'REJ-BLK-001',
    category: 'BLOCK',
    severity: 'HARD',
    message: 'Block type mismatch',
    description: 'Block type does not match required type for index',
    operatorFeedback: "Upload failed: Block {index} must be type '{expected_type}', got '{actual_type}'",
    resolution: "Set block {index} type to '{expected_type}'",
  },
  'REJ-BLK-002': {
    code: 'REJ-BLK-002',
    category: 'BLOCK',
    severity: 'HARD',
    message: 'Missing block content',
    description: 'Block content is missing or null',
    operatorFeedback: 'Upload failed: Block {index} ({type}) has no content',
    resolution: 'Add required content to block {index}',
  },
  'REJ-BLK-003': {
    code: 'REJ-BLK-003',
    category: 'BLOCK',
    severity: 'HARD',
    message: 'Invalid block content schema',
    description: 'Block content does not match block type schema',
    operatorFeedback: 'Upload failed: Block {index} ({type}) content invalid: {validation_error}',
    resolution: 'Correct block content per block type specification',
  },
  'REJ-BLK-004': {
    code: 'REJ-BLK-004',
    category: 'BLOCK',
    severity: 'HARD',
    message: 'METADATA block mismatch',
    description: 'Block 0 METADATA does not match top-level PAC fields',
    operatorFeedback: 'Upload failed: METADATA block must match top-level PAC fields',
    resolution: 'Ensure Block 0 content matches pac_id, classification, governance_tier, etc.',
  },
  'REJ-BLK-005': {
    code: 'REJ-BLK-005',
    category: 'BLOCK',
    severity: 'HARD',
    message: 'Missing required block field',
    description: 'Block is missing a required field for its type',
    operatorFeedback: "Upload failed: Block {index} ({type}) missing required field '{field_name}'",
    resolution: "Add '{field_name}' to block {index}",
  },
  
  // Integrity validation
  'REJ-INT-001': {
    code: 'REJ-INT-001',
    category: 'INTEGRITY',
    severity: 'HARD',
    message: 'Hash mismatch',
    description: 'PAC hash does not match computed hash of content',
    operatorFeedback: 'Upload failed: Hash verification failed. Expected {expected_hash}, computed {actual_hash}',
    resolution: 'Recompute SHA-256 hash of canonical PAC content',
  },
  'REJ-INT-002': {
    code: 'REJ-INT-002',
    category: 'INTEGRITY',
    severity: 'HARD',
    message: 'Invalid hash format',
    description: 'Hash is not a valid 64-character hex string',
    operatorFeedback: 'Upload failed: Hash must be 64 hex characters (SHA-256)',
    resolution: 'Provide valid SHA-256 hash (64 lowercase hex characters)',
  },
  'REJ-INT-003': {
    code: 'REJ-INT-003',
    category: 'INTEGRITY',
    severity: 'HARD',
    message: 'Ledger hash mismatch',
    description: 'Block 19 LEDGER_COMMIT hash does not match PAC hash',
    operatorFeedback: 'Upload failed: LEDGER_COMMIT hash must match PAC hash',
    resolution: 'Set Block 19 hash to match top-level PAC hash',
  },
  'REJ-INT-004': {
    code: 'REJ-INT-004',
    category: 'INTEGRITY',
    severity: 'HARD',
    message: 'Tampered content detected',
    description: 'PAC content appears to have been modified after signing',
    operatorFeedback: 'Upload failed: Content integrity violation detected',
    resolution: 'Regenerate PAC with fresh hash',
  },
  
  // Governance validation
  'REJ-GOV-001': {
    code: 'REJ-GOV-001',
    category: 'GOVERNANCE',
    severity: 'HARD',
    message: 'Invalid governance tier',
    description: 'governance_tier is not LAW, POLICY, or OPERATIONAL',
    operatorFeedback: 'Upload failed: governance_tier must be LAW, POLICY, or OPERATIONAL',
    resolution: 'Set governance_tier to valid value',
  },
  'REJ-GOV-002': {
    code: 'REJ-GOV-002',
    category: 'GOVERNANCE',
    severity: 'HARD',
    message: 'Tier authority violation',
    description: 'Issuer does not have authority for specified governance tier',
    operatorFeedback: "Upload failed: Issuer '{issuer}' cannot issue {tier}-tier PACs",
    resolution: 'Use appropriate issuer for governance tier or change tier',
  },
  'REJ-GOV-003': {
    code: 'REJ-GOV-003',
    category: 'GOVERNANCE',
    severity: 'HARD',
    message: 'fail_closed must be true',
    description: 'PAC must have fail_closed: true',
    operatorFeedback: 'Upload failed: fail_closed must be true (ChainBridge requirement)',
    resolution: 'Set fail_closed to true',
  },
  'REJ-GOV-004': {
    code: 'REJ-GOV-004',
    category: 'GOVERNANCE',
    severity: 'HARD',
    message: 'Invalid drift tolerance for tier',
    description: 'LAW-tier PACs must have ZERO drift tolerance',
    operatorFeedback: 'Upload failed: LAW-tier PACs require drift_tolerance: ZERO',
    resolution: 'Set drift_tolerance to ZERO for LAW-tier PACs',
  },
  'REJ-GOV-005': {
    code: 'REJ-GOV-005',
    category: 'GOVERNANCE',
    severity: 'HARD',
    message: 'CORRECTIVE PAC missing supersedes',
    description: 'CORRECTIVE classification requires supersedes field',
    operatorFeedback: 'Upload failed: CORRECTIVE PACs must specify supersedes',
    resolution: 'Add supersedes field with PAC ID being corrected',
  },
  
  // Authority validation
  'REJ-AUT-001': {
    code: 'REJ-AUT-001',
    category: 'AUTHORITY',
    severity: 'HARD',
    message: 'Unknown issuer',
    description: 'issuer_gid is not a recognized agent',
    operatorFeedback: "Upload failed: Issuer '{issuer_gid}' not recognized",
    resolution: 'Use valid issuer GID (e.g., JEFFREY, BENSON, GID-00)',
  },
  'REJ-AUT-002': {
    code: 'REJ-AUT-002',
    category: 'AUTHORITY',
    severity: 'HARD',
    message: 'Issuer role mismatch',
    description: "issuer_role does not match issuer_gid's registered role",
    operatorFeedback: "Upload failed: Issuer '{issuer_gid}' role is '{actual_role}', not '{claimed_role}'",
    resolution: 'Correct issuer_role to match registered role',
  },
  'REJ-AUT-003': {
    code: 'REJ-AUT-003',
    category: 'AUTHORITY',
    severity: 'HARD',
    message: 'PAC admission denied',
    description: 'Block 1 PAC_ADMISSION shows admission: DENIED',
    operatorFeedback: 'Upload failed: PAC admission was denied',
    resolution: 'Review admission criteria and resubmit',
  },
  'REJ-AUT-004': {
    code: 'REJ-AUT-004',
    category: 'AUTHORITY',
    severity: 'HARD',
    message: 'Missing runtime ACK',
    description: 'Block 4 RUNTIME_ACK_COLLECTION incomplete',
    operatorFeedback: 'Upload failed: Runtime acknowledgement not collected',
    resolution: 'Ensure runtime ACK is collected before submission',
  },
  'REJ-AUT-005': {
    code: 'REJ-AUT-005',
    category: 'AUTHORITY',
    severity: 'HARD',
    message: 'Missing agent ACK',
    description: 'Block 7 AGENT_ACK_COLLECTION incomplete',
    operatorFeedback: 'Upload failed: Agent acknowledgements not collected',
    resolution: 'Ensure all agent ACKs are collected before submission',
  },
  
  // Semantic validation
  'REJ-SEM-001': {
    code: 'REJ-SEM-001',
    category: 'SEMANTIC',
    severity: 'HARD',
    message: 'Empty goal state',
    description: 'Block 10 GOAL_STATE has no goals defined',
    operatorFeedback: 'Upload failed: PAC must define at least one goal',
    resolution: 'Add at least one goal to Block 10',
  },
  'REJ-SEM-002': {
    code: 'REJ-SEM-002',
    category: 'SEMANTIC',
    severity: 'HARD',
    message: 'Empty task list',
    description: 'Block 13 TASKS_PLAN has no tasks defined',
    operatorFeedback: 'Upload failed: PAC must define at least one task',
    resolution: 'Add at least one task to Block 13',
  },
  'REJ-SEM-003': {
    code: 'REJ-SEM-003',
    category: 'SEMANTIC',
    severity: 'HARD',
    message: 'Invalid invariant format',
    description: 'Invariant ID does not match pattern INV-{DOMAIN}-{SEQ}',
    operatorFeedback: "Upload failed: Invalid invariant ID '{invariant_id}'. Format: INV-XXX-000",
    resolution: 'Use format INV-DOMAIN-000 (e.g., INV-OCC-001)',
  },
  'REJ-SEM-004': {
    code: 'REJ-SEM-004',
    category: 'SEMANTIC',
    severity: 'HARD',
    message: 'Scope too short',
    description: 'PAC scope is less than 10 characters',
    operatorFeedback: 'Upload failed: Scope must be at least 10 characters',
    resolution: 'Provide more detailed scope description',
  },
  'REJ-SEM-005': {
    code: 'REJ-SEM-005',
    category: 'SEMANTIC',
    severity: 'HARD',
    message: 'Scope too long',
    description: 'PAC scope exceeds 500 characters',
    operatorFeedback: 'Upload failed: Scope must not exceed 500 characters',
    resolution: 'Shorten scope description',
  },
  'REJ-SEM-006': {
    code: 'REJ-SEM-006',
    category: 'SEMANTIC',
    severity: 'HARD',
    message: 'Circular task dependency',
    description: 'Task dependencies form a cycle',
    operatorFeedback: 'Upload failed: Circular dependency detected in tasks',
    resolution: 'Remove circular task dependencies',
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// REJECTION RESPONSE TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface PACUploadSuccess {
  status: 'ACCEPTED';
  pacId: string;
  acceptedAt: string;
  hash: string;
}

export interface PACUploadRejection {
  status: 'REJECTED';
  pacId: string | null;
  rejectedAt: string;
  rejectionCode: string;
  rejectionMessage: string;
  operatorFeedback: string;
  resolution: string;
  category: RejectionCategory;
  severity: RejectionSeverity;
  details?: Record<string, string>;
}

export type PACUploadResponse = PACUploadSuccess | PACUploadRejection;

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get rejection code definition by code
 */
export function getRejectionCode(code: string): RejectionCodeDefinition | undefined {
  return REJECTION_CODES[code];
}

/**
 * Get all rejection codes for a category
 */
export function getRejectionCodesByCategory(category: RejectionCategory): RejectionCodeDefinition[] {
  return Object.values(REJECTION_CODES).filter(def => def.category === category);
}

/**
 * Format operator feedback with parameters
 */
export function formatOperatorFeedback(
  code: string,
  params: Record<string, string> = {}
): string {
  const def = REJECTION_CODES[code];
  if (!def) return 'Unknown rejection code';
  
  let feedback = def.operatorFeedback;
  for (const [key, value] of Object.entries(params)) {
    feedback = feedback.replace(`{${key}}`, value);
  }
  return feedback;
}

/**
 * Format resolution with parameters
 */
export function formatResolution(
  code: string,
  params: Record<string, string> = {}
): string {
  const def = REJECTION_CODES[code];
  if (!def) return 'Unknown rejection code';
  
  let resolution = def.resolution;
  for (const [key, value] of Object.entries(params)) {
    resolution = resolution.replace(`{${key}}`, value);
  }
  return resolution;
}

/**
 * Create a rejection response
 */
export function createRejection(
  code: string,
  pacId: string | null,
  params: Record<string, string> = {}
): PACUploadRejection {
  const def = REJECTION_CODES[code];
  if (!def) {
    throw new Error(`Unknown rejection code: ${code}`);
  }
  
  return {
    status: 'REJECTED',
    pacId,
    rejectedAt: new Date().toISOString(),
    rejectionCode: code,
    rejectionMessage: def.message,
    operatorFeedback: formatOperatorFeedback(code, params),
    resolution: formatResolution(code, params),
    category: def.category,
    severity: def.severity,
    details: Object.keys(params).length > 0 ? params : undefined,
  };
}
