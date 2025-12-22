/**
 * Gameday Status — PAC-TRUST-CENTER-UI-01
 *
 * Adversarial testing statement with live facts.
 * Customer-safe language — no technical jargon.
 *
 * CONSTRAINTS:
 * - Read-only
 * - Static statement + live facts
 * - No charts or visualizations
 * - Customer-safe language
 *
 * @see PAC-TRUST-CENTER-UI-01 — Customer Trust Center (Read-Only)
 */

import { classNames } from '../../utils/classNames';
import { Card, CardContent, CardHeader } from '../ui/Card';
import type { GamedaySummary } from '../../types/trust';

export interface GamedayStatusProps {
  /** Gameday summary from GET /trust/gameday */
  gameday?: GamedaySummary;
  /** Optional additional className */
  className?: string;
}

/**
 * Gameday Status section.
 * Adversarial testing results in customer-friendly format.
 */
export function GamedayStatus({
  gameday,
  className,
}: GamedayStatusProps): JSX.Element {
  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardHeader className="border-b border-slate-800/50">
        <p className="text-xs text-slate-600 uppercase tracking-wider">
          adversarial_testing
        </p>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Demo data warning */}
        {!gameday && (
          <div className="border border-slate-600 bg-slate-900/50 px-3 py-2 text-xs text-slate-400 font-mono">
            UNLINKED / DEMO DATA — Not linked to live backend
          </div>
        )}

        {/* Data fields only — no marketing copy */}
        <div className="space-y-3 font-mono text-sm">
          <div className="flex justify-between">
            <span className="text-slate-600">scenarios_tested:</span>
            <span className="text-slate-400">{gameday?.scenarios_tested ?? '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-600">silent_failures:</span>
            <span className="text-slate-400">{gameday?.silent_failures ?? '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-600">fail_closed_all:</span>
            <span className="text-slate-400">{gameday?.fail_closed_all ? 'true' : 'false'}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
