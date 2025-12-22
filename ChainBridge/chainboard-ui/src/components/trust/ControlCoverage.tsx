/**
 * Control Coverage — PAC-TRUST-CENTER-UI-01
 *
 * Visual checklist of governance controls.
 * Boolean status only — no percentages, SLAs, or trends.
 *
 * CONSTRAINTS:
 * - Read-only
 * - Boolean status only (✅ Enforced / Unavailable)
 * - No percentages
 * - No SLAs
 * - No trend lines
 *
 * @see PAC-TRUST-CENTER-UI-01 — Customer Trust Center (Read-Only)
 */

import { classNames } from '../../utils/classNames';
import { Card, CardContent, CardHeader } from '../ui/Card';

export interface ControlCoverageItem {
  /** Control identifier */
  id: string;
  /** Customer-friendly control name */
  name: string;
  /** Status label */
  status: string;
  /** Whether control is active */
  active: boolean;
}

export interface ControlCoverageProps {
  /** Coverage items from GET /trust/coverage */
  coverage?: ControlCoverageItem[];
  /** Optional additional className */
  className?: string;
}

/**
 * Default coverage items per PAC specification.
 */
const DEFAULT_COVERAGE: ControlCoverageItem[] = [
  { id: 'acm', name: 'Access Control (ACM)', status: 'present', active: true },
  { id: 'drcp', name: 'Decision Routing (DRCP)', status: 'present', active: true },
  { id: 'diggi', name: 'Agent Constraints (DIGGI)', status: 'present', active: true },
  { id: 'artifact', name: 'Artifact Reference', status: 'present', active: true },
  { id: 'scope', name: 'Scope Enforcement', status: 'present', active: true },
  { id: 'failclosed', name: 'Fail-Closed Execution', status: 'present', active: true },
];

/**
 * Single control row — boolean status display.
 */
function ControlRow({ item }: { item: ControlCoverageItem }): JSX.Element {
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-800/30 last:border-b-0">
      <span className="text-sm text-slate-300">{item.name}</span>
      <span className="text-sm text-slate-400 font-mono">
        {item.active ? item.status : 'absent'}
      </span>
    </div>
  );
}

/**
 * Control Coverage section.
 * Customer-facing checklist of governance controls.
 */
export function ControlCoverage({
  coverage,
  className,
}: ControlCoverageProps): JSX.Element {
  const items = coverage ?? DEFAULT_COVERAGE;
  const isDemo = !coverage;

  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardHeader className="border-b border-slate-800/50">
        <p className="text-xs text-slate-600 uppercase tracking-wider">
          control_coverage
        </p>
      </CardHeader>

      <CardContent className="py-2">
        {isDemo && (
          <div className="border border-slate-600 bg-slate-900/50 px-3 py-2 text-xs text-slate-400 font-mono mb-3">
            UNLINKED / DEMO DATA — Not linked to live backend
          </div>
        )}
        {items.map((item) => (
          <ControlRow key={item.id} item={item} />
        ))}
      </CardContent>
    </Card>
  );
}
