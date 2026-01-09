/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * OCC Hardening Utilities — UI Security & State Enforcement
 * PAC-BENSON-P23-C: Parallel Platform Hardening (Corrective)
 *
 * Provides UI-level security and state enforcement:
 * - Read-only state enforcement
 * - Input sanitization
 * - Event validation
 * - State immutability helpers
 *
 * INVARIANTS:
 * - INV-UI-001: No optimistic state rendering
 * - INV-UI-002: Read-only display enforcement
 * - INV-UI-003: Input sanitization
 *
 * Author: SONNY (GID-02) — Frontend Lead
 * Security Review: SAM (GID-06)
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// INPUT SANITIZATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Threat patterns for input validation.
 */
const THREAT_PATTERNS: Array<{ id: string; name: string; pattern: RegExp; severity: string }> = [
  { id: 'XSS-001', name: 'Script Tag', pattern: /<script[^>]*>/gi, severity: 'critical' },
  { id: 'XSS-002', name: 'Event Handler', pattern: /on\w+\s*=/gi, severity: 'high' },
  { id: 'XSS-003', name: 'JavaScript URI', pattern: /javascript:/gi, severity: 'critical' },
  { id: 'XSS-004', name: 'Data URI', pattern: /data:[^,]*;base64/gi, severity: 'medium' },
  { id: 'INJ-001', name: 'Path Traversal', pattern: /\.\.\//g, severity: 'high' },
];

/**
 * Sanitize user input to prevent XSS and injection attacks.
 * INV-UI-003: Input sanitization
 */
export function sanitizeInput(input: string, maxLength = 1000): string {
  if (typeof input !== 'string') {
    return '';
  }

  // Truncate to max length
  let sanitized = input.slice(0, maxLength);

  // HTML entity encode dangerous characters
  const entityMap: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#x27;',
    '/': '&#x2F;',
    '`': '&#x60;',
    '=': '&#x3D;',
  };

  sanitized = sanitized.replace(/[&<>"'`=/]/g, (char) => entityMap[char] || char);

  // Remove null bytes
  sanitized = sanitized.replace(/\0/g, '');

  return sanitized;
}

/**
 * Check if input contains threat patterns.
 */
export function detectThreats(input: string): Array<{ id: string; name: string; severity: string }> {
  const threats: Array<{ id: string; name: string; severity: string }> = [];

  for (const threat of THREAT_PATTERNS) {
    if (threat.pattern.test(input)) {
      threats.push({ id: threat.id, name: threat.name, severity: threat.severity });
    }
  }

  return threats;
}

/**
 * Validate and sanitize input, throwing if threats detected.
 */
export function validateInput(input: string, fieldName: string): string {
  const threats = detectThreats(input);

  if (threats.length > 0) {
    console.error(`[SECURITY] Threats detected in ${fieldName}:`, threats);
    throw new Error(`Invalid input in ${fieldName}: security threat detected`);
  }

  return sanitizeInput(input);
}

// ═══════════════════════════════════════════════════════════════════════════════
// READ-ONLY STATE ENFORCEMENT
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Create a deeply frozen (immutable) copy of an object.
 * INV-UI-001: No optimistic state rendering
 */
export function deepFreeze<T extends object>(obj: T): Readonly<T> {
  // Get all property names
  const propNames = Object.getOwnPropertyNames(obj) as (keyof T)[];

  // Freeze nested objects first
  for (const name of propNames) {
    const value = obj[name];
    if (value && typeof value === 'object') {
      deepFreeze(value as object);
    }
  }

  return Object.freeze(obj);
}

/**
 * Create a read-only proxy that throws on mutation attempts.
 * INV-UI-002: Read-only display enforcement
 */
export function createReadOnlyProxy<T extends object>(target: T): Readonly<T> {
  return new Proxy(target, {
    set(_target, property) {
      console.error(`[INV-UI-002] Mutation blocked: Cannot set property "${String(property)}"`);
      throw new Error(`INV-UI-002: State mutation forbidden. Property "${String(property)}" is read-only.`);
    },
    deleteProperty(_target, property) {
      console.error(`[INV-UI-002] Deletion blocked: Cannot delete property "${String(property)}"`);
      throw new Error(`INV-UI-002: State mutation forbidden. Cannot delete "${String(property)}".`);
    },
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// STATE VALIDATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Valid OCC state values for validation.
 */
export const VALID_AGENT_STATES = ['IDLE', 'EXECUTING', 'BLOCKED', 'COMPLETED', 'FAILED', 'AWAITING_ACK'] as const;
export const VALID_HEALTH_STATES = ['HEALTHY', 'DEGRADED', 'UNHEALTHY', 'OFFLINE', 'UNKNOWN'] as const;
export const VALID_PAC_STATES = [
  'ADMISSION',
  'RUNTIME_ACTIVATION',
  'AGENT_ACTIVATION',
  'EXECUTING',
  'WRAP_COLLECTION',
  'REVIEW_GATE',
  'BER_ISSUED',
  'SETTLED',
  'FAILED',
  'CANCELLED',
] as const;

export type AgentState = typeof VALID_AGENT_STATES[number];
export type HealthState = typeof VALID_HEALTH_STATES[number];
export type PACState = typeof VALID_PAC_STATES[number];

/**
 * Validate agent execution state.
 */
export function isValidAgentState(state: string): state is AgentState {
  return VALID_AGENT_STATES.includes(state as AgentState);
}

/**
 * Validate health state.
 */
export function isValidHealthState(state: string): state is HealthState {
  return VALID_HEALTH_STATES.includes(state as HealthState);
}

/**
 * Validate PAC lifecycle state.
 */
export function isValidPACState(state: string): state is PACState {
  return VALID_PAC_STATES.includes(state as PACState);
}

// ═══════════════════════════════════════════════════════════════════════════════
// EVIDENCE HASH UTILITIES
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Verify that an object contains an evidence hash.
 * INV-OCC-005: Evidence immutability
 */
export function hasEvidenceHash(obj: unknown): boolean {
  if (typeof obj !== 'object' || obj === null) {
    return false;
  }

  const hashFields = ['evidence_hash', 'content_hash', 'hash', 'proof_hash'];

  for (const field of hashFields) {
    if (field in obj && typeof (obj as Record<string, unknown>)[field] === 'string') {
      return true;
    }
  }

  return false;
}

/**
 * Extract evidence hash from object.
 */
export function getEvidenceHash(obj: unknown): string | null {
  if (typeof obj !== 'object' || obj === null) {
    return null;
  }

  const hashFields = ['evidence_hash', 'content_hash', 'hash', 'proof_hash'];
  const record = obj as Record<string, unknown>;

  for (const field of hashFields) {
    if (field in record && typeof record[field] === 'string') {
      return record[field] as string;
    }
  }

  return null;
}

// ═══════════════════════════════════════════════════════════════════════════════
// ACCESSIBILITY HELPERS (LIRA)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Generate accessible status announcement.
 */
export function getStatusAnnouncement(
  entityType: 'agent' | 'pac' | 'decision',
  entityId: string,
  state: string,
): string {
  const stateLabels: Record<string, string> = {
    IDLE: 'is idle',
    EXECUTING: 'is executing',
    BLOCKED: 'is blocked',
    COMPLETED: 'has completed',
    FAILED: 'has failed',
    AWAITING_ACK: 'is awaiting acknowledgment',
    HEALTHY: 'is healthy',
    DEGRADED: 'is degraded',
    UNHEALTHY: 'is unhealthy',
    OFFLINE: 'is offline',
    UNKNOWN: 'has unknown status',
  };

  const label = stateLabels[state] || `is in ${state} state`;
  return `${entityType} ${entityId} ${label}`;
}

/**
 * Generate aria-label for complex components.
 */
export function generateAriaLabel(
  componentType: string,
  context: Record<string, string | number>,
): string {
  const parts = [componentType];

  for (const [key, value] of Object.entries(context)) {
    parts.push(`${key}: ${value}`);
  }

  return parts.join(', ');
}

// ═══════════════════════════════════════════════════════════════════════════════
// EXPORTS
// ═══════════════════════════════════════════════════════════════════════════════

export default {
  sanitizeInput,
  detectThreats,
  validateInput,
  deepFreeze,
  createReadOnlyProxy,
  isValidAgentState,
  isValidHealthState,
  isValidPACState,
  hasEvidenceHash,
  getEvidenceHash,
  getStatusAnnouncement,
  generateAriaLabel,
  VALID_AGENT_STATES,
  VALID_HEALTH_STATES,
  VALID_PAC_STATES,
};
