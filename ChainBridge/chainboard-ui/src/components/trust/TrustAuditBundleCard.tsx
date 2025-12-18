/**
 * Trust Audit Bundle Card — PAC-TRUST-CENTER-01
 *
 * Displays latest audit bundle metadata.
 * Read-only — shows bundle ID, hash, timestamp, and verification command.
 *
 * CONSTRAINTS:
 * - Display only: bundle ID, timestamp, hash, status
 * - Include static verification snippet
 * - No buttons or controls
 *
 * @see PAC-TRUST-CENTER-01 — Public Trust Center (Read-Only)
 */

import { Archive, CheckCircle2, Clock, AlertCircle } from 'lucide-react';

import { classNames } from '../../utils/classNames';
import { Card, CardContent, CardHeader } from '../ui/Card';
import { TrustEmptyState } from './TrustEmptyState';
import type { AuditBundleMetadata } from '../../types/trust';

export interface TrustAuditBundleCardProps {
  /** Audit bundle metadata */
  bundle?: AuditBundleMetadata;
  /** Optional additional className */
  className?: string;
}

/**
 * Status display configuration.
 */
const statusConfig = {
  'offline-verifiable': {
    icon: CheckCircle2,
    text: 'Offline-verifiable',
    color: 'text-slate-300',
  },
  pending: {
    icon: Clock,
    text: 'Pending',
    color: 'text-slate-400',
  },
  unavailable: {
    icon: AlertCircle,
    text: 'Unavailable',
    color: 'text-slate-500',
  },
};

/**
 * Audit bundle metadata display card.
 * Shows latest audit export information.
 */
export function TrustAuditBundleCard({
  bundle,
  className,
}: TrustAuditBundleCardProps): JSX.Element {
  // Missing data → explicit empty state
  if (!bundle) {
    return <TrustEmptyState section="Audit Bundle" className={className} />;
  }

  const status = statusConfig[bundle.status];
  const StatusIcon = status.icon;

  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardHeader className="border-b border-slate-800/50">
        <div className="flex items-center gap-2">
          <Archive className="h-5 w-5 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Latest Audit Bundle
          </h3>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Bundle ID */}
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
            Bundle ID
          </p>
          <p className="text-sm text-slate-300 font-mono">
            {bundle.bundle_id}
          </p>
        </div>

        {/* Metadata grid */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
              Created
            </p>
            <time
              dateTime={bundle.created_at}
              className="text-sm text-slate-400 font-mono"
            >
              {bundle.created_at}
            </time>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
              Status
            </p>
            <div className="flex items-center gap-1.5">
              <StatusIcon className={classNames('h-4 w-4', status.color)} />
              <span className={classNames('text-sm', status.color)}>
                {status.text}
              </span>
            </div>
          </div>
        </div>

        {/* Bundle hash */}
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
            Bundle Hash
          </p>
          <p className="text-sm text-slate-400 font-mono break-all">
            {bundle.bundle_hash}
          </p>
        </div>

        {/* Verification command — static snippet */}
        <div className="border-t border-slate-800/50 pt-3">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">
            Verification Command
          </p>
          <pre className="text-xs text-slate-400 font-mono bg-slate-900/50 rounded px-3 py-2 overflow-x-auto">
            python verify_audit_bundle.py &lt;bundle&gt;
          </pre>
        </div>
      </CardContent>
    </Card>
  );
}
