/**
 * Human Approval Modal (HAM) v1 — Type Contract
 *
 * Types for the strict human approval interface.
 * These types ensure compile-time enforcement of the approval contract.
 *
 * @see PAC-DIGGI-04 — Human Approval Modal
 */

// ============================================================
// CANONICAL INTENT TYPES
// ============================================================

/**
 * Canonical intent representation — the action being approved.
 * This is IMMUTABLE and displayed verbatim to the approver.
 */
export interface CanonicalIntent {
  /** The verb of the action (e.g., EXECUTE, BLOCK) */
  readonly verb: string;
  /** The target of the action */
  readonly target: string;
  /** Optional amount for financial operations */
  readonly amount?: string;
  /** Environment context (e.g., PRODUCTION, STAGING) */
  readonly environment?: string;
  /** The agent GID that requested this action */
  readonly requested_by: string;
  /** Unique correlation ID for audit trail */
  readonly correlation_id: string;
  /** Additional metadata (read-only) */
  readonly metadata?: Readonly<Record<string, unknown>>;
}

/**
 * Human approval context — full context for the approval modal.
 * Triggered by ESCALATE to human.operator or requires_human_approval=true.
 */
export interface HumanApprovalContext {
  /** The canonical intent requiring approval */
  readonly intent: CanonicalIntent;
  /** Risk factors and constraints from backend */
  readonly risks: readonly string[];
  /** Flag indicating human approval is required */
  readonly requires_human_approval: true;
  /** Optional denial reason that led to this escalation */
  readonly denial_reason?: string;
  /** Optional denial detail */
  readonly denial_detail?: string;
  /** Source of the escalation request */
  readonly escalation_source?: string;
}

// ============================================================
// APPROVER IDENTITY TYPES
// ============================================================

/**
 * Human approver identity — who is authorizing the action.
 * This is bound to the approval for non-repudiability.
 */
export interface ApproverIdentity {
  /** Unique user identifier */
  readonly user_id: string;
  /** Role of the approver (e.g., "AI Ops Lead") */
  readonly role: string;
  /** ISO-8601 timestamp of the approval */
  readonly timestamp: string;
  /** Optional session ID for audit correlation */
  readonly session_id?: string;
}

// ============================================================
// APPROVAL OUTPUT TYPES
// ============================================================

/**
 * Approval intent — the output emitted when user authorizes.
 * Frontend does NOT execute anything — this is sent to backend.
 */
export interface ApprovalIntent {
  /** Always ESCALATE for approval outputs */
  readonly verb: 'ESCALATE';
  /** Always approved.execution for successful approvals */
  readonly target: 'approved.execution';
  /** Identity of the human who authorized */
  readonly authorized_by: ApproverIdentity;
  /** Reference to the original intent being approved */
  readonly approval_of: string;
  /** Full canonical intent for audit completeness */
  readonly approved_intent: CanonicalIntent;
}

/**
 * Rejection intent — emitted when user cancels/rejects.
 */
export interface RejectionIntent {
  /** Always ESCALATE for rejection outputs */
  readonly verb: 'ESCALATE';
  /** Always rejected.by_human for rejections */
  readonly target: 'rejected.by_human';
  /** Identity of the human who rejected */
  readonly rejected_by: ApproverIdentity;
  /** Reference to the original intent being rejected */
  readonly rejection_of: string;
  /** Optional rejection reason */
  readonly reason?: string;
}

// ============================================================
// MODAL STATE TYPES
// ============================================================

/**
 * Approval modal state — tracks user progress through confirmation.
 */
export interface ApprovalModalState {
  /** Whether the checkbox is checked */
  readonly checkboxChecked: boolean;
  /** Current value of the typed confirmation */
  readonly typedConfirmation: string;
  /** Whether submission is in progress */
  readonly isSubmitting: boolean;
  /** Error message if any */
  readonly error: string | null;
  /** Whether approval has been submitted (prevents duplicates) */
  readonly hasSubmitted: boolean;
}

/**
 * Initial modal state — all confirmations unchecked.
 */
export const INITIAL_APPROVAL_STATE: ApprovalModalState = {
  checkboxChecked: false,
  typedConfirmation: '',
  isSubmitting: false,
  error: null,
  hasSubmitted: false,
} as const;

// ============================================================
// VALIDATION TYPES
// ============================================================

/**
 * Validation result for approval context.
 */
export interface ApprovalValidationResult {
  readonly valid: boolean;
  readonly reason?: string;
}

/**
 * Required confirmation phrase — case-sensitive, no autofill.
 */
export const REQUIRED_CONFIRMATION_PHRASE = 'AUTHORIZE' as const;

// ============================================================
// VALIDATION FUNCTIONS
// ============================================================

