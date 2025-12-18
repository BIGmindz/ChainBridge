/**
 * Evidence Artifacts — PAC-SONNY-TRUST-UI-REDUCTION-01
 *
 * Displays audit bundle metadata only.
 * No icons, no adjectives, no interpretation.
 *
 * CONSTRAINTS:
 * - Display: ID, hash, timestamp
 * - No icons implying security/safety
 * - No adjectives
 * - No interpretation
 *
 * Format per PAC:
 *   Artifact: <name>
 *   Source: <file path or test suite>
 *   What this shows: one sentence, factual
 *
 * @see PAC-SONNY-TRUST-UI-REDUCTION-01
 */

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';
import type { AuditBundleMetadata } from '../../types/trust';

export interface EvidenceArtifactsProps {
  /** Audit bundle metadata */
  bundle?: AuditBundleMetadata;
  /** Optional className */
  className?: string;
}

/**
 * Evidence Artifacts section.
 * Displays audit bundle data — no interpretation.
 */
export function EvidenceArtifacts({
  bundle,
  className,
}: EvidenceArtifactsProps): JSX.Element {
  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardContent className="space-y-4">
        {/* Section header — factual format */}
        <div className="border-b border-slate-800/50 pb-3">
          <p className="text-xs text-slate-500 uppercase tracking-wider">
            Artifact
          </p>
          <p className="text-sm text-slate-300">Audit Bundle</p>
        </div>

        {/* Source — file path only, no interpretation */}
        <div className="border-b border-slate-800/50 pb-3">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
            Source
          </p>
          <p className="text-sm text-slate-400 font-mono">
            proofpacks/audit_bundle.json
          </p>
        </div>

        {/* Data fields — no adjectives, no interpretation */}
        <div className="space-y-3 pt-2">
          <div>
            <p className="text-xs text-slate-600 mb-1">Bundle ID</p>
            <p className="text-sm text-slate-300 font-mono">
              {bundle?.bundle_id ?? '—'}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-600 mb-1">Bundle Hash</p>
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
        </div>

        {/* Offline verification instruction */}
        <div className="border-t border-slate-800/50 pt-3">
          <p className="text-xs text-slate-600">
            To verify: compute SHA-256 of bundle contents and compare to hash.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
