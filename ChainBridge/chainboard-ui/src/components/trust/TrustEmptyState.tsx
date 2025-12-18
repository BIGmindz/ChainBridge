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

import { FileQuestion } from 'lucide-react';

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
 */
export function TrustEmptyState({
  section,
  className,
}: TrustEmptyStateProps): JSX.Element {
  return (
    <div
      className={classNames(
        'flex items-center gap-3 rounded-lg border border-slate-700/50 bg-slate-800/30 px-4 py-4',
        className
      )}
    >
      <FileQuestion className="h-5 w-5 text-slate-500 flex-shrink-0" />
      <div>
        <p className="text-sm text-slate-400">
          {section} data unavailable
        </p>
        <p className="text-xs text-slate-600 mt-0.5">
          This section cannot be displayed at this time
        </p>
      </div>
    </div>
  );
}
