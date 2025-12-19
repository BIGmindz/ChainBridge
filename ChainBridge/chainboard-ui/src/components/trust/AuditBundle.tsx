/**
 * Audit Bundle — PAC-SONNY-TRUST-MIN-UI-01
 *
 * Literal data only. No interpretation.
 *
 * Fields:
 * - Bundle ID
 * - Hash
 * - Created timestamp
 * - Verification instruction (literal)
 *
 * @see PAC-SONNY-TRUST-MIN-UI-01
 */

import { Link } from 'react-router-dom';

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';
import type { AuditBundleMetadata } from '../../types/trust';

export interface AuditBundleProps {
  bundle?: AuditBundleMetadata;
  /** Optional artifact ID for ProofPack navigation */
  artifactId?: string;
  className?: string;
}

export function AuditBundle({
  bundle,
  artifactId,
  className,
}: AuditBundleProps): JSX.Element {
  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardContent className="space-y-3">
        <p className="text-xs text-slate-600 uppercase tracking-wider border-b border-slate-800/50 pb-2">
          Audit Bundle
        </p>

        <div>
          <p className="text-xs text-slate-600 mb-1">Bundle ID</p>
          <p className="text-sm text-slate-300 font-mono">
            {bundle?.bundle_id ?? '—'}
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-600 mb-1">Hash</p>
          <p className="text-sm text-slate-300 font-mono break-all">
            {bundle?.bundle_hash ?? '—'}
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-600 mb-1">Recorded At (UTC)</p>
          <p className="text-sm text-slate-300 font-mono">
            {bundle?.created_at ?? '—'}
          </p>
        </div>

        <div className="border-t border-slate-800/50 pt-3">
          <p className="text-xs text-slate-600 mb-1">Verification</p>
          <p className="text-xs text-slate-500 font-mono">
            sha256sum proofpacks/audit_bundle.json
          </p>
        </div>

        {artifactId ? (
          <div className="border-t border-slate-800/50 pt-3">
            <Link
              to={`/proof-artifacts/${artifactId}`}
              className="text-xs text-slate-400 hover:text-slate-200 font-mono"
            >
              View Proof →
            </Link>
          </div>
        ) : (
          <div className="border-t border-slate-800/50 pt-3">
            <p className="text-xs text-slate-600 font-mono">No ProofPack linked</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
