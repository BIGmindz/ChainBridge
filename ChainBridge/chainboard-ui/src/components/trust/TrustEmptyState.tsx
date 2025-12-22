/**
 * Trust Empty State — PAC-TRUST-CENTER-01
 *
 * Explicit empty state for Trust Center sections.
 * Rendered when data is missing or unavailable.
 *
 * CONSTRAINTS:
 * - No buttons
 * - No retry affordance
 * - No interpretation
 * - Exact text only
 *
 * @see PAC-TRUST-CENTER-01 — Public Trust Center (Read-Only)
 */

import { classNames } from '../../utils/classNames';

export interface TrustEmptyStateProps {
  /** Section name for context */
  section: string;
  /** Optional additional className */
  className?: string;
}

/**
 * Empty state component for Trust Center sections.
 * Displays when data is missing or unavailable.
 * No icons. No semantic colors. Neutral text only.
 */
export function TrustEmptyState({
  section,
  className,
}: TrustEmptyStateProps): JSX.Element {
  return (
    <div
      className={classNames(
        'border border-slate-700/50 bg-slate-800/30 px-4 py-4',
        className
      )}
    >
      <p className="text-sm text-slate-400 font-mono">
        {section}: No data available
      </p>
    </div>
  );
}
