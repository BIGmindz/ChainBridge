/**
 * PDO Artifacts — PAC-SONNY-TRUST-HARDEN-01
 *
 * Provenance Decision Objects rendered as first-class evidence.
 * Structure only — no narrative, no summarization.
 *
 * CONSTRAINTS:
 * - Display: PDO ID, input refs, decision ref, outcome ref, recorded timestamp
 * - No expandable prose
 * - No narrative explanation
 * - No icons implying status/quality/health
 * - Read-only
 *
 * @see PAC-SONNY-TRUST-HARDEN-01 — Trust Center Evidence-Only Hardening
 */

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';

/**
 * PDO record structure.
 * Mirrors backend PDO schema — read-only.
 */
export interface PDORecord {
  /** Canonical PDO identifier */
  pdo_id: string;
  /** Input artifact references */
  input_refs: string[];
  /** Decision reference ID */
  decision_ref: string;
  /** Outcome reference ID */
  outcome_ref: string;
  /** ISO 8601 timestamp of PDO creation (UTC) */
  recorded_at: string;
  /** Source system that generated the PDO */
  source_system: 'chainiq' | 'chainpay' | 'oc' | 'occ';
}

export interface PDOArtifactsProps {
  /** Array of PDO records */
  pdos?: PDORecord[];
  /** Optional className */
  className?: string;
}

/**
 * PDO Artifacts section.
 * Renders PDOs as immutable evidence records.
 * Structure only — no interpretation.
 */
export function PDOArtifacts({
  pdos = [],
  className,
}: PDOArtifactsProps): JSX.Element {
  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardContent className="space-y-3">
        <p className="text-xs text-slate-600 uppercase tracking-wider border-b border-slate-800/50 pb-2">
          Provenance Decision Objects
        </p>

        {pdos.length === 0 ? (
          <p className="text-xs text-slate-600 font-mono">
            No PDO records available.
          </p>
        ) : (
          <div className="space-y-4">
            {pdos.map((pdo) => (
              <div
                key={pdo.pdo_id}
                className="border-b border-slate-800/30 pb-3 last:border-b-0 last:pb-0"
              >
                <div className="mb-2">
                  <p className="text-xs text-slate-600 mb-1">PDO ID</p>
                  <p className="text-sm text-slate-300 font-mono break-all">
                    {pdo.pdo_id}
                  </p>
                </div>

                <div className="mb-2">
                  <p className="text-xs text-slate-600 mb-1">Source System</p>
                  <p className="text-sm text-slate-300 font-mono uppercase">
                    {pdo.source_system}
                  </p>
                </div>

                <div className="mb-2">
                  <p className="text-xs text-slate-600 mb-1">Input References</p>
                  {pdo.input_refs.length === 0 ? (
                    <p className="text-sm text-slate-500 font-mono">—</p>
                  ) : (
                    <ul className="space-y-1">
                      {pdo.input_refs.map((ref, idx) => (
                        <li key={idx} className="text-sm text-slate-300 font-mono break-all">
                          {ref}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="mb-2">
                  <p className="text-xs text-slate-600 mb-1">Decision Reference</p>
                  <p className="text-sm text-slate-300 font-mono break-all">
                    {pdo.decision_ref || '—'}
                  </p>
                </div>

                <div className="mb-2">
                  <p className="text-xs text-slate-600 mb-1">Outcome Reference</p>
                  <p className="text-sm text-slate-300 font-mono break-all">
                    {pdo.outcome_ref || '—'}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-600 mb-1">Recorded At (UTC)</p>
                  <p className="text-sm text-slate-300 font-mono">
                    {pdo.recorded_at}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
