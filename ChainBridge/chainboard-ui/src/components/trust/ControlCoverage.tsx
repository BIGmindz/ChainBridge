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

import { Check, Shield } from 'lucide-react';

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
  { id: 'acm', name: 'Access Control (ACM)', status: 'Enforced', active: true },
  { id: 'drcp', name: 'Decision Routing (DRCP)', status: 'Active', active: true },
  { id: 'diggi', name: 'Agent Constraints (DIGGI)', status: 'Enabled', active: true },
  { id: 'artifact', name: 'Artifact Verification', status: 'Required', active: true },
  { id: 'scope', name: 'Scope Enforcement', status: 'Enforced', active: true },
  { id: 'failclosed', name: 'Fail-Closed Execution', status: 'Enforced', active: true },
];

/**
 * Single control row — boolean status display.
 */
function ControlRow({ item }: { item: ControlCoverageItem }): JSX.Element {
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-800/30 last:border-b-0">
      <span className="text-sm text-slate-300">{item.name}</span>
      <div className="flex items-center gap-2">
        {item.active ? (
          <>
            <Check className="h-4 w-4 text-slate-400" />
            <span className="text-sm text-slate-400">{item.status}</span>
          </>
        ) : (
          <span className="text-sm text-slate-600">Unavailable</span>
        )}
      </div>
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

  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardHeader className="border-b border-slate-800/50">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Control Coverage
          </h3>
        </div>
      </CardHeader>

      <CardContent className="py-2">
        {items.map((item) => (
          <ControlRow key={item.id} item={item} />
        ))}
      </CardContent>
    </Card>
  );
}
