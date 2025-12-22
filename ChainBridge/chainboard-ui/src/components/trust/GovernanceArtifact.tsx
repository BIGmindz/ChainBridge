/**
 * Governance Artifact — PAC-SONNY-TRUST-MIN-UI-01
 *
 * Literal data only. No interpretation.
 *
 * Fields:
 * - Fingerprint hash
 * - Timestamp
 * - Schema version
 *
 * @see PAC-SONNY-TRUST-MIN-UI-01
 */

import { Link } from 'react-router-dom';

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';
import type { GovernanceFingerprint } from '../../types/trust';

export interface GovernanceArtifactProps {
  fingerprint?: GovernanceFingerprint;
  /** Optional artifact ID for ProofPack navigation */
  artifactId?: string;
  className?: string;
}

export function GovernanceArtifact({
  fingerprint,
  artifactId,
  className,
}: GovernanceArtifactProps): JSX.Element {
  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardContent className="space-y-3">
        <p className="text-xs text-slate-600 uppercase tracking-wider border-b border-slate-800/50 pb-2">
          Governance Fingerprint
        </p>

        <div>
          <p className="text-xs text-slate-600 mb-1">Hash</p>
          <p className="text-sm text-slate-300 font-mono break-all">
            {fingerprint?.fingerprint_hash ?? '—'}
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-600 mb-1">Recorded At (UTC)</p>
          <p className="text-sm text-slate-300 font-mono">
            {fingerprint?.timestamp ?? '—'}
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-600 mb-1">Schema Version</p>
          <p className="text-sm text-slate-300 font-mono">
            {fingerprint?.schema_version ?? '—'}
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
