/**
 * Trust Overview — PAC-TRUST-CENTER-UI-01
 *
 * Top section of customer-facing Trust Center.
 * Static copy + live data from API.
 *
 * CONSTRAINTS:
 * - Read-only
 * - No controls
 * - No AI claims
 * - Customer-safe language
 *
 * @see PAC-TRUST-CENTER-UI-01 — Customer Trust Center (Read-Only)
 */

import { Shield } from 'lucide-react';

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';
import type { GovernanceFingerprint, AuditBundleMetadata, GamedaySummary } from '../../types/trust';

export interface TrustOverviewProps {
  /** Governance fingerprint from GET /trust/fingerprint */
  fingerprint?: GovernanceFingerprint;
  /** Latest audit bundle from GET /trust/audit/latest */
  auditBundle?: AuditBundleMetadata;
  /** Gameday summary from GET /trust/gameday */
  gameday?: GamedaySummary;
  /** Optional additional className */
  className?: string;
}

/**
 * Trust Overview section.
 * Customer-safe static copy + live governance data.
 */
export function TrustOverview({
  fingerprint,
  auditBundle,
  gameday,
  className,
}: TrustOverviewProps): JSX.Element {
  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardContent className="py-8">
        {/* Header with shield icon */}
        <div className="flex items-center gap-3 mb-6">
          <Shield className="h-10 w-10 text-slate-400" />
          <h2 className="text-xl font-semibold text-slate-200">
            Governance Overview
          </h2>
        </div>

        {/* Customer-safe static copy */}
        <p className="text-base text-slate-300 leading-relaxed mb-8 max-w-2xl">
          ChainBridge operates with enforced governance controls.
          Decisions are rule-based, auditable, and fail-closed.
        </p>

        {/* Live data fields */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Governance Fingerprint Hash */}
          <div className="space-y-1">
            <p className="text-xs text-slate-500 uppercase tracking-wider">
              Governance Fingerprint
            </p>
            <p className="text-sm text-slate-300 font-mono truncate" title={fingerprint?.fingerprint_hash}>
              {fingerprint?.fingerprint_hash ?? 'Unavailable'}
            </p>
          </div>

          {/* Last Audit Bundle ID */}
          <div className="space-y-1">
            <p className="text-xs text-slate-500 uppercase tracking-wider">
              Last Audit Bundle
            </p>
            <p className="text-sm text-slate-300 font-mono">
              {auditBundle?.bundle_id ?? 'Unavailable'}
            </p>
          </div>

          {/* Last Gameday Run Timestamp */}
          <div className="space-y-1">
            <p className="text-xs text-slate-500 uppercase tracking-wider">
              Last Validation Run
            </p>
            <p className="text-sm text-slate-300 font-mono">
              {gameday ? 'Completed' : 'Unavailable'}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
