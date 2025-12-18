/**
 * Governance Risk Badge — PAC-SONNY-03
 *
 * Non-interactive visual element for risk signal display.
 * INFORMATIONAL ONLY — does not affect decision.
 *
 * CONSTRAINTS:
 * - No buttons
 * - No color implying "good / bad outcome"
 * - Risk is informational only
 * - Governance decision remains primary
 * - No implied authority
 *
 * @see PAC-SONNY-03 — Risk Annotation (Read-Only)
 */

import { Info } from 'lucide-react';

import { classNames } from '../../utils/classNames';

export interface GovernanceRiskBadgeProps {
  /** Risk category — rendered verbatim */
  category: string;
  /** Optional additional className */
  className?: string;
}

/**
 * Non-interactive risk signal badge.
 * Visual indicator only — no authority implied.
 */
export function GovernanceRiskBadge({
  category,
  className,
}: GovernanceRiskBadgeProps): JSX.Element {
  return (
    <span
      className={classNames(
        'inline-flex items-center gap-1.5 rounded px-2 py-0.5',
        'bg-slate-700/50 border border-slate-600/50',
        'text-xs text-slate-400',
        className
      )}
      // Explicitly not a button — no role="button"
      aria-label={`Risk signal: ${category}`}
    >
      <Info className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
      <span className="uppercase tracking-wider font-medium">RISK SIGNAL</span>
      <span className="text-slate-500">|</span>
      <span className="font-mono">{category}</span>
    </span>
  );
}

/**
 * Informational disclaimer shown with risk annotations.
 * Makes clear that risk does not affect decision.
 */
export function GovernanceRiskDisclaimer({
  className,
}: {
  className?: string;
}): JSX.Element {
  return (
    <p
      className={classNames(
        'text-xs text-slate-600 italic',
        className
      )}
    >
      Informational — does not affect decision
    </p>
  );
}
