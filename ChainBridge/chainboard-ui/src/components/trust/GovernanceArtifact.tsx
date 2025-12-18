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

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';
import type { GovernanceFingerprint } from '../../types/trust';

export interface GovernanceArtifactProps {
  fingerprint?: GovernanceFingerprint;
  className?: string;
}

export function GovernanceArtifact({
  fingerprint,
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
      </CardContent>
    </Card>
  );
}
