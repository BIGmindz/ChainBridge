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

  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardContent className="space-y-4">
        {/* Section header — factual format */}
        <div className="border-b border-slate-800/50 pb-3">
          <p className="text-xs text-slate-500 uppercase tracking-wider">
            Artifact
          </p>
          <p className="text-sm text-slate-300">Observed Controls</p>
        </div>

        {/* What this shows */}
        <div className="border-b border-slate-800/50 pb-3">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
            What this shows
          </p>
          <p className="text-sm text-slate-400">
            Controls where code exists and tests pass.
          </p>
        </div>

        {/* Control list — presence only */}
        <ul className="space-y-3 pt-2">
          {items.map((control) => (
            <li key={control.id} className="text-sm">
              <div className="flex items-baseline justify-between">
                <span className="text-slate-300">{control.name}</span>
                <span className="text-slate-500 text-xs">
                  {control.present ? 'present' : 'absent'}
                </span>
              </div>
              <p className="text-xs text-slate-600 font-mono mt-0.5">
                {control.test_suite}
              </p>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
