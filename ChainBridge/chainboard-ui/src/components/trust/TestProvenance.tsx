/**
 * Test Provenance — PAC-SONNY-TRUST-UI-REDUCTION-01
 *
 * Displays test suite status (boolean only).
 * Links to test directories.
 *
 * CONSTRAINTS:
 * - Boolean pass status only
 * - No counts, percentages, coverage metrics
 * - Link to test directories
 *
 * @see PAC-SONNY-TRUST-UI-REDUCTION-01
 */

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';

export interface TestSuite {
  /** Suite name */
  name: string;
  /** Directory path */
  path: string;
  /** Recorded status — boolean only, no interpretation */
  recorded: boolean;
}

export interface TestProvenanceProps {
  /** Test suites to display */
  suites?: TestSuite[];
  /** Optional className */
  className?: string;
}

/**
 * Default test suites — UNLINKED / DEMO DATA.
 * In production, these must be fetched from backend.
 */
const DEFAULT_SUITES: TestSuite[] = [
  { name: 'Governance', path: 'tests/governance/', recorded: true },
  { name: 'Security', path: 'tests/security/', recorded: true },
  { name: 'Scope Guard', path: 'tests/scope_guard/', recorded: true },
  { name: 'OCC', path: 'tests/occ/', recorded: true },
  { name: 'ChainBoard', path: 'tests/chainboard/', recorded: true },
  { name: 'Agents', path: 'tests/agents/', recorded: true },
];

/**
 * Test Provenance section.
 * Shows test suite status — boolean only.
 */
export function TestProvenance({
  suites,
  className,
}: TestProvenanceProps): JSX.Element {
  const items = suites ?? DEFAULT_SUITES;

  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardContent className="space-y-4">
        {/* Section header — factual format */}
        <div className="border-b border-slate-800/50 pb-3">
          <p className="text-xs text-slate-500 uppercase tracking-wider">
            Artifact
          </p>
          <p className="text-sm text-slate-300">Test Provenance</p>
        </div>

        {/* What this shows */}
        <div className="border-b border-slate-800/50 pb-3">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
            What this shows
          </p>
          <p className="text-sm text-slate-400">
            Test suite record status at build time.
          </p>
        </div>

        {/* UNLINKED warning for demo data */}
        {!suites && (
          <div className="border border-slate-600 bg-slate-900/50 px-3 py-2 text-xs text-slate-400 font-mono">
            UNLINKED / DEMO DATA — Not linked to live backend
          </div>
        )}

        {/* Test suite list — boolean status only */}
        <ul className="space-y-2 pt-2">
          {items.map((suite) => (
            <li
              key={suite.path}
              className="flex items-center justify-between text-sm"
            >
              <div>
                <span className="text-slate-300">{suite.name}</span>
                <span className="text-slate-600 font-mono text-xs ml-2">
                  {suite.path}
                </span>
              </div>
              <span className="text-slate-500 text-xs font-mono">
                {suite.recorded ? 'recorded' : 'absent'}
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
