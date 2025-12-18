/**
 * Diggi Components — CRC v1 + PAC-DIGGI-05-FE
 *
 * Correction Rendering Contract components for ChainBoard.
 * These components render governance denial responses with bounded next steps.
 *
 * @see PAC-DIGGI-03 — Correction Rendering Contract
 * @see PAC-DIGGI-05-FE — Diggi Operator UX
 */

export { DiggiDenialPanel } from './DiggiDenialPanel';
export { DiggiConstraintList } from './DiggiConstraintList';
export { DiggiNextStepButton } from './DiggiNextStepButton';
export { DiggiErrorBoundary } from './DiggiErrorBoundary';

// PAC-DIGGI-05-FE additions
export {
  DiggiCorrectionPanel,
  type DiggiCorrectionPanelProps,
} from './DiggiCorrectionPanel';
