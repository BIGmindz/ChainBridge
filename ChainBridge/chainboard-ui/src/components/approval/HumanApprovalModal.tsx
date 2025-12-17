/**
 * HumanApprovalModal (HAM) v1 — Human Approval Interface
 *
 * The ONLY UI path to authorize restricted actions.
 * Produces a signed approval intent with non-repudiable audit trail.
 *
 * TRIGGERS:
 * - Diggi correction plan: verb=ESCALATE, target=human.operator
 * - Backend response: requires_human_approval=true
 *
 * CONSTRAINTS (NON-NEGOTIABLE):
 * - No auto-approve
 * - No "Approve All"
 * - No approval without identity context
 * - No approval without viewing full intent
 * - No edits to the intent being approved
 * - No keyboard-only confirmation for destructive actions
 *
 * @see PAC-DIGGI-04 — Human Approval Modal
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { AlertTriangle, X, ShieldCheck, XCircle, Loader2 } from 'lucide-react';
import { ApprovalErrorBoundary } from './ApprovalErrorBoundary';
import { ImmutableIntentView } from './ImmutableIntentView';
import { RiskDisclosurePanel } from './RiskDisclosurePanel';
import { ApprovalConfirmation } from './ApprovalConfirmation';
import type {
  HumanApprovalContext,
  ApproverIdentity,
  ApprovalIntent,
  RejectionIntent,
  ApprovalModalState,
} from '../../types/approval';
import {
  INITIAL_APPROVAL_STATE,
  validateApprovalContext,
  validateApproverIdentity,
  canSubmitApproval,
  createApprovalIntent,
  createRejectionIntent,
} from '../../types/approval';

// ============================================================
// TYPES
// ============================================================

interface Props {
  /** The approval context — must be validated before display */
  context: HumanApprovalContext;
  /** Current user identity — must be present for approval */
  currentUser: ApproverIdentity | null;
  /** Callback when approval is submitted */
  onApprove: (intent: ApprovalIntent) => Promise<void>;
  /** Callback when user cancels/rejects */
  onCancel: (intent: RejectionIntent | null) => void;
  /** Whether the modal is open */
  isOpen: boolean;
}

// ============================================================
// COMPONENT
// ============================================================

/**
 * Human Approval Modal — strict approval interface.
 *
 * Renders as a modal portal, traps focus until resolved.
 * Close button disabled until completion or explicit cancel.
 * Frontend does NOT execute anything — only emits approval/rejection intent.
 */
