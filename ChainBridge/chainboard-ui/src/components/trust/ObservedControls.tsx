/**
 * Observed Controls — PAC-SONNY-TRUST-UI-REDUCTION-01
 *
 * Displays control presence only.
 * "present" = code exists AND tests pass
 *
 * CONSTRAINTS:
 * - Presence only (present / absent)
 * - No counts, percentages, scores
 * - No icons (no checkmarks, shields, locks)
 * - No "Enforced", "Active", "Enabled" — just "present"
 *
 * @see PAC-SONNY-TRUST-UI-REDUCTION-01
 */

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';

export interface ObservedControl {
  /** Control identifier */
  id: string;
  /** Control name — factual, no adjectives */
  name: string;
  /** Test suite that validates this control */
  test_suite: string;
  /** Presence: code exists AND tests pass */
  present: boolean;
}

export interface ObservedControlsProps {
  /** Controls to display */
  controls?: ObservedControl[];
  /** Optional className */
  className?: string;
}

/**
 * Default controls mapped to test suites.
 */
const DEFAULT_CONTROLS: ObservedControl[] = [
  {
    id: 'identity',
    name: 'Identity enforcement',
    test_suite: 'tests/governance/test_acm_evaluator.py',
    present: true,
  },
  {
    id: 'scope',
    name: 'Scope enforcement',
    test_suite: 'tests/governance/test_atlas_scope.py',
    present: true,
  },
  {
    id: 'artifact',
    name: 'Artifact verification',
    test_suite: 'tests/governance/test_governance_fingerprint.py',
    present: true,
  },
  {
    id: 'drift',
    name: 'Drift detection',
    test_suite: 'tests/governance/test_boot_checks.py',
    present: true,
  },
];

/**
 * Observed Controls section.
 * Presence only — no metrics.
 */
export function ObservedControls({
  controls,
  className,
}: ObservedControlsProps): JSX.Element {
  const items = controls ?? DEFAULT_CONTROLS;
  const isDemo = !controls;

  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardContent className="space-y-4">
        {/* Demo data warning */}
        {isDemo && (
          <div className="border border-slate-600 bg-slate-900/50 px-3 py-2 text-xs text-slate-400 font-mono">
            UNLINKED / DEMO DATA — Not linked to live backend
          </div>
        )}

        {/* Section header — neutralized */}
        <div className="border-b border-slate-800/50 pb-3">
          <p className="text-xs text-slate-600 uppercase tracking-wider">
            observed_controls
          </p>
        </div>

        {/* Control list — presence only */}
        <div className="space-y-3 pt-2 font-mono text-sm">
          {items.map((control) => (
            <div key={control.id}>
              <div className="flex items-baseline justify-between">
                <span className="text-slate-400">{control.id}:</span>
                <span className="text-slate-500">
                  {control.present ? 'present' : 'absent'}
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                {control.test_suite}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
