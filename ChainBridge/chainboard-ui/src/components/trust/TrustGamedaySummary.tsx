/**
 * Trust Gameday Summary — PAC-TRUST-CENTER-01
 *
 * Displays adversarial testing summary.
 * Read-only — text display only, no charts or controls.
 *
 * CONSTRAINTS:
 * - Display text only
 * - No charts
 * - No metrics visualization
 * - No interpretation
 *
 * @see PAC-TRUST-CENTER-01 — Public Trust Center (Read-Only)
 */

import { FlaskConical } from 'lucide-react';

import { classNames } from '../../utils/classNames';
import { Card, CardContent, CardHeader } from '../ui/Card';
import { TrustEmptyState } from './TrustEmptyState';
import type { GamedaySummary } from '../../types/trust';

export interface TrustGamedaySummaryProps {
  /** Gameday test results */
  gameday?: GamedaySummary;
  /** Optional additional className */
  className?: string;
}

/**
 * Adversarial testing summary display.
 * Shows PAC-GOV-GAMEDAY-01 results as text.
 */
export function TrustGamedaySummary({
  gameday,
  className,
}: TrustGamedaySummaryProps): JSX.Element {
  // Missing data → explicit empty state
  if (!gameday) {
    return <TrustEmptyState section="Adversarial Testing" className={className} />;
  }

  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardHeader className="border-b border-slate-800/50">
        <div className="flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Adversarial Testing Summary
          </h3>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Text-only display — no charts, no visualization */}
        <ul className="space-y-2">
          <li className="flex items-center gap-2 text-sm text-slate-300">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-500 flex-shrink-0" />
            {gameday.scenarios_tested} adversarial scenarios tested
          </li>
          <li className="flex items-center gap-2 text-sm text-slate-300">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-500 flex-shrink-0" />
            {gameday.silent_failures} silent failures
          </li>
          <li className="flex items-center gap-2 text-sm text-slate-300">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-500 flex-shrink-0" />
            {gameday.fail_closed_all ? 'Fail-closed in all cases' : 'Fail-closed status: incomplete'}
          </li>
        </ul>

        {/* Source reference */}
        <p className="text-xs text-slate-600 italic border-t border-slate-800/50 pt-3">
          Source: PAC-GOV-GAMEDAY-01
        </p>
      </CardContent>
    </Card>
  );
}
