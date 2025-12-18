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

import { FlaskConical } from 'lucide-react';

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
        <div className="flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Adversarial Testing
          </h3>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Customer-safe static statement */}
        <p className="text-sm text-slate-400 leading-relaxed">
          ChainBridge governance controls are continuously validated using adversarial
          test scenarios designed to simulate misuse, escalation, and tampering.
        </p>

        {/* Live facts — no charts, no trends */}
        <div className="grid grid-cols-3 gap-4 py-2">
          <div className="text-center">
            <p className="text-2xl font-semibold text-slate-200">
              {gameday?.scenarios_tested ?? '—'}
            </p>
            <p className="text-xs text-slate-500 uppercase tracking-wider mt-1">
              Scenarios Tested
            </p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-semibold text-slate-200">
              {gameday?.silent_failures ?? '—'}
            </p>
            <p className="text-xs text-slate-500 uppercase tracking-wider mt-1">
              Silent Failures
            </p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-semibold text-slate-200">
              {gameday?.fail_closed_all ? 'Yes' : '—'}
            </p>
            <p className="text-xs text-slate-500 uppercase tracking-wider mt-1">
              Fail-Closed
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
