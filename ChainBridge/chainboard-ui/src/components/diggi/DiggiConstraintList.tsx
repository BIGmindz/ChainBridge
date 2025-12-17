/**
 * Diggi Constraint List — CRC v1
 *
 * Read-only list of constraints explaining why an action was denied.
 * Renders backend constraints verbatim with no modification.
 *
 * CONSTRAINTS:
 * - Renders constraints exactly as received
 * - No sorting or reordering
 * - No editing capability
 * - No inline actions
 *
 * @see PAC-DIGGI-03 — Correction Rendering Contract
 */

import { AlertCircle } from 'lucide-react';

import { classNames } from '../../utils/classNames';
import type { DiggiConstraintListProps } from '../../types/diggi';

/**
 * Renders a read-only list of constraints.
 * Each constraint is displayed as a bullet point with warning styling.
 */
export function DiggiConstraintList({
  constraints,
  className,
}: DiggiConstraintListProps): JSX.Element {
  if (!constraints || constraints.length === 0) {
    return (
      <div className={classNames('text-sm text-slate-500 italic', className)}>
        No constraints provided
      </div>
    );
  }

  return (
    <div className={classNames('space-y-2', className)}>
      <div className="flex items-center gap-2 mb-3">
        <AlertCircle className="h-4 w-4 text-amber-400" />
        <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-300">
          Constraints
        </h4>
      </div>
      <ul className="space-y-2">
        {constraints.map((constraint, index) => (
          <li
            key={index}
            className="flex items-start gap-2 text-sm text-slate-300"
          >
            <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-amber-500/60" />
            <span className="leading-relaxed">{constraint}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