export function HumanApprovalModal({
  context,
  currentUser,
  onApprove,
  onCancel,
  isOpen,
}: Props): JSX.Element | null {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<Element | null>(null);

  // Modal state
  const [state, setState] = useState<ApprovalModalState>(INITIAL_APPROVAL_STATE);

  // Validation state
  const [validationError, setValidationError] = useState<string | null>(null);

  // ============================================================
  // VALIDATION — FAIL CLOSED
  // ============================================================

  useEffect(() => {
    if (!isOpen) return;

    // Validate context
    const contextValidation = validateApprovalContext(context);
    if (!contextValidation.valid) {
      setValidationError(`Invalid approval context: ${contextValidation.reason}`);
      return;
    }

    // Validate user identity
    if (!currentUser) {
      setValidationError('Missing user identity. Cannot proceed with approval.');
      return;
    }

    const identityValidation = validateApproverIdentity(currentUser);
    if (!identityValidation.valid) {
      setValidationError(`Invalid user identity: ${identityValidation.reason}`);
      return;
    }

    setValidationError(null);
  }, [isOpen, context, currentUser]);

  // ============================================================
  // FOCUS TRAP
  // ============================================================

  useEffect(() => {
    if (isOpen) {
      // Store previous focus
      previousActiveElement.current = document.activeElement;

      // Focus modal
      if (modalRef.current) {
        modalRef.current.focus();
      }

      // Trap focus
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Tab' && modalRef.current) {
          const focusableElements = modalRef.current.querySelectorAll(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          );
          const firstElement = focusableElements[0] as HTMLElement;
          const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

          if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement?.focus();
          } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement?.focus();
          }
        }

        // Block escape — must use explicit cancel
        if (e.key === 'Escape') {
          e.preventDefault();
        }
      };

      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    } else {
      // Restore focus
      if (previousActiveElement.current instanceof HTMLElement) {
        previousActiveElement.current.focus();
      }
    }
  }, [isOpen]);

  // ============================================================
  // STATE HANDLERS
  // ============================================================

  const handleCheckboxChange = useCallback((checked: boolean) => {
    setState((prev) => ({
      ...prev,
      checkboxChecked: checked,
      // Clear typed confirmation when unchecking
      typedConfirmation: checked ? prev.typedConfirmation : '',
    }));
  }, []);

  const handleTypedConfirmationChange = useCallback((value: string) => {
    setState((prev) => ({
      ...prev,
      typedConfirmation: value,
    }));
  }, []);

  // ============================================================
  // APPROVAL HANDLER
  // ============================================================

  const handleApprove = useCallback(async () => {
    // Guard: cannot submit if prerequisites not met
    if (!canSubmitApproval(state)) {
      return;
    }

    // Guard: duplicate submission
    if (state.hasSubmitted) {
      setState((prev) => ({
        ...prev,
        error: 'Approval already submitted. Duplicate submissions are blocked.',
      }));
      return;
    }

    // Guard: missing identity
    if (!currentUser) {
      setState((prev) => ({
        ...prev,
        error: 'Missing user identity. Cannot submit approval.',
      }));
      return;
    }

    // Create approval intent
    const approvalIntent = createApprovalIntent(context, {
      ...currentUser,
      timestamp: new Date().toISOString(),
    });

    setState((prev) => ({ ...prev, isSubmitting: true, error: null }));

    try {
      await onApprove(approvalIntent);
      setState((prev) => ({ ...prev, hasSubmitted: true, isSubmitting: false }));
    } catch (error) {
      // Network failure — approval aborted, no retry
      setState((prev) => ({
        ...prev,
        isSubmitting: false,
        error: `Approval failed: ${error instanceof Error ? error.message : 'Unknown error'}. No automatic retry.`,
      }));
    }
  }, [state, currentUser, context, onApprove]);

  // ============================================================
  // CANCEL HANDLER
  // ============================================================

  const handleCancel = useCallback(() => {
    if (state.isSubmitting) {
      // Cannot cancel during submission
      return;
    }

    // Create rejection intent if user has identity
    const rejectionIntent = currentUser
      ? createRejectionIntent(
          context,
          { ...currentUser, timestamp: new Date().toISOString() },
          'User cancelled approval'
        )
      : null;

    // Reset state
    setState(INITIAL_APPROVAL_STATE);

    // Notify parent
    onCancel(rejectionIntent);
  }, [state.isSubmitting, currentUser, context, onCancel]);

  // ============================================================
  // RENDER
  // ============================================================

  if (!isOpen) {
    return null;
  }

  const canApprove = canSubmitApproval(state) && !validationError;

  const modalContent = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="ham-title"
      aria-describedby="ham-description"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        ref={modalRef}
        tabIndex={-1}
        className="relative z-10 mx-4 max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-xl border border-slate-700 bg-slate-900 shadow-2xl"
      >
        <ApprovalErrorBoundary>
          {/* Header — Non-Dismissible */}
          <div className="border-b border-slate-700 bg-slate-800/50 px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-500/20">
                <AlertTriangle className="h-5 w-5 text-amber-400" />
              </div>
              <div>
                <h2
                  id="ham-title"
                  className="text-lg font-semibold text-slate-100"
                >
                  ⚠️ Human Approval Required
                </h2>
                <p
                  id="ham-description"
                  className="text-sm text-slate-400"
                >
                  This action cannot proceed without explicit authorization.
                </p>
              </div>
            </div>
          </div>

          {/* Content — Scrollable */}
          <div className="max-h-[60vh] overflow-y-auto p-6 space-y-6">
            {/* Validation Error — Hard Block */}
            {validationError && (
              <div className="rounded-lg border-2 border-red-500 bg-red-950/50 p-4">
                <div className="flex items-start gap-3">
                  <XCircle className="h-5 w-5 flex-shrink-0 text-red-400" />
                  <div>
                    <p className="font-medium text-red-300">Approval Blocked</p>
                    <p className="mt-1 text-sm text-red-200">
                      {validationError}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Section 2: Immutable Intent Summary */}
            <ImmutableIntentView intent={context.intent} />

            {/* Section 3: Risk & Constraints */}
            <RiskDisclosurePanel
              risks={context.risks}
              denialReason={context.denial_reason}
              denialDetail={context.denial_detail}
            />

            {/* Section 4: Explicit Confirmation (Two-Step) */}
            {!validationError && (
              <ApprovalConfirmation
                checkboxChecked={state.checkboxChecked}
                onCheckboxChange={handleCheckboxChange}
                typedConfirmation={state.typedConfirmation}
                onTypedConfirmationChange={handleTypedConfirmationChange}
                disabled={state.isSubmitting || state.hasSubmitted}
              />
            )}

            {/* Submission Error */}
            {state.error && (
              <div className="rounded-lg border border-red-500/50 bg-red-950/30 p-4">
                <div className="flex items-start gap-3">
                  <XCircle className="h-5 w-5 flex-shrink-0 text-red-400" />
                  <p className="text-sm text-red-200">{state.error}</p>
                </div>
              </div>
            )}

            {/* Duplicate Submission Block */}
            {state.hasSubmitted && (
              <div className="rounded-lg border border-emerald-500/50 bg-emerald-950/30 p-4">
                <div className="flex items-start gap-3">
                  <ShieldCheck className="h-5 w-5 flex-shrink-0 text-emerald-400" />
                  <p className="text-sm text-emerald-200">
                    Approval submitted successfully. This modal will close automatically.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Footer — Action Buttons */}
          <div className="border-t border-slate-700 bg-slate-800/30 px-6 py-4">
            <div className="flex items-center justify-end gap-3">
              {/* Cancel Button */}
              <button
                type="button"
                onClick={handleCancel}
                disabled={state.isSubmitting}
                className="
                  flex items-center gap-2 rounded-lg border border-slate-600 px-4 py-2
                  text-sm font-medium text-slate-300
                  transition-colors
                  hover:bg-slate-700 hover:text-slate-100
                  disabled:cursor-not-allowed disabled:opacity-50
                "
              >
                <X className="h-4 w-4" />
                <span>CANCEL</span>
              </button>

              {/* Authorize Button */}
              <button
                type="button"
                onClick={handleApprove}
                disabled={!canApprove}
                className="
                  flex items-center gap-2 rounded-lg px-4 py-2
                  text-sm font-semibold
                  transition-colors
                  disabled:cursor-not-allowed disabled:opacity-50
                  enabled:bg-emerald-600 enabled:text-white enabled:hover:bg-emerald-500
                  disabled:bg-slate-700 disabled:text-slate-500
                "
              >
                {state.isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>AUTHORIZING...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="h-4 w-4" />
                    <span>AUTHORIZE ACTION</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </ApprovalErrorBoundary>
      </div>
    </div>
  );

  // Render as portal
  return createPortal(modalContent, document.body);
}

// ============================================================
// RE-EXPORTS
// ============================================================

export { ApprovalErrorBoundary } from './ApprovalErrorBoundary';
export { ImmutableIntentView } from './ImmutableIntentView';
export { RiskDisclosurePanel } from './RiskDisclosurePanel';
export { ApprovalConfirmation } from './ApprovalConfirmation';
export type {
  HumanApprovalContext,
  ApproverIdentity,
  ApprovalIntent,
  RejectionIntent,
  ApprovalModalState,
} from '../../types/approval';
