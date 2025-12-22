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

import { Link } from 'react-router-dom';

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';

export interface AdversarialTestingProps {
  testCount?: number;
  lastRun?: string;
  suiteLocation?: string;
  /** Optional artifact ID for ProofPack navigation */
  artifactId?: string;
  className?: string;
}

export function AdversarialTesting({
  testCount,
  lastRun,
  suiteLocation = 'tests/governance/gameday/',
  artifactId,
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

        {artifactId ? (
          <div className="border-t border-slate-800/50 pt-3">
            <Link
              to={`/proof-artifacts/${artifactId}`}
              className="text-xs text-slate-400 hover:text-slate-200 font-mono"
            >
              View Proof →
            </Link>
          </div>
        ) : (
          <div className="border-t border-slate-800/50 pt-3">
            <p className="text-xs text-slate-600 font-mono">No ProofPack linked</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
