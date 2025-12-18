/**
 * Governance Timeline Empty State — PAC-SONNY-02
 *
 * Rendered only when events.length === 0.
 * Text is exact, no marketing or embellishment.
 *
 * CONSTRAINTS:
 * - No buttons
 * - No actions
 * - No suggestions
 * - Exact text only
 *
 * @see PAC-SONNY-02 — Governance Timeline (Read-Only) UI
 */

import { FileText } from 'lucide-react';

import { classNames } from '../../utils/classNames';

export interface GovernanceTimelineEmptyStateProps {
  /** Optional additional className */
  className?: string;
}

/**
 * Empty state for governance timeline.
 * Text is exact per PAC specification.
 */
export function GovernanceTimelineEmptyState({
  className,
}: GovernanceTimelineEmptyStateProps): JSX.Element {
  return (
    <div
      className={classNames(
        'flex flex-col items-center justify-center py-12 text-center',
        className
      )}
    >
      <FileText className="h-12 w-12 text-slate-600 mb-4" />
      {/* Exact text — no marketing */}
      <p className="text-sm text-slate-500">
        No governance events recorded.
      </p>
    </div>
  );
}
