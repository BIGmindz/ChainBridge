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
        <p className="text-xs text-slate-600 uppercase tracking-wider">
          Adversarial Testing Records
        </p>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Text-only display — no charts, no visualization, no bullets */}
        <div className="space-y-2 font-mono text-sm">
          <div className="text-slate-400">
            <span className="text-slate-600">scenarios_tested:</span> {gameday.scenarios_tested}
          </div>
          <div className="text-slate-400">
            <span className="text-slate-600">silent_failures:</span> {gameday.silent_failures}
          </div>
          <div className="text-slate-400">
            <span className="text-slate-600">fail_closed_all:</span> {gameday.fail_closed_all ? 'true' : 'false'}
          </div>
        </div>

        {/* Source reference */}
        <p className="text-xs text-slate-600 font-mono border-t border-slate-800/50 pt-3">
          source: PAC-GOV-GAMEDAY-01
        </p>
      </CardContent>
    </Card>
  );
}
