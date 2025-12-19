/**
 * Trust Coverage List — PAC-TRUST-CENTER-01
 *
 * Displays governance coverage as presence indicators.
 * Read-only — no metrics, no counts, no charts.
 *
 * CONSTRAINTS:
 * - Render presence only (✔ / present)
 * - No metrics, counts, or charts
 * - No interpretation
 *
 * @see PAC-TRUST-CENTER-01 — Public Trust Center (Read-Only)
 */

import { classNames } from '../../utils/classNames';
import { Card, CardContent, CardHeader } from '../ui/Card';
import { TrustEmptyState } from './TrustEmptyState';
import type { GovernanceCoverageItem } from '../../types/trust';

export interface TrustCoverageListProps {
  /** Coverage items to display */
  coverage?: GovernanceCoverageItem[];
  /** Optional additional className */
  className?: string;
}

/**
 * Default coverage items if not provided.
 * These represent the documented governance capabilities.
 */
const DEFAULT_COVERAGE_ITEMS: GovernanceCoverageItem[] = [
  { feature_id: 'acm', name: 'ACM enforcement', present: true },
  { feature_id: 'drcp', name: 'DRCP escalation', present: true },
  { feature_id: 'diggi', name: 'Diggi corrections', present: true },
  { feature_id: 'artifact', name: 'Artifact reference', present: true },
  { feature_id: 'scope', name: 'Scope guard enforcement', present: true },
  { feature_id: 'failclosed', name: 'Fail-closed execution binding', present: true },
];

/**
 * Single coverage item row.
 * Presence indicator only — no metrics.
 */
function CoverageItem({
  item,
}: {
  item: GovernanceCoverageItem;
}): JSX.Element {
  return (
    <li className="flex items-center gap-3 py-2">
      {/* Presence indicator — neutral text, no icons */}
      <span className="text-xs text-slate-500 font-mono w-16">
        {item.present ? 'present' : 'absent'}
      </span>
      <span
        className={classNames(
          'text-sm',
          item.present ? 'text-slate-300' : 'text-slate-500'
        )}
      >
        {item.name}
      </span>
    </li>
  );
}

/**
 * Governance coverage list.
 * Shows presence of governance capabilities.
 */
export function TrustCoverageList({
  coverage,
  className,
}: TrustCoverageListProps): JSX.Element {
  // Use default items if not provided
  const items = coverage ?? DEFAULT_COVERAGE_ITEMS;
  const isDemo = !coverage;

  // If explicitly empty array, show empty state
  if (coverage && coverage.length === 0) {
    return <TrustEmptyState section="Governance Coverage" className={className} />;
  }

  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardHeader className="border-b border-slate-800/50">
        <p className="text-xs text-slate-600 uppercase tracking-wider">
          coverage_by_trust_area
        </p>
      </CardHeader>

      <CardContent>
        {isDemo && (
          <div className="border border-slate-600 bg-slate-900/50 px-3 py-2 text-xs text-slate-400 font-mono mb-3">
            UNLINKED / DEMO DATA — Not linked to live backend
          </div>
        )}
        <div className="divide-y divide-slate-800/30">
          {items.map((item) => (
            <CoverageItem key={item.feature_id} item={item} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
