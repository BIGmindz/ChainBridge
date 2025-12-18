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

import { Shield, Check } from 'lucide-react';

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
  { feature_id: 'artifact', name: 'Artifact integrity verification', present: true },
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
      {/* Presence indicator — neutral styling, no red/green judgment */}
      <span
        className={classNames(
          'flex h-5 w-5 items-center justify-center rounded-full flex-shrink-0',
          item.present
            ? 'bg-slate-700/50 text-slate-300'
            : 'bg-slate-800/50 text-slate-600'
        )}
      >
        {item.present && <Check className="h-3 w-3" />}
      </span>
      <span
        className={classNames(
          'text-sm',
          item.present ? 'text-slate-300' : 'text-slate-500'
        )}
      >
        {item.name}
      </span>
      {item.present && (
        <span className="text-xs text-slate-600 ml-auto">present</span>
      )}
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

  // If explicitly empty array, show empty state
  if (coverage && coverage.length === 0) {
    return <TrustEmptyState section="Governance Coverage" className={className} />;
  }

  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardHeader className="border-b border-slate-800/50">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Governance Coverage
          </h3>
        </div>
      </CardHeader>

      <CardContent>
        <ul className="divide-y divide-slate-800/30">
          {items.map((item) => (
            <CoverageItem key={item.feature_id} item={item} />
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