/**
 * Validates that the approval context has all required fields.
 * Fails closed — any missing field invalidates the context.
 */
export function validateApprovalContext(
  context: unknown
): ApprovalValidationResult {
  if (context === null || context === undefined) {
    return { valid: false, reason: 'Approval context is null or undefined' };
  }

  if (typeof context !== 'object') {
    return { valid: false, reason: 'Approval context is not an object' };
  }

  const ctx = context as Record<string, unknown>;

  // Check requires_human_approval flag
  if (ctx.requires_human_approval !== true) {
    return { valid: false, reason: 'requires_human_approval must be true' };
  }

  // Check intent object
  if (!ctx.intent || typeof ctx.intent !== 'object') {
    return { valid: false, reason: 'Missing or invalid intent object' };
  }

  const intent = ctx.intent as Record<string, unknown>;

  // Check required intent fields
  if (typeof intent.verb !== 'string' || intent.verb.trim() === '') {
    return { valid: false, reason: 'Intent missing verb' };
  }

  if (typeof intent.target !== 'string' || intent.target.trim() === '') {
    return { valid: false, reason: 'Intent missing target' };
  }

  if (typeof intent.requested_by !== 'string' || intent.requested_by.trim() === '') {
    return { valid: false, reason: 'Intent missing requested_by' };
  }

  if (typeof intent.correlation_id !== 'string' || intent.correlation_id.trim() === '') {
    return { valid: false, reason: 'Intent missing correlation_id' };
  }

  // Check risks array
  if (!Array.isArray(ctx.risks)) {
    return { valid: false, reason: 'Risks must be an array' };
  }

  return { valid: true };
}

/**
 * Validates that the approver identity is complete.
 */
export function validateApproverIdentity(
  identity: unknown
): ApprovalValidationResult {
  if (identity === null || identity === undefined) {
    return { valid: false, reason: 'Approver identity is null or undefined' };
  }

  if (typeof identity !== 'object') {
    return { valid: false, reason: 'Approver identity is not an object' };
  }

  const id = identity as Record<string, unknown>;

  if (typeof id.user_id !== 'string' || id.user_id.trim() === '') {
    return { valid: false, reason: 'Missing user_id' };
  }

  if (typeof id.role !== 'string' || id.role.trim() === '') {
    return { valid: false, reason: 'Missing role' };
  }

  if (typeof id.timestamp !== 'string' || id.timestamp.trim() === '') {
    return { valid: false, reason: 'Missing timestamp' };
  }

  return { valid: true };
}

/**
 * Checks if the typed confirmation matches the required phrase.
 * Case-sensitive, exact match required.
 */
export function isConfirmationValid(typed: string): boolean {
  return typed === REQUIRED_CONFIRMATION_PHRASE;
}

/**
 * Checks if all approval prerequisites are satisfied.
 */
export function canSubmitApproval(state: ApprovalModalState): boolean {
  return (
    state.checkboxChecked &&
    isConfirmationValid(state.typedConfirmation) &&
    !state.isSubmitting &&
    !state.hasSubmitted &&
    state.error === null
  );
}

// ============================================================
// FACTORY FUNCTIONS
// ============================================================

/**
 * Creates an approval intent from the context and approver identity.
 * This is the output sent to the backend.
 */
export function createApprovalIntent(
  context: HumanApprovalContext,
  approver: ApproverIdentity
): ApprovalIntent {
  return {
    verb: 'ESCALATE',
    target: 'approved.execution',
    authorized_by: approver,
    approval_of: `correlation_id:${context.intent.correlation_id}`,
    approved_intent: context.intent,
  };
}

/**
 * Creates a rejection intent from the context and rejector identity.
 */
export function createRejectionIntent(
  context: HumanApprovalContext,
  rejector: ApproverIdentity,
  reason?: string
): RejectionIntent {
  return {
    verb: 'ESCALATE',
    target: 'rejected.by_human',
    rejected_by: rejector,
    rejection_of: `correlation_id:${context.intent.correlation_id}`,
    reason,
  };
}

// ============================================================
// TYPE GUARDS
// ============================================================

/**
 * Type guard for HumanApprovalContext.
 */
export function isHumanApprovalContext(
  value: unknown
): value is HumanApprovalContext {
  return validateApprovalContext(value).valid;
}

/**
 * Type guard for ApproverIdentity.
 */
export function isApproverIdentity(
  value: unknown
): value is ApproverIdentity {
  return validateApproverIdentity(value).valid;
}

/**
 * Checks if a Diggi correction step triggers human approval.
 * Triggered by verb=ESCALATE, target=human.operator
 */
export function isHumanEscalationStep(step: {
  verb: string;
  target?: string;
}): boolean {
  return (
    step.verb === 'ESCALATE' &&
    step.target === 'human.operator'
  );
}
