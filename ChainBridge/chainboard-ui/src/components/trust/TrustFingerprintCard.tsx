/**
 * Trust Fingerprint Card — PAC-TRUST-CENTER-01
 *
 * Displays system governance fingerprint.
 * Read-only — no controls, no interpretation.
 *
 * CONSTRAINTS:
 * - Display only: hash, timestamp, schema version
 * - Exact copy text as specified
 * - No buttons or controls
 *
 * @see PAC-TRUST-CENTER-01 — Public Trust Center (Read-Only)
 */

import { Fingerprint } from 'lucide-react';

import { classNames } from '../../utils/classNames';
import { Card, CardContent, CardHeader } from '../ui/Card';
import { TrustEmptyState } from './TrustEmptyState';
import type { GovernanceFingerprint } from '../../types/trust';

export interface TrustFingerprintCardProps {
  /** Fingerprint data from governance_fingerprint.json */
  fingerprint?: GovernanceFingerprint;
  /** Optional additional className */
  className?: string;
}

/**
 * Governance fingerprint display card.
 * Shows current governance configuration hash.
 */
export function TrustFingerprintCard({
  fingerprint,
  className,
}: TrustFingerprintCardProps): JSX.Element {
  // Missing data → explicit empty state
  if (!fingerprint) {
    return <TrustEmptyState section="Governance Fingerprint" className={className} />;
  }

  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardHeader className="border-b border-slate-800/50">
        <div className="flex items-center gap-2">
          <Fingerprint className="h-5 w-5 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            System Governance Fingerprint
          </h3>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Fingerprint hash */}
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
            Fingerprint Hash
          </p>
          <p className="text-sm text-slate-300 font-mono break-all">
            {fingerprint.fingerprint_hash}
          </p>
        </div>

        {/* Metadata row */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
              Timestamp
            </p>
            <time
              dateTime={fingerprint.timestamp}
              className="text-sm text-slate-400 font-mono"
            >
              {fingerprint.timestamp}
            </time>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
              Schema Version
            </p>
            <p className="text-sm text-slate-400 font-mono">
              {fingerprint.schema_version}
            </p>
          </div>
        </div>

        {/* Exact copy text — no modification */}
        <p className="text-xs text-slate-500 italic border-t border-slate-800/50 pt-3">
          This fingerprint represents the current governance configuration. Any change produces a new hash.
        </p>
      </CardContent>
    </Card>
  );
}
