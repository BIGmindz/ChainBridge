/**
 * Diggi Correction Types — CRC v1
 *
 * Strict type definitions for the Deterministic Correction Contract.
 * These types match the backend DCC output exactly.
 *
 * CONSTRAINTS:
 * - UI must render backend output verbatim
 * - No additional fields permitted
 * - No optional UI-only extensions
 *
 * @see PAC-DIGGI-03 — Correction Rendering Contract
 */

/**
 * Permitted verbs in correction steps.
 * EXECUTE, APPROVE, and BLOCK are FORBIDDEN.
 */
export type DiggiCorrectionVerb = "PROPOSE" | "ESCALATE" | "READ";

/**
 * A single allowed next step in a correction plan.
 * Rendered as one button in the UI.
 */
export type DiggiCorrectionStep = {
  /** The verb for this action (PROPOSE, ESCALATE, or READ only) */
  verb: DiggiCorrectionVerb;
  /** Target resource for ESCALATE */
  target?: string;
  /** Scope for PROPOSE/READ */
  target_scope?: string;
  /** Human-readable description — rendered as button label */
  description: string;
};

/**
 * The correction plan attached to a DENY response.
 * Contains constraints explaining why, and bounded next steps.
 */
export type DiggiCorrectionPlan = {
  /** The denial reason code (matches DenialReason enum) */
  cause: string;
  /** List of constraints explaining why the action was denied */
  constraints: string[];
  /** List of allowed next steps — each renders as one button */
  allowed_next_steps: DiggiCorrectionStep[];
};

/**
 * Wrapper type matching the backend EvaluationResult.correction_plan structure.
 */
export type DiggiCorrectionPlanWrapper = {
  correction_plan: DiggiCorrectionPlan;
};

/**
 * Full denial response from backend governance evaluation.
 * This is what the UI receives on a DENY decision.
 */
export type DiggiDenialResponse = {
  /** Always "DENY" for denial responses */
  decision: "DENY";
  /** The agent that was denied */
  agent_gid: string;
  /** The verb that was attempted */
  intent_verb: string;
  /** The target that was attempted */
  intent_target: string;
  /** The denial reason code */
  reason: string;
  /** Human-readable denial detail */
  reason_detail: string;
  /** Where the intent should be routed (typically GID-00) */
  next_hop?: string;
  /** The correction plan with bounded next steps */
  correction_plan?: DiggiCorrectionPlanWrapper;
  /** ISO timestamp */
  timestamp: string;
  /** Correlation ID for audit trail */
  correlation_id?: string;
};

/**
 * Props for the main DiggiDenialPanel component.
 */
export type DiggiDenialPanelProps = {
  /** The full denial response from backend */
  denial: DiggiDenialResponse;
  /** Callback when user selects a next step */
  onStepSelect?: (step: DiggiCorrectionStep) => void;
  /** Optional additional className */
  className?: string;
};

/**
 * Props for the constraint list component.
 */
export type DiggiConstraintListProps = {
  /** List of constraint strings */
  constraints: string[];
  /** Optional additional className */
  className?: string;
};

/**
 * Props for the next step button component.
 */
export type DiggiNextStepButtonProps = {
  /** The correction step to render */
  step: DiggiCorrectionStep;
  /** Callback when button is clicked */
  onClick?: () => void;
  /** Whether the button is disabled */
  disabled?: boolean;
  /** Optional additional className */
  className?: string;
};

/**
 * Validation result for correction plan.
 */
export type DiggiValidationResult = {
  /** Whether the correction plan is valid */
  isValid: boolean;
  /** Error message if invalid */
  error?: string;
};

/**
 * Validates a correction plan wrapper.
 * Returns validation result indicating if the plan can be rendered.
 *
 * @param plan - The correction plan wrapper to validate
 * @returns Validation result with isValid flag and optional error
 */
export function validateCorrectionPlan(
  plan: DiggiCorrectionPlanWrapper | null | undefined
): DiggiValidationResult {
  if (!plan) {
    return { isValid: false, error: "Governance response invalid: missing correction_plan" };
  }

  if (!plan.correction_plan) {
    return { isValid: false, error: "Governance response invalid: malformed correction_plan" };
  }

  const inner = plan.correction_plan;

  if (typeof inner.cause !== "string" || !inner.cause) {
    return { isValid: false, error: "Governance response invalid: missing cause" };
  }

  if (!Array.isArray(inner.constraints)) {
    return { isValid: false, error: "Governance response invalid: constraints must be array" };
  }

  if (!Array.isArray(inner.allowed_next_steps)) {
    return { isValid: false, error: "Governance response invalid: allowed_next_steps must be array" };
  }

  // Validate each step
  for (const step of inner.allowed_next_steps) {
    if (!step.verb || !step.description) {
      return { isValid: false, error: "Governance response invalid: malformed step" };
    }

    // Check for forbidden verbs
    const verb = step.verb.toUpperCase();
    if (verb === "EXECUTE" || verb === "APPROVE" || verb === "BLOCK") {
      return { isValid: false, error: `Governance response invalid: forbidden verb ${verb}` };
    }
  }

  return { isValid: true };
}

/**
 * Checks if a verb is a known permitted verb.
 * Unknown verbs should not render buttons.
 *
 * @param verb - The verb string to check
 * @returns True if the verb is known and permitted
 */
export function isKnownVerb(verb: string): verb is DiggiCorrectionVerb {
  const upper = verb.toUpperCase();
  return upper === "PROPOSE" || upper === "ESCALATE" || upper === "READ";
}
