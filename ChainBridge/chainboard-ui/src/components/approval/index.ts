/**
 * Human Approval Modal (HAM) v1 — Component Index
 *
 * @see PAC-DIGGI-04 — Human Approval Modal
 */

// Main modal component
export { HumanApprovalModal } from './HumanApprovalModal';

// Sub-components
export { ApprovalConfirmation } from './ApprovalConfirmation';
export { ApprovalErrorBoundary } from './ApprovalErrorBoundary';
export { ImmutableIntentView } from './ImmutableIntentView';
export { RiskDisclosurePanel } from './RiskDisclosurePanel';

// Types (re-exported from types/approval.ts)
export type {
  CanonicalIntent,
  HumanApprovalContext,
  ApproverIdentity,
  ApprovalIntent,
  RejectionIntent,
  ApprovalModalState,
  ApprovalValidationResult,
} from '../../types/approval';

// Constants and utilities
export {
  INITIAL_APPROVAL_STATE,
  REQUIRED_CONFIRMATION_PHRASE,
  validateApprovalContext,
  validateApproverIdentity,
  isConfirmationValid,
  canSubmitApproval,
  createApprovalIntent,
  createRejectionIntent,
  isHumanApprovalContext,
  isApproverIdentity,
  isHumanEscalationStep,
} from '../../types/approval';
