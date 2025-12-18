/**
 * Adversarial Testing — PAC-SONNY-TRUST-MIN-UI-01
 *
 * Literal data only. No interpretation.
 *
 * Fields:
 * - Number of tests
 * - Last execution timestamp
 * - Test suite location
 *
 * @see PAC-SONNY-TRUST-MIN-UI-01
 */

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';

export interface AdversarialTestingProps {
  testCount?: number;
  lastRun?: string;
  suiteLocation?: string;
  className?: string;
}

export function AdversarialTesting({
  testCount,
  lastRun,
  suiteLocation = 'tests/governance/gameday/',
  className,
}: AdversarialTestingProps): JSX.Element {
  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardContent className="space-y-3">
        <p className="text-xs text-slate-600 uppercase tracking-wider border-b border-slate-800/50 pb-2">
          Adversarial Testing
        </p>

        <div>
          <p className="text-xs text-slate-600 mb-1">Test Count</p>
          <p className="text-sm text-slate-300 font-mono">
            {testCount ?? '—'}
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-600 mb-1">Last Recorded (UTC)</p>
          <p className="text-sm text-slate-300 font-mono">
            {lastRun ?? '—'}
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-600 mb-1">Suite Location</p>
          <p className="text-sm text-slate-300 font-mono">
            {suiteLocation}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
